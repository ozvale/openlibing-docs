# Proposal: 发布评审详情页漏洞信息区域与漏洞公告发布

> 仓库：openlibing-web
> 变更名：publish-review-vuln-bulletin
> 模式：Standard
> 关联需求：openlibing-web/_docs/260703.md（第一次改动描述 + 第二次改动描述）

## 背景

发布评审详情页（publishReview/detail）原有"发布信息"区域展示发布审核相关内容。
本次需在该区域之后新增"漏洞信息"区域，支持用户在发布评审过程中发布漏洞公告，
并展示漏洞公告的发布状态（失败/已发布/执行中）及公告地址。

## 需求范围

### 功能点

1. **漏洞信息区域 UI**
   - 位置：发布信息区域之后
   - 显示条件：与发布信息区域相同（reviewStatus !== -1 && !== 0）
   - 区块："发布漏洞公告" + "发布公告"按钮（同级）

2. **发布漏洞公告表单**
   - 修复版本号：input，必填，未填时"发布公告"按钮不可点击
   - 仓库：textarea，placeholder 提示"用英文逗号隔开的仓库名"

3. **漏洞公告发布接口（triggerVulnerabilityBulletin）**
   - URL 参数：userId（store）、projectId（store）
   - body：reviewId（路由 query）、fixedProduct、repos（逗号字符串转数组）
   - 响应：code=200 且 data 存在表示成功

4. **详情接口扩展（getPublishReviewDetailById）**
   - data 新增 vulnerabilityBulletinList（Array，仅 1 个元素）
   - 元素字段：id、fixedProduct、repos（url[]）、reviewId、createTime、publishStatus、publishStatusName
   - 可能不存在该字段（未发布过）

5. **状态展示与交互**
   - 无数据：表单可编辑，按钮可点击
   - publishStatus=3（失败）：statusIcon(execute_failed)，表单可编辑，可重新发布
   - publishStatus=5（已发布）：statusIcon(execute_success)，表单禁用，展示公告地址列表
   - 其他（执行中）：statusIcon(executing)，表单禁用，按钮隐藏

6. **回填策略**
   - 仅首次 getDetailData 回填表单（避免轮询覆盖用户输入）
   - repos url 转仓库名显示（split('/').filter(Boolean).pop()）

## 验收标准

- [ ] 漏洞信息区域在发布信息之后正确显示（条件：reviewStatus ≠ -1 且 ≠ 0）
- [ ] 修复版本号必填，未填时按钮禁用
- [ ] 仓库 textarea placeholder 为"用英文逗号隔开的仓库名"
- [ ] 点击发布公告：params 带 userId/projectId，body 带 reviewId/fixedProduct/repos(数组)
- [ ] 成功后（code=200 && data）ElMessage 提示 + 刷新详情
- [ ] 首次回填表单，后续轮询不覆盖用户输入
- [ ] repos 回填时 url 转仓库名显示
- [ ] publishStatus=3：红色 statusIcon，表单可编辑，按钮显示
- [ ] publishStatus=5：绿色 statusIcon，表单禁用，按钮隐藏，显示公告地址列表
- [ ] 执行中：旋转 statusIcon，表单禁用，按钮隐藏

## 非目标

- "发布公告"按钮的具体后端发布逻辑（由后端实现）
- 漏洞公告的 i18n 国际化（本次未涉及）
