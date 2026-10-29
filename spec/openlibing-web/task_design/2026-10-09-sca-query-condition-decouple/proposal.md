# 风险数据看板与检测中心-SCA 查询条件解耦（级联改独立组合）

## Why

两处查询条件为强级联，用户被迫按层级补齐前置条件，无法以独立视角查询：

1. **合法合规-风险数据看板**（`src/views/sca/componentAnalysis/index.vue`）：平台→代码仓→分支强级联。代码仓下拉 `:disabled="!choosePlatformValue"`（未选平台禁用）、分支下拉 `:disabled="!chooseGitUrlValue"`（未选代码仓禁用）。用户只想按代码仓或分支查询时，必须先补齐平台/仓库前置条件。**该页面两个 tab 受影响**："开源片段引用合规"与"项目合规-文件级兼容性"（`isShowItem` 对 `isOpenSource || secondActiveName === 'file'` 均放行平台/代码仓/分支下拉，两 tab 共用同一组查询条件与同一份代码）；"项目合规-二进制包级兼容性"tab 条件为版本/包名/兼容性，不涉及本级联，不在范围。
2. **检测中心-SCA**（`src/views/InspectionCenter/index.vue`）：仓库→分支级联。分支下拉 `:disabled="!formInSpection.repoId"`（未选仓库禁用），且远程搜索接口 `GET /ci-portal/v1/full/repo/branch-list` 强制要求 `repoId`，无项目级分支搜索能力。

**详情页排查结论（均无独立级联下拉，无需改动）**：风险数据详情 `gitUrlList.vue` 的查询条件由父组件传入；PR 扫描详情 `openSourceDetail.vue` 仅有 PR 状态/日期/关键字过滤。

**范围变更记录（2026-10-10）**：PR 扫描-开源片段引用合规（`PRComponentAnalysis/components/openSourceCompliance/index.vue`）原在改造范围内，一度经需求方确认移出范围（本地改动曾还原），同日经需求方确认**恢复改造**，最终在范围内（见 What Changes 第 3 节与 design.md D8）。

**需求变更（2026-10-14）**：项目合规菜单下本次需求涉及的平台下拉框（`componentAnalysis/index.vue` 查询条件区，项目合规-文件级兼容性与开源片段引用合规两 tab 共用）新增 `atomgit` 平台项；同日二次澄清——仓库链接 URL 跳转部分（两个 analysisTable 的 `openReposUrl` + `ATOMGIT_BASE_URL` 配置）属改造范围、已复原，见 What Changes 第 5 节与 design.md D9。**同日三次澄清（范围再扩大）**：PR 扫描列表（`openSourceCompliance/index.vue`）的平台下拉也新增 `atomgit`（此前一轮曾按"仅项目合规"回退，本轮需求方明确要求加入）；同时优化 PR 扫描下拉的树接口重复调用——数据已加载且项目未变时点击下拉不再重复请求，见 What Changes 第 5 节与 design.md D9。**需求取消（2026-10-16，需求方确认）**：atomgit 相关改动**整体回退**——两处平台下拉恢复 `gitee`/`gitcode` 两项、`ATOMGIT_BASE_URL` 配置与两个 analysisTable 的域名映射全部移除（URL 跳转逻辑恢复到改造前）；PR 扫描树请求缓存优化与 atomgit 无关，**保留**。见 What Changes 第 5 节与 design.md D9。

**价值**：

- 查询效率提升：条件任意组合、按需查询，减少强制性点击与平台间来回切换。
- 可扩展性：查询条件解耦后，后续新增代码托管平台无需调整级联逻辑（平台维度从树数据动态推导，不再依赖硬编码聚合）。

## What Changes

### 1. 合法合规-风险数据看板（前端独立完成；覆盖"开源片段引用合规"+"项目合规-文件级兼容性"两个 tab，共用同一组查询条件）

- **三个下拉完全独立**：平台、代码仓、分支互不联动、互不清空——即使选择矛盾组合也保留已选值；代码仓选项恒为全平台聚合、分支选项恒为全部分支聚合，不随上级选择过滤。
- **分支选项去重**：同名分支按名称去重，仅展示分支名称（不带仓库归属后缀）。
- **选分支仅筛选列表**：分支是列表筛选条件（`chooseBranchValue` 存分支名称字符串），选择后停留在列表原地刷新，不再作为详情入口跳转；详情仍通过看板行点击进入（`detailRow` 与筛选状态分离）。
- **树数据加载时机前置**：页面初始化即加载树（现状首次选择平台或从看板行点击时才加载）；聚合推导带数组守卫并辅以重试，树接口软失败时下拉不为空。
- **平台下拉动态化**：三个已知平台 `['gitee', 'gitcode', 'atomgit']` **恒展示**（2026-10-14 修复为并集语义——原交集实现会因项目树中暂无某平台仓库而过滤掉该平台项），树数据的平台 key（过滤 `nameCommunity` 且仅认数组字段）推导出的新增托管平台自动追加，无需改代码。
- **聚合态消歧展示**：代码仓选项在跨平台同名时以 `名称（平台）` 形式消歧。

### 2. 检测中心-SCA（前端改造；后端新接口已落地）

> 方案变更（2026-10-13/14）：筛选方案从"表单区独立下拉"最终变更为"表头多选筛选"，本节按最终实现描述。

- **筛选数据源为 SCA 新接口**：`GET /gateway/openlibing-sca/version/scan/repoBranchList`，入参 `communityId`（当前项目 ID，2026-10-12 新增——选项数据收敛为当前项目下的全量仓库/分支，与其他 tab 按项目过滤行为对齐），返回 `{code, message, data: {repos: string[], branches: string[]}}` 去重名称数组（后端 dev_beta_20261019 提交 52575f7 已落地）。URL 前缀经需求方确认采用 `/version/scan`（`ManualVersionScanController` 实际挂载路径，`/open/scan` 属 `OpenScanController` 无此接口）。
- **筛选移至表头（仅 SCA tab，最终方案）**：仓库/分支/检查结果三列表头复用门禁检查列表"检查结果"列的 `FilterDropdown` 组件（关键词搜索 + 多选 + 全选 + 筛选/重置按钮，激活时漏斗图标变蓝），`type="checkbox"` 多选；检查结果选项为固定状态项（未执行扫描/扫描中/扫描成功/扫描失败），承接原"任务状态"下拉的筛选职责。
- **表单区下拉按 tab 隐藏**：仓库/分支/任务状态三个下拉以 `v-if="activeName !== 'sca'"` 在 SCA tab 整体不展示，CodeCheck/AntiPoison tab 完整保留原有 repoId/branchId 绑定、远程搜索、分支依赖仓库的级联，原逻辑零改动；SCA tab 表单区仅保留批量操作按钮。
- **变更行为**：任一列筛选变更（含重置）仅重置分页并原地刷新列表，各列筛选互不关联、互不清空。
- **切 tab 重置**：`switchTab` 清空 `scaRepoFilter`/`scaBranchFilter`/`scaStatusFilter`（表格销毁重建，FilterDropdown 选中态随之重置），重置对象补 `repoId`/`branchId`/`branchName` 防跨 tab 残留串扰。
- **查询参数**：`/version/scan/query` 请求体以 `repoName`/`branchName`/`scanStatus` 字段上送筛选数组（2026-10-14 拼写确认：沿用原单值字段名、不改为复数，值由单值变为多选数组）；名称过滤后端已支持，数组过滤后端已实现（2026-10-14 需求方确认）。

### 3. PR 扫描-开源片段引用合规（前端独立完成）

- **平台/代码仓下拉完全互不影响（列表态）**：移除代码仓下拉 `:disabled="!choosePlatformValue"` 与平台下拉 `@clear` 重置绑定（列表态清除平台不再连带清空已选代码仓）；代码仓选项恒为全量聚合（`getAllRepositories`，不随已选平台过滤）；选/清平台均不清空已选代码仓，矛盾组合保留已选值。
- **树数据加载时机前置**：`projectId` 就绪即自动加载树（watch `projectIdValue` immediate，规避 projectInfo 分步填充的时序问题），两个下拉不依赖点击触发拉取；树数据带数组守卫，树接口软失败时选项为空但不崩溃，下拉点击可重新拉取。
- **聚合态消歧展示**：代码仓选项跨平台同名时以 `名称（平台）` 形式消歧。
- **兜底回显**：已选仓库不在选项集（树未加载/软失败）时，下拉仍回显已选仓库。
- **选代码仓仅筛选列表**（2026-10-12 需求变更）：选代码仓不再跳转详情，仅为筛选动作——列表按仓库名（`repository` 参数，后端已实现，2026-10-14 需求方确认）原地刷新并重置页码；详情唯一入口为看板行点击。
- **保留原有语义**：详情态下变更/清除平台或代码仓任一下拉仍退出详情回列表（清平台时代码仓选择保留、列表原地刷新）；项目切换清空重置（`changeSelectCommunity`）、从详情返回列表（`returnDetail`）行为不变。

### 4. 后端依赖（openlibing-sca）

| 接口                                                                                       | 状态                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /version/scan/repoBranchList`                                                         | 已落地：dev_beta_20261019 提交 52575f7（2026-10-10），返回去重仓库/分支名称数组；2026-10-12 增加 `communityId` 入参（当前项目 ID），下拉数据收敛为项目内全量            |
| `POST /version/scan/query` 按 `repoName`/`branchName` 过滤                                 | 后端已支持（需求方确认，2026-10-10）；2026-10-14 起前端仍以 `repoName`/`branchName` 字段上送（拼写不变，值改为多选数组），数组值过滤后端已实现（2026-10-14 需求方确认） |
| `POST /version/scan/query` 按 `scanStatus` 数组过滤（2026-10-14 新增，检查结果列多选筛选） | 已实现（2026-10-14 需求方确认），数组过滤（`repoName`/`branchName`/`scanStatus`）生效                                                                                   |
| `POST /open/person/repos` 按 `repository` 过滤（PR 扫描选仓筛选，2026-10-12 新增）         | 已实现（2026-10-14 需求方确认），选仓筛选生效                                                                                                                           |

原方案的 openlibing-codecheck `branch-list` 项目级搜索扩展**已废弃**：检测中心-SCA 改用自有新接口，不再依赖 codecheck 接口，无需扩展。

### 5. atomgit 平台支持（2026-10-14 需求变更，**2026-10-16 需求取消、整体回退**）

> 该需求曾经历多轮范围澄清（平台下拉先后覆盖项目合规 `componentAnalysis/index.vue` 与 PR 扫描列表 `openSourceCompliance/index.vue`；URL 跳转部分经二次确认纳入），2026-10-16 需求方确认**整体取消**：atomgit 选项与仓库链接域名支持全部回退，所有页面平台下拉恢复 `['gitee', 'gitcode']` 两项原状，`ATOMGIT_BASE_URL` 配置与域名映射移除。**唯一保留**：PR 扫描列表树接口重复调用优化（`communityTreeProjectId` 缓存标识，与 atomgit 无关的独立体验需求，2026-10-14 同步提出）。

- **保留（PR 扫描树请求缓存）**：`openSourceCompliance/index.vue` data 新增 `communityTreeProjectId` 缓存标识，`getCommunityTreeData` 在"树已成功加载且 projectId 未变"时跳过重复请求（点击平台/代码仓下拉的 `@click="repoInit"` 不再重拉树），项目切换由 projectId watch 触发重拉、软失败不记录缓存保持可重试（见 design.md D9）。
- **已回退（不再生效）**：`componentAnalysis/index.vue` platformOptions 补 atomgit、PR 扫描列表 platformOptions 补 atomgit、`config.json` 的 `ATOMGIT_BASE_URL`、两个 analysisTable 的 `openReposUrl` 平台域名映射——均恢复到改造前状态。

## Capabilities

### New Capabilities

- `risk-dashboard-decoupled-query`：风险数据看板平台/代码仓/分支查询条件完全独立的能力契约（覆盖"开源片段引用合规"+"项目合规-文件级兼容性"两 tab 共用查询区）——任一条件可单独或任意组合使用，选项恒为全量聚合，分支选项去重仅展示名称，选分支仅筛选列表不进详情，矛盾组合保留已选值。
- `inspection-sca-repo-branch-decoupled-query`：检测中心-SCA tab 查询条件独立的能力契约——仓库/分支/检查结果三列表头多选筛选（`FilterDropdown`，样式同门禁检查列表"检查结果"列），选项为当前项目下全量去重数据/固定状态项，各列互不关联，选中值按 `repoName`/`branchName`/`scanStatus` 字段（数组）上送 `/version/scan/query` 过滤任务列表；SCA tab 表单区下拉不展示；CodeCheck/AntiPoison tab 行为不变。

### Modified Capabilities

无（`openspec/specs/` 下暂无本模块既有 spec）。

## Impact

- **受影响代码**（openlibing-web）：
  - `apps/web-openlibing/src/views/sca/componentAnalysis/index.vue`：三级下拉解禁、选项恒全量聚合、分支去重、选分支仅筛选、树加载时机前置、平台动态化、矛盾组合保留已选值（对"开源片段引用合规"+"项目合规-文件级兼容性"两 tab 同时生效）。
  - `apps/web-openlibing/src/views/sca/PRComponentAnalysis/components/openSourceCompliance/index.vue`：代码仓下拉解禁、选项恒全量聚合（`getAllRepositories`）、选代码仓仅筛选（`repository` 参数上送、`getChooseRepository` 删除，详情仅经行点击进入）、选/清平台不清代码仓（移除平台 `@clear` 重置绑定）、详情态下拉变更/清除退出详情回列表、树初始化加载（projectId watch）、同名消歧、兜底回显；`getCommunityTreeData` 增加 `communityTreeProjectId` 缓存标识（树已加载且项目未变时点击下拉跳过重复请求，软失败不记录缓存保持可重试，2026-10-16 回退 atomgit 后保留）。
  - `apps/web-openlibing/src/views/sca/softInformation/communityList.vue`：列表组件接收分支名称筛选参数（`chooseBranchValue`），支持"仅按分支筛选列表"。
  - `apps/web-openlibing/src/utils/scaUtils.js`：新增 `getAllPlatformRepos`/`getAllRepoBranchs`/`getAllRepositories` 聚合函数（不改既有函数签名）。
  - `apps/web-openlibing/src/api/url.ts` / `api.ts`：新增 `SCA_REPO_BRANCH_LIST` 常量与 `scaRepoBranchList` GET 函数。
  - `apps/web-openlibing/src/views/InspectionCenter/index.vue`：SCA tab 表单区下拉隐藏（`v-if="activeName !== 'sca'"`）、表头 FilterDropdown 多选筛选（仓库/分支/检查结果三列，选项映射 `scaFilterOptions`）、`handleScaFilterChange` 变更处理（FilterDropdown `{name, data}` payload）、`getSca` 以 `repoName`/`branchName`/`scanStatus` 字段上送筛选数组、切 tab 重置（含 `scaStatusFilter`）。
  - `apps/web-openlibing/src/components/filterDropdown.vue`：全选框状态修复（初始 `isIndeterminate` 置 false、`reset()`/关闭面板未筛选分支补 `checkAll`/`isIndeterminate` 复位；共享组件，15 个使用页面同步受益，2026-10-14）。
  - ~~`apps/web-openlibing/src/views/sca/personalScandTaskInfor/analysisTable.vue` 与 `PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue` 的 `openReposUrl` 平台域名映射、`config.json` 的 `ATOMGIT_BASE_URL`~~：2026-10-16 需求取消，**已整体回退**（两文件 `openReposUrl` 恢复 gitee 二元判断原状，配置项已移除）。
- **明确不受影响（回归验证点）**：
  - `InspectionCenter/index.vue` 的 CodeCheck / AntiPoison tab：仓库/分支下拉仍为原 repoId/branchId 绑定与"未选仓库禁用分支"级联行为，零改动。
  - `src/views/sca/component/communityRepoSelect/index.vue`（平台→代码仓级联组件）：使用方为合规度量（`complianceMeasure.vue`）与 PR 扫描详情（`PRScanDetail.vue`），零改动；其依赖的 `filterRepositories`（`utils/index.js`）签名保留不动。
  - `src/views/sca/softInformation/gitUrlList.vue`（风险数据详情）与 `openSourceDetail.vue`（PR 扫描详情）：零改动。
  - 风险数据看板"项目合规-二进制包级兼容性"tab：条件为版本/包名/兼容性，不涉本级联，零改动。
  - `src/utils/index.js` 中 `getPlatformRepos`/`getPlatformRepoBranchs` 同名副本：无引用方（死代码），不动。
- **风险**：
  - 检测中心-SCA 依赖 beta 环境部署后端提交 52575f7；未部署时 `repoBranchList` 返回 404，仓库/分支表头筛选选项为空态（不影响其他 tab 与既有查询）；数组过滤（`repoName`/`branchName`/`scanStatus`）后端已实现（2026-10-14 需求方确认），无降级风险。
  - 看板列表查询（`getRepos`）历史从未收到过 `platform='' && repository!=''` 的组合，独立过滤表现需联调验证；若后端条件非独立，需 openlibing-sca 后端修复。
