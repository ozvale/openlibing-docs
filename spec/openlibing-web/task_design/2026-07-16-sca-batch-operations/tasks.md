# 检测中心 SCA 列表批量操作实现任务清单

## 任务分组

### 第一组：API 与 URL 定义

- [ ] 1.1 新增 SCA 删除 URL 常量
  - 文件：`apps/web-openlibing/src/api/url.ts`
  - 新增 `export const SCA_DELETE_VERSION_SCAN = \`${SCA}/version/scan/deleteByIds\`;`
- [ ] 1.2 新增 SCA 删除 API 函数
  - 文件：`apps/web-openlibing/src/api/api.ts`
  - 新增 `export const scaDeleteVersionScan: RequestFunc = (a, s) => apiClient.post(urls.SCA_DELETE_VERSION_SCAN, a, s);`

### 第二组：表格选择状态

- [ ] 2.1 新增 SCA 选中状态
  - 文件：`apps/web-openlibing/src/views/InspectionCenter/index.vue`
  - 新增 `scaSelection` ref 用于存储选中行
  - 新增 `batchScanLoading` 和 `batchDeleteLoading` ref 用于控制 loading 状态
  - 新增 `batchScanDisabled` computed 用于控制批量扫描按钮禁用状态
- [ ] 2.2 新增 `handleScaSelectionChange` 函数
  - 接收 `rows`，赋值给 `scaSelection.value`
- [ ] 2.3 SCA `el-table` 增加 selection 列
  - 在表格首列插入 `type="selection"` 的勾选列
  - `el-table` 增加事件绑定
  - 所有记录均可勾选（不做 :selectable 限制）
- [ ] 2.4 筛选/分页切换清空选中
  - 在相关切换函数中调用清空选中状态

### 第三组：批量操作按钮区

- [ ] 3.1 模板新增批量按钮区
  - 文件：`apps/web-openlibing/src/views/InspectionCenter/index.vue`
  - 在筛选表单尾部新增 `<el-form-item v-if="activeName === 'sca'" class="sca-batch-actions">`
  - 内含「批量扫描」「批量删除」两个 `el-button`
  - 批量扫描 `:disabled="batchScanDisabled"`（未勾选或全为扫描中时禁用）
  - 批量删除 `:disabled="scaSelection.length === 0"`
  - 批量扫描 `:loading="batchScanLoading"` `@click="handleBatchScan"`
  - 批量删除 `:loading="batchDeleteLoading"` `@click="handleBatchDelete"`
- [ ] 3.2 新增样式 `.sca-batch-actions`
  - 在 `<style lang="less" scoped>` 中新增
  - `width: auto; margin-left: auto;` 让按钮区靠右
  - `:deep(.el-form-item__content) { display: flex; gap: 12px; margin-left: 0; }`

### 第四组：扫描参数改造

- [ ] 4.1 改造 `startVersionScan` 单条扫描参数
  - 文件：`apps/web-openlibing/src/views/InspectionCenter/index.vue`
  - 调用 `scaQueryVersionScanStart` 时，参数由对象改为 `[{ repoId, branchId, branchName }]` 数组形式（长度 1）

### 第五组：批量扫描

- [ ] 5.1 实现 `handleBatchScan`
  - 区分 scanning / targets
  - scanning 数量 > 0 时 `ElMessage.warning` 提示跳过数量
  - targets 为空时 `ElMessage.info` 提示无需发起（防御性，UI 已阻止此场景）
  - `ElMessageBox.confirm` 二次确认
  - 一次性调用 `scaQueryVersionScanStart`，参数 `targets.map(r => ({ repoId, branchId, branchName }))`（数组形式）
  - `res.code === 200` 时 `ElMessage.success`，否则 `ElMessage.error`
  - `batchScanLoading` 控制 loading
  - 完成后调用 `getFullTask()`

### 第六组：批量删除

- [ ] 6.1 实现 `handleBatchDelete`
  - 使用 `ElMessageBox.confirm` 进行二次确认
  - 调用 `scaDeleteVersionScan` 接口，入参为 id 数组
  - 根据响应码显示成功或失败消息
  - 当前页全删空且非第一页时回退一页
  - 使用 `batchDeleteLoading` 控制 loading 状态
  - 完成后调用 `getFullTask()` 刷新列表

### 第七组：单条删除

- [ ] 7.1 操作列追加「删除」按钮
  - 文件：`apps/web-openlibing/src/views/InspectionCenter/index.vue`
  - 在 SCA 表格 `item.value === 'operation'` 模板中，于「开始扫描」`el-tooltip` 之后追加删除按钮
  - `<el-tooltip content="删除">`
  - `<el-button :icon="Delete" @click="handleSingleDelete(row)" link class="icon-btn ml-10" />`（不做禁用，扫描中也支持删除）
- [ ] 7.2 实现 `handleSingleDelete`
  - `ElMessageBox.confirm` 二次确认
  - 调用 `scaDeleteVersionScan`，入参 `[row.id]`（单元素 id 数组）
  - 成功后若当前页仅剩 1 条且 `pageNum > 1`，`pageNum -= 1`
  - 调用 `getFullTask()`

### 第八组：图标导入

- [ ] 8.1 导入 `Delete` 图标
  - 文件：`apps/web-openlibing/src/views/InspectionCenter/index.vue`
  - 在 `@element-plus/icons-vue` 导入语句中追加 `Delete` 图标

### 第九组：联调与测试

- [ ] 9.1 前端联调后端接口
  - 确认 `scaQueryVersionScan` 返回项包含 `id` 字段
  - 确认 `scaQueryVersionScanStart` 接受 `[...]` 数组参数
  - 确认 `/version/scan/deleteByIds` 接受 id 数组入参
- [ ] 9.2 功能自测
  - 选中 0/1/N 条时按钮禁用态
  - 所有记录均可勾选，包括扫描中记录
  - 勾选全为扫描中时批量扫描按钮禁用，批量删除按钮可点击
  - 勾选包含不同状态时批量扫描按钮可点击，自动筛选掉扫描中记录并提示跳过数量
  - 批量扫描请求参数为 `[...]` 数组形式
  - 单条扫描请求参数为 `[singleRow]` 单元素数组
  - 批量删除请求参数为 id 数组 `['1', '2', ...]`
  - 单条删除请求参数为单元素 id 数组 `[row.id]`
  - 批量删除成功刷新与分页回退
  - 扫描中记录的删除按钮可点击，删除成功刷新
  - 切换 Tab/筛选/分页后选中清空
  - 二次确认取消不触发请求
- [ ] 9.3 回归测试
  - CodeCheck / AntiPoisoning Tab 表格不受影响
  - SCA 单条开始扫描行为一致（参数变化但功能不变）
  - 日志弹窗、失败日志下载不受影响

## 任务依赖关系

- 第一组无依赖，可优先开始
- 第二组、第八组无依赖，可并行
- 第三组依赖第二组（状态）与第八组（图标）
- 第四组无依赖，可独立
- 第五组依赖第二组（选中状态）与第四组（参数形式参考）
- 第六组依赖第一组（API）与第二组（选中状态）
- 第七组依赖第一组（API）与第八组（图标）
- 第九组依赖所有开发任务完成

## 执行顺序建议

1. 第一组 → 第二组 + 第八组（并行）
2. 第三组 + 第四组 → 第五组 + 第六组 + 第七组（并行）
3. 第九组

## 当前状态

- ⏳ 待实现
- 后端 `openlibing-sca`：
  - `startVersionScan` 需支持 `[...]` 数组参数
  - 删除接口 `/version/scan/deleteByIds` 已提供，入参为 id 数组
