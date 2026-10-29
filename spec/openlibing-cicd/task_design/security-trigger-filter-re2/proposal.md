# security-trigger-filter-re2: 触发过滤规则改用 RE2 线性引擎并补齐写入口校验

## 需求背景

流水线配置中的触发过滤规则（trigger filter）由用户自定义正则，用于决定分支是否触发流水线。原实现存在两处缺陷：

- 写入口无校验：`updatePipelineConfig` 仅有 `pattern == null || length > 500` 与 `java.util.regex.Pattern.compile` 两道内联判断；`batchUpdatePipelineConfig` 完全没有校验。
- 运行侧使用 `java.util.regex` 回溯引擎，且每次匹配都 `Pattern.compile(...)` 新建对象，无缓存、无超时。

攻击者可配置 `(a+)+$` 这类嵌套量词规则，在长分支名上产生指数级回溯，卡死处理 webhook 的线程，属于 CWE-1333 正则表达式拒绝服务（ReDoS）。运行侧与本缺陷同根因，故一并整改。

## 功能描述

- 正则引擎由 `java.util.regex` 切换为 `com.google.re2j`（RE2 线性时间引擎），从根本上消除回溯爆炸。
- 新增 `TriggerFilterValidator`，作为写入口与运行侧共用的唯一校验入口，保证入库规则在 RE2 下一定可执行。
- 校验规则：非空、非纯空白、无首尾空白、长度不超过 200 字符、不含嵌套量词、可被 `com.google.re2j.Pattern.compile` 编译。
- `updatePipelineConfig` 改为调用统一校验器；`batchUpdatePipelineConfig` 补齐同等校验，且在任何 DB 查询之前返回，不做部分更新。
- 运行侧编译结果按 pattern 缓存（上限 1024，超限整体清空）；非法规则编译结果为空，按「该条规则不命中」降级处理，不再抛异常中断。

## 验收标准

- [x] `pom.xml` 引入 `com.google.re2j:re2j:${re2j.version}`，版本 `1.7`
- [x] 新增 `TriggerFilterValidator`，覆盖 null 元素、空串、纯空白、首尾空白、超长（200）、嵌套量词、编译失败七类拒绝路径，并返回对应中文文案
- [x] `TriggerFilterEvaluator` 全部改用 `com.google.re2j.Pattern`，配套编译缓存与失败降级
- [x] `updatePipelineConfig` 与 `batchUpdatePipelineConfig` 均使用统一校验器；批量更新入口校验失败直接返回「批量更新已取消：…」
- [x] `PipelineTriggerFilterDTO` 长度约束由 500 收敛为 200
- [x] `TriggerFilterValidatorTest` 20 例全部通过，断言精确中文文案
- [x] `TriggerFilterEvaluatorTest` 覆盖 INCLUDE/EXCLUDE/混合、空配置、非法 pattern 降级、null 规则元素跳过，并以 `(a+)+$` + 1000 字符输入在 2 秒内完成验证线性时间
- [x] `PipelineServiceImplTest` 新增 `batchUpdatePipelineConfig_InvalidTriggerFilter_RejectedWithoutUpdate`，断言未发生任何 DB 查询
- [x] BETA 环境 `trigger_filters` 存量数据完成 RE2 兼容性扫描，确认无风险
- [ ] 生产环境 `trigger_filters` 存量数据未扫描：上线前必须按同一标准确认为零风险，否则存量不兼容规则会静默不命中
- [ ] 运行期编译失败告警未实现：当前仅 `warn` 日志，无规则/流水线标识计数与监控

## 影响范围

| 文件                                                                                    | 操作 | 说明                                                                             |
| --------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------- |
| `pom.xml`                                                                               | 修改 | 新增 `re2j.version = 1.7` 与 re2j 依赖                                           |
| `src/main/java/com/openlibing/cicd/common/utils/TriggerFilterValidator.java`            | 新增 | 82 行统一校验器，常量 `MAX_PATTERN_LENGTH = 200`                                 |
| `src/main/java/com/openlibing/cicd/business/listener/TriggerFilterEvaluator.java`       | 修改 | 切换 RE2J，新增 `COMPILE_CACHE_MAX_SIZE = 1024` 与编译缓存，非法规则降级为不命中 |
| `src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java`      | 修改 | 配置更新与批量更新改用统一校验，批量更新补齐零校验缺口                           |
| `src/main/java/com/openlibing/cicd/business/dto/pipeline/PipelineTriggerFilterDTO.java` | 修改 | `@Size` 500 → 200，`@NotBlank` 文案调整                                          |
| `src/test/java/com/openlibing/cicd/common/utils/TriggerFilterValidatorTest.java`        | 新增 | 20 个用例                                                                        |
| `src/test/java/com/openlibing/cicd/business/listener/TriggerFilterEvaluatorTest.java`   | 修改 | 扩充匹配、降级、线性时间用例                                                     |
| `src/test/java/com/openlibing/cicd/business/service/impl/PipelineServiceImplTest.java`  | 修改 | 新增批量更新非法规则拒绝用例                                                     |

对外行为变化：

- 接口出入参结构不变，但错误文案全部改变；长度上限由 500 收紧为 200。
- 批量更新入口新增拒绝路径，返回「批量更新已取消：」+ 具体原因。
- 拒绝 RE2 不支持的语法（反向引用、lookaround、占有量词）与嵌套量词。
- 运行期遇到非法规则由「抛异常中断」改为「该条规则不命中」，即不触发流水线而非报错。
- 无新增配置项，无 yml 改动。

## 关联 Issue

- #448 写入口批量更新无校验、正则无复杂度限制
  https://gitcode.com/openlibing/openlibing-cicd/issues/448
- #463 运行侧同根因
  https://gitcode.com/openlibing/openlibing-cicd/issues/463

## 关联 PR 与提交

- PR `!635`「【安全】触发过滤规则补齐写入口校验并切换 RE2 线性引擎（规避 ReDoS）」，分支 `fix/security-vuln-448-463-trigger-filter-regex`，base `upstream/release_20261029_iter2`（base commit `d1615a06a`），状态已 merged
- `a274cbe6e` replace trigger filter regex engine with RE2J
- `9073d78cf` reject null and blank-padded trigger filter rules
- diff 规模：8 文件，418 insertions / 31 deletions
