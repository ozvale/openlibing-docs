# Proposal: sbom-notice-display-whitelist

## Why

SBOM 成分分析页面的 NOTICE（声明文档）扫描/导出能力（见 `2026-09-10-add-sbom-notice-export`）此前面向所有社区无条件展示入口。需求方要求该能力仅对白名单社区开放：由 openlibing-sca 后端基于配置中心（Nacos）维护社区白名单，前端按当前社区（项目名）查询展示配置，非白名单社区不展示 NOTICE 相关入口，避免能力在未就绪/未签约社区暴露。

## What Changes

- **新增展示配置查询接口**：在 SCA API 模块 `src/api/scaApi/softWareCompent.js` 新增 `noticeScanDisplayConfig`，GET `/gateway/openlibing-sca/project/notice/scan/display/config`，请求参数 `community`（社区名，取当前 `projectName`），返回 `{ canDisplay: boolean }`。白名单缺省、未命中或查询失败均为 false（fail-closed），Nacos 配置变更实时生效。
- **成分分析页新增展示开关**：`CompositionAnalysis/index.vue` 新增 `noticeDisplayEnabled`（默认 false），`watch` 项目名（`immediate: true`）按社区查询一次展示配置；fail-closed——请求返回前不展示、查询失败不展示、社区切换后不保留上一社区的展示结果。
- **NOTICE 导出入口按开关隐藏**（共 4 处，整条链路）：
  - 页面顶栏「导出声明文档」按钮（`v-if="noticeDisplayEnabled"`）；
  - 行操作下拉中的「声明文档」菜单项（`v-if="noticeDisplayEnabled"`）；
  - `ProductExportDialog.vue` 弹窗内「导出」按钮兜底隐藏（新增 `displayEnabled` prop，由父组件透传）；
  - `noticeExport/index.vue` 弹窗内「导出声明文档」按钮兜底隐藏（新增 `displayEnabled` prop）。
    弹窗内兜底保证即便弹窗通过其他路径打开，非白名单社区也无法触发 NOTICE 导出。
- **探测请求静默化**：展示配置查询以 `{ disabledLoading: true, enabledErrorMsg: false }` 发起——失败不弹全局错误提示、不触发整页 loading，静默降级为不展示。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `sbom-notice-export`（`2026-09-10-add-sbom-notice-export` 引入）：其全部导出入口（顶栏按钮、行下拉项、弹窗内导出按钮）的可见性新增社区白名单前置条件；白名单外社区整链路隐藏，白名单内社区行为不变。

## Impact

- **代码**（openlibing-web 仓 `notice_sbom` 分支，2 个提交）：
  - `apps/web-openlibing/src/api/scaApi/softWareCompent.js`：新增 `noticeScanDisplayConfig`
  - `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`：新增 `noticeDisplayEnabled` 开关与 watch 探测；顶栏按钮、行下拉项、两个弹窗透传受控
  - `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/ProductExportDialog.vue`：新增 `displayEnabled` prop，控制弹窗内「导出」按钮
  - `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/noticeExport/index.vue`：新增 `displayEnabled` prop，控制弹窗内「导出声明文档」按钮
- **接口**（依赖 openlibing-sca 后端，已在 openlibing-sca commit `169eb2f4` 落地）：
  - GET `/gateway/openlibing-sca/project/notice/scan/display/config`，params `{ community: string }`，响应 `{ code, data: { canDisplay: boolean } }`。
- **无破坏性变更**：白名单内社区（canDisplay=true）所有既有 NOTICE 导出行为不变；非白名单社区仅隐藏入口，其余 SBOM 功能不受影响。

## 关联

- 业务仓 PR：openlibing/openlibing-web#849（分支 `notice_sbom`）
- 跨仓 Issue：https://gitcode.com/openlibing/openlibing-sca/issues/88
- 前置能力 spec：`openlibing-docs/spec/openlibing-web/task_design/2026-09-10-add-sbom-notice-export/`
