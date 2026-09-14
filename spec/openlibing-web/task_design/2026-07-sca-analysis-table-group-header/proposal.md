# Proposal: SCA 分析表二级表头 + nginx /argus 配置缩进统一

## 需求背景

SCA 模块下的"合法合规分析表"（`analysisTable.config.js` 的 `column`）被 3 个页面共用：软件信息 gitUrlList、PR 组件分析 openSourceCompliance、个人扫描任务 analysisTable。原表格是单层表头平铺 22 个列，列多且语义跨度大（源代码信息 / 开源软件信息 / 分析与审核结果），阅读时缺乏分组层次。

同时 gamma 环境的 `nginx_gamma.conf` 中 `/argus` location 块缩进与相邻块不一致（16 空格 vs 18 空格），需要统一。

## 需求描述

1. 为共用分析表增加二级表头，按列语义分三组：
   - **源代码**（含代码行）：`fileName`、`detail`、`type`、`lines`
   - **开源软件代码**（代码行之后到分析结果之前）：`ossLines`、`vendor`、`component`、`version`、`purl`、`file`、`licenses`、`clarifyConfirmType`
   - **分析及审核结果**（含分析结果到末尾）：`clarifyType`、`matched`、`reviewStatus`、`riskLevel`、`committerType`、`vulnerLeveList`、`clarifyAuthor`、`applyTime`、`reviewUserName`、`reviewTime`
2. 三个使用该 `column` 的表格页面都同步展示二级表头，原有列渲染逻辑（`#header` / `#default` slot、特殊列处理）保持不变。
3. 列设置弹框、导出等依赖 `table.column.forEach` 的逻辑不受影响。
4. 统一 `nginx_gamma.conf` 中 `/argus` 块缩进为 18 空格，与相邻 location 块一致。

## 验收标准

- [ ] `analysisTable.config.js` 新增 `columnGroups` 导出，包含三个分组，分组 id 并集等于全部 22 个列 id，无遗漏无重复
- [ ] `gitUrlList.vue`、`openSourceCompliance/analysisTable.vue`、`personalScandTaskInfor/analysisTable.vue` 三个表格均渲染二级表头，组名分别为「源代码」「开源软件代码」「分析及审核结果」
- [ ] 子列的 `show` 控制仍生效（列设置弹框勾选/取消勾选后二级表头内对应列正常显隐）
- [ ] 子列原有特殊渲染逻辑不受影响（clarifyType / reviewStatus 的 tooltip、漏洞标签、purl el-tag、双击编辑等）
- [ ] `table.column.forEach` 相关逻辑（列设置、导出）行为不变
- [ ] `nginx_gamma.conf` 中 `/argus` 块缩进与 `/ai`、`/build`、`/api-management` 一致（18 空格）
- [ ] 三个 vue 文件无模板/TS 诊断错误

## 影响范围

| 文件                                                                                                      | 变更类型 | 说明                                                                                 |
| --------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------ |
| `apps/web-openlibing/src/views/sca/analysisTable.config.js`                                               | 功能新增 | 新增 `columnGroups` 导出                                                             |
| `apps/web-openlibing/src/views/sca/softInformation/gitUrlList.vue`                                        | 功能新增 | import columnGroups；table 挂载 columnGroups；template 外层加父 el-table-column 包裹 |
| `apps/web-openlibing/src/views/sca/PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue` | 功能新增 | 同上                                                                                 |
| `apps/web-openlibing/src/views/sca/personalScandTaskInfor/analysisTable.vue`                              | 功能新增 | 同上                                                                                 |
| `apps/web-openlibing/nginx/nginx_gamma.conf`                                                              | 格式调整 | `/argus` 块缩进统一为 18 空格                                                        |

单仓前端改动，无接口/数据模型/鉴权变化。

## 模式判定

Light 模式：单仓、5 个文件、改动以模板结构 + 配置为主、无接口与数据模型变化、无安全影响、最小验证。
