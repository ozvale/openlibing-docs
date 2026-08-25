# security-enhance-purchase-confirm — 技术设计

## 方案概述

在 `CustomRuleConfig.vue` “规则集配置”标题栏中间空白区（“规则集配置”与“导入规则”按钮之间）增加安全增强规则实时提示框（“增强规则集包”文字内嵌华为云购买说明固定链接），检测逻辑与后端分类规则对齐（`ruleTages` 包含 `security_enhance`）。提示仅引导、不阻断保存，未购买时的兜底由后端错误翻译承担。

> 方案变更记录（2026-08-24/25，用户确认）：① 初版为保存时 `ElMessageBox` 购买确认弹窗（已购买→继续 / 未购买→中断），后改为常驻提示框 + 华为云链接，不再拦截保存；
> ② 文案与链接改版：文案改为 `包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`（不再显示条数），链接挂在“增强规则集包”上；
> ③ 位置调整：提示框从保存按钮旁（`cl-submit`）移至“规则集配置”标题栏（`rule-config-main` 的 `.subTitle`）中间空白区，位于“规则集配置”与“导入规则”按钮之间；
> ④ 链接定版：曾设计 region 动态拼接订阅页 URL（取项目详情接口 `hwProjectEntity.region`），后按用户要求改为固定链接 `https://support.huaweicloud.com/price-devcloud/codearts_29_0016.html`（华为云定价文档），不依赖任何接口。

## 架构决策

### 前端（openlibing-web）

| 决策                                                                                                                                            | 说明                                                                                                                                                  | 原因                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 前端本地判定（方案 A）                                                                                                                          | 用 `handleSubmitData()` 产出的最终 `ruleIds` 与已加载 `ruleList` 匹配 `ruleTages`                                                                     | 用户可勾选的规则必然在已加载列表中；零额外请求。已评估方案 B（调接口反查全量标签），因复杂度高、覆盖的是用户不可见规则而放弃               |
| `computed` 实时联动（方案更新）                                                                                                                 | `securityEnhanceRules = computed(() => getSecurityEnhanceRules(handleSubmitData().ruleIds))`                                                          | 提示框随勾选实时增删，比保存时弹窗更早触达用户；`handleSubmitData` 为纯计算无副作用，依赖的 `newRule`/`oldRule`/`enableRuleIds` 均为响应式 |
| 提示框挂载在“规则集配置”标题栏中间空白区（`rule-config-main` 的 `.subTitle`，`space-between` 三段式布局，位于“规则集配置”与“导入规则”按钮之间） | warning `el-alert`，文案 `包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`，其中“增强规则集包”为 `el-link` 指向华为云订阅页（新窗口打开）    | 保存按钮旁空间局促影响美观；标题栏中间有大片空白，提示在页面加载勾选后即持续可见，且不与保存区新开/新关条数提示相互挤占                    |
| 购买链接固定 URL（常量 `SECURITY_ENHANCE_PURCHASE_URL`）                                                                                        | `https://support.huaweicloud.com/price-devcloud/codearts_29_0016.html`（华为云定价文档，新窗口打开）                                                  | 用户指定；零接口依赖、零失败分支，后续换链接只改常量单处                                                                                   |
| 提示不阻断保存                                                                                                                                  | `submitForm()` 恢复原流程（保留复制确认弹窗）                                                                                                         | 购买与否由用户决策，强拦截体验差；未购买时后端华为云错误翻译兜底                                                                           |
| 后端判定依据 `ruleTages`                                                                                                                        | 接口返回的单条规则无独立 `ruleSecurity` 字段；后端 `RuleDelegateImpl#filterByCriteria` 用 `ruleTages.toLowerCase().contains("security_enhance")` 分类 | 与后端逻辑保持一致，避免前后端分类口径不一致                                                                                               |
| 纯前端提示，不调购买接口                                                                                                                        | 只做引导展示                                                                                                                                          | 平台暂无购买状态查询接口                                                                                                                   |

### 后端（openlibing-codecheck）

| 决策                                | 说明                                                                                      | 原因                                                                                                                                                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 业务层修复，不动公共层（方案 2）    | 只改 `customTaskRuleSet` / `listCriterions` 两个业务方法，`signAndExecute` 归一化逻辑不变 | `CC.00050006` 是通用码，"未购买"仅存在于 `error_msg` 文本中，保留 `error_code` 也无法精确分支；改公共层波及 4 处消费点（`getTaskProgress/Summary/Details` 会出现错误消息质量回退，`getTaskCmetrics` 日志行为变化） |
| 字符串匹配识别                      | `error_msg.contains("未购买安全增强包")`                                                  | 华为云未提供结构化的购买状态错误码，`service_error_msg` 嵌在 `error_msg` 文本内，字符串匹配是唯一可行方式（仓内已有先例：`re.contains("language非法或无效")`）                                                     |
| 抛 `BusinessException` 传递友好消息 | 翻译为中文提示（含"请先购买增强规则集包"），原始 `error_msg` 进日志                       | `BusinessException(errorMessage, code)` 是仓内既有错误传递机制，`callCustomTaskRuleSet` 已有捕获先例，前端 `ElMessage.error(res.message)` 直接可用                                                                 |
| `Integer.parseInt` 加固             | try-catch 兜底 500                                                                        | 消除非数字错误码触发 `NumberFormatException` 的隐患（当前靠公共层丢弃 `error_code` 间接兜底，属脆弱依赖）                                                                                                          |

## 涉及文件

| 文件                                                                                         | 操作 | 说明                                                                                                               |
| -------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------ |
| `apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/children/CustomRuleConfig.vue` | 修改 | 新增检测函数 + `securityEnhanceRules` computed + 标题栏提示框（`.subTitle` 中间空白区），`submitForm()` 保持原流程 |
| `openlibing-codecheck .../common/utils/codecheck/RestCodeCheckUtil.java`                     | 修改 | `customTaskRuleSet` 错误分支识别+加固；`listCriterions` 错误体透出（签名加 `throws BusinessException`）            |
| `openlibing-codecheck .../business/impl/RuleDelegateImpl.java`                               | 修改 | `getAccountRulesBySet` 捕获 `BusinessException` 透出真实原因（替代"获取规则列表失败"）                             |
| 对应测试文件                                                                                 | 修改 | `RestCodeCheckUtilTest` 补错误分支用例                                                                             |

## 实现要点

前端：

1. 新增 `getSecurityEnhanceRules(ruleIdsStr)`：解析最终保存的 `ruleIds` 字符串，在 `ruleList` 中筛选 `ruleTages?.toLowerCase().includes('security_enhance')` 的规则
2. 新增 `securityEnhanceRules` computed：基于 `handleSubmitData().ruleIds` 实时计算命中规则列表，随勾选/取消联动
3. `.subTitle` 标题栏（“规则集配置”与“导入规则”按钮之间）插入 `el-alert`（type: warning，show-icon，不可关闭）：文案 `包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`，其中“增强规则集包”为 `el-link`（`type: 'primary'`，`target="_blank"`，`:href="SECURITY_ENHANCE_PURCHASE_URL"` 固定链接）；配套样式 `.cl-security-enhance-tip`（flex 内不撑满、紧凑 padding、内嵌 `el-link` 基线对齐、背景/边框/文字配色与“新启用/新停用”条数提示 `.cl-new-num`（rules.less）一致）
4. `submitForm()` 不做拦截：保持原有提交与复制确认逻辑

后端：

5. `customTaskRuleSet` 错误分支：提取 `errorCode`/`errorMsg` 后记录 error 日志（保留原始报错可追溯）；`errorMsg` 含"未购买安全增强包"→ 抛 `BusinessException("规则集包含代码检查安全增强类规则，请先购买增强规则集包后再保存", 500)`；`Integer.parseInt` 用 try-catch 包裹，`NumberFormatException` 兜底 500
6. `listCriterions`：`CriterionResponse.result` 为 null 时二次解析错误体，`error_msg` 含"未购买安全增强包"→ 抛友好 `BusinessException`（方法签名追加 `throws BusinessException`，唯一调用方同步适配）
7. `getAccountRulesBySet`：捕获 `BusinessException` → `MultiResponse().code(e.getCode()).message(e.getErrorMessage())`（与 `callCustomTaskRuleSet` 既有模式一致）

## 风险 & 缓解

- 已知局限：基于规则集带入但未加载到当前分页的规则不在前端检测范围内（用户未见过/未勾选这些规则，符合交互实际）；如需全量覆盖需后端支持，本期不做
- 前端行为变化风险：新增提示框可能影响既有标题栏布局 → 提示仅在命中增强规则时渲染，未勾选时 DOM 不出现，保存区（`cl-submit`）零改动；`.subTitle` 为 `space-between` flex 布局，提示框样式约束为不撑满（`flex:none; width:auto`），不挤压“规则集配置”与“导入规则”
- 华为云购买链接可维护性：链接为固定常量 `SECURITY_ENHANCE_PURCHASE_URL` → 华为云若调整文档地址仅需改常量（单处）
- 后端字符串匹配脆弱性：华为云若调整 `error_msg` 文案会失配 → 失配时回退现状（原样透传/通用失败文案），不劣于当前行为；匹配子串取核心词"未购买安全增强包"
- `listCriterions` 签名变更（checked exception）：全仓仅 1 个调用方（已核对），编译期即可确认无遗漏

## 跨仓影响

- openlibing-web 与 openlibing-codecheck 通过现有 HTTP 接口交互，**接口契约不变**：codecheck 仅改变错误场景下的 `message` 文案与不再触发 `NumberFormatException`，响应结构（`{code, message}`）不变
- 前端无需为后端改动做适配（`ElMessage.error(res.message)` 已能展示友好文案）
