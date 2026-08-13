# 实现任务清单

## 1. 新增 API 接口

- [x] 1.1 在 `api/Repos/url.ts` 中新增 `FILE_CONTENT`、`DUPLICATION_BLOCK_DETAIL`、`QUERY_REPO_FILTER_META` 三个 URL 常量
- [x] 1.2 在 `api/Repos/api.ts` 中新增 `fileContent`、`duplicationBlockDetail`、`queryRepoFilterMeta` 三个 API 函数

## 2. 新增 DuplicationCodeDrawer 组件

- [x] 2.1 创建 `views/Repos/dialog/DuplicationCodeDrawer.vue`
- [x] 2.2 集成 CodeMirror 6 编辑器（只读模式，代码高亮）
- [x] 2.3 实现 `computeBlockLanes` 算法：重叠块分层轨道分配
- [x] 2.4 实现 `BlockColorMarker`：行号旁 Gutter 颜色条纹（选中红色、未选中黄色）
- [x] 2.5 实现块导航功能：上一个/下一个/跳转到顶部/跳转到底部
- [x] 2.6 实现全屏模式切换
- [x] 2.7 实现段间省略逻辑（块间距 > 10 行时插入省略占位行）
- [x] 2.8 实现 `visible` v-model 双向绑定

## 3. 重构 MetricsDetailDialog

- [x] 3.1 新增 `duplicationLineCount`、`totalLines`、`duplicationBlockCount` 列定义（metricType=3）
- [x] 3.2 新增表头 tooltip 系统（`QuestionFilled` 图标 + `el-popover`）
- [x] 3.3 metricType=3 默认按 `duplicationRate` 降序排列
- [x] 3.4 修复 `handleSortChange` 重复触发问题（去重判断）
- [x] 3.5 文件名称列在 metricType=3 时改为可点击链接（蓝色 + hover 下划线）
- [x] 3.6 集成 `DuplicationCodeDrawer` 组件（通过 `cellClick` 事件触发）
- [x] 3.7 metricType=4 移除合并单元格逻辑，改为平铺列表
- [x] 3.8 metricType=4 实现奇偶行交替背景色（`tableRowClassName`）
- [x] 3.9 metricType=4 序号列标签改为"重复文件序列号"
- [x] 3.10 重复率列值后追加 `%` 后缀
- [x] 3.11 支持数组类型列渲染（`white-space: pre-line`）

## 4. 重构 branches.vue 组件通信

- [x] 4.1 移除 MetricsDetailDialog 的 el-dialog 包裹
- [x] 4.2 新增 `goMetricsDetail` emit 事件
- [x] 4.3 `openMetricsDetail` 改为通过 emit 通知父组件
- [x] 4.4 新增 `v-model`（`modelValue`）双向绑定分支搜索关键字
- [x] 4.5 `getBranchedData` 新增 `overrideBranchName` 参数，修复搜索后立即触发的问题

## 5. 重构 index.vue 主页面

- [x] 5.1 新增 `showMetricsDetail` 状态控制页面区域切换
- [x] 5.2 新增 `goMetricsDetail` 方法（接收参数 + 显示组件 + 同步 URL）
- [x] 5.3 新增 `syncMetricsQuery` 方法（将度量参数同步到 URL query）
- [x] 5.4 新增 `onActivated` 钩子（keep-alive 重新激活时清理 URL）
- [x] 5.5 项目切换时关闭子页面（`showBranch`/`showMetricsDetail`/`showUserManage`）
- [x] 5.6 `autoGoBranch` 仅首次进入时触发（`!oldValue` 判断）
- [x] 5.7 新增 `branchSearchCache` 并通过 v-model 传递给 branches
- [x] 5.8 `branchBack` 返回时清空 `branchSearchCache`

## 6. 验证方式

- 人工验证：总文件重复率列表文件名称可点击，打开抽屉后 CodeMirror 正确渲染文件内容
- 人工验证：颜色条纹正确标识重复代码块，选中/未选中颜色区分正确
- 人工验证：上一个/下一个/顶部/底部导航功能正常
- 人工验证：全屏模式切换正常
- 人工验证：切换项目时子页面自动关闭，URL 参数被清理
- 人工验证：度量详情刷新后页面状态恢复
- 人工验证：从度量详情返回分支列表时搜索关键字保留
- 人工验证：metricType=4 平铺列表 + 奇偶行交替背景色
- 人工验证：排序切换不触发重复请求
- 无单元测试（纯页面交互逻辑，行为变化通过人工验证）