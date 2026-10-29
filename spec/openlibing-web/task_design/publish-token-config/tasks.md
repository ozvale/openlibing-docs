# Tasks: publish-token-config

## Phase 1 调研

- [x] T1 确认交互参照：发布设置页「中心仓配置」模块的列表/弹窗/操作交互
- [x] T2 确认表格列与表单字段（联调后端后对齐）：tokenType / login / tokenMasked / creatorName / createTime
- [x] T3 确认接口占位路径：`/config/{query,add,update,delete}PublishTokenInfo`

## Phase 2 实现步骤

- [x] T4 `PlatformRelease/url.ts` 新增 4 个接口常量
- [x] T5 `PlatformRelease/api.ts` 新增 4 个 `RequestFunc` 封装
- [x] T6 新建 `publishTokenTable.vue`：列表查询 + 表格列 + 操作列（编辑/删除图标）
- [x] T7 新建/编辑弹窗：令牌类型选择框（gitee/gitcode）、账号用户名、账号令牌（`token`），三项必填
- [x] T8 编辑回显时令牌类型禁用修改
- [x] T9 删除操作：二次确认后调删除接口
- [x] T10 批量删除按钮（含 `v-uem-record` 埋点），未勾选提示「请选择至少一条数据」
- [x] T11 `publishSetting/index.vue` 左侧新增第三个 listBox 菜单 + 右侧条件渲染

## Phase 3 验证

- [x] T12 pre-commit 全钩子通过
- [x] T13 三点 diff 验证：4 文件 +339/-3，无基底污染（merge-base 为 master !818）
- [x] T14 用户自测：菜单切换、增删改查、批量删除、表单必填校验正常

## Phase 4 业务 PR

- [x] T15 推送 `lt-platform10-2` 分支到 fork 仓（`liting_0916/openlibing-web`）
- [x] T16 创建业务 PR（base: `release_20261019`，head: `liting_0916:lt-platform10-2`）→ [PR #821](https://gitcode.com/openlibing/openlibing-web/merge_requests/821)
- [x] T17 补打 `ai-assisted` 标签
- [ ] T18 在 [openlibing-platform-release Issue #63](https://gitcode.com/openlibing/openlibing-platform-release/issues/63) 页面手动关联 PR（GitCode CLI 不支持跨仓 PR 关联）

## Phase 5 归档

- [ ] T19 业务 PR 合入后，生成 `archive.md` 沉淀经验
- [ ] T20 通过 docs PR 提交归档（关联业务 Issue）

## Commit 关联表

| Task    | Commit      | 说明                           |
| ------- | ----------- | ------------------------------ |
| T4-T11  | `8e3b70a9e` | 发布令牌配置模块主体           |
| T10     | `8142d4ce0` | 批量删除 + 表单字段对齐后端    |
| T14     | -           | 用户自测（含模块高度样式调整） |
| T15-T17 | -           | 业务 PR #821 创建              |
| T18-T20 | 待执行      | 手动关联 + 归档                |

Generated-by: GLM-5.3
