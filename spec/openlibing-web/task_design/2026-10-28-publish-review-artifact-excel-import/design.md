# 技术方案

## 方案概述

在发布评审详情页 `reviewDetail.vue` 的制品信息区块头部增加"下载制品信息模板"按钮与"上传制品信息"上传组件；新增两个接口封装：模板下载（blob 流）与 Excel 解析（multipart 表单）。解析成功后把后端返回的制品信息转换为页面表单结构并追加到 `dataList.releaseArtifactInfoList`；解析失败时通过弹窗展示后端返回的行级错误。

## 接口设计

| 项目     | 模板下载                                      | Excel 解析                                                                  |
| -------- | --------------------------------------------- | --------------------------------------------------------------------------- |
| 路径     | `GET /base/downloadArtifactInfoTemplate`      | `POST /base/parseArtifactInfoExcel`                                         |
| 请求参数 | `projectId`、`reviewId`，`responseType: blob` | `multipart/form-data`：`projectId`、`reviewId`、`file`                      |
| 返回结构 | Excel 文件流                                  | `{ code, msg, data: { success, artifactInfoList, rowErrors } }`             |
| 失败处理 | `ElMessageBox.alert` 展示后端 `msg`           | `success=false` 时弹窗展示 `rowErrors`；异常/非 200 时 `ElMessageBox.alert` |

## 字段映射

| Excel 解析返回字段      | 表单字段                                    | 转换规则                                                                                                                                         |
| ----------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `releaseMethod`         | `releaseMethod` / `releaseMethodList`       | 中文顿号 `、` 转英文逗号后拆分为数组，空值默认 `['2']`                                                                                           |
| `repoUrl`               | `repoId` / `repoUrl`                        | 按 `repoUrl` 与仓库列表匹配（去除末尾 `/` 与 `.git`），匹配成功回填 `repoId`                                                                     |
| `pypiRepoId`            | `pypiRepoId` / `pypiRepoIds`                | 有值时包装为数组                                                                                                                                 |
| `releasePipelineParams` | `releasePipelineParams`                     | 后端 `[{ key: value }]` 转为表单 `[{ paramName, paramValue }]`                                                                                   |
| 其他字段                | 同名字段                                    | `softwareDownloadType`、`tagSource`、`tagSourceData`、`tagName`、`tagMessage`、`releaseName`、`releaseDescription`、`pipelineId`、`pipelineName` |
| —                       | `releaseResultList` / `scanVirusScanVoList` | 新导入行初始化为空数组                                                                                                                           |

## 改动文件

| 文件                                                                          | 改动说明                                                                 |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `apps/web-openlibing/src/api/PlatformRelease/url.ts`                          | 新增 `DOWNLOAD_ARTIFACT_INFO_TEMPLATE`、`PARSE_ARTIFACT_INFO_EXCEL` 常量 |
| `apps/web-openlibing/src/api/PlatformRelease/api.ts`                          | 新增 `downloadArtifactInfoTemplate`、`parseArtifactInfoExcel` 请求方法   |
| `apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue` | 头部按钮与上传组件、文件校验、解析回填、错误弹窗、样式调整               |

## 核心代码

```javascript
// 上传前校验：xlsx + 10MB
if (!/\.xlsx$/i.test(rawFile.name)) {
  ElMessage.error("仅允许上传xlsx格式的Excel文件！");
  return;
}
if (rawFile.size > 10 * 1024 * 1024) {
  ElMessage.error("文件大小超过10MB限制！");
  return;
}

// 代码仓匹配：忽略末尾斜杠与 .git
const normalizeRepoUrl = (url) =>
  `${url || ""}`.replace(/\/+$/, "").replace(/\.git$/, "");

// 追加回填
dataList.value.releaseArtifactInfoList =
  dataList.value.releaseArtifactInfoList.concat(artifacts);
```

## 影响范围

- **影响范围**：发布评审详情页制品信息区块的头部操作区与数据回填逻辑
- **权限**：下载/上传按钮均受 `isDataOwner` 控制；病毒扫描报告下载按钮保持原有显示条件
- **不影响**：制品信息原有手工增删改、评审提交、发布执行链路

## 风险分析

1. **代码仓匹配失败**：`repoUrl` 与仓库列表不一致时 `repoId` 为空，已通过警告提示引导用户手动选择，不阻断导入
2. **重复导入**：当前为追加语义，多次上传会重复追加相同制品，需用户在提交前自行核对
3. **大数据量解析**：单次导入条数未做前端上限控制，依赖后端解析能力；文件大小已限制 10MB
4. **接口不可用**：解析接口异常时给出错误提示且不修改现有数据，用户仍可手工填写
