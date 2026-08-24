# security-enhance-purchase-confirm — 技术设计

## 方案概述

在 `CustomRuleConfig.vue` 的 `submitForm()` 最前置增加安全增强规则检测与购买确认弹窗，检测逻辑与后端分类规则对齐（`ruleTages` 包含 `security_enhance`）。

## 架构决策

### 前端（openlibing-web）

| 决策 | 说明 | 原因 |
|------|------|------|
| 前端本地判定（方案 A） | 用 `handleSubmitData()` 产出的最终 `ruleIds` 与已加载 `ruleList` 匹配 `ruleTages` | 用户可勾选的规则必然在已加载列表中；零额外请求。已评估方案 B（保存前调接口反查全量标签），因复杂度高、覆盖的是用户不可见规则而放弃 |
| 挂载点在 `submitForm()` 最前置 | 购买确认先于"复制到社区"确认弹窗 | 三种保存场景（add/copy/config）共用单一入口，统一拦截 |
| 后端判定依据 `ruleTages` | 接口返回的单条规则无独立 `ruleSecurity` 字段；后端 `RuleDelegateImpl#filterByCriteria` 用 `ruleTages.toLowerCase().contains("security_enhance")` 分类 | 与后端逻辑保持一致，避免前后端分类口径不一致 |
| 纯前端确认，不调购买接口 | 信任用户"已购买"确认 | 平台暂无购买状态查询接口，需求也仅要求提示确认 |

### 后端（openlibing-codecheck）

| 决策 | 说明 | 原因 |
|------|------|------|
| 业务层修复，不动公共层（方案 2） | 只改 `customTaskRuleSet` / `listCriterions` 两个业务方法，`signAndExecute` 归一化逻辑不变 | `CC.00050006` 是通用码，"未购买"仅存在于 `error_msg` 文本中，保留 `error_code` 也无法精确分支；改公共层波及 4 处消费点（`getTaskProgress/Summary/Details` 会出现错误消息质量回退，`getTaskCmetrics` 日志行为变化） |
| 字符串匹配识别 | `error_msg.contains("未购买安全增强包")` | 华为云未提供结构化的购买状态错误码，`service_error_msg` 嵌在 `error_msg` 文本内，字符串匹配是唯一可行方式（仓内已有先例：`re.contains("language非法或无效")`） |
| 抛 `BusinessException` 传递友好消息 | 翻译为中文提示（含"请先购买增强规则集包"），原始 `error_msg` 进日志 | `BusinessException(errorMessage, code)` 是仓内既有错误传递机制，`callCustomTaskRuleSet` 已有捕获先例，前端 `ElMessage.error(res.message)` 直接可用 |
| `Integer.parseInt` 加固 | try-catch 兜底 500 | 消除非数字错误码触发 `NumberFormatException` 的隐患（当前靠公共层丢弃 `error_code` 间接兜底，属脆弱依赖） |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/children/CustomRuleConfig.vue` | 修改 | 新增检测函数 + 重构 `submitForm()` 增加弹窗前置拦截（约 40 行） |
| `openlibing-codecheck .../common/utils/codecheck/RestCodeCheckUtil.java` | 修改 | `customTaskRuleSet` 错误分支识别+加固；`listCriterions` 错误体透出（签名加 `throws BusinessException`） |
| `openlibing-codecheck .../business/impl/RuleDelegateImpl.java` | 修改 | `getAccountRulesBySet` 捕获 `BusinessException` 透出真实原因（替代"获取规则列表失败"） |
| 对应测试文件 | 修改 | `RestCodeCheckUtilTest` 补错误分支用例 |

## 实现要点

前端：

1. 新增 `getSecurityEnhanceRules(ruleIdsStr)`：解析最终保存的 `ruleIds` 字符串，在 `ruleList` 中筛选 `ruleTages?.toLowerCase().includes('security_enhance')` 的规则
2. `submitForm()` 重构为：先构建 `doSubmit()`（内含原复制确认 + 提交逻辑），保存前检测，命中则 `ElMessageBox.confirm`（确认 → `doSubmit()`；取消 → 静默中断），未命中直接 `doSubmit()`
3. 弹窗文案含命中规则条数，按钮：`已购买，继续保存` / `未购买`，type: warning，与页面现有弹窗风格一致

后端：

4. `customTaskRuleSet` 错误分支：提取 `errorCode`/`errorMsg` 后记录 error 日志（保留原始报错可追溯）；`errorMsg` 含"未购买安全增强包"→ 抛 `BusinessException("规则集包含代码检查安全增强类规则，请先购买增强规则集包后再保存", 500)`；`Integer.parseInt` 用 try-catch 包裹，`NumberFormatException` 兜底 500
5. `listCriterions`：`CriterionResponse.result` 为 null 时二次解析错误体，`error_msg` 含"未购买安全增强包"→ 抛友好 `BusinessException`（方法签名追加 `throws BusinessException`，唯一调用方同步适配）
6. `getAccountRulesBySet`：捕获 `BusinessException` → `MultiResponse().code(e.getCode()).message(e.getErrorMessage())`（与 `callCustomTaskRuleSet` 既有模式一致）

## 风险 & 缓解

- 已知局限：基于规则集带入但未加载到当前分页的规则不在前端检测范围内（用户未见过/未勾选这些规则，符合交互实际）；如需全量覆盖需后端支持，本期不做
- 前端行为变化风险：新增弹窗可能影响既有保存操作路径 → 验收标准保证未勾选增强规则时行为与现状完全一致
- 后端字符串匹配脆弱性：华为云若调整 `error_msg` 文案会失配 → 失配时回退现状（原样透传/通用失败文案），不劣于当前行为；匹配子串取核心词"未购买安全增强包"
- `listCriterions` 签名变更（checked exception）：全仓仅 1 个调用方（已核对），编译期即可确认无遗漏

## 跨仓影响

- openlibing-web 与 openlibing-codecheck 通过现有 HTTP 接口交互，**接口契约不变**：codecheck 仅改变错误场景下的 `message` 文案与不再触发 `NumberFormatException`，响应结构（`{code, message}`）不变
- 前端无需为后端改动做适配（`ElMessage.error(res.message)` 已能展示友好文案）
