# security-enhance-purchase-confirm

> 关联业务 Issue: https://gitcode.com/openlibing/openlibing-web/issues/275

## 需求背景

“代码检查安全增强”类规则属于付费增强能力，需优先购买增强规则集包后方可使用。当前规则集配置页保存时不做任何购买确认，未购买用户可能保存了无法生效的规则集。

**范围扩展（2026-08-24，用户确认）**：华为云在未购买时会返回错误 `{"error_code":"CC.00050006","error_msg":"... service_error_msg is: 未购买安全增强包"}`，后端 codecheck 仓当前未识别该错误：保存路径把原始英文拼接串透传给前端，查询路径则把真实原因吞掉（“获取规则列表失败”）。经用户确认，后端修复复用本 Issue，不新建。

## 功能描述

### 前端（openlibing-web，已交付）

在规则集配置页（新增 / 复制 / 修改三种保存场景）保存时：

1. 检测本次保存最终启用的规则中是否包含“代码检查安全增强”类规则（判定依据：规则标签 `ruleTages` 包含 `security_enhance`，与后端 `RuleDelegateImpl` 分类逻辑一致）
2. 若包含，弹出确认弹窗：此类规则需优先购买增强规则集包，请确认是否已购买
3. 点击“已购买，继续保存”→ 继续原有保存流程（复制到社区场景继续走已有复制确认弹窗）
4. 点击“未购买”→ 中断保存，不发起保存请求

### 后端（openlibing-codecheck，新增）

1. `RestCodeCheckUtil#customTaskRuleSet`（保存规则集路径）：识别华为云错误 `error_msg` 含“未购买安全增强包”时，抛出友好中文 `BusinessException`；同时加固错误码解析（`Integer.parseInt` 对非数字错误码兜底 500）
2. `RestCodeCheckUtil#listCriterions`（规则列表查询路径）：错误响应不再吞掉，识别“未购买安全增强包”时抛友好 `BusinessException`，调用方 `RuleDelegateImpl#getAccountRulesBySet` 透出真实原因
3. **不动公共层**：`signAndExecute`/`signAndExecuteWithException` 的错误体归一化逻辑保持不变（`CC.00050006` 为通用码，保留也无法精确分支；改公共层会波及 4 处消费点）

不做的事：

- 不调用购买状态接口做强制校验（前端提示信任用户确认；后端仅在华为云实际报错时翻译）
- 不阻断勾选行为（保存时才提示）
- 不修改华为云错误体归一化公共逻辑

## 验收标准

前端：

- [ ] 新增规则集勾选安全增强类规则后保存，弹出购买确认弹窗
- [ ] 点击“已购买，继续保存”，保存流程正常继续（含复制确认弹窗链式场景）
- [ ] 点击“未购买”，中断保存，不发请求，页面停留在配置页
- [ ] 未勾选安全增强类规则时保存，不出现弹窗，行为与现状一致
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

