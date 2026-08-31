# security-enhance-purchase-confirm — 技术设计

## 方案概述

在 `CustomRuleConfig.vue` 保存按钮旁增加安全增强规则实时提示框（“增强规则集包”文字内嵌华为云订阅链接，region 动态取自社区对接的华为云项目），检测逻辑与后端分类规则对齐（`ruleTages` 包含 `security_enhance`）。提示仅引导、不阻断保存，未购买时的兜底由后端错误翻译承担。

> 方案变更记录（2026-08-24，用户确认）：
> ① 初版为保存时 `ElMessageBox` 购买确认弹窗（已购买→继续 / 未购买→中断），后改为按钮旁常驻提示框 + 华为云链接，不再拦截保存；
> ② 文案与链接改版：文案改为 `包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`（不再显示条数），链接挂在“增强规则集包”上，指向华为云订阅页 `https://console.huaweicloud.com/devcloud/?region=<region>#/subscribe/apply?packageType=feature&version=`，`region` 来自 `/openlibing-framework/project/get-project-detail-info` 的 `data.hwProjectEntity.region`，缺省 `cn-southwest-2`。

## 架构决策

### 前端（openlibing-web）

| 决策                                              | 说明                                                                                                                                                  | 原因                                                                                                                                       |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 前端本地判定（方案 A）                            | 用 `handleSubmitData()` 产出的最终 `ruleIds` 与已加载 `ruleList` 匹配 `ruleTages`                                                                     | 用户可勾选的规则必然在已加载列表中；零额外请求。已评估方案 B（调接口反查全量标签），因复杂度高、覆盖的是用户不可见规则而放弃               |
| `computed` 实时联动（方案更新）                   | `securityEnhanceRules = computed(() => getSecurityEnhanceRules(handleSubmitData().ruleIds))`                                                          | 提示框随勾选实时增删，比保存时弹窗更早触达用户；`handleSubmitData` 为纯计算无副作用，依赖的 `newRule`/`oldRule`/`enableRuleIds` 均为响应式 |
| 提示框挂载在保存按钮旁（`cl-submit` flex 容器内） | warning `el-alert`，文案 `包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`，其中“增强规则集包”为 `el-link` 指向华为云订阅页（新窗口打开）    | 用户视线焦点即保存按钮，提示触达最直接；`cl-submit` 已有 `cl-new-num` 提示先例，风格延续                                                   |
| 购买链接 region 动态获取                          | 页面初始化时调 `getProjectDetailInfo` 取 `data.hwProjectEntity.region`，拼接进订阅链接；获取失败/未绑定华为云项目时用默认 `cn-southwest-2`            | 订阅页 URL 的 region 必须与社区实际对接的华为云区域一致，硬编码会在其他区域社区跳错                                                        |
| 提示不阻断保存                                    | `submitForm()` 恢复原流程（保留复制确认弹窗）                                                                                                         | 购买与否由用户决策，强拦截体验差；未购买时后端华为云错误翻译兜底                                                                           |
| 后端判定依据 `ruleTages`                          | 接口返回的单条规则无独立 `ruleSecurity` 字段；后端 `RuleDelegateImpl#filterByCriteria` 用 `ruleTages.toLowerCase().contains("security_enhance")` 分类 | 与后端逻辑保持一致，避免前后端分类口径不一致                                                                                               |
| 纯前端提示，不调购买接口                          | 只做引导展示                                                                                                                                          | 平台暂无购买状态查询接口                                                                                                                   |

### 后端（openlibing-codecheck）

| 决策                                | 说明                                                                                      | 原因                                                                                                                                                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 业务层修复，不动公共层（方案 2）    | 只改 `customTaskRuleSet` / `listCriterions` 两个业务方法，`signAndExecute` 归一化逻辑不变 | `CC.00050006` 是通用码，"未购买"仅存在于 `error_msg` 文本中，保留 `error_code` 也无法精确分支；改公共层波及 4 处消费点（`getTaskProgress/Summary/Details` 会出现错误消息质量回退，`getTaskCmetrics` 日志行为变化） |
| 字符串匹配识别                      | `error_msg.contains("未购买安全增强包")`                                                  | 华为云未提供结构化的购买状态错误码，`service_error_msg` 嵌在 `error_msg` 文本内，字符串匹配是唯一可行方式（仓内已有先例：`re.contains("language非法或无效")`）                                                     |
| 抛 `BusinessException` 传递友好消息 | 翻译为中文提示（含"请先购买增强规则集包"），原始 `error_msg` 进日志                       | `BusinessException(errorMessage, code)` 是仓内既有错误传递机制，`callCustomTaskRuleSet` 已有捕获先例，前端 `ElMessage.error(res.message)` 直接可用                                                                 |
| `Integer.parseInt` 加固             | try-catch 兜底 500                                                                        | 消除非数字错误码触发 `NumberFormatException` 的隐患（当前靠公共层丢弃 `error_code` 间接兜底，属脆弱依赖）                                                                                                          |

## 涉及文件

| 文件                                                                                         | 操作 | 说明                                                                                                             |
| -------------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/children/CustomRuleConfig.vue` | 修改 | 新增检测函数 + `securityEnhanceRules` computed + 保存按钮旁提示框（`cl-submit` 区域），`submitForm()` 保持原流程 |
| `openlibing-codecheck .../common/utils/codecheck/RestCodeCheckUtil.java`                     | 修改 | `customTaskRuleSet` 错误分支识别+加固；`listCriterions` 错误体透出（签名加 `throws BusinessException`）          |
| `openlibing-codecheck .../business/impl/RuleDelegateImpl.java`                               | 修改 | `getAccountRulesBySet` 捕获 `BusinessException` 透出真实原因（替代"获取规则列表失败"）                           |
| 对应测试文件                                                                                 | 修改 | `RestCodeCheckUtilTest` 补错误分支用例                                                                           |

## 实现要点

前端：

1. 新增 `getSecurityEnhanceRules(ruleIdsStr)`：解析最终保存的 `ruleIds` 字符串，在 `ruleList` 中筛选 `ruleTages?.toLowerCase().includes('security_enhance')` 的规则
2. 新增 `securityEnhanceRules` computed：基于 `handleSubmitData().ruleIds` 实时计算命中规则列表，随勾选/取消联动
3. `cl-submit` 区域（保存按钮后）插入 `el-alert`（type: warning，show-icon，不可关闭）：文案 `包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`，其中“增强规则集包”为 `el-link`（`type: 'primary'`，`target="_blank"`，`:href="securityEnhancePurchaseUrl"`）；配套样式 `.cl-security-enhance-tip`（flex 内不撑满、紧凑 padding）
4. 购买链接动态拼接：`init()` 时调 `getProjectDetailInfo({ params: { projectId } })`，取 `res.data.hwProjectEntity.region` 写入 `hwRegion`（缺省 `cn-southwest-2`）；`securityEnhancePurchaseUrl = computed(() => `https://console.huaweicloud.com/devcloud/?region=${hwRegion.value}#/subscribe/apply?packageType=feature&version=`)`，请求失败静默回退默认区域
5. `submitForm()` 不做拦截：保持原有提交与复制确认逻辑

后端：

6. `customTaskRuleSet` 错误分支：提取 `errorCode`/`errorMsg` 后记录 error 日志（保留原始报错可追溯）；`errorMsg` 含"未购买安全增强包"→ 抛 `BusinessException("规则集包含代码检查安全增强类规则，请先购买增强规则集包后再保存", 500)`；`Integer.parseInt` 用 try-catch 包裹，`NumberFormatException` 兜底 500
7. `listCriterions`：`CriterionResponse.result` 为 null 时二次解析错误体，`error_msg` 含"未购买安全增强包"→ 抛友好 `BusinessException`（方法签名追加 `throws BusinessException`，唯一调用方同步适配）
8. `getAccountRulesBySet`：捕获 `BusinessException` → `MultiResponse().code(e.getCode()).message(e.getErrorMessage())`（与 `callCustomTaskRuleSet` 既有模式一致）

## 风险 & 缓解

- 已知局限：基于规则集带入但未加载到当前分页的规则不在前端检测范围内（用户未见过/未勾选这些规则，符合交互实际）；如需全量覆盖需后端支持，本期不做
- 前端行为变化风险：新增提示框可能影响既有保存区域布局 → 提示仅在命中增强规则时渲染，未勾选时 DOM 不出现，保存路径零改动；`cl-submit` 为 flex 布局，提示框样式约束为不撑满（`flex:none; width:auto`）
- 华为云购买链接可配置性：订阅页 URL 除 `region` 外固定，`region` 运行时从项目详情接口获取（缺省 `cn-southwest-2`）→ 若后续有专属购买页 URL，仅需改 `securityEnhancePurchaseUrl` computed（单处）
- region 获取失败风险：社区未绑定华为云项目（`hwProjectEntity` 为空）或接口失败 → 静默回退默认区域 `cn-southwest-2`，提示框与保存功能不受影响
- 后端字符串匹配脆弱性：华为云若调整 `error_msg` 文案会失配 → 失配时回退现状（原样透传/通用失败文案），不劣于当前行为；匹配子串取核心词"未购买安全增强包"
- `listCriterions` 签名变更（checked exception）：全仓仅 1 个调用方（已核对），编译期即可确认无遗漏

## 跨仓影响

- openlibing-web 与 openlibing-codecheck 通过现有 HTTP 接口交互，**接口契约不变**：codecheck 仅改变错误场景下的 `message` 文案与不再触发 `NumberFormatException`，响应结构（`{code, message}`）不变
- 前端无需为后端改动做适配（`ElMessage.error(res.message)` 已能展示友好文案）
