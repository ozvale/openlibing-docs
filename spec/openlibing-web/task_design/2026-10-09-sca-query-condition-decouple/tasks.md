# 风险数据看板与检测中心-SCA 查询条件解耦 — 实现任务

> 范围变更（2026-10-10）：PR 扫描-开源片段引用合规一度移出范围，同日经需求方确认恢复改造，最终在范围内（见第 3 节与 design.md D8）。
> 需求变更（2026-10-12）：PR 扫描列表选代码仓不再跳转详情，仅作为列表筛选动作（详情唯一入口为看板行点击，见 design.md D8 与交互矩阵）。
> 需求变更（2026-10-13/14）：检测中心-SCA 筛选方案从"表单区独立下拉"变更为"表头多选筛选"——复用门禁检查列表"检查结果"列的 `FilterDropdown` 组件样式（仓库/分支/检查结果三列，多选），SCA tab 表单区三个下拉不再展示（其他 tab 保留）；原任务状态下拉职责对应表头"检查结果"列，查询以 `repoName`/`branchName`/`scanStatus` 字段上送筛选数组（拼写沿用原单值契约、不改为复数；数组过滤后端已实现，2026-10-14 需求方确认）。
> 后端依赖（openlibing-sca）：`GET /version/scan/repoBranchList`（dev_beta_20261019 提交 52575f7；2026-10-12 增加 `communityId` 入参）与 `/version/scan/query` 按 `repoName`/`branchName`/`scanStatus` 数组过滤均已落地（2026-10-14 需求方确认数组过滤已实现）；`open/person/repos` 按 `repository` 过滤（PR 扫描选仓筛选）已落地（2026-10-14 需求方确认）。原 openlibing-codecheck `branch-list` 扩展需求已废弃。
> 需求变更（2026-10-14）：项目合规菜单下本次需求涉及的平台下拉框（`componentAnalysis/index.vue` 查询条件区，项目合规-文件级兼容性与开源片段引用合规两 tab 共用）新增 `atomgit` 平台项（见第 4 节与 design.md D9）。同日二次澄清：**URL 跳转部分（两个 analysisTable 的 `openReposUrl` + `ATOMGIT_BASE_URL` 配置）属改造范围、已复原**；其他页面的平台下拉选项不在范围（曾误扩，已回退保持 `['gitee', 'gitcode']` 原状）。

## 1. 风险数据看板改造（前端独立交付；同份代码对"开源片段引用合规"+"项目合规-文件级兼容性"两 tab 同时生效）

### 1.1 scaUtils.js 聚合函数

- [x] 新增 `getAllPlatformRepos(arr, community)`：定位 community 对象后聚合全部平台 key（`Object.keys` 过滤 `nameCommunity` 且仅认数组字段，平台动态推导不依赖硬编码）的代码仓，返回项附加 `platform` 归属。
- [x] 新增 `getAllRepoBranchs(arr, community, platform)`：聚合全部代码仓的 `branchList`，返回 `{...branch, repoName, platform}` 浅拷贝数组；含非数组守卫（树对象字符串元数据字段不参与）。
- [x] 保留既有 `getPlatformRepos`/`getPlatformRepoBranchs` 签名不变（仅本页使用，零回归面）。
- [x] 新增 `getAllRepositories(arr, community)`：PR 扫描扁平树聚合（匹配 `nameCommunity`，返回 `repositories` 全量数组，含非数组守卫）。

### 1.2 componentAnalysis/index.vue

- [x] 树加载时机前置：组件初始化（projectId 就绪后）调用 `getCommunityTreeData()`；`changeSelectPlatform` 去掉重拉树调用；树接口软失败带重试与数组守卫。
- [x] 项目切换重拉：`watch chooseCommunityValue` 变化时重拉树并重置平台/代码仓/分支。
- [x] `repoOptions` computed：恒为 `getAllPlatformRepos` 全平台聚合（已选平台也不过滤，条件彻底独立）。
- [x] `branchOptions` computed：恒为 `getAllRepoBranchs` 聚合，同名分支按 `branch` 名称去重，仅展示分支名称。
- [x] 移除代码仓下拉 `:disabled="!choosePlatformValue"` 与分支下拉 `:disabled="!chooseGitUrlValue"`。
- [x] 选分支仅筛选列表：拆分 `chooseBranchValue`（分支名称筛选条件）与 `detailRow`（详情行，仅看板行点击赋值）；分支下拉 change 仅更新筛选并传 `chooseBranchValue` 给 `communityList.vue` 原地刷新，不跳详情。
- [x] 详情态下拉变更回列表：详情态（`detailRow?.id`）下变更/清除平台/代码仓/分支任一下拉（`@change="handleFilterChange"`）时清除 `detailRow` 退出详情回列表，列表按当前筛选值原地刷新；列表态行为不变，程序赋值（看板行点击回填/导出返回恢复）不触发 change。
- [x] 联动清空移除：平台/代码仓/分支变化互不清空对方，矛盾组合保留已选值（归属校验按需求方确认去除）。
- [x] `platformOptions` 动态化：三个已知平台 `['gitee','gitcode','atomgit']` 恒展示（2026-10-14 修复为并集语义——原交集实现会因项目树中暂无某平台仓库而过滤该平台项），树 keys（仅认数组字段）推导的新平台追加，空树分支移除（并集含空即 base）。
- [x] 聚合态消歧：代码仓跨平台同名时 label 显示 `repoName（platform）`（`repoNameCount` 计数）。
- [x] 导出（`exportExcel`/`exportLicenseExcel`/`exportUnconfirmedExcel`）维持现状参数不改动（遗留项见 design.md D7）。

## 2. 检测中心-SCA 改造（2026-10-13/14 方案变更后：筛选移至表头多选）

- [x] 接口定义：`src/api/url.ts` 新增 `SCA_REPO_BRANCH_LIST = \`${SCA}/version/scan/repoBranchList\``；`src/api/api.ts`新增`scaRepoBranchList`（GET，支持 params 传参）。
- [x] `communityId` 入参（2026-10-12 后端契约变更）：`fetchScaRepoBranchOptions` 调用时上送 `params: { communityId: app.projectInfo?.projectId }`，选项数据收敛为当前项目下全量（两处调用时 `projectId` 均已就绪）。
- [x] 表单区下拉按 tab 隐藏（2026-10-14 需求变更）：仓库/分支/任务状态三个 `el-form-item` 加 `v-if="activeName !== 'sca'"`，SCA tab 整体不展示（表单区仅剩批量操作按钮）；SCA 专属任务状态选项块随之删除（状态筛选移至表头）；CodeCheck/AntiPoison tab 原 repoId/branchId 绑定、远程搜索与分支级联零改动。
- [x] 表头筛选（2026-10-13/14 需求变更，最终实现）：SCA 表格 `#header` 插槽复用 `FilterDropdown` 组件（`@/components/filterDropdown.vue`，样式参考门禁检查列表"检查结果"列），仓库/分支/检查结果三列 `type="checkbox"` 多选；选项映射 `scaFilterOptions`——仓库/分支取 `scaRepoList`/`scaBranchList` 全量去重名称，检查结果为固定状态项 `scaStatusOptions`（0=未执行扫描/1=扫描中/2=扫描成功/3=扫描失败，承接原"任务状态"下拉职责）；无选项的列（执行时间/耗时/操作）表头渲染纯文本 label。
- [x] 状态与拉取：新增 `scaRepoList`/`scaBranchList`；`fetchScaRepoBranchOptions()` 在①页面加载落在 sca tab（`watch projectInfo`）②`switchTab` 切到 sca 两处调用；响应 `code === 200` 时填充。
- [x] 变更处理：`handleScaFilterChange`（FilterDropdown `@change`，payload 为 `{name, data}`）——失效旧请求 + 停止轮询 + 清空 `scaSelection` + 重置 `pageNum` + 按 `name`（repoName/branchName/scanStatus）写入对应筛选数组 + 刷新列表；各列筛选互不清空。
- [x] 切 tab 重置：`switchTab` 清空 `scaRepoFilter`/`scaBranchFilter`/`scaStatusFilter`（表格销毁重建，FilterDropdown 选中态随之重置），重置对象补 `repoId`/`branchId`/`branchName`（防跨 tab 筛选残留串扰）。
- [x] 查询参数：`getSca` 以 `repoName`/`branchName`/`scanStatus` 字段上送筛选数组（2026-10-14 拼写确认：沿用原单值字段名不改为复数，覆盖 `formInSpection` 同名空值 key）；名称过滤后端已支持，`scanStatus` 数组过滤后端已实现（2026-10-14 需求方确认）。
- [x] 路由初始化（`initRouteParams`）与 `handleRepo`/`handleBranch`/`getRepoOptions`/`getBranchOptions` 等 codeCheck/AntiPoison 链路维持现状零改动。
- [x] FilterDropdown 全选框状态修复（2026-10-14 用户验证反馈，共享组件 bug）：`isIndeterminate` 初始值 `true`→`false`（修复默认未选时全选框显示半选横线）；`reset()` 与关闭面板未筛选分支补 `checkAll`/`isIndeterminate` 复位（修复全选后重置/关闭重开仍显示已勾选）。不触碰 `searchInput`/`setOptions` 异步路径（`setOptions` 依赖 `checkAll` 对新拉取分页自动补选）。

## 3. PR 扫描-开源片段引用合规改造（范围恢复，见 design.md D8）

- [x] `openSourceCompliance/index.vue`：代码仓下拉解禁（移除 `:disabled="!choosePlatformValue"`）、选项恒为 `getAllRepositories` 全量聚合、同名消歧（`repoOptionLabel`）、软失败重拉入口（`@click="repoInit"`）、已选仓库兜底回显。
- [x] 选/清平台不清空已选代码仓（列表态）：`changeSelectPlatform` 去清空逻辑；移除平台下拉 `@clear="changeSelectCommunity"` 绑定（Element Plus 清除同时触发 clear+change，change 空值已保留代码仓，旧 clear 绑定会连带清空）。
- [x] 选代码仓仅筛选（2026-10-12 需求变更）：`changeSelectGitUrl` 不再经 `getChooseRepository` 跳详情（方法已删除），改为同步 `chooseGitObject`（树未加载/匹配失败置空）→ 详情态下变更/清除时 emit `toogleDetail false` 回列表 → 重置页码并刷新；`getTableData` 按选中仓库上送 `repository` 参数（参数名与看板列表接口对齐，后端过滤已实现，2026-10-14 需求方确认）。
- [x] 详情态清除平台回列表：`changeSelectPlatform` 内补 `isDetail && !choosePlatformValue` 判断 emit `toogleDetail false`（保持原有"清除任一下拉回列表"逻辑），代码仓选择保留、列表按当前筛选原地刷新；`getDetail` 内部调用（彼时 `isDetail` 为 false）与详情态变更平台（非清除）不受影响。
- [x] 树加载时序修复：拆分 `projectIdValue`（immediate，projectId 就绪即拉树，不依赖点平台下拉）与 `chooseCommunityValue`（聚合兜底 + 刷列表）两个 watch，初始化不点平台下拉即有全量数据。
- [x] `scaUtils.js` 保留 PR 扫描专用聚合函数 `getAllRepositories`。

## 4. atomgit 平台支持（2026-10-14 需求变更，**2026-10-16 需求取消、整体回退**）+ PR 扫描树请求缓存（见 design.md D9）

- [x] **回退（2026-10-16 需求方确认取消）**：`componentAnalysis/index.vue` platformOptions base 恢复 `['gitee', 'gitcode']` 两项（并集语义保留）；PR 扫描列表 `openSourceCompliance/index.vue` platformOptions 恢复两项；两个 analysisTable（个人扫描任务/PR 扫描）`openReposUrl` 恢复 gitee 二元判断原状——atomgit 选项与域名映射全部不再生效。**例外**：`config.json` 的 `ATOMGIT_BASE_URL` 曾随回退移除，但同事 commit `de1f1150` 的 `until.js` 录入校验白名单（独立合入 beta_gamma）引用该常量导致 beta 构建失败，已恢复配置项（ca03db90，仅配置、不含任何下拉选项/映射）。
- [x] **保留**：PR 扫描下拉树接口重复调用优化（2026-10-14 同步提出、与 atomgit 无关）：`openSourceCompliance/index.vue` data 新增 `communityTreeProjectId` 缓存标识，`getCommunityTreeData` 在"已成功加载且 projectId 未变"时跳过请求（点击平台/代码仓下拉不再重拉树）；成功响应（含空数组）才记录标识、软失败不记录保持可重试、项目切换 watch 触发自动重拉；缓存命中时 `init` 分支行为保留。
- [x] ESLint 改动文件通过（含回退后 4 个文件复检）。

## 5. 验证

- [x] `pnpm exec eslint` 对全部改动文件通过（`src/views/sca/`、`src/views/InspectionCenter/`、`src/api/`、`src/utils/`）。
- [ ] 风险数据看板手测（在"开源片段引用合规"与"项目合规-文件级兼容性"两 tab 分别验证）：
  - 平台/代码仓/分支任意单选与组合（含矛盾组合保留已选值）；
  - 分支同名去重仅展示名称；选分支仅筛选列表原地刷新、不跳详情；
  - 看板行点击进入详情正常；项目切换后树刷新与条件重置；
  - 树接口软失败时下拉不为空。
- [ ] 检测中心-SCA 手测：进入/切到 Sca tab 表单区无仓库/分支/任务状态下拉（仅批量操作按钮）；仓库/分支/检查结果三列表头有筛选图标（FilterDropdown，样式与门禁检查列表"检查结果"列一致），点击展开关键词搜索 + 多选 + 全选 + 筛选/重置；选项为**当前项目下**全量去重数据（`repoBranchList` 携带 `communityId`，依赖 beta 环境已部署后端提交 52575f7 及 communityId 入参变更）与固定状态项；多选确认后漏斗变蓝、列表按 `repoName`/`branchName`/`scanStatus` 字段（数组）过滤生效（后端数组过滤已实现，2026-10-14 需求方确认）；重置恢复全量；切 tab 后筛选面板选中态重置。
- [ ] PR 扫描-开源片段引用合规手测：代码仓下拉默认可选且选项恒为全量（不随平台过滤，初始化不点平台下拉即有数据）；选代码仓仅筛选列表原地刷新、不跳详情（重置页码；看板行点击进详情正常）；选/清平台不清空已选代码仓、列表按平台刷新；详情态下变更/清除平台或代码仓任一下拉回列表（代码仓选择保留、列表原地刷新）；矛盾组合保留已选值；项目切换清空重置；`open/person/repos` 的 `repository` 过滤已确认生效（后端已实现，2026-10-14 需求方确认）；**树接口缓存（2026-10-14 新增）**：树加载成功后反复点击平台/代码仓下拉不再重复请求 `open/scan/community` 树接口（Network 面板确认），项目切换后重拉一次正常。
- [ ] atomgit 回退手测（2026-10-16 需求取消后）：项目合规（含共用同组下拉的开源片段引用合规 tab）与 PR 扫描列表平台下拉均恢复 gitee/gitcode 两项、无 atomgit；个人扫描任务/PR 扫描详情的代码仓链接 gitee 走 gitee.com、gitcode 走 gitcode.com（原逻辑回归不变）；全仓无 atomgit 残留引用。
- [ ] 不受影响模块回归：
  - 检测中心 CodeCheck / AntiPoison tab：仓库/分支下拉行为不变（未选仓库时分支禁用、远程搜索正常）；
  - 合规度量（`complianceMeasure`）与 PR 扫描详情（`PRScanDetail`）`communityRepoSelect` 行为不变（`filterRepositories` 签名与行为未动，平台下拉仍为 gitee/gitcode 两项）；
  - 风险数据详情（`gitUrlList`）从看板行点击进入正常；导出后返回详情恢复（`restoreScaDetail`）。
- [ ] 可选：`apps/web-openlibing/e2e` 补充两页面查询条件组合用例。

## 6. 交付

- [ ] 业务仓 commit（单轮交付一 commit，规范见 AGENTS.md）。
- [ ] 用户自测确认后创建业务 PR（关联业务 Issue、`ai-assisted` 标签）。
- [ ] docs 仓提交本 spec（`spec-web-openlibing-sca-query-condition-decouple` 分支 → docs PR）。
