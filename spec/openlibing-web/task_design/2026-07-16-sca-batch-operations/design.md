# 检测中心 SCA 列表批量操作技术设计

## 技术方案概述

本次改动聚焦 [InspectionCenter/index.vue](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/InspectionCenter/index.vue) 的 SCA Tab 分支（`activeName === 'sca'`），通过：

1. 为 SCA `el-table` 增加 `@selection-change` 事件与 `type="selection"` 列
2. 在 SCA 表格上方新增操作按钮区（仅 SCA Tab 显示）
3. 操作列在「开始扫描」后追加「删除」按钮
4. 复用 [ElMessageBox.confirm](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/InspectionCenter/index.vue#L1029) 二次确认范式（与 `handleDownloadLog` 一致）
5. 新增 `scaDeleteVersionScan` API 调用后端 `/version/scan/deleteByIds` 删除接口，入参为 id 数组
6. 改造 `startVersionScan` 单条扫描：调用 `scaQueryVersionScanStart` 时参数由对象改为 `[{ repoId, branchId, branchName }]` 数组形式（数组长度为 1）
7. 批量扫描：调用同一 `scaQueryVersionScanStart` 接口，参数为 `[...]` 数组形式，元素来自勾选行

实现层面遵循现有 `formInSpection` / `tableList` / `getFullTask` 数据流，不引入新全局状态。

## 模块设计

### 1. 表格选择状态

SCA `el-table` 增加选择列，支持多选操作：

- 新增 `scaSelection` ref 用于存储选中行
- 新增 `batchScanLoading` 和 `batchDeleteLoading` ref 用于控制 loading 状态
- 新增 `batchScanDisabled` computed 用于控制批量扫描按钮禁用状态（未勾选或全为扫描中时禁用）
- 新增 `handleScaSelectionChange` 函数处理选中状态变化
- SCA `el-table` 增加 `type="selection"` 列作为首列，所有记录均可勾选（包括扫描中记录）
- 在筛选/分页切换函数中清空选中状态

模板中「批量扫描」按钮使用 `batchScanDisabled` computed 实现动态禁用，「批量删除」按钮保持 `scaSelection.length === 0` 禁用条件。

### 2. 批量操作按钮区

在 SCA `el-table` 上方新增容器，仅 SCA Tab 渲染：

- 新增「批量扫描」按钮，未勾选时禁用，点击调用 `handleBatchScan`
- 新增「批量删除」按钮，未勾选时禁用，点击调用 `handleBatchDelete`
- 按钮使用 `batchScanLoading` 和 `batchDeleteLoading` 控制 loading 状态
- 按钮图标使用 `VideoPlay` 和 `Delete`

### 3. 单条扫描改造

`startVersionScan` 改造为：调用 `scaQueryVersionScanStart` 时，参数由对象改为数组形式（数组长度 1），每个元素包含 `repoId` / `branchId` / `branchName`。

### 4. 批量扫描逻辑

批量扫描处理流程：

1. 从选中集合中筛选出扫描中记录和非扫描中记录
2. 若选中集合全为扫描中，通过 UI 层 `batchScanDisabled` 阻止点击
3. 若选中集合包含扫描中记录，通过 `ElMessage.warning` 提示跳过数量
4. 通过 `ElMessageBox.confirm` 二次确认
5. 调用 `scaQueryVersionScanStart` 接口，参数为 `[{ repoId, branchId, branchName }]` 数组形式
6. 成功后刷新列表

> 设计决策：批量扫描复用 `scaQueryVersionScanStart` 单一接口，参数为 `[...]` 数组形式，由后端一次性处理批量扫描请求。单条扫描同样以 `[singleRow]` 形式调用，保证参数形态一致。
>
> 由于扫描中记录也支持删除（保留勾选能力），选中集合可能包含扫描中记录。批量扫描通过 `batchScanDisabled` computed 在 UI 层阻止"全为扫描中"场景；函数内通过 filter 筛掉扫描中记录并 `ElMessage.warning` 提示跳过数量，剩余非扫描中记录作为实际扫描目标。

### 5. 批量删除与单条删除

#### 5.1 新增 API

在 `apps/web-openlibing/src/api/url.ts` 新增 `SCA_DELETE_VERSION_SCAN` 常量，路径为 `${SCA}/version/scan/deleteByIds`。

在 `apps/web-openlibing/src/api/api.ts` 新增 `scaDeleteVersionScan` 请求函数，入参为 id 数组。

#### 5.2 后端契约

- 路径：`POST /gateway/openlibing-sca/version/scan/deleteByIds`
- 请求体：直接为 id 数组（非对象包裹），其中每个元素为 SCA 版本扫描记录主键（前端取 `row.id`）
- 响应体：包含 `code`、`message`、`data` 字段

#### 5.3 批量删除

批量删除处理流程：
1. 通过 `ElMessageBox.confirm` 二次确认
2. 调用 `scaDeleteVersionScan` 接口，入参为 id 数组
3. 成功后刷新列表，若当前页删空且回退一页

#### 5.4 单条删除

操作列「开始扫描」后追加删除按钮：

- 使用 `el-tooltip` 包裹删除按钮，悬停提示"删除"
- 点击调用 `handleSingleDelete` 函数
- 扫描中记录也支持删除，按钮不做禁用
- 删除为不可恢复操作，统一通过 ElMessageBox 二次确认兜底
- 成功后刷新列表，若当前页删空且回退一页

### 6. 图标导入

在文件头部 `@element-plus/icons-vue` 导入处追加 `Delete` 图标。

### 7. 样式

新增 `.sca-batch-actions` 样式类，用于批量操作按钮区布局。

## API 变化

| 类型 | 名称 | 路径 | 说明 |
|------|------|------|------|
| 新增 | `SCA_DELETE_VERSION_SCAN` | `${SCA}/version/scan/deleteByIds` | url.ts 常量 |
| 新增 | `scaDeleteVersionScan` | — | api.ts 请求函数，入参为 id 数组 |
| 复用（参数变更） | `scaQueryVersionScanStart` | `${SCA}/version/scan/startVersionScan` | 请求体由对象改为 `[...]` 数组形式 |

## 前端组件变化

### 修改文件

- [apps/web-openlibing/src/views/InspectionCenter/index.vue](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/InspectionCenter/index.vue)
  - 模板：SCA `el-table` 增加 selection 列、表格上方批量按钮区、操作列追加删除按钮
  - 脚本：新增 `scaSelection` / `batchScanLoading` / `batchDeleteLoading` 状态；新增 `handleScaSelectionChange` / `handleBatchScan` / `handleBatchDelete` / `handleSingleDelete`；改造 `startVersionScan` 参数为 list 数组形式；在筛选/分页切换函数中清空选中
  - 样式：新增 `.sca-batch-actions`
- [apps/web-openlibing/src/api/api.ts](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/api/api.ts)
  - 新增 `scaDeleteVersionScan`
- [apps/web-openlibing/src/api/url.ts](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/api/url.ts)
  - 新增 `SCA_DELETE_VERSION_SCAN`

### 新增文件

无。

## 数据模型变化

无前端数据模型变更。需后端确认 `scaQueryVersionScan` 返回项包含记录主键（`id`），若无则需后端在查询响应中补充。

## 安全影响

- 删除操作为不可恢复操作，前端通过 ElMessageBox 二次确认兜底
- 扫描中记录也支持删除（业务允许中断扫描任务），删除按钮不做禁用
- 删除接口需后端做权限校验（项目空间成员/管理员），前端不做权限判断
- 无新增硬编码凭证或敏感信息

## 部署影响

- 前端：构建产物更新部署
- 后端：
  - `openlibing-sca` 已有 `startVersionScan` 接口需支持 `[...]` 数组参数
  - `openlibing-sca` 删除接口 `/version/scan/deleteByIds` 已提供，入参为 id 数组
- 无数据库迁移（删除为物理删除或软删除由后端决定）

## 测试策略

### 功能测试

- 选中 0/1/N 条记录时按钮禁用态与可点击态
- 批量扫描：所选记录含「扫描中」时跳过并提示
- 批量扫描：请求参数为 `[{ repoId, branchId, branchName }]` 数组形式
- 单条扫描：请求参数为 `[{ repoId, branchId, branchName }]` 数组形式（数组长度 1）
- 批量删除：成功后列表刷新；当前页删空时回退上一页
- 单条删除：扫描中记录也支持删除；删除成功
- 删除接口失败：展示后端错误信息
- 切换 Tab / 筛选 / 分页后选中清空
- 二次确认弹窗「取消」不触发请求

### 边界测试

- 选中全页记录批量删除
- 批量扫描全部失败：错误提示正确
- `row.id` 缺失场景：前端调用前抛错并提示（防御性）

### 回归测试

- CodeCheck / AntiPoisoning Tab 表格操作不受影响
- SCA 单条「开始扫描」功能不受影响（参数变化但行为一致）
- 日志弹窗、失败日志下载功能不受影响

## 关键设计决策

1. **扫描接口参数改为数组形式**：单条与批量扫描统一调用 `scaQueryVersionScanStart`，参数为 `[...]`，单条扫描数组长度为 1。后端单一接口同时处理单条/批量，减少接口数量。
2. **删除接口入参为 id 数组**：后端 `/version/scan/deleteByIds` 接口直接接受 id 数组（如 `['1', '2']`），前端 `scaDeleteVersionScan` 调用时 `data` 直接传数组而非对象包裹。单条删除复用同接口传单元素数组 `[row.id]`。
3. **选中状态不跨页保留**：本期仅当前页选中，实现简单；跨页保留需引入 `reserve-selection` + `row-key`，留待后续迭代。
4. **扫描中记录的勾选框不禁用**：因为扫描中记录也支持删除，需要保留勾选能力。所有记录均可勾选。
5. **批量扫描按钮动态禁用**：通过 `batchScanDisabled` computed 实现"未勾选 或 勾选全为扫描中"时禁用。这是 UI 层防御，避免用户点击后无任何目标可扫描。
6. **批量扫描内做数据筛选**：选中集合可能同时包含扫描中和非扫描中记录，函数内 filter 出非扫描中记录作为实际扫描目标，并通过 `ElMessage.warning` 提示跳过数量。
7. **扫描中记录也支持删除**：业务允许中断扫描任务，删除按钮不做禁用，统一通过 ElMessageBox 二次确认兜底。
8. **删除后分页回退**：若当前页全部被删除且非第一页，`pageNum -= 1` 后刷新，避免停留在空页。
9. **复用 ElMessageBox.confirm 范式**：与 [handleDownloadLog](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/InspectionCenter/index.vue#L1027) 保持一致的交互风格。

## 影响范围汇总

- 前端单仓 `openlibing-web`，3 个文件修改
- 后端 `openlibing-sca`：
  - 需支持 `startVersionScan` 接口的 `[...]` 数组参数
  - 删除接口 `/version/scan/deleteByIds` 已提供
- 无数据库 schema 变更
