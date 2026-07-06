# Tasks: 发布评审详情页漏洞信息区域与漏洞公告发布

> 仓库：openlibing-web
> 变更名：publish-review-vuln-bulletin
> 模式：Standard

## 实现步骤

- [x] 1. 新增 TRIGGER_VULN_BULLETIN URL 常量（url.ts）
- [x] 2. 新增 triggerVulnerabilityBulletin 方法定义（api.ts）
- [x] 3. 漏洞信息区域 UI 搭建（reviewDetail.vue template）
  - [x] 3.1 detail-part 容器 + reviewPartHeader + fieldset/legend/el-form
  - [x] 3.2 修复版本号 input（必填）
  - [x] 3.3 仓库 textarea（placeholder）
  - [x] 3.4 "发布公告"按钮（v-uem-record 埋点）
- [x] 4. 状态展示 statusIcon
  - [x] 4.1 currentVulnBulletin computed
  - [x] 4.2 vulnBulletinStatus computed（3/5/其他）
- [x] 5. 表单与按钮控制
  - [x] 5.1 isVulnFormDisabled computed
  - [x] 5.2 表单 :disabled
  - [x] 5.3 按钮 v-if 显隐 + :disabled 必填
- [x] 6. 公告地址列表展示（publishStatus=5）
- [x] 7. 表单回填
  - [x] 7.1 首次回填标志位 isVulnBulletinFormInitialized
  - [x] 7.2 getDetailData 首次回填 vulnerabilityBulletinList[0]
  - [x] 7.3 repos url 转仓库名显示
- [x] 8. handlePublishVulnNotice 调用 triggerVulnerabilityBulletin
  - [x] 8.1 params(userId/projectId) + body(reviewId/fixedProduct/repos数组)
  - [x] 8.2 成功判断（code=200 && data）+ ElMessage + 刷新

## Commit 记录

- eafd83e0 feat(publish-review): add vulnerability info section UI（第一轮：UI 搭建）
- e53433e4 feat(publish-review): implement vulnerability bulletin publish logic（第二轮：完整逻辑）

## 待办（用户自测后）

- [x] 用户自测验收（对照验收标准）
- [x] 创建 GitCode Issue（用户手动在主仓创建）→ openlibing/openlibing-web#205 https://gitcode.com/openlibing/openlibing-web/issues/205
- [x] Phase 4 业务 PR → openlibing/openlibing-web#553 https://gitcode.com/openlibing/openlibing-web/pulls/553（WIP draft + ai-assisted 标签 + 关联 #205）
- [ ] Phase 5 归档 archive.md（用户触发）
