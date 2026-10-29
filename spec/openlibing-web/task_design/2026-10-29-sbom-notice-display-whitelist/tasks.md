# Tasks: sbom-notice-display-whitelist

## 1. API 层

- [x] 1.1 在 `apps/web-openlibing/src/api/scaApi/softWareCompent.js` 新增 `noticeScanDisplayConfig(a, s)`：GET `/gateway/openlibing-sca/project/notice/scan/display/config`，params `{ community }`，返回 `{ canDisplay: boolean }`，JSDoc 注明 fail-closed 语义与 Nacos 实时生效

## 2. 展示开关与探测（CompositionAnalysis/index.vue）

- [x] 2.1 新增 `noticeDisplayEnabled = ref(false)`（fail-closed 默认隐藏）
- [x] 2.2 `watch(() => app.projectInfo?.projectName, …, { immediate: true })`：进入页面与社区切换时查询展示配置；回调先复位 `false` 再发请求（不保留上一社区结果）
- [x] 2.3 探测请求传 `{ disabledLoading: true, enabledErrorMsg: false }`：失败不弹全局错误 toast、不触发整页 loading，`.catch(() => {})` 静默降级（PR #849 检视修复）
- [x] 2.4 竞态防护：响应回来时校验 `community !== app.projectInfo?.projectName` 则丢弃过期响应，关闭 fail-open 窗口（PR #849 检视修复）
- [x] 2.5 成功判定 `res?.code === 200 && Boolean(res?.data?.canDisplay)`，非 200/非真值/异常均保持 false

## 3. 入口可见性控制（整条链路）

- [x] 3.1 页面顶栏「导出声明文档」按钮加 `v-if="noticeDisplayEnabled"`
- [x] 3.2 行操作下拉「声明文档」菜单项加 `v-if="noticeDisplayEnabled"`
- [x] 3.3 `ProductExportDialog.vue` 新增 `displayEnabled` prop（默认 false），弹窗内「导出」按钮 `v-if="displayEnabled"` 兜底；父组件挂载处透传 `:display-enabled="noticeDisplayEnabled"`
- [x] 3.4 `noticeExport/index.vue` 新增 `displayEnabled` prop（默认 false），弹窗内「导出声明文档」按钮 `v-if="displayEnabled"` 兜底；父组件挂载处透传 `:display-enabled="noticeDisplayEnabled"`

## 4. 验证

- [x] 4.1 白名单社区（canDisplay=true）：顶栏按钮、行下拉项、弹窗内导出按钮全部展示，NOTICE 导出全流程行为与改造前一致
- [x] 4.2 非白名单社区（canDisplay=false / 白名单缺省 / 接口异常）：4 处入口全部隐藏，「全量导出」等其他 SBOM 功能不受影响
- [x] 4.3 探测失败路径：无全局错误 toast、无整页 loading，页面静默按不展示处理
- [x] 4.4 社区切换：切换瞬间入口立即收回；旧社区晚到的响应被丢弃，开关仅反映当前社区
- [x] 4.5 请求返回前（含首屏 immediate 触发）：入口默认隐藏，无闪烁展示
