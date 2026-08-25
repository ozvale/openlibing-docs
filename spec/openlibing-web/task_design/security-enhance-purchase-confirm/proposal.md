# security-enhance-purchase-confirm

> 关联业务 Issue: https://gitcode.com/openlibing/openlibing-web/issues/275

## 需求背景

“代码检查安全增强”类规则属于付费增强能力，需优先购买增强规则集包后方可使用。当前规则集配置页保存时不做任何购买确认，未购买用户可能保存了无法生效的规则集。

**范围扩展（2026-08-24，用户确认）**：华为云在未购买时会返回错误 `{"error_code":"CC.00050006","error_msg":"... service_error_msg is: 未购买安全增强包"}`，后端 codecheck 仓当前未识别该错误：保存路径把原始英文拼接串透传给前端，查询路径则把真实原因吞掉（“获取规则列表失败”）。经用户确认，后端修复复用本 Issue，不新建。

## 功能描述

### 前端（openlibing-web，已交付；2026-08-24/25 四次方案更新：弹窗改为常驻提示；文案与购买链接改版；提示框移至“规则集配置”标题栏；链接改为固定华为云定价文档）

在规则集配置页（新增 / 复制 / 修改三种场景共用）：

1. 实时检测当前生效的规则中是否包含“代码检查安全增强”类规则（判定依据：规则标签 `ruleTages` 包含 `security_enhance`，与后端 `RuleDelegateImpl` 分类逻辑一致；基于 `handleSubmitData()` 产出的最终 `ruleIds` 计算，随勾选实时联动）
2. 若包含，在“规则集配置”标题栏中间空白区（位于“规则集配置”与“导入规则”按钮之间）显示 warning 提示框：`包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`，其中“增强规则集包”为华为云购买说明链接（固定 URL：`https://support.huaweicloud.com/price-devcloud/codearts_29_0016.html`，新窗口打开，不依赖任何接口）
3. 提示仅作引导，**不阻断保存**：保存流程恢复原状（复制到社区场景仍走已有复制确认弹窗）；未购买时的兜底拦截由后端华为云错误翻译承担

### 后端（openlibing-codecheck，新增）

1. `RestCodeCheckUtil#customTaskRuleSet`（保存规则集路径）：识别华为云错误 `error_msg` 含“未购买安全增强包”时，抛出友好中文 `BusinessException`；同时加固错误码解析（`Integer.parseInt` 对非数字错误码兜底 500）
2. `RestCodeCheckUtil#listCriterions`（规则列表查询路径）：错误响应不再吞掉，识别“未购买安全增强包”时抛友好 `BusinessException`，调用方 `RuleDelegateImpl#getAccountRulesBySet` 透出真实原因
3. **不动公共层**：`signAndExecute`/`signAndExecuteWithException` 的错误体归一化逻辑保持不变（`CC.00050006` 为通用码，保留也无法精确分支；改公共层会波及 4 处消费点）

不做的事：

- 不调用购买状态接口做强制校验（前端仅提示引导；后端仅在华为云实际报错时翻译兜底）
- 不阻断勾选与保存行为（提示常驻展示，由用户自行决定购买或取消勾选）
- 不修改华为云错误体归一化公共逻辑

## 验收标准

前端：

- [ ] 勾选安全增强类规则后，“规则集配置”标题栏中间空白区（“规则集配置”与“导入规则”之间）实时出现 warning 提示框：`包含“代码检查安全增强”类规则，请确保已购买增强规则集包。`，“增强规则集包”可点击跳转华为云购买说明页（固定链接，新窗口打开）
- [ ] 取消勾选后提示框实时消失
- [ ] 提示不阻断保存：点击保存正常走原有流程（含复制确认弹窗）
- [ ] 未勾选安全增强类规则时不出现提示框，行为与现状一致
- [ ] 修改/复制场景同样生效

后端：

- [ ] 保存规则集时华为云返回“未购买安全增强包”错误，前端收到友好中文提示（非原始英文拼接串）
- [ ] 查询规则列表时同样错误不再显示“获取规则列表失败”，而是真实原因的友好提示
- [ ] 非数字错误码（如 `CC.00050006`）不再触发 `NumberFormatException`
- [ ] 其余错误路径行为与现状一致（原样透传 `error_msg`）
- [ ] 单元测试覆盖上述分支

## 影响范围

- 仓：openlibing-web（单文件）+ openlibing-codecheck（2 个文件 + 测试）
- web：`apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/children/CustomRuleConfig.vue`
- codecheck：`src/main/java/com/openlibing/codecheck/common/utils/codecheck/RestCodeCheckUtil.java`、`src/main/java/com/openlibing/codecheck/business/impl/RuleDelegateImpl.java` 及对应测试
