# Design: sbom-notice-display-whitelist

## Context

- NOTICE 导出链路（下拉入口 → 声明文档明细弹窗 → 生成/补充/导出）已在 `2026-09-10-add-sbom-notice-export` 落地，入口当时无条件展示。
- openlibing-sca 后端（commit `169eb2f4`，issue https://gitcode.com/openlibing/openlibing-sca/issues/88）新增展示配置接口：GET `/project/notice/scan/display/config`，按社区读 Nacos 白名单，返回 `{ canDisplay }`；白名单缺省、未命中、异常均返回 false（fail-closed），配置变更实时生效。
- 成分分析页已有 `app.projectInfo.projectName`（computed `projectName`）作为当前社区标识，页面 API 集中在 `src/api/scaApi/softWareCompent.js`（`apiClient.get/post` 风格，第二参数为请求配置，支持 `disabledLoading` / `enabledErrorMsg`）。
- 本分支 2 个提交：`6b40ae3b8`（主功能）、`64c86864a`（按业务 PR #849 检视意见修复：探测静默化 + 竞态安全）。

## Goals / Non-Goals

**Goals:**

- NOTICE 导出整条链路（顶栏按钮、行下拉项、两个弹窗内导出按钮）在非白名单社区完全隐藏。
- fail-closed：配置缺省、未命中、查询失败、响应过期一律不展示，与后端语义一致。
- 探测请求对用户无感知：不弹全局错误、无整页 loading。
- 社区切换时开关状态正确刷新，不出现「先展示后被收回」或「上一社区结果残留」。

**Non-Goals:**

- 不修改 openlibing-sca 后端与 Nacos 白名单配置结构（后端已就绪）。
- 不做开关的前端缓存/多 Tab 同步；每次进入/切换社区各查询一次即可满足需求。
- 不隐藏非 NOTICE 的 SBOM 导出能力（「全量导出」不受影响）。

## Decisions

### D0: 开关粒度与查询时机——页面级单次探测

展示开关为页面级状态 `noticeDisplayEnabled`（ref，默认 false），挂在 `CompositionAnalysis/index.vue`，通过 `watch(() => app.projectInfo?.projectName, …, { immediate: true })` 触发：进入页面立即查询一次，社区（项目）切换后再查询。不在弹窗打开时重复查询、不做轮询——白名单为低频配置，Nacos 变更后端实时生效，页面重进即可刷新，无需前端轮询同步。

### D1: API 契约

```js
noticeScanDisplayConfig: (a, s) =>
  apiClient.get(
    '/gateway/openlibing-sca/project/notice/scan/display/config',
    a,
    s,
  ),
// 调用：noticeScanDisplayConfig(
//   { params: { community } },
//   { disabledLoading: true, enabledErrorMsg: false },
// )
```

归入既有 `softWareCompent.js`（与 notice 系列接口同源），GET + `params.community`，与后端契约一致；成功判定 `res?.code === 200 && Boolean(res?.data?.canDisplay)`，其余一律视为不可展示。

### D2: fail-closed 语义

默认与兜底统一 false：初始值 false；watch 回调**先复位 false 再发请求**（社区切换瞬间即收回入口，不保留上一社区结果）；请求失败（catch）保持 false；响应非 200 或 `canDisplay` 非真值保持 false。与后端「白名单缺省/未命中/异常均 false」的语义端到端对齐，任何一端故障都不会把入口漏给非白名单社区。

### D3: 探测请求静默化（PR #849 检视修复）

探测请求传 `{ disabledLoading: true, enabledErrorMsg: false }`：

- `disabledLoading: true`——不触发 ApiClient 全局 loading（整页加载遮罩）；
- `enabledErrorMsg: false`——查询失败不弹全局错误 toast。

理由：这是一次后台可见性探测而非用户主动操作，非白名单社区查询失败属预期路径（fail-closed 即正确结果），弹错误提示/加载遮罩都会对非目标社区造成干扰；失败仅记 `.catch(() => {})` 静默吞掉（降级为不展示）。

### D4: 竞态安全——丢弃过期响应（PR #849 检视修复）

社区快速切换时，旧社区的探测响应可能晚于新社区返回。若不处理，旧响应会把开关误置为旧社区的查询结果（fail-open 窗口：白名单社区切到非白名单社区时入口短暂残留）。处理方式：响应回来时校验 `community !== app.projectInfo?.projectName` 则直接丢弃；配合 D2 的「请求前复位 false」，切换后入口立即隐藏，仅采纳与当前社区一致的最新响应。

### D5: 入口覆盖与弹窗兜底

受控入口共 4 处，由外到内：

| 入口                                                | 控制方式                                                                     |
| --------------------------------------------------- | ---------------------------------------------------------------------------- |
| 顶栏「导出声明文档」按钮                            | `v-if="noticeDisplayEnabled"`                                                |
| 行操作下拉「声明文档」菜单项                        | `v-if="noticeDisplayEnabled"`                                                |
| `ProductExportDialog` 弹窗内「导出」按钮            | 新增 prop `displayEnabled`（父组件透传 `noticeDisplayEnabled`），`v-if` 兜底 |
| `noticeExport/index.vue` 弹窗内「导出声明文档」按钮 | 新增 prop `displayEnabled`（父组件透传），`v-if` 兜底                        |

弹窗内兜底的动机：弹窗组件自身不感知白名单（保持 dumb component），但若未来出现其他路径打开弹窗（如既有会话/缓存状态），弹窗内按钮仍会被入口开关拦住，保证「非白名单社区无法触发 NOTICE 导出」不依赖单一调用路径。prop 默认 false（缺省即隐藏，同为 fail-closed）。

## Risks / Trade-offs

- [探测仅页面级一次，Nacos 变更后已打开的页面不实时收回入口] → 接受：白名单为低频运维配置；页面重进/刷新即生效；实时性需求出现时可低成本升级为轮询。
- [catch 静默吞错可能掩盖配置接口持续故障] → 接受：fail-closed 下用户可见行为与非白名单一致（入口隐藏），无错误状态需要用户处理；后端有自身监控。
- [非白名单社区弹窗理论上仍可能打开（兜底仅隐藏导出按钮）] → 弹窗打开入口本身已全部隐藏，出现该场景需要未来新增调用路径违反约定；届时由 `displayEnabled` 兜底隐藏导出按钮，风险可控。

## Open Questions

无（fail-closed 口径、入口覆盖范围、静默探测策略均已随 PR #849 检视确认）。
