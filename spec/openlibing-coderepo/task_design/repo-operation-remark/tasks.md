# 代码仓不参与运营备注能力 — 实现任务

> FE 需求名称：【openLiBing-coderepo】代码仓不参与运营时增加备注能力

## 进度: 0/19 complete

## 后端（openlibing-coderepo / master）

- [ ] Task 1: 在 `src/main/resources/db/changelog/db.changelog.xml` 末尾新增 `20261113_add_operation_remark_to_repo_info` changeSet，为 `repo_info` 增加 `operation_remark VARCHAR(200) NULL` 及 rollback，不做存量回填。
- [ ] Task 2: `RepoInfoEntity` 增加 `String operationRemark` 与 `@TableField(exist = false) Boolean isEditOperationRemark = false`。
- [ ] Task 3: `RepoDTO` 增加 `String operationRemark`，补 `@Size(max = 200)` 与拒绝控制字符的 `@Pattern`（`ValidationGroups.Default`）。
- [ ] Task 4: `SpaceRepoDTO` 增加 `String operationRemark`。
- [ ] Task 5: `BatchEditRepoInfoDTO` 不新增字段；`prepare()` 增加「开关为否时备注必填」与「长度 ≤ 200」校验。
- [ ] Task 6: `RepoInfoMapper.xml` 的 `repoInfoMap`、`repoInfoQuerySelect`、`repoInfoQuerySelectAliased`、`insertRepo`、`updateRepo` 增加 `operation_remark`；`updateRepo` 使用 `isEditOperationRemark == true` 条件以支持显式清空。
- [ ] Task 7: `RepoServiceImpl` 新增 `validateOperationRemark(Boolean, String)`；在 `addRepoInfo` 与 `createAndSaveRepoInfo` 接入新增校验与落库。
- [ ] Task 8: `RepoServiceImpl.updateRepoInfo` 与 `buildRepoInfoEntity` 接入编辑校验、生效开关值计算、备注写入/清空与 `isEditOperationRemark` 标记。
- [ ] Task 9: `RepoServiceImpl.batchUpdateRepoInfo` 接入开关联动备注校验、未设置开关时「所选仓库存在否且无备注则拦截」校验，并在 `UpdateWrapper` 中写入/清空备注。
- [ ] Task 10: `RepoServiceImpl.buildSpaceRepoDTO` 回填 `operationRemark`，保证列表接口与导出共用数据源可供反显。
- [ ] Task 11: `RepoExportDelegateImpl` 的 `TABLE_HEADERS` 末尾新增「不参与运营备注」，`fillDataRow` 写入 `operationRemark`（空值 `--`），同步更新类注释列索引清单；`RepoExportDelegateImplTest` 增加表头与有值/空值单元格断言。
- [ ] Task 12: 在 `RepoServiceImplTest` 补充单元测试：新增（否+空失败、否+有备注成功、是+备注清空）、编辑（存量否无备注失败、存量否补备注成功、改为是清空）、批量（否必填、是清空、未改开关且存在否无备注拦截）。
- [ ] Task 13: 执行后端验证：`mvn -q test -Dtest=RepoServiceImplTest,RepoExportDelegateImplTest`（或项目约定的等价命令），确认编译与相关测试通过。

## 前端（openlibing-web / beta_gamma）

- [ ] Task 14: `apps/web-openlibing/src/views/Repos/index.vue`：`FORM_FIELD_KEYS` 与新增表单默认值加入 `operationRemark`。
- [ ] Task 15: 列表在「是否参与运营」列后新增「不参与运营备注」列：`allColumns` 增加 `operationRemark` 配置，表格列使用 `show-overflow-tooltip`、空值显示 `--`；确认老用户新列默认勾选且列顺序位于「是否参与运营」之后。
- [ ] Task 16: 新增/编辑弹窗增加不参与运营备注项：仅开关为「否」展示、`maxlength=200`、必填校验、输入框占位统一「请输入不参与运营备注」、开关切「是」时清空并清除校验。
- [ ] Task 17: `apps/web-openlibing/src/views/Repos/dialog/batchEditDialog.vue` 将「是否参与运营」默认值调整为「是」，并在该表单项内条件渲染不参与运营备注行（选择否才展示；标签左对齐），不新增独立备注字段或勾选项。
- [ ] Task 18: 批量弹窗实现联动与守卫：默认「是」不展示不参与运营备注、选择否时同项展示并必填、选择是时隐藏并清空、未勾选开关且所选仓库存在「否且无不参与运营备注」时拦截；「全选」只包含现有字段。
- [ ] Task 19: 执行前端验证：`pnpm check:type`、`pnpm lint`（或仓库约定命令），并手工覆盖列表不参与运营备注列、新增/编辑/批量编辑/存量否仓补备注/切换是清空主链路。

## 交付前自检（Phase 3）

- [ ] 逐条对照 `design.md` 7 个章节做覆盖度比对，输出「已覆盖 / 未覆盖」结论。
- [ ] 检查是否涉及 HTTP 接口字段变更；如命中，询问用户是否生成前端接口说明文档并在归档时补充 `api.md`。
- [ ] 检查本轮 diff 是否存在删除代码；如有，逐条向用户确认。
