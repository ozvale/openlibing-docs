# security-enhance-purchase-confirm — 实现任务

## 进度: 14/14 complete

### 前端（openlibing-web，已完成）

- [x] Task 1: 在 `openlibing-web` 新建开发分支 `feat-security-enhance-purchase-confirm`（基于 `origin/master`）
- [x] Task 2: `CustomRuleConfig.vue` 新增 `getSecurityEnhanceRules()` 检测函数
- [x] Task 3: ~~重构 `submitForm()` 前置购买确认弹窗~~ → **Task 11 方案变更**：`submitForm()` 恢复原流程，改为保存按钮旁常驻提示框
- [x] Task 4: 验证 — ESLint（改动文件）通过；vue-tsc 全量为存量问题（与本需求无关，已核实）

### 后端（openlibing-codecheck，2026-08-24 范围扩展，已完成）

- [x] Task 5: 在 `openlibing-codecheck` 新建开发分支 `feat-security-enhance-purchase-confirm`（基于 `origin/master`）
- [x] Task 6: `RestCodeCheckUtil#customTaskRuleSet` 错误分支：原始报错日志 + "未购买安全增强包"识别翻译 + `Integer.parseInt` 加固
- [x] Task 7: `RestCodeCheckUtil#listCriterions` 错误体识别（签名加 `throws BusinessException`）+ `RuleDelegateImpl#getAccountRulesBySet` 捕获透出
- [x] Task 8: 测试补充 — `RestCodeCheckUtilTest` 新增 3 用例（未购买×2、非数字错误码），`RuleDelegateImplTest` 8 用例适配签名
- [x] Task 9: 验证 — `mvn test` 通过（RestCodeCheckUtilTest + RuleDelegateImplTest）
- [x] Task 10: 更新 docs 分支 spec（后端设计扩充）并交付后端 diff 摘要

### 方案变更（2026-08-24，用户确认）

- [x] Task 11: 前端交互从"保存时确认弹窗"改为"保存按钮旁常驻提示框（不阻断保存）"：新增 `securityEnhanceRules` computed、`cl-submit` 区域 `el-alert` + `el-link`、`.cl-security-enhance-tip` 样式；ESLint 通过；demo 已按新方案更新并经用户验证通过
- [x] Task 12（2026-08-24 二次变更）：文案改为 `包含"代码检查安全增强"类规则，请确保已购买增强规则集包。`（不再显示条数）；链接挂在"增强规则集包"上，URL 改为 `https://console.huaweicloud.com/devcloud/?region=<region>#/subscribe/apply?packageType=feature&version=`，`region` 经 `getProjectDetailInfo`（`/openlibing-framework/project/get-project-detail-info`）取 `data.hwProjectEntity.region`，缺省 `cn-southwest-2`；ESLint 通过
- [x] Task 13（2026-08-25 三次变更，用户确认"保存旁不好看"）：提示框从 `cl-submit` 保存区移至"规则集配置"标题栏（`rule-config-main` 的 `.subTitle`）中间空白区（位于"规则集配置"与"导入规则"之间，`space-between` 三段式布局）；`.cl-security-enhance-tip` 样式随迁（保留基线对齐修正），`cl-submit` 恢复主干原样；ESLint 通过；demo 同步更新
- [x] Task 14（2026-08-25 四次变更，用户确认）：购买链接放弃 region 动态拼接，改为固定 URL `https://support.huaweicloud.com/price-devcloud/codearts_29_0016.html`（华为云定价文档）；删除 `getHwRegion()`/`hwRegion`/`securityEnhancePurchaseUrl`/`DEFAULT_HW_REGION` 与 `getProjectDetailInfo` 导入及 `init()` 调用，新增常量 `SECURITY_ENHANCE_PURCHASE_URL`；ESLint 通过；demo 同步更新

## 验证方式

- 前端：ESLint 通过（本仓无单测基础设施，vue-tsc 全量为存量问题）；交互逻辑经独立 demo（Vue3 + Element Plus 复刻生产判定逻辑）演示并获用户验证通过
- 后端：Maven 单测（RestCodeCheckUtilTest 新增用例 + 既有用例回归）+ 全量编译
