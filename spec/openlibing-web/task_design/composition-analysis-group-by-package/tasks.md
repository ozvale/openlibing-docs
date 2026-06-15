# 实现步骤

- [x] 在 `queryInfo` 中新增 `groupByPackage` 字段，默认 `true`
- [x] 搜索栏 package 输入框后新增"分组展示"el-switch，绑定 `queryInfo.groupByPackage`
- [x] el-switch change 事件触发时重置页码到第 1 页并重新查询
- [x] `queryList` 中将 `groupByPackage: true` 改为 `groupByPackage: queryInfo.groupByPackage`
- [x] el-table 添加 `:row-key` 和 `:tree-props` 支持树形展开
- [x] 数据处理：分组模式下将 `packages[0]` 提升到父行，`packages.slice(1)` 作为子行
- [x] 编号列适配：分组模式父行显示 `_parentIndex`，非分组模式保持原逻辑
- [x] 软件包名称、版本列增加 `v-if` 防止子行空字段渲染异常
- [x] License 列父行不显示 "--" 占位符
- [x] Supplier 列父行不显示内容
- [x] 详情按钮改为根据 `scope.row.id` 判断显示
- [x] 分页组件添加 `:current-page` 绑定
- [x] 新增"来源信息"列（sourceInfo），无值显示 "--"
- [x] 修复 licenseIds 取值来源为 `Object.keys(res.data.licenseDistribution)`
