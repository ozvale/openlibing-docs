# 项目资源效率环比 — 技术设计

## 1. 方案概述

采用前后端协同方案：后端在现有 `ops-project-resource-efficiency` 请求上增加可选环比开关，先查询当前页，再以当前页 `projectIds` 为边界复用现有聚合 SQL 查询上一期；响应返回上一期窗口、指标原值以及后端算好的增减值（Delta）/增减率（ChangeRate），前端只负责展示样式。

该方案优先保证两期指标口径、当前页项目集合和排序分页正确，同时将后端改动限制在现有请求/响应、Service 和项目效率 Mapper，不做数据库结构变更。

## 2. 当前实现与约束

### 2.1 当前调用链

```text
POST /common/detail
  -> DetailReq 按 category 多态反序列化为 OpsProjectResourceEfficiencyReq
  -> ResourceEfficiencyService.queryProjectEfficiencyList
       -> countProjectEfficiencyList
       -> queryProjectEfficiencyList(req, windowDays)
       -> 统一 rounding 和百分比换算
       -> queryProjectResourcePools（当前页批量查询）
  -> PageResult<OpsProjectResourceEfficiencyResp>
```

关键文件：

| 文件 | 当前职责 |
| --- | --- |
| `OpsProjectResourceEfficiencyReq.java` | 项目过滤和 `engineeringScope` |
| `OpsProjectResourceEfficiencyResp.java` | 项目信息、10 个数值指标和资源池列表 |
| `ResourceEfficiencyService.java` | 时间校验、排序白名单、窗口天数、分页和响应归一化 |
| `ResourceEfficiencyMapper.java` | 项目列表/count/资源池查询定义 |
| `ResourceEfficiencyMapper.xml` | PR run、排队、卡时和资源池指标聚合 |

### 2.2 必须保持的口径

- 项目集合由绑定资源池的项目及项目筛选决定，`engineeringScope=true` 时还要求项目含运营仓。
- PR 指标按 run 级集合统计；GitHub 在工程范围内还需匹配展示配置。
- `queueP90` 和 `prAvgQueueMinutes` 使用相同 run 级排队样本。
- `prAvgUsedHours = NPU 分配卡时 / 去重 run 数`。
- 资源池指标没有仓库维度，不做仓库级过滤。
- `isAllDay=1` 时节假日过滤和分配率工作日分母继续生效。
- 当前页最多 100 条，排序字段使用白名单。

项目内没有已有环比/同比 DTO、通用对比期包装或请求深拷贝工具，不引入新的通用框架。

## 3. 业内方案调研

### 3.1 可参考模式

- **Power BI**：通过时间智能函数平移当前日期筛选上下文，在数据/语义层计算上一期度量；变化率采用 `(current - previous) / previous`，安全除法在分母为 0 时返回空值。
- **Looker**：提供“任意选择周期与紧邻前一等长周期”的 PoP 模式，上一期随当前日期范围动态变化，并用 Selected Period / Previous Period 区分两期。
- **Tableau**：将 Difference 和 Percent Difference 作为基于当前值、对比值的展示计算，说明差值和百分比差异可以由展示层基于两期原值计算。

这些工具的实现不同，但共同点是：**两期窗口及基础指标必须同口径，差值和增减率属于派生展示指标**。没有必须采用“前端双请求”或“后端返回全部派生字段”的统一标准，应结合现有接口分页和查询成本选择。

参考资料：

1. [Power BI：使用 DAX 时间智能函数](https://learn.microsoft.com/zh-cn/training/modules/dax-power-bi-time-intelligence/2-functions)
2. [Looker：Arbitrary Period and Directly Previous Period](https://discuss.google.dev/t/methods-for-period-over-period-pop-analysis-in-looker-method-7-arbitrary-period-and-directly-previous-period/119267)
3. [Tableau：表计算类型](https://help.tableau.com/current/pro/desktop/zh-cn/calculations_tablecalculations_definebasic_runningtotal.htm)

## 4. 备选方案比较

| 方案 | 正确性 | 查询成本 | 改造量 | 结论 |
| --- | --- | --- | --- | --- |
| A. 后端当前页 + 上一期 projectIds 两次聚合，后端算增减值/增减率 | 两期复用同一 SQL；当前排序分页准确；按 ID 合并 | 增加一次必要的上一期列表聚合，不重复 count 和资源池查询 | 中，复用现有 SQL | **采用** |
| B. 单 SQL 双窗口并返回完整环比 | 可保证单查询内口径一致 | 一次往返，但若不先确定当前页，会对全部项目做双期聚合 | 大，CTE、分页、排序和结果映射均需调整 | 作为后续性能优化备选 |
| C. 前端调用两次现有接口 | 默认项目排序下可用；按当前指标排序时上一期页内项目可能不同 | 两次列表 + 两次 count + 两次资源池查询，且有两个请求时点 | 后端小、前端中 | 不用于正式方案 |

增减值/增减率按用户要求由后端统一计算（口径与两期一致），前端只负责正负号、百分点和颜色的格式化展示，不重复实现计算逻辑。

## 5. 接口设计

### 5.1 请求

`OpsProjectResourceEfficiencyReq` 新增：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `includePreviousPeriod` | Boolean | 否 | `false` | 是否返回紧邻前一等长自然日周期数据 |

示例：

```json
{
  "category": "ops-project-resource-efficiency",
  "startTime": "2026-11-20 00:00:00",
  "endTime": "2026-11-24 23:59:59",
  "engineeringScope": true,
  "includePreviousPeriod": true,
  "page": 1,
  "pageSize": 20
}
```

缺省或传 `false` 时不查询上一期，也不新增 `previousPeriod` 数据。

### 5.2 响应

`OpsProjectResourceEfficiencyResp` 新增 `previousPeriod`。现有字段始终表示当前期，避免破坏现有前端和排序逻辑。

新增独立 `OpsProjectResourceEfficiencyPreviousPeriodResp`：

| 字段 | 说明 |
| --- | --- |
| `startTime/endTime` | 实际上一期查询窗口 |
| `queueP90` | 上一期 PR 排队 P90（分钟） |
| `prAvgQueueMinutes` | 上一期 PR 平均排队（分钟） |
| `npuAllocHours` | 上一期 PR NPU 分配卡时 |
| `prAvgUsedHours` | 上一期单次 run 平均消耗卡时 |
| `npuUsageRate` | 上一期全部池利用率（%） |
| `npuAllocRate` | 上一期全部池分配率（%） |
| `sharedNpuAllocRate` | 上一期共享池分配率（%） |
| `exclusiveNpuAllocRate` | 上一期独占池分配率（%） |
| `sharedNpuUsageRate` | 上一期共享池利用率（%） |
| `exclusiveNpuUsageRate` | 上一期独占池利用率（%） |

此外每个指标返回后端计算好的 `<指标>Delta`（增减值）与 `<指标>ChangeRate`（增减率，百分比数值，如 23.0 表示 +23%）：任一期为 null 时两者为 null；上一期为 0 时 Delta 可算、ChangeRate 为 null；百分比指标 Delta 单位为百分点。前端直接展示，不再计算。

示例（省略部分当前期字段）：

```json
{
  "projectId": 100,
  "projectName": "example",
  "queueP90": 12.30,
  "prAvgQueueMinutes": 8.20,
  "npuUsageRate": 65.40,
  "previousPeriod": {
    "startTime": "2026-11-15 00:00:00",
    "endTime": "2026-11-19 23:59:59",
    "queueP90": 10.00,
    "prAvgQueueMinutes": 7.50,
    "npuUsageRate": 60.00
  }
}
```

未开启时 `previousPeriod=null`。开启但上一期无记录时仍返回窗口，指标均为 `null`，以便区分“未请求”和“无数据”。

## 6. 对比窗口规则

设当前日期为 `startDate/endDate`：

```text
windowDays = endDate - startDate + 1（自然日）
previousStartTime = startTime - windowDays 天
previousEndTime = endTime - windowDays 天
```

| 当前期 | 上一期 |
| --- | --- |
| 2026-11-24 | 2026-11-23 |
| 2026-11-20～2026-11-24 | 2026-11-15～2026-11-19 |
| 2026-11-01～2026-11-03 | 2026-10-29～2026-10-31 |
| 2026-01-01～2026-01-02 | 2025-12-30～2025-12-31 |

该规则与现有整天日期筛选的 `00:00:00～23:59:59` 配合时，两期等长、紧邻且不重叠。上一期窗口由后端生成并原样返回，前端不重复推导。

`isAllDay=1` 只改变节假日过滤和分配率分母，不改变“相同自然日跨度”的平移规则。两期分别调用现有窗口天数计算，上一期可能因节假日分布不同而具有不同工作日数，这是保留现有指标口径的预期行为。

## 7. 后端实现设计

### 7.1 查询流程

```text
校验当前请求
  -> 查询当前项目总数
  -> 查询当前页当前期指标
  -> 当前页为空或未开启：按原流程返回
  -> 提取当前页 projectIds（最多 100）
  -> 新建上一期请求并复制过滤条件，不修改原请求
  -> 计算上一期 windowDays
  -> 使用同一 Mapper 查询上一期，额外传 projectIds
  -> 按 projectId 建立上一期结果 Map
  -> 两期分别执行相同 rounding 和百分比换算
  -> 为每条当前记录填充 previousPeriod
  -> 当前页资源池名称仍只批量查询一次
```

上一期请求复制项目过滤、`engineeringScope`、`isAllDay` 等查询条件；分页设为第一页，`pageSize=当前页 projectIds 数量`。由于 Mapper 额外限制 `projectIds`，上一期排序不影响合并，响应必须按 `projectId` 而不是列表位置匹配。

上一期查询不执行 count，不重复查询资源池名称，不修改当前请求的分页和排序参数。

### 7.2 Mapper 最小改造

现有方法增加可空参数：

```java
queryProjectEfficiencyList(req, windowDays, projectIds)
```

- 当前期查询传 `projectIds=null`，生成 SQL 与现状一致。
- 上一期查询传当前页 ID 集合。
- XML 只在 `proj_pool` 增加可选 `AND project_id IN (...)`，其余 `pr_run_scope`、排队样本、PR 聚合、资源池聚合和结果映射全部复用。
- 当前页为空时不调用 Mapper，避免空 `IN` 条件。

### 7.3 指标计算

| 指标类别 | 两期计算方式 |
| --- | --- |
| `queueP90` | 各期从该期全部 run 级样本重新计算 P90，不合并日/流水线 P90 |
| `prAvgQueueMinutes` | 各期对与 P90 相同的 run 级样本求平均 |
| `npuAllocHours` | 各期对窗口内申请切片求和 |
| `prAvgUsedHours` | 各期分别计算卡时合计 ÷ 该期去重 run 数 |
| 全部/共享/独占利用率 | 各期分别汇总 used、total 后相除 |
| 全部/共享/独占分配率 | 各期分别汇总 assign，并使用该期工作日/自然日分母 |

上一期结果使用与当前期相同的归一化方法，确保前端拿到的两期都是分钟、卡时或 0～100 百分比，不混用 SQL 的 0～1 比率。

### 7.4 异常处理

上一期查询失败时整个请求失败。不得捕获异常后返回全 `null` 的上一期，因为这会把查询故障伪装成无数据。未开启环比时不增加新的异常路径。

## 8. 前端实现设计

### 8.1 数据使用

- 当前列表仍读取原有字段，顺序直接使用后端当前页结果。
- 开启环比时传 `includePreviousPeriod=true`，从同一条记录的 `previousPeriod` 读取上一期原值，以及后端算好的 `<指标>Delta` / `<指标>ChangeRate`。
- 不按下标合并、不发起第二次分页请求、不自行推导上一期日期。
- Tooltip 使用后端返回的实际 `previousPeriod.startTime/endTime`。

### 8.2 计算公式

增减值与增减率由后端计算并随 `previousPeriod` 返回（`<指标>Delta` / `<指标>ChangeRate`），前端不再计算：

```text
Delta      = current - previous
ChangeRate = (current - previous) / previous × 100   // 百分比数值
```

| 场景 | Delta | ChangeRate | 建议展示 |
| --- | --- | --- | --- |
| 两期均非 `null`，`previous != 0` | 数值 | 数值 | 当前值 + 环比增减率 |
| `previous = 0` | 数值 | `null` | 增减率 `--`，可在 Tooltip 展示增减值 |
| 任一期为 `null` | `null` | `null` | `--`，不得当成 0 |
| 两期相等 | 0 | 0 | 0.00% |

ChangeRate 已是百分比数值（前端不要再乘 100）；百分比指标 Delta 单位为百分点。计算和显示保留两位小数。

### 8.3 百分比和趋势样式

- `npuUsageRate/npuAllocRate/sharedNpuAllocRate/exclusiveNpuAllocRate/sharedNpuUsageRate/exclusiveNpuUsageRate` 的 `<指标>Delta` 单位为**百分点**，例如 `65.4% - 60.0% = +5.4 个百分点`。
- `<指标>ChangeRate` 为相对增减率（%），不得与百分点混写。
- 推荐主展示“当前值 + 增减率”，Tooltip 展示上一期窗口、上一期原值和增减值。
- 排队时长下降通常代表改善；其他指标不能统一假设上升为好。颜色按指标语义配置，不能只按数值正负统一红绿。
- 本期不支持按 `<指标>Delta` 或 `<指标>ChangeRate` 排序。

## 9. 性能与边界

- 环比只增加一次上一期列表查询，且限制当前页最多 100 个项目，不采用逐项目查询。
- 当前请求未开启环比时 SQL 和查询次数不变。
- 两期查询暂时串行，避免单请求占用额外数据库连接和放大瞬时压力。
- 不为环比复制一套 SQL，避免后续指标口径修正时两期漂移。
- 不修改数据库结构，不新增缓存；数据快照一致性沿用当前看板查询语义。
- 联调阶段使用只读 `EXPLAIN`、查询日志或慢查询记录检查上一期 `projectIds` 条件生效，记录当前期与上一期查询耗时；不通过修改数据进行验证。

## 10. 涉及文件

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `OpsProjectResourceEfficiencyReq.java` | 修改 | 新增 `includePreviousPeriod` |
| `OpsResourceEfficiencyMetricsResp.java` | 新增 | 当前期与上一期共用的 10 个指标字段 + `copyMetricsFrom` / `normalize` |
| `OpsProjectResourceEfficiencyPreviousPeriodResp.java` | 新增 | 上一期窗口；指标继承公共基类，并含后端计算的 `<指标>Delta` / `<指标>ChangeRate`；工厂方法 `of(start, end, previous, current)` 一次完成赋值与计算 |
| `OpsProjectResourceEfficiencyResp.java` | 修改 | 新增 `previousPeriod` |
| `ResourceEfficiencyService.java` | 修改 | 推导窗口、复制请求、查询和合并上一期，复用归一化 |
| `ResourceEfficiencyMapper.java` | 修改 | 列表查询增加可空 `projectIds` 参数 |
| `ResourceEfficiencyMapper.xml` | 修改 | `proj_pool` 增加可选项目 ID 集合过滤 |
| `ResourceEfficiencyServiceTest.java` | 修改 | 窗口、复制条件、合并、空值和默认路径测试 |
| `ResourceEfficiencyMapperXmlTest.java` | 修改 | 可选 `projectIds` 动态 SQL 和兼容性测试 |

Controller、通用 `DetailReq` 注册、数据库表和其他 category 不需要修改。

## 11. 验证与上线策略

1. 先通过 Service 测试确认未开启时不会调用上一期 Mapper。
2. 覆盖单日、跨月、跨年和工作日窗口，以及当前页 ID 限制和按 ID 合并。
3. 覆盖 `engineeringScope=true/false/null`、上一期缺行、指标 `null`、零分母和百分比换算。
4. 运行现有资源效率测试和资源看板相关回归测试，确认默认响应兼容。
5. 前端联调核对两期窗口、差值、增减率、百分点、空值和 Tooltip。
6. 先以 `includePreviousPeriod=false` 保持旧客户端行为；前端就绪后开启，无需数据库迁移。

## 12. 后续可选优化

只有当真实查询日志证明两次聚合无法满足性能要求时，再评估方案 B 的单 SQL 双窗口或预聚合。优化前必须先解决“只计算当前页项目”与“当前期排序后再取上一期”的依赖，不能为了减少一次往返而对全部项目做双期重聚合。
