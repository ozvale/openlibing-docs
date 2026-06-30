# 260627-feature-ops-report — 技术设计

## 1. 需求概述

为 computing-resource-workspace 增加每日定时向 openlibing-framework 运营看板（`/manage/feature-dashboard/report`）上报指标数据的能力。

**本期定位**：搭架子 + 落地 2 个用户指标（`page_view` / `unique_visitor`）。业务指标暂留 TODO。

## 2. 现状分析

### 2.1 framework 端能力（已实现，不改动）

framework 已提供 [FeatureOpsDashboardController](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/controller/FeatureOpsDashboardController.java) 的 `/report` 接口，关键行为：

| 维度 | 现状 |
|------|------|
| 鉴权 | controller 上无 `@RequireAdmin` 等注解，与 `/internal-server/*` 一致，微服务可直接调 |
| 幂等 | 按 `(community, feature, 当天 [dayStart, dayEnd))` upsert，同日多次上报只保留最后一条 |
| 指标校验 | body 中每个 metricKey 必须先在 `feature_ops_dashboard_metric_config` 表录入，否则 3007 错误 |
| 值校验 | 指标值必须是 Number 或可解析为数字的字符串 |
| rate 指标 | **6/29 调研结论**：framework 当前 `develop_202606_iter2` 要求所有指标值必须是 Number 或可解析为数字的字符串（[isNumeric L529](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L529)），rate 类型存库时自动加 `%` 后缀（[serializeMetrics L518](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L518)）。历史 commit `0c08247d`（6/26）曾要求 rate 上报 `{numerator, denominator}` 对象，但 commit `13495409`（6/26 最新）回滚为裸数字。周/月/年聚合用算术平均（[calculateMetricAverages L638](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L638)），月均会失真。前端 `beta_gamma` 分支已支持解析 `{numerator, denominator}` 对象（[utils.ts](file:///d:/Code/Java/openlibing/openlibing-web/apps/web-openlibing/src/views/manageCenter/FeatureDashboard/utils.ts#L46-L60)），但 framework 端对象上报通路目前关闭 |
| 周期聚合 | framework 端在查询时按 day/week/month/year 聚合，上报方不用关心 |
| 副作用 | 上报会顺带 upsert `feature_ops_dashboard_community_feature` 关联状态为 `active` |

> **6/30 调整说明**：framework 端代码的客观行为如上表所述。本服务 6/30 起不上报 `community` 字段，导致：
> 1. 幂等去重条件 `isNotBlank(community) && isNotBlank(feature)` 不满足 → 走 insert 分支，每次上报新增一条记录（无当日 upsert）。
> 2. `upsertCommunityFeature` 不执行（同样被 `isNotBlank(community)` 拦截）。
>
> 当前定时任务每日一次，可接受无幂等。如未来出现当日多次触发（手动重试/多实例），需在 service 端自管幂等或恢复 community 上报。

### 2.2 framework 端 timestamp 解析逻辑（关键）

[parseTimestamp](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L208-L216) 实现：

```java
private LocalDateTime parseTimestamp(String timestamp) {
    if (StringUtils.isBlank(timestamp)) {
        return LocalDateTime.now(ZoneOffset.UTC);
    }
    try {
        return LocalDateTime.parse(timestamp.replace("Z", ""), DateTimeFormatter.ISO_LOCAL_DATE_TIME);
    } catch (Exception e) {
        return LocalDateTime.now(ZoneOffset.UTC);
    }
}
```

**关键点**：framework 拿到 timestamp 字符串后，直接按 `LocalDateTime` 解析，**不做时区转换**。`ZoneOffset.UTC` 只在 timestamp 为空/解析失败时的 fallback。

后续 [reportedAt.toLocalDate()](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L81) 取日期部分用于幂等去重，[resolveTimeRange](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L554-L588) 查询时间范围也是无时区 LocalDateTime 比较。**全程无时区干扰**，传什么字符串就存什么、查什么。

### 2.3 workspace 端现状

- 已有 [FrameworkClient](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/client/FrameworkClient.java) Feign 客户端，已调通 `/internal-server/get-user` 和 `/internal-server/add/microservices/log`
- 已有 [application-local.yaml](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/resources/application-local.yaml) 配置 `openlibing-framework.url: https://localhost:8071` + `skip-ssl: true`
- `@EnableScheduling` 已在 [AsyncConfig](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/common/config/AsyncConfig.java#L25) 开启
- scheduler 目录 `common/scheduler/` 下已有 `EnvStatusScheduler` / `ModelHealthScheduler` / `ThreadPoolMonitor`，统一用 `@Value` 拉 Apollo 配置，不引入 Properties 类
- `workspace_env_record` 表已有 [EnvRecord](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/entity/EnvRecord.java) 实体和 [EnvRecordMapper](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/mapper/EnvRecordMapper.java)，字段含 `userId` / `createdAt`

### 2.4 现有调用 framework 的两种风格

| 风格 | 客户端 | 端点 | 适用场景 |
|------|-------|------|---------|
| Feign 内部调用 | `FrameworkClient` | `/internal-server/*` | 微服务互调，干净无 session |
| WebClient 直调 | `OpenlibingAuthInterceptor` | `/user/get-user-info` | 借浏览器 session 透传 cookie |

**本需求选 Feign 风格**：定时任务无用户 session，不能透传 cookie；且 `/manage/feature-dashboard/report` 与 `/internal-server/*` 同属 framework controller 体系，无额外鉴权拦截。

### 2.5 workspace_env_record 状态机与时间字段（6/29 业务指标口径依据）

本期 4 个业务指标依赖 `apply_time` / `grant_time` / `release_time` 三个时间字段和 `status` / `task_type` 两个状态字段，需先梳理状态机确定口径。

#### 状态流转（基于 [EnvStatuses](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/common/constant/EnvStatuses.java) + [EnvStatusTransitionServiceImpl](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/service/env/impl/EnvStatusTransitionServiceImpl.java) + [EnvReleaseServiceImpl](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/service/env/impl/EnvReleaseServiceImpl.java)）

```
queuing → allocating → deploying → installing → success
                                              └→ install_failed → (自动释放) → releasing → released
        └→ deploy_failed (终态，不释放)
```

#### 关键时间字段设置点

| 字段 | 设置点 | 设置条件 |
|------|--------|---------|
| `apply_time` | 创建环境时 | 申请即设 |
| `grant_time` | [EnvStatusTransitionServiceImpl L151-153](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/service/env/impl/EnvStatusTransitionServiceImpl.java#L151-L153) | 解析到 nodeIp 时设（部署成功，拿到节点） |
| `release_time` | [EnvReleaseServiceImpl.completeRelease L138-141](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/service/env/impl/EnvReleaseServiceImpl.java#L138-L141) | 仅释放完成（status=released）时设，且 `updated_at = release_time`（同变量赋值） |

#### 各终态记录的字段填充情况

| 终态 status | 触发场景 | grant_time | release_time | fail_type |
|-------------|---------|-----------|--------------|-----------|
| `success` | 安装完成，独占式环境未释放 | ✅ 有 | ❌ 无（未释放） | null |
| `released`（从 success） | 任务式任务执行完自动释放，或独占式用户手动释放 | ✅ 有 | ✅ 有 | null |
| `released`（从 install_failed） | 安装失败自动释放（[handleInstallFailed](file:///d:/Code/Java/openlibing/computing-resource-workspace/src/main/java/com/workspace/business/service/env/impl/EnvStatusTransitionServiceImpl.java#L234-L242) 先设 install_failed 再调 doRelease） | ✅ 有 | ✅ 有 | HiDevLab 返回的失败原因 |
| `deploy_failed` | HiDevLab 返回 FAILED/FAILED_RELEASING，或 waiting_release 处理失败 | ❌ 无（没拿到节点） | ❌ 无（不释放） | HiDevLab 返回的失败原因 |
| `release_failed` | 释放流程失败 | ✅ 有 | ❌ 无 | HiDevLab 返回的失败原因 |

**关键结论**：
1. **`install_failed` 在表里查不到**——`handleInstallFailed` 先短暂设 `install_failed`，紧接着调 `doRelease` → `releasing` → 最终 `completeRelease` 把 status 覆盖成 `released`。表里只能靠 `fail_type` 字段回溯安装失败的记录。
2. **`deploy_failed` 状态保持不变**，不释放，`grant_time=null`、`release_time=null`。
3. **`release_time` 与 `updated_at` 在 released 记录上完全一致**（同一 `LocalDateTime.now()` 赋值），但对 `deploy_failed` 不一致（`release_time=null`，`updated_at`=失败时间）。

#### 指标口径推导

基于上表，4 个业务指标的口径：

| 指标 | 分子（参与计算的记录） | 分母/窗口 | 归属时间字段 | 边界处理 |
|------|---------------------|----------|-------------|---------|
| `apply_wait_mins` | `grant_time` 非空的记录（含 success/released/install_failed→released，不含 deploy_failed） | AVG(grant_time - apply_time) | `grant_time` | deploy_failed 无 grant_time，不参与 |
| `apply_success_rate` | 分子=`grant_time` 非空数（资源拿到=申请成功），分母=全部申请数（含 deploy_failed） | 分子 COUNT / 分母 COUNT | **分子分母同按 `apply_time`**（保证同批） | deploy_failed 入分母不入分子 |
| `exclusive_usage_mins` | `task_type='01'` + `release_time` 非空 | AVG(release_time - grant_time) | `release_time` | success 未释放的独占式不入（release_time 为空） |
| `task_usage_mins` | `task_type='02'` + `release_time` 非空 | AVG(release_time - grant_time) | `release_time` | 含 install_failed→released（grant→release 含自动释放等待，可能偏大，本期接受） |

**为何 `apply_success_rate` 用 `grant_time` 非空而非 `status=success`**：任务式环境执行完会自动释放，最终 status=released；独占式可能长期 success 未释放。按 status 取值会漏算。用 `grant_time` 非空 = 资源拿到 = 申请成功，更准确反映"申请是否成功拿到资源"。

**为何 `apply_success_rate` 分子分母都按 `apply_time` 归属**：比率要求分子分母来自同一批申请才有意义。若分子按 grant_time 归属当天、分母按 apply_time 归属当天，跨天记录会导致分子分母错配，比率失真。统一按 apply_time 归属："当天申请的记录里，最终有多少拿到了资源"。daily T+1 上报时当天申请基本已终态，不影响判断。

**为何 `install_failed→released` 计入使用时长均值**：install_failed 自动释放后 release_time 有值，符合"release_time 非空"条件。其 grant→release 时长含"安装失败后自动释放等待"时间，可能使 `task_usage_mins` 偏大。但 install_failed 占比通常很小，对 AVG 影响有限，本期接受不额外过滤。如后续发现偏差过大，可在 SQL 加 `fail_type IS NULL` 过滤。

## 3. 设计方案

### 3.1 整体结构

```
common/scheduler/FeatureOpsReportScheduler   ← 定时触发（cron + 开关）
        │
        ▼
business/service/dashboard/FeatureOpsReportService   ← 组装 body + 异常降级
        │  ├─ 计算 statDate = today + statDayOffset
        │  ├─ 计算 dayStart/dayEnd 时间窗口
        │  ├─ 调 EnvRecordMapper 查 page_view / unique_visitor（按 created_at）
        │  ├─ 调 EnvRecordMapper 查 4 个业务指标（各自归属时间字段，见 §3.2）
        │  └─ 组装 userMetrics + businessMetrics + timestamp
        │
        ▼
business/client/FrameworkClient#reportFeatureOps   ← Feign 调用
        │
        ▼
framework: POST /manage/feature-dashboard/report
```

### 3.2 指标计算

#### 用户指标（第一期已落地，unique_visitor 6/30 调整）

| metricKey | 计算逻辑 | 数据源 | 归属字段 |
|-----------|---------|--------|---------|
| `page_view` | `COUNT(*)` 当日窗口内记录条数 | `workspace_env_record.created_at` | `created_at` |
| `unique_visitor` | `COUNT(DISTINCT user_id)` **全表累计去重用户数**（6/30 调整，不再按时间窗） | `workspace_env_record.user_id` | 无（全表） |

**统计口径**：不分成功失败，所有记录都算。`page_view` 按当日窗口，`unique_visitor` 6/30 起改为全表累计 UV（语义从 DAU 变为累计 UV，指标 key 不变）。

**SQL 模板**（`EnvRecordMapper` 已有）：

```java
// page_view：当日窗口内记录条数
@Select("SELECT COUNT(*) FROM workspace_env_record "
        + "WHERE created_at >= #{startTime} AND created_at < #{endTime}")
long countByCreatedTimeRange(@Param("startTime") LocalDateTime startTime,
                             @Param("endTime") LocalDateTime endTime);

// unique_visitor：全表累计去重用户数（6/30 调整，原 countDistinctUserIdByCreatedTimeRange 已删除）
// 走 idx_env_user_id 覆盖索引扫描，O(N) 但常数小；千万级数据量需考虑缓存/增量计算
@Select("SELECT COUNT(DISTINCT user_id) FROM workspace_env_record")
long countDistinctUserIdAll();
```

> **6/30 口径变更说明**：`unique_visitor` 原实现按 `created_at` 时间窗去重（DAU 语义），6/30 起改为全表去重（累计 UV 语义）。指标 key 保持不变，framework 端 `metric_config` 无需重新注册，但同名字段下历史报表曲线与未来数据不可比，需和业务方对齐。`buildUserMetrics` 方法签名保留 `dayStart/dayEnd` 参数（仍被 `page_view` 使用）。

#### 业务指标（本期新增，6/29）

| metricKey | 计算逻辑 | 归属字段 | task_type |
|-----------|---------|---------|-----------|
| `apply_wait_mins` | `AVG(TIMESTAMPDIFF(MINUTE, apply_time, grant_time))` | `grant_time` | 不分 |
| `apply_success_rate` | 分子=`COUNT(*) WHERE grant_time IS NOT NULL`，分母=`COUNT(*)` | `apply_time`（分子分母同窗口） | 不分 |
| `exclusive_usage_mins` | `AVG(TIMESTAMPDIFF(MINUTE, grant_time, release_time))` | `release_time` | `01` |
| `task_usage_mins` | `AVG(TIMESTAMPDIFF(MINUTE, grant_time, release_time))` | `release_time` | `02` |

**SQL 模板**（在 `EnvRecordMapper` 新增）：

```java
// apply_wait_mins：按 grant_time 归属，仅 grant_time 非空
@Select("SELECT AVG(TIMESTAMPDIFF(MINUTE, apply_time, grant_time)) "
        + "FROM workspace_env_record "
        + "WHERE grant_time IS NOT NULL AND grant_time >= #{startTime} AND grant_time < #{endTime}")
Double avgApplyWaitMinutes(@Param("startTime") LocalDateTime startTime,
                           @Param("endTime") LocalDateTime endTime);

// apply_success_rate 分子：按 apply_time 归属，grant_time 非空
@Select("SELECT COUNT(*) FROM workspace_env_record "
        + "WHERE grant_time IS NOT NULL AND apply_time >= #{startTime} AND apply_time < #{endTime}")
long countGrantedByApplyTimeRange(@Param("startTime") LocalDateTime startTime,
                                  @Param("endTime") LocalDateTime endTime);

// apply_success_rate 分母：按 apply_time 归属，全部记录
@Select("SELECT COUNT(*) FROM workspace_env_record "
        + "WHERE apply_time >= #{startTime} AND apply_time < #{endTime}")
long countByApplyTimeRange(@Param("startTime") LocalDateTime startTime,
                           @Param("endTime") LocalDateTime endTime);

// exclusive_usage_mins / task_usage_mins：按 release_time 归属，release_time 非空 + task_type
@Select("SELECT AVG(TIMESTAMPDIFF(MINUTE, grant_time, release_time)) "
        + "FROM workspace_env_record "
        + "WHERE release_time IS NOT NULL AND task_type = #{taskType} "
        + "AND release_time >= #{startTime} AND release_time < #{endTime}")
Double avgUsageMinutesByTaskType(@Param("taskType") String taskType,
                                 @Param("startTime") LocalDateTime startTime,
                                 @Param("endTime") LocalDateTime endTime);
```

**设计决策**：
- `AVG` 返回 `Double`（可能为 null，当窗口内无符合条件的记录时），service 层判 null 后决定是否上报该 key。
- `TIMESTAMPDIFF(MINUTE, ...)` 返回整数分钟，`AVG` 后变 `Double`（如 `2.5`）。framework `isNumeric` 用 `Double.parseDouble` 可解析小数，不限制。
- `apply_success_rate` 分两个 COUNT 查询而非一次 SQL 算比率：service 层组装 `{numerator, denominator}` 上报，前端自行计算百分比，符合 framework rate 指标的对象格式。
- `exclusive_usage_mins` / `task_usage_mins` 共用一个带 `taskType` 参数的查询方法，避免重复 SQL。

### 3.3 时区对齐（强制）

framework 端 `timestamp` 字段不做时区转换（见 §2.2），本服务需保证：

| 项 | 取值 | 说明 |
|----|------|------|
| 上报 `timestamp` 字段 | `统计日T23:59:59`，格式 `yyyy-MM-dd'T'HH:mm:ss` | 确保归到统计日，凌晨任务（0:00-2:00 跑前一天数据）不会跨日 |
| DB 查询窗口 | `[统计日 00:00, 统计日+1 00:00)` | DB 中 `created_at` 存的是本地时间（北京时间），与 timestamp 归属日完全对齐 |
| `stat-day-offset` 配置项 | 默认 `-1` | 定时任务在北京凌晨跑，统计前一天数据 |

**为什么不传 UTC 0 点**：framework 用 `LocalDateTime` 解析，不识别时区标记，传 `2026-06-25T00:00:00Z` 去掉 Z 后也是 `2026-06-25 00:00:00`，效果一样。但传 23:59:59 语义更直观——"这是 6/25 末尾的数据"，且对边界比较（`<=` vs `<`）更安全。

**统计日计算**：

```java
// 定时任务凌晨跑，统计前一天
LocalDate statDate = LocalDate.now().plusDays(statDayOffset);  // statDayOffset 默认 -1
LocalDateTime dayStart = statDate.atStartOfDay();               // 6/25 00:00
LocalDateTime dayEnd = statDate.plusDays(1).atStartOfDay();     // 6/26 00:00
String timestamp = statDate.atTime(23, 59, 59)
    .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);             // "2026-06-25T23:59:59"
```

### 3.4 请求/响应载体设计

**不新建 DTO 文件**（团队反馈 DTO 过多）。请求用 `Map<String, Object>` 组装，响应用 `DataResult<Map<String, Object>>` 接收，只取 `reportId` 记日志。

请求字段与 framework 端 [DashboardReportRequestDTO](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardReportRequestDTO.java) 严格对齐：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `community` | String | 否 | **6/30 起不上报**（IDE 不区分社区）。framework 端 `inferCommunity(null, null)` 返回空字符串，落库 `community` 列存空字符串 |
| `repo` | String | 否 | 代码仓，本服务不上报 |
| `feature` | String | 是 | 特性名，默认 `IDE插件` |
| `userMetrics` | Map<String, Object> | 是 | 用户指标，不能为 null |
| `businessMetrics` | Map<String, Object> | 是 | 业务指标，不能为 null |
| `timestamp` | String | 否 | ISO 8601，本服务传"统计日 23:59:59" |
| `notInvolved` | Boolean | 否 | 默认 false |

**设计决策**：
- 用 `Map<String, Object>` 而非独立 DTO：team 反馈 DTO 过多，且本请求字段简单、一次性使用，独立 DTO 性价比低。
- 不复用 framework 端的 DTO 类：跨模块依赖会引入 `openlibing-framework` 业务包，违反微服务边界。
- 响应只取 `reportId` 记日志，用 `DataResult<Map<String, Object>>` 接收够用。
- 字段名/类型严格对齐 framework 端，序列化后 JSON 与 framework DTO 完全一致。

### 3.5 Feign 客户端扩展

```java
@PostMapping("/manage/feature-dashboard/report")
DataResult<Map<String, Object>> reportFeatureOps(@RequestBody Map<String, Object> request);
```

**设计决策**：
- 路径写完整 `/manage/feature-dashboard/report`，与现有 `getUserByPlatform` 调 `/internal-server/get-user` 风格一致。
- 复用 `DataResult<T>` 作为响应包装，与现有 `getUserByPlatform` / `addMicroservicesLog` 一致。
- Feign 异常由 service 层捕获处理。

### 3.6 Service 设计

```java
@Slf4j
@Service
public class FeatureOpsReportService {
    private static final DateTimeFormatter ISO_LOCAL_DATE_TIME = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private static final String METRIC_KEY_PAGE_VIEW = "page_view";
    private static final String METRIC_KEY_UNIQUE_VISITOR = "unique_visitor";
    private static final String METRIC_KEY_APPLY_WAIT_MINS = "apply_wait_mins";
    private static final String METRIC_KEY_APPLY_SUCCESS_RATE = "apply_success_rate";
    private static final String METRIC_KEY_EXCLUSIVE_USAGE_MINS = "exclusive_usage_mins";
    private static final String METRIC_KEY_TASK_USAGE_MINS = "task_usage_mins";

    private static final String TASK_TYPE_EXCLUSIVE = "01"; // 独占式
    private static final String TASK_TYPE_TASK = "02";      // 任务式

    @Value("${feature-ops.report.community:openLiBing}")
    private String community;  // 6/30 移除：IDE 不区分社区，不再注入此字段

    @Value("${feature-ops.report.feature:IDE插件}")
    private String feature;

    @Value("${feature-ops.report.stat-day-offset:-1}")
    private int statDayOffset;

    @Autowired
    private FrameworkClient frameworkClient;

    @Autowired
    private EnvRecordMapper envRecordMapper;

    public void report() {
        // 1. 计算统计日和时间窗口
        LocalDate statDate = LocalDate.now().plusDays(statDayOffset);
        LocalDateTime dayStart = statDate.atStartOfDay();
        LocalDateTime dayEnd = statDate.plusDays(1).atStartOfDay();
        String timestamp = statDate.atTime(23, 59, 59).format(ISO_LOCAL_DATE_TIME);

        // 2. 查 DB 聚合指标（DB 异常降级为 warn，整体 return）
        Map<String, Object> userMetrics;
        Map<String, Object> businessMetrics;
        try {
            userMetrics = buildUserMetrics(dayStart, dayEnd);
            businessMetrics = buildBusinessMetrics(dayStart, dayEnd);
        } catch (DataAccessException e) {
            log.warn("[FeatureOpsReport] DB 查询失败, statDate={}, err={}", statDate, e.getMessage());
            return;
        }

        // 3. 组装请求
        Map<String, Object> request = new HashMap<>();
        // 6/30 移除：IDE 不区分社区，不上报 community 字段
        // request.put("community", community);
        request.put("feature", feature);
        request.put("userMetrics", userMetrics);
        request.put("businessMetrics", businessMetrics);
        request.put("timestamp", timestamp);

        log.info("[FeatureOpsReport] 准备上报, statDate={}, userMetrics={}, businessMetrics={}",
            statDate, userMetrics, businessMetrics);

        // 4. 调 Feign + 异常降级
        try {
            DataResult<Map<String, Object>> result = frameworkClient.reportFeatureOps(request);
            if (result == null || result.getCode() != 200) {
                log.warn("[FeatureOpsReport] 上报失败, statDate={}, code={}, msg={}",
                    statDate,
                    result == null ? null : result.getCode(),
                    result == null ? null : result.getMsg());
                return;
            }
            Map<String, Object> data = result.getData();
            log.info("[FeatureOpsReport] 上报成功, statDate={}, reportId={}",
                statDate, data == null ? null : data.get("reportId"));
        } catch (FeignException e) {
            log.warn("[FeatureOpsReport] 调用 framework 异常, statDate={}, err={}",
                statDate, e.getMessage());
        }
    }

    private Map<String, Object> buildUserMetrics(LocalDateTime dayStart, LocalDateTime dayEnd) {
        Map<String, Object> userMetrics = new HashMap<>();
        userMetrics.put(METRIC_KEY_PAGE_VIEW, envRecordMapper.countByCreatedTimeRange(dayStart, dayEnd));
        userMetrics.put(METRIC_KEY_UNIQUE_VISITOR,
            envRecordMapper.countDistinctUserIdByCreatedTimeRange(dayStart, dayEnd));
        return userMetrics;
    }

    private Map<String, Object> buildBusinessMetrics(LocalDateTime dayStart, LocalDateTime dayEnd) {
        Map<String, Object> businessMetrics = new HashMap<>();

        // apply_wait_mins：按 grant_time 归属，可能为 null（当日无 grant 记录）
        Double applyWaitMins = envRecordMapper.avgApplyWaitMinutes(dayStart, dayEnd);
        if (applyWaitMins != null) {
            businessMetrics.put(METRIC_KEY_APPLY_WAIT_MINS, applyWaitMins);
        }

        // apply_success_rate：分子分母同按 apply_time 归属
        long granted = envRecordMapper.countGrantedByApplyTimeRange(dayStart, dayEnd);
        long total = envRecordMapper.countByApplyTimeRange(dayStart, dayEnd);
        Map<String, Object> rateValue = new HashMap<>();
        rateValue.put("numerator", granted);
        rateValue.put("denominator", total);
        businessMetrics.put(METRIC_KEY_APPLY_SUCCESS_RATE, rateValue);

        // exclusive_usage_mins / task_usage_mins：按 release_time 归属 + task_type
        Double exclusiveUsageMins = envRecordMapper.avgUsageMinutesByTaskType(TASK_TYPE_EXCLUSIVE, dayStart, dayEnd);
        if (exclusiveUsageMins != null) {
            businessMetrics.put(METRIC_KEY_EXCLUSIVE_USAGE_MINS, exclusiveUsageMins);
        }
        Double taskUsageMins = envRecordMapper.avgUsageMinutesByTaskType(TASK_TYPE_TASK, dayStart, dayEnd);
        if (taskUsageMins != null) {
            businessMetrics.put(METRIC_KEY_TASK_USAGE_MINS, taskUsageMins);
        }

        return businessMetrics;
    }
}
```

**设计决策**：
- **异常降级**：定时任务不能因上报失败拖垮服务，所有异常（含 Feign 异常 + framework 返回非 200 + DB 查询异常）都降级为 warn 日志。
- **不抛业务异常**：上游 scheduler 不需要做 try-catch，service 内部完全吞掉异常。
- **DB 查询包在同一个 try-catch**：用户指标和业务指标一起查，任一失败则整体不上报（保证同一天数据一致性，避免部分上报）。
- **`apply_success_rate` 始终上报**：即使分母为 0（当日无申请），也传 `{numerator:0, denominator:0}`，前端处理除零。其余 3 个 count 指标当 AVG 为 null（窗口内无符合条件记录）时**不上报该 key**，避免传 null 被 framework `isNumeric` 拒绝。
- **`apply_success_rate` 不带 `metricId` 字段**：用户给的示例含 `metricId`，但 metricId 是前端看板配置表的主键，workspace 侧不知道。先按 `{numerator, denominator}` 上报，若 framework 或前端必须要 metricId 再补（需先查 framework metric_config 表反查，复杂度上升）。
- **community/feature/statDayOffset 用 `@Value` 注入**：与 `ModelHealthScheduler` 风格一致，从 Apollo 拉取，不在代码里硬编码。
- **timestamp 显式传**：传"统计日 23:59:59"，确保归到统计日。详见 §3.3 时区对齐。
- **notInvolved 不设**：本服务是 active 状态，不是 not_involve。

### 3.7 Scheduler 设计

```java
@Slf4j
@Component
public class FeatureOpsReportScheduler {

    @Value("${feature-ops.report.enabled:false}")
    private boolean enabled;

    @Autowired
    private FeatureOpsReportService featureOpsReportService;

    @Scheduled(cron = "${feature-ops.report.cron:0 0 2 * * ?}")
    public void reportDaily() {
        if (!enabled) {
            return;
        }
        log.info("[FeatureOpsReport] 定时上报任务触发");
        featureOpsReportService.report();
    }
}
```

**设计决策**：
- **默认关闭**：`enabled` 默认 `false`。前端看板录入指标 key 之前，开启会被 3007 拒绝。
- **cron 默认每天凌晨 2 点**：`0 0 2 * * ?`。配合 `stat-day-offset=-1`，统计前一天数据。Apollo 可动态调整。
- **不用分布式锁**：~~framework 端已做 `(community, feature, 当天)` 幂等 upsert，多实例并发上报只保留最后一条，不需要在 workspace 侧加锁。~~ **6/30 调整**：本服务不上报 `community`，framework 端走 insert 分支无幂等。当前定时任务每日一次且单实例，可接受；如未来多实例部署，需在 service 端自管幂等（如用 `report_id = UUID(community+feature+statDate)` 或在 workspace 侧加 Redis 锁）。
- **开关检查在方法内**：而不是 `@ConditionalOnProperty`。后者会在启动时决定是否注册 bean，无法通过 Apollo 动态开关；方法内检查支持运行时切换。

### 3.8 配置设计

在 `application.yaml` 末尾追加：

```yaml
# 运营看板数据上报配置
feature-ops:
  report:
    # 总开关，默认关闭，等前端看板录入指标 key 后通过 Apollo 开启
    enabled: false
    # 每日上报 cron，默认凌晨 2 点
    cron: "0 0 2 * * ?"
    # 社区名（必须与 Apollo dashboard.matrix.communities 中的某项一致）
    # 6/30 起停用：IDE 不区分社区，不上报 community 字段。保留配置项仅为兼容历史，读取后不使用
    community: openLiBing
    # 特性名（必须与 Apollo dashboard.matrix.features 中的某项一致）
    feature: 数字化运营看板
    # 统计日偏移量，默认 -1（统计前一天），凌晨任务配合使用
    stat-day-offset: -1
```

**设计决策**：
- 配置项命名 `feature-ops.report.*`，与现有 `maas.gateway.*` 风格一致（小写连字符 + 层级）。
- 全部带默认值，本地起服务不配 Apollo 也能跑。
- `community` / `feature` 默认值取 Apollo `dashboard.matrix.features` 默认列表中的项（`openLiBing` / `数字化运营看板`），避免默认值与 framework 端配置不一致导致 3007。
- `stat-day-offset` 默认 `-1`，配合凌晨 2 点 cron 统计前一天数据。
- **6/30 调整**：`community` 配置项保留但代码不再注入使用，对应 `@Value` 字段已删除。后续可在 application.yaml 清理该项。

## 4. 数据流

```
每天 02:00
   │
   ▼
FeatureOpsReportScheduler.reportDaily()
   │  enabled=true 才继续
   ▼
FeatureOpsReportService.report()
   │  1. statDate = today + (-1) = 昨天
   │  2. dayStart = 昨天 00:00, dayEnd = 今天 00:00
   │  3. timestamp = "昨天T23:59:59"
   │  4. 用户指标（按 created_at 窗口）：
   │     - pageView = COUNT(*)
   │     - uniqueVisitor = COUNT(DISTINCT user_id)
   │  5. 业务指标（各自归属字段，见 §3.2）：
   │     - apply_wait_mins = AVG(grant_time - apply_time) WHERE grant_time ∈ [dayStart, dayEnd)
   │     - apply_success_rate = {numerator: COUNT(grant_time 非空), denominator: COUNT(*)} WHERE apply_time ∈ [dayStart, dayEnd)
   │     - exclusive_usage_mins = AVG(release_time - grant_time) WHERE task_type='01' AND release_time ∈ [dayStart, dayEnd)
   │     - task_usage_mins = AVG(release_time - grant_time) WHERE task_type='02' AND release_time ∈ [dayStart, dayEnd)
   │  6. 组装 request (community/feature/userMetrics/businessMetrics/timestamp)
   ▼
FrameworkClient.reportFeatureOps(request)
   │  POST https://localhost:8071/manage/feature-dashboard/report
   ▼
framework: FeatureOpsDashboardController.report()
   │  1. parseTimestamp(timestamp) → 昨天 23:59:59 (LocalDateTime, 无时区)
   │  2. 推断 community（已传则用）
   │  3. validateMetricKeys（查 metric_config 表，6 个 metricKey 必须已配置）
   │  4. validateMetricValues（值必须是数字；apply_success_rate 传 {numerator,denominator} 对象可能被 isNumeric 拒绝，见 §7 决策 12）
   │  5. 按 (community, feature, 昨天 [00:00, 次日 00:00)) upsert report
   │  6. upsert community_feature 关联状态为 active
   ▼
返回 DataResult<DashboardReportData>
   │
   ▼
service 检查 code != 200 → warn 日志
service 检查 code == 200 → info 日志（含 statDate/reportId）
service 捕获 Feign/DB 异常 → warn 日志
```

## 5. 异常与降级

| 异常场景 | 处理 | 用户感知 |
|---------|------|---------|
| `enabled=false` | scheduler 直接 return | 无 |
| DB 查询失败（连接/超时） | warn 日志记 statDate + err，不调 framework | 看板当日无数据 |
| framework 返回 code != 200（如 3007 指标 key 未配置） | warn 日志记 statDate + code + msg | 看板当日无数据 |
| Feign 网络异常 / 超时 | warn 日志记 statDate + err | 看板当日无数据 |
| framework 反序列化失败 | warn 日志记 statDate + err | 看板当日无数据 |

**关键原则**：所有异常都不向上抛，scheduler 永远成功。运营看板是辅助功能，不能影响主业务。

## 6. 涉及文件清单

### 6.1 新增文件（第一期已完成）

| 文件 | 说明 |
|------|------|
| `business/service/dashboard/FeatureOpsReportService.java` | 上报 service（第一期已建，本期扩展业务指标组装） |
| `common/scheduler/FeatureOpsReportScheduler.java` | 定时任务 |

### 6.2 修改文件

| 文件 | 改动说明 |
|------|---------|
| `business/client/FrameworkClient.java` | 第一期已新增 `reportFeatureOps` 方法，本期不动 |
| `business/mapper/EnvRecordMapper.java` | 本期新增 4 个业务指标聚合方法：`avgApplyWaitMinutes` / `countGrantedByApplyTimeRange` / `countByApplyTimeRange` / `avgUsageMinutesByTaskType` |
| `business/service/dashboard/FeatureOpsReportService.java` | 本期扩展：移除 TODO，新增 `buildBusinessMetrics` 方法组装 4 个业务指标 |
| `application.yaml` 或 Apollo | 第一期已新增 `feature-ops.report.*`，本期不动 |

### 6.3 不修改

- `application-local.yaml`：`openlibing-framework.url` / `skip-ssl` 已配好，不动
- `AsyncConfig.java`：`@EnableScheduling` 已开，不动
- `RedisConfig.java`：工作区已有无关改动，不动
- framework 仓：本期不涉及
- 前端仓：本期不涉及（前端 `beta_gamma` 分支已支持 `{numerator, denominator}` 解析）

## 7. 关键决策记录

| # | 决策 | 原因 |
|---|------|------|
| 1 | 用 Feign 而非 WebClient | 定时任务无 session，Feign 风格与现有 `FrameworkClient` 一致 |
| 2 | 不新建 DTO 文件，请求用 `Map<String, Object>` | 团队反馈 DTO 过多，本请求字段简单一次性使用，独立 DTO 性价比低 |
| 3 | 不复用 framework 端 DTO 类 | 跨模块依赖会引入 framework 业务包，违反微服务边界 |
| 4 | service 吞所有异常 | 定时任务不能拖垮主服务 |
| 5 | scheduler 默认关闭 | 前端看板录入指标 key 前开启会被 3007 拒绝 |
| 6 | 不加分布式锁 | framework 端按天幂等 upsert，多实例并发安全 |
| 7 | community/feature/statDayOffset 用 `@Value` 注入 | 与 `ModelHealthScheduler` 风格一致，支持 Apollo 动态调整 |
| 8 | cron 默认每天 02:00 + stat-day-offset=-1 | 凌晨任务统计前一天数据，避开 0 点业务高峰 |
| 9 | timestamp 传"统计日 23:59:59"而非 UTC 0 点 | framework 用 LocalDateTime 解析不做时区转换，23:59:59 语义直观且边界安全 |
| 10 | 用户指标不分成功失败都统计 | 用户行为统计口径，失败申请也是一次访问 |
| 11 | 业务指标 6/29 扩展 | 4 个业务指标口径见 §2.5，本期落地 |
| 12 | `apply_success_rate` 按 `{numerator, denominator}` 对象上报 | 用户指示"先按别人那样写"。**风险**：framework 当前 `isNumeric` 校验可能拒绝对象（见 §2.1），若报错再决定改 framework 或退化为裸数字 |
| 13 | `apply_success_rate` 用 `grant_time` 非空而非 `status=success` 作分子 | 任务式执行完自动释放最终 status=released，按 status 会漏算；grant_time 非空=资源拿到=申请成功，更准确 |
| 14 | `apply_success_rate` 分子分母同按 `apply_time` 归属 | 比率要求分子分母同批，避免跨天错配失真 |
| 15 | `install_failed→released` 计入使用时长均值 | release_time 非空即参与 AVG，install_failed 占比小影响有限，本期接受 |
| 16 | count 指标 AVG 为 null 时不上报该 key | 避免传 null 被 framework `isNumeric` 拒绝；`apply_success_rate` 例外（始终上报，分母为 0 时传 `{0,0}`） |
| 17 | `apply_success_rate` 不带 `metricId` 字段 | workspace 侧不知 metricId（前端看板配置表主键），先按 `{numerator, denominator}` 上报，必要时再补 |

## 8. 待用户补充 / 后续改造

| # | 待补充项 | 影响 |
|---|---------|------|
| 1 | 指标 key 是否已在前端看板录入 | 若未录入会被 3007 拒绝。需运营先录入 6 个 metricKey（含本期 4 个业务指标） |
| 2 | 是否需要补单元测试 | 等指标稳定后补 |
| 3 | **framework rate 指标对象上报支持** | 本期 `apply_success_rate` 按 `{numerator, denominator}` 上报，若 framework `isNumeric` 拒绝需改 framework 校验（恢复 `0c08247d` 逻辑）或退化为裸数字。需跟踪 framework 仓改造 |
| 4 | **framework rate 指标月均聚合失真** | framework 当前对 rate 做算术平均（[calculateMetricAverages L638](file:///d:/Code/Java/openlibing/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java#L638)），月均会失真。若 framework 后续支持分子分母累加再除，月均才准确。需跟踪 |
| 5 | `workspace_env_record` 各时间字段的实际时区 | 当前假设存的是北京时间。若实际是 UTC，需调整 SQL 窗口计算 |
| 6 | `task_usage_mins` 是否需过滤 `fail_type IS NULL` | 本期接受 install_failed 计入。若实际数据偏差过大，加 `fail_type IS NULL` 过滤安装失败记录 |
| 7 | `apply_success_rate` 是否需要 `metricId` 字段 | 当前不带。若 framework 或前端要求，需先查 framework metric_config 表反查 metricId |
