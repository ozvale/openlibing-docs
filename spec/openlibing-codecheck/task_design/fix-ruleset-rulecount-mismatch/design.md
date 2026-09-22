# fix-ruleset-rulecount-mismatch — 技术设计

## 方案概述

在 `RuleSetListImpl` 三个查询方法返回结果前，统一调用规则数统计逻辑为每个 `CodeCheckProjectRuleSetVo` 填充 `ruleCount`；同时修正 `JsonUtil.ruleCount` 的空值/去重缺陷，使两套接口的规则数统计口径一致。

## 架构决策

### 决策 1：在 Service 层填充 ruleCount，而非 Operation 层

`ruleCount` 是 `@Transient` 字段，不持久化，属于"展示态"计算。放在 Service 层（`RuleSetListImpl`）填充，与现有 `RuleDelegateImpl.getProjectRuleSet` 的处理方式保持一致，职责清晰，避免污染 MongoDB 查询层。

### 决策 2：复用并修正 JsonUtil.ruleCount，而非新增方法

`JsonUtil.ruleCount` 已被多处调用（`RuleDelegateImpl`、`RuleSetOperation`、`FileDownloadDelegateImpl`）。直接修正该方法（去重、过滤空值、null 安全）可同时修复对比基线 `RuleDelegateImpl.getProjectRuleSet` 的统计偏差，使两套接口口径统一。

但 `JsonUtil.ruleCount` 当前返回 `String[]`，多处调用方依赖该返回类型做 `Arrays.asList` 或 `.length`。为最小化影响：
- 保留 `ruleCount(String)` 返回 `String[]` 的签名不变（调用方依赖），但内部修正为去重 + 过滤空值 + null 安全。
- 新增 `ruleCountInt(String)` 方法返回 `int`，供需要直接拿数量的调用方使用（`RuleSetListImpl`、`RuleDelegateImpl`）。

### 决策 3：去重口径

`rule_ids` 字段语义为"启动规则id"逗号分隔字符串。重复 id 属于脏数据，统计规则数时应去重。使用 `LinkedHashSet` 去重并过滤空白，保持稳定。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/codecheck/common/utils/common/JsonUtil.java` | 修改 | 修正 `ruleCount(String)` 去重/过滤空值/null 安全；新增 `ruleCountInt(String)` 返回 int |
| `src/main/java/com/openlibing/codecheck/business/impl/RuleSetListImpl.java` | 修改 | 三个查询方法填充 ruleCount |
| `src/test/java/com/openlibing/codecheck/common/utils/common/JsonUtilTest.java` | 修改 | 补充去重/空值/null 测试用例 |
| `src/test/java/com/openlibing/codecheck/business/impl/RuleSetListImplTest.java` | 新增/修改 | 补充三个查询方法 ruleCount 填充测试 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 修正 `JsonUtil.ruleCount` 影响其他调用方（`RuleSetOperation`、`FileDownloadDelegateImpl`） | 这些调用方用 `Arrays.asList(ruleCount(...))` 做 `contains` 判断或 `.length` 统计，去重 + 过滤空值后语义更正确，不会引入回归；通过现有测试覆盖验证 |
| `RuleSetListImpl` 缺少现成单测，Mock 依赖较多 | 优先补充针对 ruleCount 填充逻辑的测试，必要时使用 Mockito mock `RuleSetListOperation` 和 `CommonHelper` 等依赖 |
| `CodeCheckProjectRuleSetListVo.getRuleSetList()` 返回不可变列表 | 填充 ruleCount 是对列表内元素的 `setRuleCount`，不修改列表结构，不受不可变列表影响 |

## 跨仓影响

无。改动仅限 `openlibing-codecheck` 单仓。
