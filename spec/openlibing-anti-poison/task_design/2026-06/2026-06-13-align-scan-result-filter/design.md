## Context

### 当前状态

| 层级 | 现状 |
|------|------|
| 前端 `PoisoningDetail.vue` | 表头 `filterDropdown` 单选；`handleFilter` 将选中值以 `tableFilters[name] = data[0].value`（`0`/`1`）合并进请求体 |
| 前端 API | 版本级 `getScanResult`；门禁级 `get-scan-pr-result-group`（`GET_INC_POISONING`） |
| 后端 `ParamModel` | 无 `isSuccess`/`isPass` 字段，JSON 反序列化时丢弃 |
| 后端查询 | `getScanResult`、`getScanPRResultGroup` 仅按 project/repo/branch/时间过滤 |
| MongoDB | `TaskEntity`/`PRTaskEntity` 存 `is_success`、`is_pass` 为 **Boolean** |

### 约束

- 前端已上线筛选 UI，参数名必须为 `isSuccess`、`isPass`，值必须为 `0`/`1`（与 `StaticCheckList` 等页面一致）
- 不改变现有分页响应结构 `{ count, data }`
- 筛选为可选；不传则不限制

## Goals / Non-Goals

**Goals:**

- 后端识别并应用 `isSuccess`、`isPass` 筛选
- 版本级与门禁级 PR 分组列表行为一致
- 筛选后的 `count` 与分页 `data` 一致
- 补充可自动化验证的单元测试

**Non-Goals:**

- 不改造 `get-scan-pr-result`（子行展开）接口
- 不新增动态筛选项拉取 API（本需求为静态枚举）
- 不改变 Mongo 文档 schema

## Decisions

### 1. ParamModel 字段类型：Integer（0/1）

**选择**：`private Integer isSuccess;`、`private Integer isPass;`

**理由**：与前端透传值一致；`null` 表示未筛选；避免 Boolean 与 `0`/`1` 混用歧义。

**替代方案**：Boolean — 需前端改传 `true`/`false`，与现有实现及同项目惯例不一致。

### 2. 入参到 Mongo 的映射

```text
isSuccess == 1  →  criteria.and("is_success").is(true)
isSuccess == 0  →  criteria.and("is_success").is(false)
isSuccess == null → 不添加条件

isPass 同理映射 is_pass
```

在 `ScanResultDetailOperation` 提取私有方法 `applySuccessPassFilter(Criteria, ParamModel)` 供 `getScanResult` 与 `getScanPRResultGroup` 复用，避免重复。

### 3. getScanPRResultGroup 筛选时机：聚合前 $match

**选择**：在 `$group` 之前的 `Aggregation.match(criteria)` 中加入 `is_success`/`is_pass` 条件。

**理由**：先过滤原始 `POISON_PR_TASK` 文档再分组，保证 `count`（无分页的完整聚合）与分页列表语义一致。

**风险**：同一 PR 多次扫描且状态 mixed 时，仅匹配状态的扫描参与分组；与「按条件查扫描记录再按 PR 聚合」的产品语义一致。

### 4. 计数逻辑

`ProblemShieldServiceImpl` 已在分页查询后清空 `pageNum`/`pageSize` 再查 count；筛选条件写入 `ParamModel` 后，count 查询自动继承相同 Criteria，无需额外改动 Service 层。

### 5. 前端对齐

前端 **无需修改** 请求字段。联调验收清单：

- 仅选「成功」→ 全部 `isSuccess === true`
- 仅选「失败」→ 全部 `isSuccess === false`
- 仅选「通过/未通过」→ `isPass` 对应
- 重置筛选 → 请求体不含字段，返回全量

可选：在 `openlibing-web` 的 Poisoning API 类型或注释中声明 `isSuccess?`、`isPass?` 为 `0 | 1`。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 前端传字符串 `"0"`/`"1"` | Jackson 通常可反序列化为 Integer；单测覆盖；必要时加 `@JsonDeserialize` |
| 聚合 count 性能 | 筛选在 `$match` 缩小数据集，影响可控；与现网无筛选路径相比仅多索引友好条件 |
| 仅改 PR 分组接口、漏改 getScanResult | tasks 明确要求两接口同步；单测各一条 |

## Migration Plan

1. 部署后端（向后兼容：旧请求无新字段，行为不变）
2. 前端筛选 UI 已存在，部署后直接联调
3. 回滚： revert 后端 ParamModel 与 Operation 改动即可，前端无依赖新版本

## Open Questions

- Mongo 是否已对 `is_success`/`is_pass` 建复合索引（非阻塞，可后续优化）
- ci-portal 转发层是否对 request body 做字段白名单过滤（联调时确认）
