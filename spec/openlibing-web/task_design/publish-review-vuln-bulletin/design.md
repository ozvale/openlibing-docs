# Design: 发布评审详情页漏洞信息区域与漏洞公告发布

> 仓库：openlibing-web
> 变更名：publish-review-vuln-bulletin
> 模式：Standard

## 技术方案

### 改动文件

| 文件 | 改动 |
|------|------|
| apps/web-openlibing/src/api/url.ts | 新增 TRIGGER_VULN_BULLETIN URL 常量 |
| apps/web-openlibing/src/api/api.ts | 新增 triggerVulnerabilityBulletin 方法定义 |
| apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue | 漏洞信息区域 UI + 业务逻辑 |

### UI 结构

复用 reviewDetail.vue 既有模式（reviewPartHeader + fieldset + legend + el-form）：

```html
<div class="detail-part" v-if="显示条件(同发布信息)">
  <reviewPartHeader title="漏洞信息" />
  <fieldset>
    <legend>
      发布漏洞公告
      <statusIcon v-if="有数据" :status="vulnBulletinStatus" />
    </legend>
    <div class="fieldset-content">
      <el-form :disabled="isVulnFormDisabled">
        <el-form-item label="修复版本号" required>
          <el-input v-model="vulnNoticeForm.fixedProduct" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input type="textarea" v-model="vulnNoticeForm.repos"
            placeholder="用英文逗号隔开的仓库名" />
        </el-form-item>
      </el-form>
      <el-button v-if="!isVulnFormDisabled"
        :disabled="!vulnNoticeForm.fixedProduct"
        @click="handlePublishVulnNotice">发布公告</el-button>
    </div>
    <!-- 已发布时展示公告地址列表 -->
    <div v-if="showVulnBulletinUrls">
      <div v-for="url in currentVulnBulletin.repos" :key="url">
        <a :href="url" target="_blank">{{ url }}</a>
      </div>
    </div>
  </fieldset>
</div>
```

### 状态管理

| computed | 逻辑 | 用途 |
|----------|------|------|
| currentVulnBulletin | dataList.vulnerabilityBulletinList?.[0] | 当前漏洞公告数据 |
| vulnBulletinStatus | 无数据→空；3→execute_failed；5→execute_success；其他→executing | statusIcon |
| isVulnFormDisabled | 有数据 && publishStatus !== 3 | 表单禁用 + 按钮显隐 |
| showVulnBulletinUrls | publishStatus === 5 | 公告地址列表 |

### 回填策略

- 新增 `isVulnBulletinFormInitialized` ref（初始 false）
- getDetailData 中：`if (!isVulnBulletinFormInitialized.value) { 回填; 设 true }`
- 首次回填后，后续轮询跳过回填，保留用户输入
- repos 回填：`url.split('/').filter(Boolean).pop()` 取仓库名，join(',') 显示

### API 调用

```ts
triggerVulnerabilityBulletin(
  { userId: app.user.userId, projectId: app.projectInfo.projectId },
  { reviewId: route.query.reviewId, fixedProduct, repos: repos字符串.split(',').map(trim).filter(Boolean) }
).then(res => {
  if (res.code === 200 && res.data) {
    ElMessage.success('发布成功');
    getDetailData(); // 刷新
  }
});
```

## 影响范围

- **模块**：Publish/publishReview（发布评审详情页）
- **接口**：新增 triggerVulnerabilityBulletin；getPublishReviewDetailById 返回值扩展（后端已支持）
- **数据模型**：无前端 schema 变化，仅消费后端新增的 vulnerabilityBulletinList 字段
- **安全**：低（无鉴权/凭证/输入注入风险，params 来自 store，body 来自表单）
- **部署**：无（纯前端改动）
- **测试**：Standard 模式要求相关测试；本次为 UI + 接口对接，无独立可测单元（依赖后端数据），自测覆盖

## 无新决策

本设计完全遵循 reviewDetail.vue 既有架构与模式（reviewPartHeader/fieldset/el-form/statusIcon/computed），无新技术决策。
