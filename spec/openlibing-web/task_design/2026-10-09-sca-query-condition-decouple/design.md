# 风险数据看板与检测中心-SCA 查询条件解耦 — 技术设计

## Context

### 模块一：合法合规-风险数据看板（`src/views/sca/componentAnalysis/index.vue`）

页面结构：`componentAnalysis/index.vue`（查询条件区 + tab 切换）→ `communityList.vue`（风险数据看板列表） / `giturlList.vue`（分支风险数据详情，按 `scanId` 查询）。

**tab 覆盖关系**：页面内"开源片段引用合规"（`activeName === 'openSourceCompliance'`）与"项目合规-文件级兼容性"（`activeName === 'projectCompliance' && secondActiveName === 'file'`）两个 tab 共用同一组平台/代码仓/分支下拉框——`isShowItem('platform'/'repo'/'branch')` 对 `isOpenSource || secondActiveName === 'file'` 均返回 true，本模块改造对两 tab 同时生效。"项目合规-二进制包级兼容性"tab（`binary`/`binary_license`）条件为版本/包名/兼容性（`version`/`packageName`/`compatibility`），不涉及本级联，不在范围。

改造前级联链路：

```text
平台下拉(硬编码 ['gitee','gitcode'])
  └─ 代码仓下拉 :disabled="!choosePlatformValue"
       repoOptions = getPlatformRepos(communityOpts, community, platform)   （platform 为空返回 []）
  └─ 分支下拉 :disabled="!chooseGitUrlValue"
       branchOptions = getPlatformRepoBranchs(communityOpts, community, platform, repoName)   （platform/repoName 任一为空返回 []）
```

关键现状事实：

- 树数据 `communityOpts` 来自 `getCommunityRepoBranch({params: {projectId}})`（`GET /openlibing-sca/open/scan/community/branch`），**一次性返回全量树**，与平台无关。结构：`[{ nameCommunity, gitee: [repos], gitcode: [repos] }]`，`repos: [{ repoName, branchList: [{ id, branch, ... }] }]`（平台是 community 对象上的 key；树对象上还存在 `community` 等字符串元数据字段，聚合时必须只认数组字段）。
- 树初始为 `[]`，**首次选择平台**或从看板行点击才加载；`changeSelectPlatform` 每次变化还会重拉一次树（树与平台无关，属冗余请求）。
- 看板列表查询（`communityList.vue` `initQueryData`）：`getRepos({community, pageNo, pageSize, platform, repository})`——`platform` 与 `repository` 是**相互独立的参数**。
- 平台下拉 options 原硬编码 `['gitee', 'gitcode']`。
- 导出（`exportExcel`/`exportLicenseExcel`/`exportUnconfirmedExcel`）只传 `community + platform`，不含 `repository`——现状导出本就忽略仓库筛选。

### 模块二：检测中心-SCA（`src/views/InspectionCenter/index.vue`）

该页面为 **CodeCheck / AntiPoison / Sca 三个 tab 共用**（`activeName`），查询条件区为公共模板：

- 仓库下拉：remote 搜索 `getRepoSelectApi(projectId, repoName)`，绑定 `formInSpection.repoId`。
- 分支下拉：`:disabled="!formInSpection.repoId"`，remote 搜索 `getBranchOptions`——`if (!formInSpection.repoId) return`，调用 `getRepoBranchList({params: {repoId, branchName}})`（codecheck 接口 `GET /ci-portal/v1/full/repo/branch-list`，**repoId 必传**，无项目级搜索能力）。
- SCA 任务查询 `getSca`：`scaQueryVersionScan({data: {...formInSpection, scanStatus, communityId}})`（`POST /gateway/openlibing-sca/version/scan/query`），`formInSpection` 含 `repoId/repoName/branchId/branchName` 全量上送。

### 范围变更记录（PR 扫描）

PR 扫描-开源片段引用合规（`PRComponentAnalysis/components/openSourceCompliance/index.vue`）原在本设计范围，2026-10-10 一度经需求方确认移出（本地改动曾还原），同日经需求方确认**恢复改造**，最终在范围内（方案见 D8）。`filterRepositories`（`utils/index.js`）与共享组件 `communityRepoSelect` 不受本需求任何影响（PR 扫描页改用 `getAllRepositories` 后，`filterRepositories` 仅由 `communityRepoSelect` 使用）。

### 共享组件排查结论（改动隔离依据）

| 共享点                                                                         | 使用方                                                             | 处置                                                                                                                                             |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/views/sca/component/communityRepoSelect/index.vue`（平台→代码仓级联组件） | 合规度量 `complianceMeasure.vue`、PR 扫描详情 `PRScanDetail.vue`   | **零改动**，不在需求范围（2026-10-14 atomgit 范围澄清后保持原状）                                                                                |
| `src/utils/scaUtils.js` `getPlatformRepos`/`getPlatformRepoBranchs`            | 仅 `componentAnalysis/index.vue`                                   | 保留原函数签名不动，**新增** `getAllPlatformRepos`/`getAllRepoBranchs` 聚合函数                                                                  |
| `src/utils/index.js` `filterRepositories`                                      | 共享组件 `communityRepoSelect`                                     | 本需求**零接触**（PR 扫描页改用 `scaUtils.js` 的 `getAllRepositories`，不再引用）                                                                |
| `src/utils/index.js` 内 `getPlatformRepos`/`getPlatformRepoBranchs` 同名副本   | 无引用（死代码）                                                   | 不动                                                                                                                                             |
| `InspectionCenter/index.vue` 查询条件区                                        | 三 tab 共用                                                        | 仓库/分支/任务状态三个下拉以 `v-if="activeName !== 'sca'"` 在 SCA tab 整体隐藏（CodeCheck/AntiPoison 走原分支零改动）；SCA 筛选移至表头（见 D6） |
| `openSourceDetail.vue`（PR 扫描详情）/ `gitUrlList.vue`（风险数据详情）        | 无级联下拉（前者仅 PR 状态/日期/关键字过滤，后者条件由父组件传入） | **零改动**                                                                                                                                       |

## Goals / Non-Goals

**Goals：**

- 风险数据看板：平台/代码仓/分支三个条件完全独立（任意单独或组合可用，矛盾组合保留已选值）；选项恒为全量聚合；分支选项同名去重仅展示名称；选分支仅筛选列表不进详情（对"开源片段引用合规"+"项目合规-文件级兼容性"两 tab 同时生效；前端独立完成，无后端依赖）。
- 检测中心-SCA：筛选移至表头——仓库/分支/检查结果三列复用门禁检查列表"检查结果"列的 `FilterDropdown` 多选筛选（仓库/分支选项取 SCA 新接口返回的项目内全量去重数据，检查结果为固定状态项），选中按 `repoName`/`branchName`/`scanStatus` 字段（数组）上送 `/version/scan/query` 过滤任务列表；SCA tab 表单区三个下拉不再展示，CodeCheck/AntiPoison tab 下拉保持原样。
- PR 扫描-开源片段引用合规：平台/代码仓两下拉互不影响（代码仓默认可选、选项恒为全量聚合、选/清平台不清代码仓），选代码仓仅筛选列表不跳详情（2026-10-12 需求变更，详情仅经看板行点击进入）。
- 新增代码托管平台时聚合逻辑无需调整（平台维度动态推导）。
- 不影响 CodeCheck / AntiPoison tab、合规度量、PR 扫描详情（`PRScanDetail`/`openSourceDetail`）等不涉及模块。

**Non-Goals：**

- 不改 `communityRepoSelect` 组件及其使用方（需求范围外）。
- 不改看板导出参数（`repository` 不上送为既有行为，见 D7）。
- 不实现后端接口（`repoBranchList` 与 query 名称过滤均已由 openlibing-sca 落地）。
- 不动 CodeCheck/AntiPoison tab 的路由参数初始化逻辑（`initRouteParams` 的 repo/branch query 场景保持现状）。

## Decisions

### D1：树加载时机前置 + 项目切换重拉（风险数据看板）

树数据与平台无关且聚合选项依赖全量树，改为：

- 组件初始化（projectId 就绪后）即调用 `getCommunityTreeData()`；聚合推导带**数组守卫**（`Array.isArray(communityObj[key])`，树对象含 `community` 等字符串元数据字段，无守卫会在 `.forEach` 上抛 TypeError 导致下拉为空）并辅以树接口软失败重试，保证下拉不因树接口偶发失败而空。
- `changeSelectPlatform` 去掉重拉树调用（冗余请求）。
- 项目切换时重拉树并重置平台/代码仓/分支条件。

### D2：聚合函数新增于 `scaUtils.js`，保留原函数

新增两个纯函数（不改既有 `getPlatformRepos`/`getPlatformRepoBranchs`，最小回归面）：

```js
// 聚合所有平台的代码仓（跨平台允许同名，供消歧展示）
getAllPlatformRepos(arr, community); // 返回 [{ repoName, platform, ...repo }]

// 聚合所有代码仓的分支（不做平台/仓库过滤）
getAllRepoBranchs(arr, community); // 返回 [{ ...branch, repoName, platform }]
```

- 平台集合从 community 对象动态推导：`Object.keys(communityObj).filter(k => k !== 'nameCommunity' && Array.isArray(communityObj[k]))`——**不依赖硬编码平台列表**，且只认数组字段排除字符串元数据。
- 分支浅拷贝 `{...branch, repoName, platform}` 不污染树原对象。

### D3：三条件完全独立 + 分支去重 + 选分支仅筛选

- `repoOptions` computed **恒为** `getAllPlatformRepos` 聚合（已选平台也不过滤——三条件彻底独立）。
- `branchOptions` computed **恒为** `getAllRepoBranchs` 聚合，并按 `item.branch` 名称**去重**（`Set` 实现），仅展示分支名称；分支选中值为名称字符串。
- **选分支不进详情**：拆分状态——`chooseBranchValue`（分支名称，列表筛选条件）与 `detailRow`（详情行，仅由看板行点击赋值）。分支下拉 change 仅更新 `chooseBranchValue` 并把筛选参数传给列表组件（`communityList.vue` 接收 `chooseBranchValue`），列表原地刷新；详情进入路径（看板行点击 → `detailRow`）不受影响。
- **详情态下拉变更回列表**：还原原先"下拉变更→详情条件失效自动回列表"的语义——平台/代码仓/分支三个下拉 `@change` 统一走 `handleFilterChange`：`detailRow?.id` 存在（详情态）时清除 `detailRow` 退出详情回列表，列表按当前筛选值原地刷新；列表态下无操作（互不关联改造不受影响）。程序赋值（看板行点击回填 `updateChooseUrlVal`、导出返回恢复 `restoreScaDetail`）不触发 change，详情进入/恢复链路不受影响。
- **矛盾组合保留已选值**：平台/代码仓/分支变化时互不清空对方（无归属校验——需求方确认彻底各选各的）。

### D4：平台下拉选项（已知平台恒展示 + 树推导平台追加）

`platformOptions` 返回**并集**：已知平台 `['gitee', 'gitcode']` 恒展示，树数据 community 对象 keys（过滤 `nameCommunity`、仅认数组字段）中的新增托管平台自动追加其后。

> 演进记录：初版为 base∩树平台交集（项目树中暂无某平台仓库节点时该平台项被过滤，曾致 atomgit 未展示）；2026-10-14 改为并集语义（已知平台不依赖树数据存在性，空树分支随之移除）。2026-10-16 atomgit 需求取消后 base 恢复两项，并集语义保留（已知平台恒展示，新增平台仍可自动追加）。

### D5：代码仓聚合态消歧

`repoNameCount` 统计聚合选项中的同名仓库数：代码仓选项跨平台同名时 label 显示 `repoName（platform）`，否则纯 `repoName`；代码仓选中值仍为 `repoName` 字符串（查询契约不变）。

### D6：检测中心-SCA 筛选移至表头（FilterDropdown 多选）+ 表单区下拉按 tab 隐藏（核心决策）

**方案演进**：初版为"SCA 专属独立下拉（`v-if` 互斥渲染）"；2026-10-13 需求变更筛选移至表头多选（el-table 原生 filters）；2026-10-14 最终定为复用门禁检查列表"检查结果"列的 `FilterDropdown` 组件，且表单区下拉在 SCA tab 不再展示。原"codecheck `branch-list` 项目级搜索扩展"方案（方案 C）废弃，改用 openlibing-sca 自有新接口：

- **接口**：`GET /gateway/openlibing-sca/version/scan/repoBranchList`，入参 `communityId`（当前项目 ID，取 `projectInfo.projectId`，2026-10-12 新增——选项"全量"语义收敛为**当前项目下**的全量仓库/分支，与其他 tab 按项目过滤的行为对齐），返回 `{code, message, data: {repos: string[], branches: string[]}}`（后端 dev_beta_20261019 提交 52575f7 已落地）。URL 前缀经需求方确认：接口实际挂载于 `ManualVersionScanController`（`@RequestMapping("/version/scan")`）；`/open/scan` 前缀属 `OpenScanController`（无此接口），网关无重写，用错会 404。
- **前端接口定义**：`src/api/url.ts` 新增 `SCA_REPO_BRANCH_LIST = \`${SCA}/version/scan/repoBranchList\``；`src/api/api.ts`新增`scaRepoBranchList`（GET）。
- **表单区下拉按 tab 隐藏（2026-10-14 需求变更）**：仓库/分支/任务状态三个 `el-form-item` 加 `v-if="activeName !== 'sca'"`（SCA 列表上方下拉不再展示，表单区仅剩批量操作按钮）；SCA 专属任务状态选项块随之删除；CodeCheck/AntiPoison tab 渲染分支与改造前逐字节一致，零行为变化。
- **表头筛选（FilterDropdown，样式参考门禁检查列表"检查结果"列）**：SCA 表格列 `#header` 插槽渲染 `@/components/filterDropdown.vue`（`type="checkbox"` 多选，`new-filter-icon`，面板含关键词搜索/多选/全选/筛选/重置，激活时漏斗图标变蓝；与门禁检查列表 `IncrementCheckList` 同款组件）。选项映射 `scaFilterOptions(columnKey)`：仓库/分支列取 `scaRepoFilters`/`scaBranchFilters` computed（全量去重名称 → `{label, value}`），检查结果列取固定 `scaStatusOptions`（0=未执行扫描/1=扫描中/2=扫描成功/3=扫描失败，承接原"任务状态"下拉职责）；无选项的列表头渲染纯文本 label。
- **拉取时机**：两处调用 `fetchScaRepoBranchOptions()`——①页面加载落在 sca tab（`watch projectInfo` → `initRouteParams` 之后）；②`switchTab` 切到 sca。两处调用时 `projectId` 均已就绪，请求上送 `communityId`（`params: { communityId: app.projectInfo?.projectId }`）；响应 `code === 200` 时填充 `scaRepoList`/`scaBranchList`（FilterDropdown 每次打开面板时基于当前 options 初始化，内置关键词本地过滤）。
- **变更处理**：`handleScaFilterChange`（FilterDropdown `@change`，payload `{name, data}`）——`invalidateTaskRequests` + 停止轮询 + 清空 `scaSelection` + 重置 `pageNum` + 按 `name`（repoName/branchName/scanStatus）写入 `scaRepoFilter`/`scaBranchFilter`/`scaStatusFilter` + `getFullTask()`；**各列筛选互不清空**（互不关联）。
- **切 tab 重置**：`switchTab` 清空 `scaRepoFilter`/`scaBranchFilter`/`scaStatusFilter`（SCA 表格 `v-else-if` 渲染，切 tab 即销毁重建，FilterDropdown 内部选中态随之重置）；重置对象在原有基础上补 `repoId: ''`/`branchId: ''`/`branchName: ''`（原仅重置 `repoName`），防止 codeCheck 选过的 repoId 残留串扰 sca 查询参数。
- **查询参数（2026-10-14 变更）**：`getSca` 以 `repoName`/`branchName`/`scanStatus` 字段上送筛选数组（拼写确认：沿用原单值字段名、不改为复数，值由单值变为多选数组，并覆盖 `formInSpection` 中的同名空字符串 key）；名称过滤后端已支持，数组过滤后端已实现（2026-10-14 需求方确认）。

### D7：导出参数不含 `repository` —— 维持现状

看板三处导出现状只传 `community + platform`。本次聚焦查询链路，导出补参涉及后端消费确认，列为遗留项不在本 spec 范围。

### D8：PR 扫描-开源片段引用合规下拉解耦（共享函数隔离 + 选仓仅筛选）

PR 扫描树与风险数据看板树**结构不同**（扁平结构，仓库对象自带 `platform` 字段），且该页详情**仅经看板行点击进入**（2026-10-12 需求变更：选代码仓不再作为详情入口，仅为列表筛选动作），故与看板方案做隔离、筛选语义对齐：

- `scaUtils.js` 新增 `getAllRepositories(arr, community)`（匹配 `nameCommunity`，返回 `repositories` 全量数组，含非数组守卫）；PR 扫描页改用它，不再引用 `filterRepositories`（共享组件 `communityRepoSelect` 仍在用，签名不动）。
- 模板：代码仓下拉移除 `:disabled="!choosePlatformValue"`，加 `@click="repoInit"`（树未加载/软失败时可点击重拉）；选项 label 经 `repoOptionLabel` 跨平台同名时消歧为 `repository（platform）`；已选仓库不在选项集时**兜底回显**（label 取 `chooseGitObject.repository`）。
- 选项恒为全量：`changeSelectPlatform` 不再清空 `chooseGitUrlValue`/`chooseGitObject`、`gitUrlOpts` 恒为 `getAllRepositories` 聚合（选/清平台仅刷新表格）；`changeSelectCommunity`（项目切换）保留清空重置语义；树加载完成后在 `getCommunityTreeData` 内同步更新 `gitUrlOpts`。
- 清平台不清代码仓（列表态）：移除平台下拉 `@clear="changeSelectCommunity"` 绑定——Element Plus 清除按钮会同时触发 `clear` 与 `change`（`change` 携带空值已走 `changeSelectPlatform` 保留代码仓），旧 `clear` 绑定会连带清空已选代码仓，违反"清平台不清代码仓"语义。详情态下清除平台**仍需退出详情回列表**（保持原有"清除任一下拉回列表"逻辑）：`changeSelectPlatform` 内以 `isDetail && !choosePlatformValue` 判断 emit `toogleDetail false`，代码仓选择保留、列表按当前筛选原地刷新；详情态下变更平台（非清除）与 `getDetail` 内部调用（彼时 `isDetail` 尚为 false）均不受影响。
- 树加载前置：树数据仅依赖 `projectId`——watch `projectIdValue`（immediate，就绪或切换项目即触发）调用 `getCommunityTreeData()`；`chooseCommunityValue` watch 仅刷新列表并做聚合兜底（树先于社区名就绪时用已缓存树数据同步聚合）。两个下拉的 `@click="repoInit"` 保留为软失败重拉兜底（树已成功加载时命中 D9 缓存标识、点击不再重复请求）。
- 选代码仓仅筛选（2026-10-12 需求变更）：`changeSelectGitUrl` 不再经 `getChooseRepository` 调 `getDetail` 跳详情（`getChooseRepository` 已删除），改为同步 `chooseGitObject`（选中项匹配，树未加载/匹配失败置空）→ 详情态下变更/清除时 emit `toogleDetail false` 退出详情回列表 → 重置 `currentPage` 并携带 `repository`（取 `chooseGitObject.repository`）刷新列表；列表接口 `open/person/repos` 按仓库名过滤为**新增后端依赖**（参数名 `repository` 与看板接口对齐，后端已实现，2026-10-14 需求方确认）。
- `getDetail`（看板行点击，详情唯一入口）流程不变（回填平台/代码仓，`getCommunityTreeData(true)` 的 init 路径与全量选项兼容）；`returnDetail` 返回列表清空下拉与 `chooseGitObject`、列表退出仓库筛选，保持原状。

### D9：PR 扫描树请求缓存（2026-10-14 需求变更；同日 atomgit 平台支持**已于 2026-10-16 需求取消、整体回退**）

**atomgit 需求回退记录（2026-10-16 需求方确认）**：2026-10-14 曾多轮澄清新增 atomgit——平台下拉（`componentAnalysis/index.vue` base 数组 + PR 扫描列表 `openSourceCompliance/index.vue` 硬编码选项）与仓库链接域名映射（`config.json` 的 `ATOMGIT_BASE_URL` + 两个 analysisTable 的 `openReposUrl` 平台映射表）。2026-10-16 需求方确认**整体取消**：上述改动全部回退到改造前状态——所有页面平台下拉恢复 `['gitee', 'gitcode']` 两项，`openReposUrl` 恢复"gitee 二元三元"判断（gitee 走 GITEE_BASE_URL、其余默认 GITCODE_BASE_URL）。

> **例外（2026-10-16 构建修复 ca03db90）**：回退曾一并移除 `config.json` 的 `ATOMGIT_BASE_URL`，但同事 commit `de1f1150`（repos 模块独立需求：atomgit 作为 gitcode 镜像域名的录入校验白名单）在 `utils/until.js` 的 `whiteLinks` 中引用该常量，且该改动已独立合入 `beta_gamma`——配置缺失导致 beta 构建 Rollup 报错 `"ATOMGIT_BASE_URL" is not exported`。已恢复该配置常量（仅配置项，不含任何平台下拉选项/URL 映射，本任务回退结论不变）。

本节仅保留与 atomgit 无关的独立优化：

实现（保留项）：

- **PR 扫描树请求缓存（`openSourceCompliance/index.vue`）**：data 新增 `communityTreeProjectId` 缓存标识；`getCommunityTreeData` 开头判断"标识非空且等于当前 projectId"则跳过请求（`@click="repoInit"` 点击平台/代码仓下拉不再重拉树，命中缓存时 `init` 分支行为保留）。成功响应（含空数组）才记录标识，软失败（非数组）不记录——保持点击下拉可重试；项目切换由 `projectIdValue` watch 触发，projectId 变化后标识不匹配自动重拉。树数据仅依赖 projectId，projectId 不变时数据不会变化，跳过请求无数据一致性风险。
- **不涉及**：`utils/common.ts` 账号标识（gitCode/gitee 账号绑定）、`profileLink.ts` 个人主页域名、`validateSafeUrl` 链接白名单（仅 Repos 模块）——均不动。

## 交互矩阵

### 风险数据看板（开源片段引用合规 / 项目合规-文件级兼容性两 tab 同构）

| 已选平台 | 已选代码仓 | 代码仓下拉选项                 | 分支下拉选项                       | 分支选中后                     |
| -------- | ---------- | ------------------------------ | ---------------------------------- | ------------------------------ |
| 任意     | 任意       | 恒全平台聚合（跨平台同名消歧） | 恒全部分支聚合（同名去重、纯名称） | 仅筛选列表，原地刷新，不跳详情 |

三条件任意单独或组合使用，互不清空；矛盾组合保留已选值。看板列表随平台/代码仓独立过滤；详情仅经看板行点击进入。

### 检测中心-SCA

| 表头筛选列 | 数据源                                                                      | 选中值                        | 变更行为                            |
| ---------- | --------------------------------------------------------------------------- | ----------------------------- | ----------------------------------- |
| 仓库       | `repoBranchList`（communityId=当前项目）→ `data.repos`（项目内全量去重）    | `scaRepoFilter`（名称数组）   | 重置分页 + 刷新列表，不清其他列筛选 |
| 分支       | `repoBranchList`（communityId=当前项目）→ `data.branches`（项目内全量去重） | `scaBranchFilter`（名称数组） | 重置分页 + 刷新列表，不清其他列筛选 |
| 检查结果   | 固定状态项（0=未执行扫描/1=扫描中/2=扫描成功/3=扫描失败）                   | `scaStatusFilter`（状态数组） | 重置分页 + 刷新列表，不清其他列筛选 |

SCA tab 表单区无下拉（仅批量操作按钮）；三列筛选任意组合按 `repoName`/`branchName`/`scanStatus` 字段（数组）上送 `/version/scan/query`；切 tab 表格销毁重建、筛选面板选中态重置。CodeCheck/AntiPoison tab：仓库 repoId 远程搜索 + 分支 repoId 级联禁用 + 任务状态下拉，与改造前完全一致。

### PR 扫描-开源片段引用合规

| 操作       | 列表态                                                 | 详情态                                   |
| ---------- | ------------------------------------------------------ | ---------------------------------------- |
| 选代码仓   | 列表按 `repository` 筛选原地刷新（重置页码），不跳详情 | 退出详情回列表，列表按 `repository` 筛选 |
| 清代码仓   | 列表刷新（退出仓库筛选）                               | 退出详情回列表，列表无仓库筛选           |
| 选/清平台  | 列表按平台刷新，代码仓选择与筛选保留                   | 清平台退出详情回列表；变更平台仅刷新列表 |
| 看板行点击 | 进详情（唯一详情入口）                                 | —                                        |

两下拉互不清空，矛盾组合保留已选值；`returnDetail` 从详情返回列表清空下拉与仓库筛选。

## 后端接口契约（openlibing-sca）

### `GET /version/scan/repoBranchList`（已落地：dev_beta_20261019 提交 52575f7；2026-10-12 增加 `communityId` 入参）

- 入参 `communityId`（2026-10-12 新增，当前项目 ID，前端取 `projectInfo.projectId` 上送，按项目过滤下拉数据源）；返回 `ResponseEntity.success({repos, branches})`，前端消费 `{code: 200, message, data: {repos: string[], branches: string[]}}`。
- `repos`/`branches` 为去重名称字符串数组（后端基于已扫描任务聚合）。

### `POST /version/scan/query`（名称过滤已支持；数组化为 2026-10-14 契约变更）

- 2026-10-14 起请求体中 `repoName`/`branchName`/`scanStatus` 字段值由单值改为多选数组（字段拼写沿用原单值契约、不改为复数），前端在 `getSca` 显式上送并覆盖 `formInSpection` 同名空值 key。
- `repoId`/`branchId` 空串→null 时跳过 ID 过滤；`repoName`/`branchName`/`scanStatus` 数组过滤后端均已实现（2026-10-14 需求方确认），无降级风险。

### `GET /openlibing-sca/open/scan/repos` 验证项（联调）

- 看板列表 `platform='' && repository!=''` 组合的独立过滤表现（历史上该组合不会出现）；若非独立需 openlibing-sca 后端修复后"仅选代码仓"场景才可交付。

### `POST /open/person/repos`（PR 扫描列表）`repository` 过滤（新增依赖，已确认支持）

- 选代码仓仅筛选后，列表请求在 `community`/`platform`/分页参数基础上新增 `repository`（仓库名，取选中项 `repository` 字段）上送过滤；参数名与看板列表接口对齐。
- 后端 `repository` 过滤已实现（2026-10-14 需求方确认），"仅选代码仓"筛选可交付。

~~openlibing-codecheck `GET /ci-portal/v1/full/repo/branch-list` 项目级搜索扩展~~：**已废弃**（检测中心-SCA 改用自有新接口）。

## 涉及文件

| 文件                                                                                                      | 操作   | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/sca/componentAnalysis/index.vue`                                           | 修改   | 移除两处 disabled、computed 恒聚合、分支去重、选分支仅筛选（`chooseBranchValue`/`detailRow` 状态分离）、树初始化加载与项目切换重拉、platformOptions 动态化（对"开源片段引用合规"+"项目合规-文件级兼容性"两 tab 同时生效）；已知平台 `['gitee','gitcode']` 恒展示（并集，见 D4；2026-10-16 atomgit 回退后 base 恢复两项）                                                                                                                                                                           |
| `apps/web-openlibing/src/views/sca/softInformation/communityList.vue`                                     | 修改   | 接收 `chooseBranchValue` 分支名称筛选参数，支持"仅按分支筛选列表"                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `apps/web-openlibing/src/utils/scaUtils.js`                                                               | 修改   | 新增 `getAllPlatformRepos`/`getAllRepoBranchs`/`getAllRepositories` 聚合函数（含数组守卫）                                                                                                                                                                                                                                                                                                                                                                                                         |
| `apps/web-openlibing/src/api/url.ts` / `api.ts`                                                           | 修改   | 新增 `SCA_REPO_BRANCH_LIST` 常量与 `scaRepoBranchList` GET 函数                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `apps/web-openlibing/src/views/InspectionCenter/index.vue`                                                | 修改   | 表单区下拉 `v-if="activeName !== 'sca'"` 按 tab 隐藏、表头 FilterDropdown 多选筛选（`scaFilterOptions` 选项映射、`scaStatusOptions` 固定状态项）、`fetchScaRepoBranchOptions` 拉取（communityId）、`handleScaFilterChange` 变更处理、`getSca` 数组参数上送、`switchTab` 重置（含 `scaStatusFilter`）                                                                                                                                                                                               |
| `apps/web-openlibing/src/views/sca/PRComponentAnalysis/components/openSourceCompliance/index.vue`         | 修改   | 代码仓下拉解禁、选项恒全量聚合（`getAllRepositories`）、选代码仓仅筛选（`repository` 参数上送、`getChooseRepository` 删除，详情仅经行点击进入）、选/清平台不清代码仓（移除平台 `@clear` 重置绑定）、详情态下拉变更/清除退出详情回列表、树初始化加载（projectId watch）、同名消歧、兜底回显；`getCommunityTreeData` 缓存标识 `communityTreeProjectId`（树已加载且项目未变时点击下拉跳过重复请求，见 D9；2026-10-16 atomgit 回退后保留）；平台下拉 `platformOptions` 恢复 `['gitee','gitcode']` 两项 |
| `apps/web-openlibing/src/components/filterDropdown.vue`                                                   | 修改   | 全选框状态修复（2026-10-14 用户验证反馈）：初始 `isIndeterminate` 置 false、`reset()` 与关闭面板未筛选分支补 `checkAll`/`isIndeterminate` 复位；`searchInput`/`setOptions` 异步路径不动（`setOptions` 依赖 `checkAll` 对新拉取分页自动补选）。共享组件，15 个使用页面同步受益                                                                                                                                                                                                                      |
| `apps/web-openlibing/src/views/sca/personalScandTaskInfor/analysisTable.vue`                              | 回退   | `openReposUrl` 平台域名映射 2026-10-16 需求取消已回退，恢复 gitee 二元判断原状（见 D9 回退记录）                                                                                                                                                                                                                                                                                                                                                                                                   |
| `apps/web-openlibing/src/views/sca/PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue` | 回退   | 同上，`openReposUrl` 已回退恢复原状                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `apps/web-openlibing/src/assets/js/config.json`                                                           | 回退   | `ATOMGIT_BASE_URL` 2026-10-16 需求取消已移除                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `apps/web-openlibing/src/views/sca/softInformation/gitUrlList.vue`                                        | 零改动 | 风险数据详情条件由父组件传入                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `apps/web-openlibing/src/utils/index.js`（`filterRepositories` 等）                                       | 零改动 | 共享组件 `communityRepoSelect` 依赖，签名与行为不变                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## 风险与兼容性

| 风险                                                               | 缓解                                                                                              |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| 后端 `getRepos` 不支持"仅 repository 无 platform"独立过滤          | 联调阶段优先验证；不满足则升级为 openlibing-sca 后端依赖，看板"仅选代码仓"场景延后，其余组合先行  |
| `open/person/repos` `repository` 过滤（PR 扫描选仓筛选的新增依赖） | 已解除：后端过滤已实现（2026-10-14 需求方确认），"仅选代码仓"筛选场景可交付                       |
| beta 环境未部署后端提交 52575f7                                    | `repoBranchList` 404 时两下拉空态，不影响其他 tab 与既有查询；发布节奏与后端对齐                  |
| 三 tab 共用页面误伤 CodeCheck/AntiPoison                           | SCA 下拉 `v-if="activeName === 'sca'"` 互斥渲染，原下拉在 `v-else` 分支零改动；回归清单覆盖两 tab |
| 树接口软失败导致下拉空                                             | 聚合推导数组守卫 + 初始化重试；失败时不阻塞页面其余功能                                           |
| 聚合选项规模（大项目全量分支/仓库）                                | 两页下拉均 `filterable` 本地过滤，无新增请求                                                      |
| 跨 tab 筛选残留串扰（codeCheck 的 repoId 残留影响 sca 查询）       | `switchTab` 重置对象补全 `repoId`/`branchId`/`branchName`                                         |

## 验证策略

1. 静态检查：`pnpm lint`（`src/views/sca/`、`src/views/InspectionCenter/`、`src/api/`、`src/utils/` 均在检查范围）。
2. 手测矩阵：
   - 风险数据看板：平台/代码仓/分支任意单选与组合（在"开源片段引用合规"与"项目合规-文件级兼容性"两 tab 分别验证）；分支同名去重纯名称展示；选分支仅筛选列表不跳详情；看板行点击进详情正常；项目切换后树刷新与条件重置。
   - 检测中心-SCA：进入/切到 Sca tab 下拉默认全量展示；仓库×分支×任务状态任意组合（含仅分支、矛盾组合）；下拉本地关键字过滤。
   - PR 扫描-开源片段引用合规：代码仓下拉默认可选且选项恒为全量（不随平台过滤）；选代码仓仅筛选列表原地刷新、不跳详情（重置页码；看板行点击进详情正常）；选/清平台不清空已选代码仓、列表按平台刷新；详情态下变更/清除平台或代码仓任一下拉回列表（列表态互不清空不受影响）；矛盾组合保留已选值；项目切换清空重置；`open/person/repos` 的 `repository` 过滤已确认生效（后端已实现，2026-10-14 需求方确认）。
   - atomgit 平台（2026-10-14 需求变更，仅项目合规菜单范围）：项目合规-文件级兼容性 tab（及共用同组下拉的开源片段引用合规 tab）平台下拉恒展示 gitee/gitcode/atomgit 三项（含项目树暂无 atomgit 仓库节点的情形，并集语义）；选 atomgit 后列表按平台过滤（树数据含 atomgit 仓库时）；合法合规其他页面（PR 扫描、合规度量/PR 扫描详情、管理配置、个人扫描任务信息）平台下拉仍为 gitee/gitcode 两项，无 atomgit；atomgit 平台扫描数据的代码仓地址链接跳转 `https://atomgit.com/{org}/{repo}/tree/{branch}` 正常（个人扫描任务/PR 扫描详情，URL 跳转部分 2026-10-14 二次确认复原）；gitee/gitcode 链接与过滤行为回归不变。
3. 回归（不受影响模块）：检测中心 CodeCheck/AntiPoison tab 仓库/分支下拉行为不变（含未选仓库时分支禁用）；合规度量（`complianceMeasure`）与 PR 扫描详情（`PRScanDetail`）的 `communityRepoSelect` 行为不变（`filterRepositories` 签名与行为未动）；风险数据详情（`gitUrlList`）从看板行点击进入正常；导出后返回详情恢复（`restoreScaDetail`）。
4. 可选：`apps/web-openlibing/e2e`（Playwright）补充两页面查询条件用例。
