# security-trigger-filter-re2 — 工程设计

## 1. 方案设计

采用「引擎替换 + 校验前移」双管齐下：

1. 运行侧把正则引擎整体换成 `com.google.re2j`。RE2 不回溯，匹配时间与输入长度线性相关，`(a+)+$` 这类规则不再产生指数级回溯，CWE-1333 从根上失效。
2. 写入口新增 `TriggerFilterValidator`，与运行侧使用同一引擎做编译校验。规则能入库即代表运行时一定能执行，消除「入库成功、运行时崩」的错位。
3. 补齐 `batchUpdatePipelineConfig` 的零校验缺口，并保证校验发生在任何 DB 查询之前，失败即整体取消，不产生部分更新。

选择 RE2J 而非「自研超时包装 java.util.regex」的原因：超时只能止损，仍需额外的线程/中断管理，且超时边界不稳定；RE2J 直接使病态输入不可构造，同时保留编译期语法校验能力。

## 2. 实现逻辑设计

### 2.1 写入口校验流程

`updatePipelineConfig` 与 `batchUpdatePipelineConfig` 统一走 `TriggerFilterValidator.validate(List<String>)`：

1. 列表为 `null` 或空 → 放行（未配置过滤规则）。
2. 遍历元素，元素为 `null` → 返回「分支规则不能为空」。
3. 逐条调用 `validatePattern`，按顺序短路返回首个错误：
   - 空或纯空白 → 「请填写分支规则」
   - 首尾存在空白 → 「分支规则首尾不能有空格…」
   - 长度 > 200 → 「分支规则最多 200 个字符，当前 N 个字符」
   - 命中嵌套量词启发式 → 提示改写为 `feature/.*`
   - `com.google.re2j.Pattern.compile` 失败 → 提示检查括号、避免 `\1`、`(?=)` 等
4. 有错误：`updatePipelineConfig` 直接 `DataResult.failureMessage(triggerFilterError)`；`batchUpdatePipelineConfig` 返回「批量更新已取消：」+ 原因，且此时尚未执行 `selectByProjectAndPipelineIds` 等查询。

原 `updatePipelineConfig` 的内联校验（`pattern == null || length > 500`、`java.util.regex.Pattern.compile`）整体删除，避免两套判定标准并存。

### 2.2 运行侧匹配流程

`TriggerFilterEvaluator.singleMatch`：

1. 先判断 `compiledPatterns.size() >= COMPILE_CACHE_MAX_SIZE`（1024），超限整体 `clear()`。
2. `computeIfAbsent(pattern, TriggerFilterEvaluator::compile)` 取编译结果。
3. `compile` 返回 `Optional<Pattern>`：编译失败为空 Optional，该条规则按「不命中」处理。
4. 匹配期捕获 `RuntimeException`，只 warn 并返回 `false`，不向上抛出。
5. INCLUDE/EXCLUDE 分流处增加 `r != null` 过滤，避免 null 元素进入匹配逻辑。

### 2.3 关键代码

```java
private static Optional<Pattern> compile(String pattern) {
    try {
        return Optional.of(Pattern.compile(pattern));
    } catch (PatternSyntaxException e) {
        log.warn("...");
        return Optional.empty();
    }
}
```

```java
private static final Pattern NESTED_QUANTIFIER =
        Pattern.compile("\\((?:[^()]*[+*{][^()]*)\\)\\s*(?:[+*]|\\{\\d)");
```

## 3. 类设计

### 3.1 `TriggerFilterValidator`（新增，`common/utils`）

- 常量：`MAX_PATTERN_LENGTH = 200`；嵌套量词启发式正则 `\((?:[^()]*[+*{][^()]*)\)\s*(?:[+*]|\{\d)`。
- `validate(List<String> patterns)`：列表级校验，负责 null 元素判定。
- `validatePattern(String pattern)`：单条规则校验，返回中文错误文案，合法时返回空。

### 3.2 `TriggerFilterEvaluator`（修改，`business/listener`）

- 依赖类型由 `java.util.regex.Pattern/Matcher` 改为 `com.google.re2j.Pattern/PatternSyntaxException`。
- 新增 `COMPILE_CACHE_MAX_SIZE = 1024` 与 `Map<String, Optional<Pattern>> compiledPatterns = new ConcurrentHashMap<>()`。
- 新增私有静态方法 `compile(String)`，返回 `Optional<Pattern>`。
- `singleMatch` 增加缓存上限判断、`computeIfAbsent` 取编译结果、异常降级、null 规则过滤。

### 3.3 `PipelineServiceImpl`（修改，`business/service/impl`）

- `updatePipelineConfig`（约 1644 行）：改为 `TriggerFilterValidator.validate`，删除原内联长度/编译校验。
- `batchUpdatePipelineConfig`（约 1698 行）：新增校验调用（约 1708 行），位于所有 DB 查询之前。
- 删除 `PipelineTriggerFilterDTO` 的无用 import。

### 3.4 `PipelineTriggerFilterDTO`（修改，`business/dto/pipeline`）

- `pattern` 字段：`@Size(max = 500)` → `@Size(max = 200)`，message 改为「分支规则最多 200 个字符」；`@NotBlank` message 改为「请填写分支规则」。
- 注释补充语义：整串匹配，直接写分支名即精确匹配，前缀匹配写 `feature/.*`。

## 4. 数据模型设计

无变更。`trigger_filters` 表结构、字段与 liquibase 脚本均未改动，本次仅将 `pattern` 的业务长度约束由 500 收敛为 200，属应用层校验收敛，不涉及 DDL 与数据迁移。

## 5. 性能设计

- 匹配复杂度由回溯引擎的最坏指数级降为 RE2 的线性时间，`(a+)+$` 配 1000 字符输入可稳定在秒级以内完成（测试用 `assertTimeoutPreemptively(Duration.ofSeconds(2))` 固化）。
- 消除每次匹配重复 `Pattern.compile` 的开销：编译结果按 pattern 字符串缓存，`ConcurrentHashMap` + `computeIfAbsent` 保证并发安全与单次编译。
- 缓存上限 1024，超限整体 `clear()` 而非 LRU：实现简单、无额外同步，过滤规则总量天然有限，清空后重建成本可接受。
- 不再需要匹配超时机制；RE2 下超时逻辑本身即无必要。

## 6. API接口设计

出入参结构无变化，无需前端适配，但存在以下契约级行为变化：

| 变化点         | 原行为                                                            | 现行为                                                                                                      |
| -------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 长度上限       | 500 字符                                                          | 200 字符                                                                                                    |
| 校验错误文案   | 「过滤规则 pattern 长度不能超过 500 字符」「过滤规则正则非法：…」 | 「分支规则最多 200 个字符，当前 N 个字符」「请填写分支规则」「分支规则首尾不能有空格…」等面向用户的中文提示 |
| 批量更新入口   | 无任何校验，直接执行                                              | 校验失败返回「批量更新已取消：」+ 原因，且不执行任何 DB 查询                                                |
| 支持的语法     | `java.util.regex` 全集                                            | 拒绝反向引用、lookaround、占有量词及嵌套量词                                                                |
| 运行期非法规则 | 抛异常中断                                                        | 该条规则不命中（不触发流水线）                                                                              |

## 7. 安全设计

- 缺陷类型：CWE-1333 正则表达式拒绝服务。原实现在长分支名上对嵌套量词规则产生指数级回溯，可卡死处理 webhook 的线程。
- 缓解措施：改用 RE2 线性引擎（消除回溯）、写入口强制编译校验（阻断病态规则入库）、嵌套量词启发式拦截（对常见攻击形态前置拒绝）、长度上限收敛到 200（压缩输入空间）、批量入口前置校验（堵住无校验写入通道）。
- 校验与执行同引擎：写入口使用 `com.google.re2j.Pattern.compile` 判定，保证「能入库即可执行」，不依赖两套语义的等价假设。

残留风险与上线注意：

- 现网已入库且超过 200 字符、或含 RE2 不支持语法的规则，更新配置时会被拒绝修改，需要用户改写规则。
- 运行侧这类存量规则会静默不命中，即该规则不再触发流水线，且不会报错提示。
- 已对 BETA 环境 `trigger_filters` 存量数据做过 RE2 兼容性扫描，确认无风险；生产存量数据需按同一标准确认。
