# Design: virus-scan-report-download

## 方案概览

1. **API 封装**：`url.ts` 增加 `VIRUS_SCAN_REPORT_DOWNLOAD` 常量，`api.ts` 增加 `getVirusScanReport` GET 封装。
2. **header 插槽扩展**：`reviewPartHeader.vue` 增加可选具名 slot `headerAction`，`margin-left: auto` 靠右排布；未传 slot 时布局与原样式完全一致。
3. **下载按钮与流程**：`reviewDetail.vue` 制品信息标题行通过 `headerAction` slot 插入下载按钮，下载流程为 `ElMessageBox.confirm → blob 请求 → exportFile 落盘`。

## 实现逻辑

### 1. 接口定义

```ts
// url.ts
export const VIRUS_SCAN_REPORT_DOWNLOAD = FRAME_WORK + "/base/virusScanReport";

// api.ts
export const getVirusScanReport: RequestFunc = (a, s) =>
  apiClient.get(urls.VIRUS_SCAN_REPORT_DOWNLOAD, a, s);
```

参数：`projectId`、`reviewId`（query 传参），响应为 word 二进制流。

### 2. headerAction 可选插槽

```vue
<!-- reviewPartHeader.vue -->
<div class="review-part-header">
  <span class="review-part-title">{{ title }}</span>
  <slot name="headerAction"></slot>
</div>

<style>
.review-part-header {
  display: flex;
  align-items: center;
}
.review-part-header > :last-child {
  margin-left: auto;
}
</style>
```

`headerAction` 为可选插槽，其余 8 处使用 `reviewPartHeader` 的页面未传该 slot，布局零回归。

### 3. 下载流程（reviewDetail.vue）

```ts
const downloadLoading = ref(false);

const downloadVirusScanReport = () => {
  ElMessageBox.confirm("确认下载病毒扫描报告？", "提示", { type: "warning" })
    .then(() => {
      downloadLoading.value = true;
      getVirusScanReport({
        params: { projectId, reviewId },
        responseType: "blob",
      })
        .then((res) => {
          exportFile(
            res,
            `病毒扫描报告${dayjs().format("YYYYMMDDHHmmss")}.docx`,
          );
        })
        .finally(() => {
          downloadLoading.value = false;
        });
    })
    .catch(() => {});
};
```

## 类与组件

| 文件                                                       | 角色             | 变更                                                        |
| ---------------------------------------------------------- | ---------------- | ----------------------------------------------------------- |
| `apps/web-openlibing/src/api/url.ts`                       | 接口地址常量     | 新增 `VIRUS_SCAN_REPORT_DOWNLOAD`                           |
| `apps/web-openlibing/src/api/api.ts`                       | 接口封装         | 新增 `getVirusScanReport`                                   |
| `.../publishReview/detail/components/reviewPartHeader.vue` | 详情区标题头组件 | 新增可选具名 slot `headerAction`                            |
| `.../publishReview/detail/reviewDetail.vue`                | 发布评审详情页   | 制品信息标题行右侧下载按钮 + `downloadVirusScanReport` 流程 |

## 数据模型

无新增数据模型。下载按钮展示依赖现有详情数据：

| 数据                 | 来源         | 用途                                     |
| -------------------- | ------------ | ---------------------------------------- |
| `isDataOwner`        | 详情接口返回 | 当前用户是否为数据责任人（按钮展示条件） |
| `virusScanStatus`    | 详情接口返回 | `=== 2` 表示扫描完成（按钮展示条件）     |
| `projectId/reviewId` | 路由/详情    | 下载接口 query 参数                      |

## 安全

- 下载入口有双重条件：`isDataOwner`（权限）+ `virusScanStatus === 2`（状态），非责任人不可见。
- 下载前二次确认，防止误操作。
- 报告文件名由前端拼接 `病毒扫描报告{时间戳}.docx`，无用户可控路径成分，无路径穿越风险。

## 影响范围

- 仅影响发布评审详情页制品信息区。
- `reviewPartHeader.vue` 插槽为可选能力，其余使用处零回归。
- 不影响后端接口、数据模型。

## 回滚策略

revert 业务 commit 即可整体回退（`reviewPartHeader.vue` 插槽随整体 revert 一并移除，不影响其他页面）。

Generated-by: GLM-5.3
