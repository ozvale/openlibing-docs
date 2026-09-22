# Archive: 发布评审详情页漏洞信息区域与漏洞公告发布

> 仓库：openlibing-web
> 变更名：publish-review-vuln-bulletin
> 模式：Standard
> 归档时间：2026-07-06

## 需求完成情况

全部完成。在发布评审详情页新增"漏洞信息"区域，支持发布漏洞公告功能。

## 关联产物

| 产物 | 链接 |
|------|------|
| 业务 Issue | openlibing/openlibing-web#205 |
| 业务 PR | openlibing/openlibing-web#553 |
| 业务仓 commit | eafd83e0, e53433e4, e74a97ba |

## 实现总结

### 改动文件
- apps/web-openlibing/src/api/url.ts — TRIGGER_VULN_BULLETIN URL 常量
- apps/web-openlibing/src/api/api.ts — triggerVulnerabilityBulletin 方法定义
- apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue — 漏洞信息区域 UI + 业务逻辑

### 核心实现
1. 漏洞信息区域 UI（reviewPartHeader + fieldset + el-form 模式）
2. triggerVulnerabilityBulletin API 调用（params: userId/projectId, body: reviewId/fixedProduct/repos）
3. 状态展示（statusIcon: execute_failed/execute_success/executing）
4. 表单回填（首次回填标志位，避免轮询覆盖用户输入）
5. repos url 转仓库名显示（split/filter/pop）
6. 按钮显隐控制（v-if + isVulnFormDisabled）
7. 公告地址列表展示（publishStatus=5）
8. 漏洞信息区域按 projectId 控制显示（仅特定项目）

## 经验沉淀

### 跨仓 PR 创建（gitcode CLI）
- `--fork` 参数未生效，跨仓 PR 需用 `--head meroFuruya:dev-260702`（owner:branch 格式）
- 正确命令：`gitcode pr create -R openlibing/openlibing-web --head <fork_owner>:<branch> --base <base> --title ... --body-file <UTF-8> --draft`

### 轮询场景的表单回填
- 轮询刷新详情时，表单回填会覆盖用户正在输入的内容
- 解决方案：首次回填标志位（isVulnBulletinFormInitialized），仅首次 getDetailData 回填

### Windows 中文 commit message
- PowerShell 命令行传中文会乱码
- 解决方案：用 Write 工具写 UTF-8 文件 + git commit -F <file>

## 验收结果

用户自测通过，验收标准 10 项全部满足。
