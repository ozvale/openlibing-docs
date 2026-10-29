# security-trigger-filter-re2 — 实现任务

## 进度: 10/10 complete

- [x] Task 1 — 引入 re2j 依赖
- [x] Task 2 — 新增 `TriggerFilterValidator` 统一校验器
- [x] Task 3 — `TriggerFilterEvaluator` 切换 RE2J 引擎并加入编译缓存与失败降级
- [x] Task 4 — `updatePipelineConfig` 改用统一校验器
- [x] Task 5 — `batchUpdatePipelineConfig` 补齐前置校验
- [x] Task 6 — `PipelineTriggerFilterDTO` 长度约束收敛至 200
- [x] Task 7 — 新增 `TriggerFilterValidatorTest`
- [x] Task 8 — 扩充 `TriggerFilterEvaluatorTest`
- [x] Task 9 — `PipelineServiceImplTest` 新增批量更新拒绝用例
- [x] Task 10 — BETA 环境存量规则 RE2 兼容性扫描

## 详细任务

### Task 1 — 引入 re2j 依赖

- 文件：`pom.xml`
- 改动：新增属性 `re2j.version = 1.7`，新增依赖 `com.google.re2j:re2j:${re2j.version}`。
- 验证方式：`mvn -q dependency:tree` 确认依赖解析成功；编译通过。

### Task 2 — 新增 `TriggerFilterValidator` 统一校验器

- 文件：`src/main/java/com/openlibing/cicd/common/utils/TriggerFilterValidator.java`（新增，82 行）
- 改动：
  - 常量 `MAX_PATTERN_LENGTH = 200`；嵌套量词启发式正则 `\((?:[^()]*[+*{][^()]*)\)\s*(?:[+*]|\{\d)`。
  - `validate(List<String>)`：列表为 null/空放行，元素为 null 返回「分支规则不能为空」。
  - `validatePattern(String)`：依次拒绝空或纯空白、首尾空白、超长（200）、嵌套量词、RE2 编译失败，各返回对应中文文案。
- 验证方式：由 Task 7 单元测试覆盖全部拒绝路径与文案。

### Task 3 — `TriggerFilterEvaluator` 切换 RE2J 引擎

- 文件：`src/main/java/com/openlibing/cicd/business/listener/TriggerFilterEvaluator.java`
- 改动：
  - `java.util.regex.Pattern/Matcher` → `com.google.re2j.Pattern/PatternSyntaxException`。
  - 新增 `COMPILE_CACHE_MAX_SIZE = 1024` 与 `ConcurrentHashMap<String, Optional<Pattern>> compiledPatterns`；超限整体 `clear()` 后 `computeIfAbsent(..., TriggerFilterEvaluator::compile)`。
  - `compile` 返回 `Optional<Pattern>`，失败为空 → 该条规则不命中；匹配期 `RuntimeException` 仅 warn 返回 `false`；INCLUDE/EXCLUDE 分流增加 `r != null` 过滤。
- 验证方式：`TriggerFilterEvaluatorTest`；结合 `(a+)+$` + 1000 字符输入的超时断言验证线性时间。

### Task 4 — `updatePipelineConfig` 改用统一校验器

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java`（约 1644 行）
- 改动：删除原内联校验（`pattern == null || length > 500` → 「过滤规则 pattern 长度不能超过 500 字符」，`java.util.regex.Pattern.compile` → 「过滤规则正则非法：…」），改调 `TriggerFilterValidator.validate`，失败返回 `DataResult.failureMessage(triggerFilterError)`。
- 验证方式：`PipelineServiceImplTest` 既有更新配置用例回归通过。

### Task 5 — `batchUpdatePipelineConfig` 补齐前置校验

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java`（约 1698 / 1708 行）
- 改动：原方法零校验，新增与 Task 4 相同的校验，位置在任何 DB 查询之前；失败返回「批量更新已取消：」+ 原因，不做部分更新。同时删除 `PipelineTriggerFilterDTO` 的无用 import。
- 验证方式：Task 9 用例断言 `!result.ok()`、msg 含指定文案，且 `pipelineInfoMapper.selectByProjectAndPipelineIds` 从未被调用。

### Task 6 — `PipelineTriggerFilterDTO` 长度约束收敛

- 文件：`src/main/java/com/openlibing/cicd/business/dto/pipeline/PipelineTriggerFilterDTO.java`
- 改动：`@Size(max = 500)` → `@Size(max = 200)`，message 改为「分支规则最多 200 个字符」；`@NotBlank` message 改为「请填写分支规则」；注释说明整串匹配语义。
- 验证方式：DTO 校验用例与配置更新接口回归。

### Task 7 — 新增 `TriggerFilterValidatorTest`

- 文件：`src/test/java/com/openlibing/cicd/common/utils/TriggerFilterValidatorTest.java`（新增）
- 改动：20 个用例，覆盖 null/空列表放行、null 元素拒绝、9 个现网真实 pattern 放行、首尾空白、201 字符、4 种嵌套量词、语法错误、RE2 不兼容语法，全部断言精确中文文案。
- 验证方式：`mvn -q test -Dtest=TriggerFilterValidatorTest`。

### Task 8 — 扩充 `TriggerFilterEvaluatorTest`

- 文件：`src/test/java/com/openlibing/cicd/business/listener/TriggerFilterEvaluatorTest.java`
- 改动：新增 INCLUDE/EXCLUDE/混合、空配置、非法 pattern 降级为不命中、null 规则元素跳过；新增 `(a+)+$` 配 1000 字符输入，用 `assertTimeoutPreemptively(Duration.ofSeconds(2))` 验证线性时间。
- 验证方式：`mvn -q test -Dtest=TriggerFilterEvaluatorTest`。

### Task 9 — `PipelineServiceImplTest` 新增批量更新拒绝用例

- 文件：`src/test/java/com/openlibing/cicd/business/service/impl/PipelineServiceImplTest.java`
- 改动：新增 `batchUpdatePipelineConfig_InvalidTriggerFilter_RejectedWithoutUpdate`，pattern 为 `(feature/.*)+`，断言 `!result.ok()`、msg 含「批量更新已取消」与「请改成」，并 `verify(pipelineInfoMapper, never()).selectByProjectAndPipelineIds(...)`。
- 验证方式：`mvn -q test -Dtest=PipelineServiceImplTest`。

### Task 10 — BETA 环境存量规则 RE2 兼容性扫描

- 文件：无代码改动
- 改动：对 BETA 环境 `trigger_filters` 存量数据做 RE2 兼容性扫描，确认无超过 200 字符或含 RE2 不支持语法的规则。
- 验证方式：扫描结果确认为零风险；生产环境按同一标准另行确认。
