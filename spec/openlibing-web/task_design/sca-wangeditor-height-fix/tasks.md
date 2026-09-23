# sca-wangeditor-height-fix — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 在 `editor.create()` 前通过 `editor.config.height` 设置编辑区高度（含原因注释）
- [x] Task 2: 移除 create 后对容器 `style.height` 的 DOM 分支设置，`minHeight` 逻辑内联 `dom` 查询保持不变
- [x] Task 3: 验证内容超出高度时编辑区可滚动查看全部内容，ESLint 无新增错误

## 交付记录

- 业务 commit：6bb7b506 fix(sca): set wangEditor height via config before create（分支 feature-sca-inspection）
- 业务 PR：https://gitcode.com/openlibing/openlibing-web/merge_requests/801（base: release_20260923）
- 关联 Issue：openlibing/openlibing-web#303
