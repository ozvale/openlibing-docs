# 2026-08-26 用户管理页小屏布局错位修复 - 任务清单

## 实现步骤

- [x] 账号类型表单项 `style="width: 500px"` 改为 `class="account-type-item"`
- [x] 新增 `.account-type-item` 弹性宽度样式（flex: 1 1 280px; min-width: 280px; max-width: 500px）
- [x] `.header` 添加 `flex-wrap: wrap` 与 `row-gap: 12px`
- [x] `.user-form` 添加 `flex: 1 1 auto` + `flex-wrap: wrap` + `row-gap: 12px`
- [x] 表格列设置最小宽度：用户名 min-width=100、组织 min-width=90、用户组 min-width=110、创建时间 min-width=150
- [x] 加宽账号用户名列：gitCode min-width=170、gitee min-width=160、openUBMC 固定 width=220
- [x] 分页组件添加 `:pager-count="5"`
- [x] 提交 commit（`c4bb8a9f`）并推送 `fix-user-layout` 分支
- [x] 创建业务 PR 并关联业务 Issue

## 验证记录

| 场景                       | 结果                                   |
| -------------------------- | -------------------------------------- |
| 小屏窄窗口：账号类型表单项 | 弹性收缩至 280px 下限，不溢出容器      |
| 小屏窄窗口：header 筛选区  | 自动换行，元素间距 12px，无拥挤        |
| 小屏窄窗口：表格列宽       | 列按 min-width 展示，openUBMC 表头完整 |
| 小屏窄窗口：分页           | 一行展示，无换行无横向滚动             |
| 大屏正常窗口               | 布局与原有一致，功能正常               |
