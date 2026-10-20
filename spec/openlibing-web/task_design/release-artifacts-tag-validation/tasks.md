# Tasks: release-artifacts-tag-validation

## Phase 1 调研

- [x] T1 调研 GitCode 网站新建 tag 的命名校验规则
- [x] T2 梳理 `releaseArtifacts.vue` 两个 tag 输入场景（选择框 allow-create + 输入框）及既有 `handleChange` 联动
- [x] T3 校验规则经三轮迭代与用户对齐（字符集引入 `_.-/` → 结尾限制 → 首字符限制 + 提示文案优化）

## Phase 2 实现步骤

- [x] T4 定义 `TAG_NAME_REG` 正则（负向前瞻实现结尾/连续限制 + 白名单字符集 + 长度限制）
- [x] T5 实现 `handleTagNameChange`：校验失败清空输入 + `ElMessage.error` 完整规则提示，通过后回落 `handleChange`
- [x] T6 选择框 allow-create 场景 `@change` 接入 `handleTagNameChange`
- [x] T7 输入框场景 `@change` 接入 `handleTagNameChange`
- [x] T8 提示文案优化为完整规则描述（用户确认版）

## Phase 3 验证

- [x] T9 pre-commit 全钩子通过
- [x] T10 三点 diff 验证：1 文件 +16/-2，无基底污染（merge-base 为 master !818）
- [x] T11 用户自测：非法输入（连续 `/`、`.lock` 结尾、特殊字符开头等）提示并清空；合法输入流程正常

## Phase 4 业务 PR

- [x] T12 推送 `lt-platform10-3` 分支到 fork 仓（`liting_0916/openlibing-web`）
- [x] T13 创建业务 PR（base: `release_20261019`，head: `liting_0916:lt-platform10-3`）→ [PR #822](https://gitcode.com/openlibing/openlibing-web/merge_requests/822)
- [x] T14 补打 `ai-assisted` 标签
- [ ] T15 在 [openlibing-platform-release Issue #63](https://gitcode.com/openlibing/openlibing-platform-release/issues/63) 页面手动关联 PR（GitCode CLI 不支持跨仓 PR 关联）

## Phase 5 归档

- [ ] T16 业务 PR 合入后，生成 `archive.md` 沉淀经验
- [ ] T17 通过 docs PR 提交归档（关联业务 Issue）

## Commit 关联表

| Task    | Commit      | 说明                                      |
| ------- | ----------- | ----------------------------------------- |
| T1-T8   | `c77e233bb` | tag 校验正则 + 提示文案（含三轮规则迭代） |
| T11     | -           | 用户自测                                  |
| T12-T14 | -           | 业务 PR #822 创建                         |
| T15-T17 | 待执行      | 手动关联 + 归档                           |

Generated-by: GLM-5.3
