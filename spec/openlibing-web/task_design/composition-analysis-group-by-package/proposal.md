# CompositionAnalysis 分组展示功能

**Issue**: openlibing/openlibing-web#188

## 需求背景

SBOM 软件成分分析页面（CompositionAnalysis）当前固定以 `groupByPackage: true` 请求后端接口，返回的数据按 package 分组后包含 `packages` 子数组。用户需要能够切换分组/非分组模式，并在分组模式下以树形表格展示展开的子包信息。

## 验收标准

- [x] 搜索栏新增"分组展示"el-switch 开关，默认开启
- [x] 开关状态绑定 `queryInfo.groupByPackage`，切换时重置页码到第 1 页并重新查询
- [x] `groupByPackage: true` 时，接口返回数据含 `packages` 数组，第一条 package 数据提升到父行展示，其余作为可展开子行
- [x] `groupByPackage: false` 时，保持原有扁平表格展示
- [x] 分组模式下父行显示序号、软件包名称、版本；子行不重复显示序号
- [x] 分组模式下父行有 `id` 时显示"详情"按钮并支持正常跳转
- [x] 分页组件绑定 `:current-page`，切换开关后页码 UI 同步更新
- [x] 新增"来源信息"列（sourceInfo 字段），无值时显示 "--"
- [x] 修复 licenseIds 取值来源为 `res.data.licenseDistribution` 对象的键名集合

## 影响范围

- 文件：`apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`
- 模块：SBOM 管理 - 软件成分分析
- 接口：`querySbomPackages`（参数 `groupByPackage` 由硬编码改为动态传入）
