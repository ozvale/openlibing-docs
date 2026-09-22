# 260627-feature-ops-report — 向 framework 运营看板上报每日指标

## 需求背景

openlibing-framework 已提供运营看板（`/manage/feature-dashboard/*`），支持：
- 前端看板定义指标（`POST /metrics`）
- 微服务每日上报指标数据（`POST /report`）
- 看板按 day/week/month/year 自行做周期聚合统计

我们服务（computing-resource-workspace）作为运营看板的数据上报方之一，需要：
1. 每天定时调用 framework 的 `/manage/feature-dashboard/report` 接口上报当日指标。
2. 上报的指标 key 必须先在前端看板录入到 `feature_ops_dashboard_metric_config` 表，否则 framework 端会抛 3007 错误。
3. 看板的周/月/年统计由 framework 端在查询时聚合，本服务只负责每日数据上报，不做周期聚合。

## 功能描述

### 第一期（已完成，6/27）
- Feign 客户端方法 `FrameworkClient.reportFeatureOps(...)`。
- `FeatureOpsReportService` + `FeatureOpsReportScheduler`，落地 2 个用户指标：
  - `page_view`：当日 `workspace_env_record` 表 `created_at` 落在窗口内的记录条数。
  - `unique_visitor`：当日 `workspace_env_record` 表 `created_at` 落在窗口内的 `user_id` 去重数。
- `EnvRecordMapper` 的两个聚合查询方法（`countByCreatedTimeRange` / `countDistinctUserIdByCreatedTimeRange`）。
- 配置开关默认关闭，通过 `@Value` 从 Apollo 拉取配置项。

### 本期（6/29 扩展，业务指标）
在已搭好的上报架子基础上，补充 **4 个业务指标**：

| metricKey | metricType | aggregationType | 上报值形态 | 口径 |
|-----------|-----------|-----------------|-----------|------|
| `apply_wait_mins` | business_metric | count | 裸数字（分钟，小数） | `AVG(grant_time - apply_time)`，仅 `grant_time` 非空记录，按 `grant_time` 归属当天 |
| `apply_success_rate` | business_metric | rate | `{metricId, numerator, denominator}` | 分子=`grant_time` 非空数，分母=全部申请数，分子分母同窗口按 `apply_time` 归属当天 |
| `exclusive_usage_mins` | business_metric | count | 裸数字（分钟，小数） | `AVG(release_time - grant_time)`，仅 `release_time` 非空 + `task_type='01'`，按 `release_time` 归属当天 |
| `task_usage_mins` | business_metric | count | 裸数字（分钟，小数） | `AVG(release_time - grant_time)`，仅 `release_time` 非空 + `task_type='02'`，按 `release_time` 归属当天 |

**task_type 含义**：`01` 独占式、`02` 任务式。

### 6/30 调整：IDE 不区分社区

- 移除上报请求中的 `community` 字段（IDE 业务不区分社区）。
- 同步移除 `FeatureOpsReportService` 中的 `@Value("${feature-ops.report.community:openLiBing}")` 注入。
- framework 端 `inferCommunity(null, null)` 返回空字符串，落库时 `community` 列存空字符串；`upsertCommunityFeature` 不执行。
- **副作用**：framework 端幂等去重条件 `isNotBlank(community) && isNotBlank(feature)` 不满足，每次上报都会新增一条记录。当前定时任务每日一次，可接受；如未来出现当日多次触发，需在 service 端自管幂等或恢复 community。

### 6/30 调整：unique_visitor 口径变更（全表累计 UV）

- 指标 key 保持 `unique_visitor` 不变（framework 端 `metric_config` 无需重新注册）。
- 统计口径从"当日 `created_at` 落在窗口内的 `user_id` 去重数"改为"**全表所有记录的 `user_id` 去重数**"（累计 UV）。
- `EnvRecordMapper` 删除 `countDistinctUserIdByCreatedTimeRange(start, end)`，新增 `countDistinctUserIdAll()`，SQL 为 `SELECT COUNT(DISTINCT user_id) FROM workspace_env_record`（无 `WHERE`）。
- 走覆盖索引扫描（`idx_env_user_id`），短期性能无忧；长期数据量到千万级时需考虑缓存/增量计算。
- **语义破坏性提醒**：同名字段下，历史报表曲线（DAU 语义）与未来数据（累计 UV 语义）不可比，需和业务方/dashboard 消费方对齐。

### 本期不做
- 单元测试（Standard 模式不强制，等指标稳定后补）。
- 跨仓改动（不动 framework 仓）。
- framework 端任何接口/表的改造。

## 状态机关键事实（指标口径依据）

详细分析见 design.md §2.3。要点：

| 终态 status | grant_time | release_time | 在各指标中的归属 |
|-------------|-----------|--------------|------------------|
| `success` → `released`（任务式自动释放） | ✅ 有 | ✅ 有 | 入申请时间均值、入成功率分子、入使用时长均值 |
| `success`（独占式，未释放） | ✅ 有 | ❌ 无 | 入申请时间均值、入成功率分子、不入使用时长（release_time 为空） |
| `deploy_failed`（部署失败，不释放） | ❌ 无 | ❌ 无 | 不入申请时间、入成功率分母（失败）、不入使用时长 |
| `install_failed` → `released`（安装失败自动释放） | ✅ 有 | ✅ 有 | 入申请时间均值、入成功率分子（grant 拿到算成功）、入使用时长均值（含自动释放等待，可能偏大，本期接受） |

**核心判定**：`grant_time` 非空 = 资源拿到 = 申请成功；`release_time` 非空 = 有使用时长数据。

## 指标定义（需先在前端看板录入到 `feature_ops_dashboard_metric_config` 表）

| metricKey | metricType | aggregationType | metricName | 计算逻辑 |
|-----------|-----------|-----------------|-----------|---------|
| `page_view` | user_metric | count | 访问量 | `COUNT(*) FROM workspace_env_record WHERE created_at ∈ [dayStart, dayEnd)` |
| `unique_visitor` | user_metric | count | 用户数 | `COUNT(DISTINCT user_id) FROM workspace_env_record WHERE created_at ∈ [dayStart, dayEnd)` |
| `apply_wait_mins` | business_metric | count | 平均申请时间(分) | `AVG(TIMESTAMPDIFF(MINUTE, apply_time, grant_time)) WHERE grant_time IS NOT NULL AND grant_time ∈ [dayStart, dayEnd)` |
| `apply_success_rate` | business_metric | rate | 平均申请成功率 | 分子=`COUNT(*) WHERE grant_time IS NOT NULL AND apply_time ∈ [dayStart, dayEnd)`，分母=`COUNT(*) WHERE apply_time ∈ [dayStart, dayEnd)` |
| `exclusive_usage_mins` | business_metric | count | 独占式平均使用时长(分) | `AVG(TIMESTAMPDIFF(MINUTE, grant_time, release_time)) WHERE release_time IS NOT NULL AND task_type='01' AND release_time ∈ [dayStart, dayEnd)` |
| `task_usage_mins` | business_metric | count | 任务式平均使用时长(分) | `AVG(TIMESTAMPDIFF(MINUTE, grant_time, release_time)) WHERE release_time IS NOT NULL AND task_type='02' AND release_time ∈ [dayStart, dayEnd)` |

> 前端看板录入时 `feature` 与第一期一致，`community` 字段不需要（指标配置只按 feature 维度）。

## 验收标准

### 第一期（已完成）
- [x] workspace 启动后，`feature-ops.report.enabled=false` 时 scheduler 不触发上报。
- [x] `feature-ops.report.enabled=true` 时，scheduler 按 cron 定时触发 `FeatureOpsReportService.report()`。
- [x] `report()` 能正确组装请求并通过 Feign 发出请求。
- [x] `page_view` / `unique_visitor` 两个指标的值来自 `workspace_env_record` 表当日聚合。
- [x] framework 端返回非 200 时，service 端记录 warn 日志，不抛出影响主流程的异常。
- [x] Feign 调用失败（网络/超时）时同样降级为日志，不抛异常。
- [x] `timestamp` 字段传"统计日 23:59:59"。
- [x] 编译通过（`mvn compile`）。

### 本期（6/29 业务指标扩展）
- [ ] 4 个业务指标值来自 `workspace_env_record` 表聚合，时间窗口与归属字段符合上表口径。
- [ ] `apply_success_rate` 上报值为 `{metricId, numerator, denominator}` 结构；其余 3 个为裸数字（小数可解析）。
- [ ] `install_failed` 自动释放后 status=released 的记录被正确纳入各指标（grant_time 非空入分子、release_time 非空入使用时长均值）。
- [ ] `deploy_failed`（无 grant_time）入成功率分母、不入申请时间/使用时长均值。
- [ ] 跨天记录按各自终态时间归属（申请时间按 grant_time、使用时长按 release_time、成功率分子分母同按 apply_time）。
- [ ] 业务指标聚合失败（DB 异常）时降级为 warn 日志，不影响用户指标上报。
- [ ] 编译通过（`mvn compile`）。

## 影响范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/client/FrameworkClient.java` | 已新增（第一期） | `reportFeatureOps` 方法 |
| `business/mapper/EnvRecordMapper.java` | 修改 | 新增 4 个业务指标聚合查询方法 |
| `business/service/dashboard/FeatureOpsReportService.java` | 修改 | 补充 4 个业务指标的组装逻辑，移除 TODO |
| `common/scheduler/FeatureOpsReportScheduler.java` | 已新增（第一期） | 无需改动 |
| `application.yaml` 或 Apollo | 已新增（第一期） | 无需改动 |

## 关键约束

- ~~framework 端按 `(community, feature, 当天)` 做幂等 upsert，同一天多次上报只保留最后一条。~~ **6/30 更新**：本服务不上报 `community`，framework 端 `isNotBlank(community)` 判定为 false，走 insert 分支，每次上报都新增一条记录（无当日去重）。当前定时任务每日一次可接受。
- framework 端要求 `userMetrics` / `businessMetrics` 不能为 null；若某日确实无数据，传空 map `{}`。
- **framework 端当前对 rate 指标的处理**：历史 commit `0c08247d`（6/26）曾要求 rate 上报 `{numerator, denominator}` 对象，但后续 commit `13495409`（6/26 最新）**回滚**为要求所有指标值必须是 Number 或可解析为数字的字符串（[isNumeric](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L529)），rate 类型存库时自动加 `%` 后缀。
- **`{numerator, denominator}` 对象上报风险**：本期 `apply_success_rate` 按既定格式 `{metricId, numerator, denominator}` 上报，**可能被 framework `isNumeric` 校验拒绝**。先按此格式实现，若 framework 报错再决定：①改 framework 校验（恢复 `0c08247d` 逻辑）②退化为传裸数字（牺牲月均聚合准确性）。前端 `beta_gamma` 分支已支持解析 `{numerator, denominator}` 对象（[utils.ts resolveMetricNumeric](file:///d:/Code/Java/openlibing/openlibing-web/apps/web-openlibing/src/views/manageCenter/FeatureDashboard/utils.ts#L46-L60)）。
- count 类指标**不限制小数**：framework `isNumeric` 用 `Double.parseDouble`，平均时长传小数（如 `2.7`）可正常通过。
- 指标值必须是数字（Number 或可解析为数字的字符串）或 rate 类型的 `{numerator, denominator}` 对象，不能传字符串文案。
- **时区对齐**：framework 端 `timestamp` 字段不做时区转换，按 `LocalDateTime` 直接解析。本服务传"统计日 23:59:59"确保归到统计日。详见 design.md §时区对齐。
