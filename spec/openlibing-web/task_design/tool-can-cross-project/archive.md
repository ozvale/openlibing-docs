# tool-can-cross-project — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-framework/issues/82
- 业务 PR: https://gitcode.com/openlibing/openlibing-web/pulls/685
- docs PR: <待创建后补齐>

## 交付历程

- commit `42dfe0742a29aad589426677839c4123deb2467c`: 工具管理-增加跨社区是否审核标识 — 新增 `canCrossProject` 列配置、`el-switch` 渲染、二次确认与接口调用、表单校验规则
- commit `9ee5e2d19c146d6e535fe1ec6e572356d6bae444`: 工具管理-增加跨社区是否审核标识联调 — 联调修复

## 用户自测反馈

无返工，一次交付通过。

## 最终验证

- 工具版本列表新增「跨项目使用该工具版本是否需审核」列，开关状态正确 ✅
- 切换开关弹出二次确认，确认后接口更新成功，列表自动刷新 ✅
- 取消二次确认时开关状态回滚，提示「已取消」 ✅
- 表单 `canCrossProject` 必填校验生效 ✅
- 「创建时间」列正确显示 ✅
- 操作列宽度自适应 ✅

## 设计偏差与取舍

- 原始 commit message 中描述为「跨社区是否审核标识」，实际字段名为 `canCrossProject`，业务语义为「跨项目使用该工具版本是否需审核」。spec 文档以代码实现为准，统一使用 `canCrossProject` / 跨项目审核。
- 无其他偏差。

## 可复用经验

- `el-switch` 的 `before-change` 属性返回 Promise reject 时，Element Plus 会自动回滚开关状态，无需手动同步 `v-model` 绑定值。这一机制非常适合「切换需二次确认」的场景。
- 表格列配置中，列标题较长时（如 15 字以上）需显式设置 `width`，否则表头会换行显示影响美观。

## 归档日期

2026-08-12
