# 任务清单

## Phase 1: 需求确认

- [x] 理解需求：请求失败时重置按钮 loading 状态
- [x] 关联 Issue：openlibing/openlibing-web#300

## Phase 2: 设计与计划

- [x] 确定修改方案：`addVuln` / `updateVuln` 请求链新增 `.catch()` 分支重置 `btnLoading`
- [x] 简单变更，spec 仅包含 proposal.md 和 tasks.md（省略 design.md）

## Phase 3: 编码实现

- [x] `addVuln()`：`.then()` 后追加 `.catch(() => { btnLoading.value = false; })`
- [x] `updateVuln()`：同上
- [x] 提交代码到本地分支 `fix-vuln-issue-time-tooltip`

## Phase 4: PR 提交

- [x] 推送到 fork 仓 `dyy-1/openlibing-web_0907:fix-vuln-issue-time-tooltip`
- [x] 创建 [PR #795](https://gitcode.com/openlibing/openlibing-web/pull/795) 到 `openlibing/openlibing-web:release_20260923`
- [x] 补打 `ai-assisted` 标签，CI 通过，已合入（2026-09-22）

## Phase 5: 归档

- [x] 创建 spec 文档并提交到 openlibing-docs
