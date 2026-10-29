# 检测中心 SCA 列表新增批量扫描、批量删除与单行删除操作

**Issue**: openlibing/openlibing-web#（待创建/关联）

## 需求背景

检测中心（InspectionCenter）的 SCA（软件成分分析）Tab 当前仅支持对单条版本扫描记录发起扫描（`startVersionScan`），缺乏批量操作能力。当用户需要对多个仓库/分支并发起版本扫描，或清理历史无用扫描记录时，只能逐条点击，效率低下，且无法删除任何扫描记录。

CodeCheck、AntiPoisoning 两个 Tab 同样缺少批量能力，但本期仅针对 SCA Tab 交付，以解决 SCA 批量扫描与记录清理的高频诉求。

参考同页面 [Repos/branches.vue](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/Repos/branches.vue) 中已有的 `type="selection"` 多选交互模式，统一平台批量操作体验。

## 功能描述

### 做什么

- SCA 列表新增行勾选能力（多选 checkbox，支持跨页保留选中状态在本期不实现）
  - 所有记录均可勾选，包括扫描中记录（因为扫描中记录也支持删除）
- SCA 列表右上方新增「批量扫描」按钮：
  - 选中 0 条时按钮禁用
  - 选中 ≥1 条但全为扫描中（`scanStatus === 1`）时按钮禁用（无可发起扫描的目标）
  - 选中包含不同扫描状态时按钮可点击，点击后自动筛选掉扫描中记录，弹窗二次确认后对非扫描中记录发起扫描，请求参数为 `[...]` 数组形式，每个元素包含 `repoId` / `branchId` / `branchName`
  - 若筛选后跳过了扫描中记录，通过 `ElMessage.warning` 提示跳过数量
- SCA 列表右上方新增「批量删除」按钮：
  - 选中 0 条时按钮禁用
  - 选中 ≥1 条时点击后二次确认，确认后调用 `scaDeleteVersionScan` 接口，入参为 id 数组（直接传 `['1', '2', ...]`，非对象包裹）
  - 扫描中记录也支持删除
  - 刷新列表
- SCA 列表操作列新增「删除」按钮：
  - 单条记录二次确认后调用 `scaDeleteVersionScan` 接口，入参为单元素 id 数组 `[row.id]`
  - 扫描中记录也支持删除
  - 刷新列表
- 单条「开始扫描」操作改造：调用 `scaQueryVersionScanStart` 时参数由对象改为 `[{ repoId, branchId, branchName }]` 数组形式（数组长度为 1）

### 不做什么

- 不实现跨页选中状态保留（仅在当前页选中）
- 不修改 CodeCheck、AntiPoisoning Tab 的表格与操作
- 不修改 `scaQueryVersionScan` 查询参数与返回结构
- 不实现回收站/软删除恢复能力

## 验收标准

- [ ] SCA Tab 切换后，列表首列出现 `type="selection"` 勾选列
- [ ] 所有记录均可勾选，包括扫描中记录
- [ ] 未勾选任何记录时，「批量扫描」「批量删除」按钮禁用
- [ ] 勾选全为扫描中记录时，「批量扫描」按钮禁用（「批量删除」按钮仍可点击）
- [ ] 勾选包含不同扫描状态记录时，「批量扫描」按钮可点击，自动筛选掉扫描中记录并 `ElMessage.warning` 提示跳过数量，对非扫描中记录发起扫描，请求参数为 `[...]` 数组形式
- [ ] 单条「开始扫描」请求体为 `[{ repoId, branchId, branchName }]`，数组长度为 1
- [ ] 勾选记录后，「批量删除」按钮可点击，弹窗二次确认后删除所选记录
- [ ] 操作列新增「删除」按钮，点击后二次确认删除单条记录
- [ ] 扫描中记录的删除按钮可点击（不做禁用）
- [ ] 批量/单条删除成功后，列表自动刷新，分页参数保持当前页（删除后若当前页无数据，回退到上一页）
- [ ] 删除接口失败时，`ElMessage` 展示后端错误信息，列表不残留脏状态
- [ ] 批量扫描/删除过程中按钮 loading，防止重复提交
- [ ] 切换 Tab、切换仓库/分支、切换分页时，已选行清空

## 影响范围

- 前端文件：
  - `apps/web-openlibing/src/views/InspectionCenter/index.vue`（主要修改）
  - `apps/web-openlibing/src/api/api.ts`（新增 `scaDeleteVersionScan`）
  - `apps/web-openlibing/src/api/url.ts`（新增 `SCA_DELETE_VERSION_SCAN` 常量）
- 后端接口：
  - `openlibing-sca` 已有 `startVersionScan` 接口需支持 `[...]` 数组参数形式
  - `openlibing-sca` 删除接口 `/version/scan/deleteByIds`（入参为 id 数组 `['1', '2', ...]`）
- 模块：检测中心 - SCA Tab
- 数据模型：无前端数据模型变更
