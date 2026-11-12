# 技术方案

## 变更文件

| 文件                                                                          | 变更类型 |
| ----------------------------------------------------------------------------- | -------- |
| `apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue` | 修改     |

## 实现说明

`reviewDetail.vue` 中通过计算属性 `showVulnNoticeForm` 控制漏洞公告表单是否展示，依赖 Pinia 中 `app.projectInfo.projectId`。

变更前：

```js
// 仅MindCluster和openLiBing显示漏洞公告
const showVulnNoticeForm = computed(() => {
  const pid = app.projectInfo?.projectId;
  return pid === 3 || pid === 300038;
});
```

变更后：

```js
// 仅MindCluster、openLiBing、MindIE、MindStudio、MindSporeOpenSource、MindSpeed、AscendForPyTorch显示漏洞公告
const showVulnNoticeForm = computed(() => {
  const pids = [300038, 3, 300036, 300037, 300062, 300091, 4];
  const pid = app.projectInfo?.projectId;
  return pids.includes(pid);
});
```

## 项目 ID 对照

| 项目                | projectId |
| ------------------- | --------- |
| MindCluster         | 300038    |
| openLiBing          | 3         |
| MindIE              | 300036    |
| MindStudio          | 300037    |
| MindSporeOpenSource | 300062    |
| MindSpeed           | 300091    |
| AscendForPyTorch    | 4         |

## 影响范围

- 仅影响发布评审详情页漏洞公告表单的**可见性判断**
- 不涉及接口、数据结构、权限校验的变更
- 漏洞公告表单自身的渲染、校验、提交逻辑保持不变

## 风险与验证

1. **风险**：项目 ID 为硬编码构建，若后续新增项目仍需改动代码。本次以白名单数组形式集中维护，降低散落判断带来的漏改风险。
2. **验证方式**：分别以白名单内 7 个项目和其他项目进入发布评审详情页，确认表单显隐符合预期。
