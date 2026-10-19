# tasks: 适配后端 SCA CSRF 修复（GET → POST）

## Phase 0: 上下文加载与分支准备

- [x] 识别目标仓：`openlibing/openlibing-web`
- [x] 确认当前分支：`dev_wt`
- [x] 拉取后端 PR #256 完整 diff，识别 GET → POST 改造的接口清单
- [x] 在前端代码中匹配实际调用点（10 处，涉及 6 个唯一接口）
- [x] 确认流程模式：Light
- [ ] 基于主仓 master 新建分支 `feat-sca-csrf-adapt`
- [ ] 确认 Issue 关联方式

## Phase 1: 业务 Issue 与需求确认

- [ ] 在 `openlibing/openlibing-web` 仓创建业务 Issue（或关联已有 Issue）
  - Issue 标题：`feat: 适配后端 sca CSRF 修复（GET → POST）`
  - Issue 描述：参考 `proposal.md` 的需求范围与验收标准
  - 关联后端 PR：https://gitcode.com/openlibing/openlibing-sca/pull/256
- [ ] 用户确认需求范围

## Phase 2: 轻量设计与计划

- [x] 生成 proposal.md（已归档到 `openlibing-docs/spec/openlibing-web/task_design/sca-csrf-get-to-post-adapt/`）
- [x] 生成 design.md（已归档同上目录）
- [x] 生成 tasks.md（本文件）
- [ ] 用户确认实现计划

## Phase 3: AI 编码交付

### 3.1 修改 `apps/web-openlibing/src/api/scaApi/softWareCompent.js`

- [ ] L79-85 `refreshConfirmNum`：`apiClient.get` → `apiClient.post`
- [ ] L158-164 `exportDataStatus`：`apiClient.get` → `apiClient.post`
- [ ] L338-344 `exportCommunityData`：`apiClient.get` → `apiClient.post`
- [ ] L350-356 `exportLicenseData`：`apiClient.get` → `apiClient.post`
- [ ] L490-496 `exportBinaryLicenseComplianceData`：`apiClient.get` → `apiClient.post`
- [ ] L502-508 `exportBinaryNoticeData`：`apiClient.get` → `apiClient.post`

### 3.2 修改 `apps/web-openlibing/src/sca/src/api/softWareCompent.js`

- [ ] L89-95 `refreshConfirmNum`：`method: 'get'` → `method: 'post'`
- [ ] L178-184 `exportDataStatus`：`method: 'get'` → `method: 'post'`
- [ ] L368-374 `exportCommunityData`：`method: 'get'` → `method: 'post'`
- [ ] L380-386 `exportLicenseData`：`method: 'get'` → `method: 'post'`

### 3.3 自检

- [ ] 改动仅涉及 10 处 method 切换，无无关格式化或重构
- [ ] 未修改任何调用方代码（`*.vue`）
- [ ] 未修改 URL 路径
- [ ] 未修改参数传递方式（仍为 `params`）
- [ ] 未删除/修改已有注释

### 3.4 本地验证

- [ ] `pnpm lint`（或 `pnpm eslint`）通过
- [ ] `pnpm build` 或 `pnpm dev` 启动无 TS/ESLint 报错

### 3.5 提交 commit

- [ ] 单 commit，commit message 格式：
  ```
  feat(sca): adapt sca CSRF fix by switching GET to POST

  - Adapt 10 API calls across 2 files to align with backend PR #256
  - Files: scaApi/softWareCompent.js, sca/src/api/softWareCompent.js
  - Methods: refreshConfirmNum, exportDataStatus, exportCommunityData,
    exportLicenseData, exportBinaryLicenseComplianceData, exportBinaryNoticeData

  Refs <issue-url>
  Co-authored-by: Trae <noreply@trae.ai>
  Generated-by: GLM-5.2
  ```

## 用户自测/反馈循环

- [ ] 用户在 gamma 环境验证 6 个功能点（详见 design.md 验证策略）
- [ ] 用户明确确认完成

## Phase 4: 业务 PR 交付

- [ ] 向用户确认 PR 参数（源分支、目标分支、标题、描述、标签、关联 Issue）
- [ ] 通过 `gitcode pr create` 创建跨仓 PR（`--head fork-owner:feat-sca-csrf-adapt`）
- [ ] 通过 `gitcode pr edit <n> -R openlibing/openlibing-web --labels ai-assisted` 补打标签
- [ ] 通过 `gitcode pr view <n> -R openlibing/openlibing-web --json` 验证 head.repo.full_name 为 fork 仓
- [ ] 交付 PR URL 给用户

## Phase 5: 最终归档（用户触发）

- [ ] 在 `openlibing-docs` 仓基于 master 新建分支 `spec-openlibing-web-sca-csrf-get-to-post-adapt`
- [ ] 提交 spec 文件：`spec/openlibing-web/task_design/sca-csrf-get-to-post-adapt/`（proposal.md + design.md + tasks.md）
- [ ] 创建 docs PR：`docs(spec-openlibing-web): sca-csrf-get-to-post-adapt`
- [ ] PR 描述关联业务 Issue（跨仓引用完整 URL）
- [ ] 补打 `ai-assisted` 标签
- [ ] 业务 Issue 状态确认（关闭/完成）
