# Tasks: project-token-login-parsing

## Phase 1 调研

- [x] T1 确认接口契约：`POST /project/parse-token-login`，data 传 `token`、`platform`
- [x] T2 梳理三平台表单字段命名：`{platform}Token` / `{platform}Login`
- [x] T3 确认返回结构兼容策略：`res.data?.login ?? res.data ?? ''`（联调后可简化）

## Phase 2 实现步骤

- [x] T4 `url.ts` 新增 `PARSE_TOKEN_LOGIN` 常量
- [x] T5 `api.ts` 新增 `parseTokenLogin` POST 封装
- [x] T6 实现 `handleTokenChange(platform)`：空值直通、解析成功回显用户名、静默失败
- [x] T7 三平台（gitee/gitcode/github）令牌输入框 `@change` 接入
- [x] T8 三个「公共账号用户名」表单项移除 `v-if="type === 'edit'"`（新增项目也展示，用户自测确认）
- [x] T9 `toolItem.vue` 图标上传接口两处补传 `projectId`（用户改动随本需求打包提交）

## Phase 3 验证

- [x] T10 pre-commit 全钩子通过
- [x] T11 三点 diff 验证：4 文件 +27/-16，无基底污染（merge-base 为 master !818）
- [x] T12 用户自测：输入令牌后用户名回显正常，新增/编辑项目均生效

## Phase 4 业务 PR

- [x] T13 推送 `lt-project10` 分支到 fork 仓（`liting_0916/openlibing-web`）
- [x] T14 创建业务 PR（base: `release_20261019`，head: `liting_0916:lt-project10`）→ [PR #824](https://gitcode.com/openlibing/openlibing-web/merge_requests/824)
- [x] T15 补打 `ai-assisted` 标签
- [ ] T16 在 [openlibing-framework Issue #116](https://gitcode.com/openlibing/openlibing-framework/issues/116) 页面手动关联 PR（GitCode CLI 不支持跨仓 PR 关联）

## Phase 5 归档

- [ ] T17 业务 PR 合入后，生成 `archive.md` 沉淀经验
- [ ] T18 通过 docs PR 提交归档（关联业务 Issue）

## Commit 关联表

| Task    | Commit      | 说明                                               |
| ------- | ----------- | -------------------------------------------------- |
| T4-T7   | `06b5a6cb3` | 接口封装 + 三平台令牌解析回显                      |
| T8-T9   | `06b5a6cb3` | 用户名展示调整 + 图标上传补 projectId（同 commit） |
| T12     | -           | 用户自测                                           |
| T13-T15 | -           | 业务 PR #824 创建                                  |
| T16-T18 | 待执行      | 手动关联 + 归档                                    |

Generated-by: GLM-5.3
