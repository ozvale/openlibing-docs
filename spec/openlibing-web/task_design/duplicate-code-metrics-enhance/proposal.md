# 仓库重复代码度量详情增强

## 需求背景

仓库管理（Repos）页面的代码度量详情存在以下问题：

1. **总文件重复率（metricType=3）缺少重复代码块钻取能力**：用户只能看到每个文件的重复率/重复行数，无法查看具体的重复代码片段和对应文件，不利于定位和修复重复代码问题。
2. **总文件重复率列表缺少重复代码块数量列**：无法快速了解每个文件的重复代码块分布情况。
3. **度量详情对话框与仓库分支列表耦合**：MetricsDetailDialog 作为 el-dialog 嵌入在 branches.vue 中，导致对话框状态与分支列表状态耦合，切换项目时对话框状态残留。
4. **切换项目时未重置子页面状态**：切换到其他项目时，仓库分支页、度量详情页、用户管理页未自动关闭，URL 参数残留。
5. **度量详情刷新后无法恢复**：进入度量详情后刷新页面，URL 未同步度量参数（repoId/branchName/pipelineRunId/metricType），导致页面回退到仓库列表。
6. **总文件重复率列表缺少表头说明和排序**：缺少"重复代码行数""有效代码行数""重复率""重复代码块数量"列的定义说明，且默认未按重复率降序排列。
7. **总文件重复率（metricType=4）合并单元格逻辑复杂**：原始合并单元格方案在数据变化时容易出错，且用户体验不佳。
8. **分支搜索缺少缓存**：从度量详情返回分支列表时，之前的搜索关键字丢失。

## 功能描述

### 新增重复代码块抽屉（DuplicationCodeDrawer）

- 在总文件重复率（metricType=3）详情中，文件名称列变为可点击链接
- 点击文件名称打开抽屉，展示该文件的所有重复代码块
- 抽屉使用 CodeMirror 编辑器渲染文件内容，以颜色条纹标识重复代码块位置
- 支持重复代码块导航（上一个/下一个/跳转到顶部/跳转到底部）
- 支持全屏模式
- 需要调用两个新接口：`fileContent`（获取文件内容）和 `duplicationBlockDetail`（获取重复代码块明细）

### 度量详情对话框重构

- 将 MetricsDetailDialog 从 branches.vue 的 el-dialog 中提升到 index.vue 作为独立页面区域
- branches.vue 通过 emit 事件通知父组件打开度量详情
- 度量详情新增 `duplicationBlockCount`（重复代码块数量）列
- 新增 `duplicationLineCount`（重复代码行数）和 `totalLines`（有效代码行数）列
- 各列新增问号提示（tooltip）说明计算规则
- 总文件重复率列表默认按重复率降序排列
- 总文件重复率（metricType=4）改为平铺列表，文件名列显示原始文件名，奇偶行交替背景色
- 修复排序切换时空触发重复请求的问题

### 项目切换行为优化

- 切换项目时自动关闭仓库分支页、度量详情页、用户管理页
- 通过 `onActivated` 钩子在 keep-alive 重新激活时清理 URL 参数
- 仅在首次进入（非项目切换）时自动跳转仓库分支（`autoGoBranch`）

### 分支搜索缓存

- 分支搜索关键字通过 `v-model` 在父子组件间双向绑定
- 从度量详情返回分支列表时保留搜索关键字

### URL 同步

- 进入度量详情时将参数同步到 URL query，刷新后可恢复

## 验收标准

- [ ] 总文件重复率列表文件名称可点击，打开重复代码块抽屉
- [ ] 重复代码块抽屉正确渲染文件内容，颜色条纹标识重复代码块
- [ ] 重复代码块导航（上一个/下一个/顶部/底部）功能正常
- [ ] 全屏模式切换正常
- [ ] 总文件重复率列表默认按重复率降序排列
- [ ] 总文件重复率列表显示重复代码行数、有效代码行数、重复代码块数量列
- [ ] 各列表头问号提示正确显示计算规则说明
- [ ] 切换项目时仓库分支/度量详情/用户管理页面自动关闭
- [ ] 切换项目时 URL 参数被清理
- [ ] 度量详情刷新后页面状态恢复
- [ ] 从度量详情返回分支列表时搜索关键字保留
- [ ] 总文件重复率（metricType=4）平铺列表正确展示，奇偶行交替背景色
- [ ] 排序切换不触发重复请求

## 影响范围

| 文件                                                                   | 仓库           | 变更类型           |
| ---------------------------------------------------------------------- | -------------- | ------------------ |
| `apps/web-openlibing/src/api/Repos/api.ts`                             | openlibing-web | 新增 3 个 API 函数 |
| `apps/web-openlibing/src/api/Repos/url.ts`                             | openlibing-web | 新增 3 个 URL 常量 |
| `apps/web-openlibing/src/views/Repos/dialog/DuplicationCodeDrawer.vue` | openlibing-web | 新增组件           |
| `apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue`   | openlibing-web | 重构               |
| `apps/web-openlibing/src/views/Repos/branches.vue`                     | openlibing-web | 重构               |
| `apps/web-openlibing/src/views/Repos/index.vue`                        | openlibing-web | 重构               |

## 关联后端接口

| 接口                                               | 用途                                 |
| -------------------------------------------------- | ------------------------------------ |
| `/code-repo/metrics/code/file-content`             | 获取文件内容（用于 CodeMirror 渲染） |
| `/code-repo/metrics/code/duplication-block/detail` | 获取文件重复代码块明细               |
| `/code-repo/project-repo/query-repo-filter-meta`   | 获取仓库筛选元数据                   |
