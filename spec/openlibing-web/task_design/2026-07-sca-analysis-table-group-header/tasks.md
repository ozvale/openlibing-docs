# Tasks: SCA 分析表二级表头 + nginx /argus 配置缩进统一

## 实现步骤

- [x] 1. 在 `analysisTable.config.js` 新增 `columnGroups` 导出，定义三个分组（源代码 / 开源软件代码 / 分析及审核结果）及其包含的列 id
- [x] 2. `gitUrlList.vue`：import `columnGroups`，`table` 对象挂载 `columnGroups`
- [x] 3. `gitUrlList.vue`：template 外层用 `v-for="group in table.columnGroups"` 渲染父 `el-table-column`（label=组名），原 `el-table-column` 作为子列，过滤条件改为 `it.show && group.ids.includes(it.id)`
- [x] 4. `openSourceCompliance/analysisTable.vue`：同步骤 2-3
- [x] 5. `personalScandTaskInfor/analysisTable.vue`：同步骤 2-3
- [x] 6. 校验三处子列的 `#header` / `#default` slot 逻辑原样保留（clarifyType / reviewStatus tooltip、漏洞标签、purl el-tag、双击编辑等）
- [x] 7. 校验 `table.column.forEach` 相关逻辑（selectList、列设置弹框、导出）未受影响
- [x] 8. 统一 `nginx_gamma.conf` 中 `/argus` location 块缩进为 18 空格

## 验证

- [x] 三个 vue 文件 GetDiagnostics 无错误
- [x] `columnGroups` 的 id 并集 = 全部 22 个列 id，无遗漏无重复
- [x] SCA 二级表头改动已提交（业务仓 commit `03e5c14b`「合法合规增加二级表头」）
