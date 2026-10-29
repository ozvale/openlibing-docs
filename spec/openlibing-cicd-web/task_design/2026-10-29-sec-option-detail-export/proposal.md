# Proposal: 安全编译选项扫描结果支持导出（前端）

## 需求背景

产物安全编译选项扫描详情页此前仅支持页面查看（顶部产物基础信息 + 逐安全编译选项指标明细 + 文件级扫描结果弹窗），无法离线留档与线下分析。安全团队与研发团队需要将当前扫描记录一键导出为 Excel 文件，用于归档与线下分析。

本次改造为 openlibing-cicd-web 前端部分：在产物包扫描详情页新增「导出扫描结果」按钮，调用后端导出任务创建接口，通过 wujie bus 通知主站导出中心统一展示进度并自动下载。后端部分（openlibing/openlibing-cicd#495）负责异步生成双 Sheet Excel 并上传 OBS。

## 需求描述

1. **导出入口**：详情页顶部工具栏（标题右侧操作区）新增「导出扫描结果」按钮，与既有「备案项列表」按钮并列，带 `Download` 图标与 loading 态
2. **导出任务创建**：点击后携带 `projectId` + `recordId` 调用 `POST /build-artifact/sec-option/detail/export` 创建异步导出任务
3. **导出中心联动**：从响应中提取导出任务 ID，通过 wujie bus 上报 `host-export-task` 事件（`type: SEC_OPTION_DETAIL`），由主站导出中心浮窗展示进度、完成后自动下载
4. **反馈与降级**：提交成功提示「已提交导出任务」；脱离 wujie 宿主（bus 不可用）时降级提示；参数缺失与接口异常均有明确反馈

## 验收标准

- [x] 详情页工具栏展示「导出扫描结果」按钮，与「备案项列表」并列
- [x] 点击按钮发起导出，导出中心出现任务并展示进度，成功后自动下载 Excel
- [x] `projectId` / `recordId` 缺失时按钮给出 warning 提示「缺少项目或扫描记录信息，暂时无法导出」，不发请求
- [x] 接口返回无任务 ID 时提示「导出任务创建失败」
- [x] 非 wujie 宿主或宿主未提供 bus 时提示「后台任务已创建，但未检测到导出中心，请稍后手动查看」，不误报成功
- [x] 请求期间按钮 loading 防重复点击，结束后（成功/失败/异常）恢复
- [x] 接口异常时由请求拦截器统一提示，按钮状态正常恢复

## 实现偏差说明（回写）

- **导出按钮落点**：需求 Issue（openlibing/openlibing-cicd#495）原文为「详情页选项明细表格区右上角」新增「导出」按钮；实际实现位于详情页顶部工具栏（标题右侧操作区），与既有「备案项列表」按钮并列（见 `PackageDetailView.vue` 的 `view-toolbar` / `toolbar-actions` 区块）。偏差原因：导出对象是整份扫描记录（基础信息 + 指标明细 + 文件级结果），并非仅表格区数据，放在页面既有操作区与整页级操作语义一致；本文档需求描述与验收标准已按实际落点回写，后续以本文档为实现口径的权威描述。

## 影响范围

### 修改文件

| 文件                                              | 说明                                                                               |
| ------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `src/api/SecurityOptions/url.ts`                  | 新增 `BUILD_ARTIFACT_SEC_OPTION_DETAIL_EXPORT` URL 常量                            |
| `src/api/SecurityOptions/api.ts`                  | 新增 `buildArtifactSecOptionDetailExport` 请求函数封装                             |
| `src/views/SecurityOptions/PackageDetailView.vue` | 工具栏新增导出按钮；新增 `handleExport` 提交流程（含参数校验、bus 上报、降级提示） |

### 复用设施（无改动）

| 设施                                | 说明                                                        |
| ----------------------------------- | ----------------------------------------------------------- |
| `src/utils/notifyHostExportTask.ts` | wujie bus 导出任务上报工具（返回 boolean 表示是否送达宿主） |
| `src/utils/extractExportId.ts`      | 从导出接口响应中提取任务 ID                                 |
| 主站导出中心（web-openlibing）      | 监听 `host-export-task` 事件，展示进度并自动下载            |

## 关联 Issue

- https://gitcode.com/openlibing/openlibing-cicd/issues/495 （跨仓需求唯一 Issue，前后端共用）
- 业务 PR：https://gitcode.com/openlibing/openlibing-cicd-web/merge_requests/194
