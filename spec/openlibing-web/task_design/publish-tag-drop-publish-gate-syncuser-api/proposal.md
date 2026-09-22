# 发布评审场景修复（tag 列移除 / 发布按钮病毒扫描约束 / 同步项目用户接口前缀修正）

## 需求背景

发布管理评审页 `apps/web-openlibing/src/views/Publish/publishReview/detail/` 存在三处需要修复的问题，均与发布评审流程相关，覆盖 Issue #79 中"发布管理的 tag 验证场景的修复"项并补充发布按钮前置约束与同步项目用户接口归属修正。

## 需求范围

### Bug 修复 / 行为收敛

1. **releaseArtifacts.vue — 移除"tag 名称校验"列**
   - 产物评审页 `releaseArtifacts.vue` 此前展示"tag 名称校验"列，引用 `tagValidationResult` / `tagValidationDetail` 字段并使用 `getTagResult` / `getTagResultDetailTip` 两个辅助函数渲染成功/失败状态
   - 该列已不在产物校验流程中使用，字段不再维护，保留会造成 UI 引用过期字段、误导评审人员
   - 移除整段 `<el-table-column label="tag名称校验">` 及两个辅助函数

2. **reviewDetail.vue — "同意发布"按钮加病毒扫描状态约束**
   - 评审详情页"同意发布"按钮此前无病毒扫描状态约束，存在扫描未完成即可触发的风险
   - 新增 `:disabled="dataList.virusScanStatus !== 2"`，仅当扫描完成（status===2）时允许点击

3. **url.ts — SYNC_PROJECT_USER 接口前缀修正**
   - `SYNC_PROJECT_USER` 此前定义为 `CODE_REPO + '/sync-user/sync-project-user'`，挂在代码仓服务域下
   - 同步项目用户接口实际属于框架工作台（FRAME_WORK）服务域，原先路径指向错误
   - 改为 `FRAME_WORK + '/sync-user/sync-project-user'`

## 影响范围

| 文件                                                                                         | 影响                                                      |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `apps/web-openlibing/src/views/Publish/publishReview/detail/components/releaseArtifacts.vue` | 移除整段 tag 名称校验列及配套函数（-45 行）               |
| `apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue`                | "同意发布"按钮加 disabled 绑定（+1 行）                   |
| `apps/web-openlibing/src/api/url.ts`                                                         | SYNC_PROJECT_USER 前缀 CODE_REPO → FRAME_WORK（1 行变更） |

## 验收标准

- [x] 评审详情页：病毒扫描未完成（virusScanStatus !== 2）时"同意发布"按钮置灰不可点击
- [x] 评审详情页：病毒扫描完成（virusScanStatus === 2）时"同意发布"按钮可点击
- [x] 产物列表页：原"tag 名称校验"列已不显示，其余列正常
- [x] 项目用户同步接口调用路径为 `FRAME_WORK/sync-user/sync-project-user`，返回 200
- [x] pre-commit 本地通过（Prettier / ESLint / gitleaks 均 Passed）

## 关联

- Issue: openlibing/openlibing-platform-release#79
- 业务 PR: openlibing/openlibing-web#793
- 目标分支: release_20260923
