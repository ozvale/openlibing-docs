# 代码仓不参与运营备注能力 — 设计文档

> FE 需求名称：【openLiBing-coderepo】代码仓不参与运营时增加备注能力
> 基线分支：`openlibing-web` = `beta_gamma`（前端由其他开发人员实现）；`openlibing-coderepo` = `master`（实现分支 `repo-operation-remark`，fork 开发）。
> 本文档为 Phase 1.5 归档后开发与覆盖度比对的唯一设计基线。

## 1. 方案设计

### 1.1 影响仓清单与结论

| 仓 / 组件                               | 结论           | 依据                                                                                                                                                                                    |
| --------------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `openlibing-web`                        | 需代码改动     | `apps/web-openlibing/src/views/Repos/index.vue` 新增/编辑弹窗；`apps/web-openlibing/src/views/Repos/dialog/batchEditDialog.vue` 批量编辑属性弹窗                                        |
| `openlibing-coderepo`                   | 需代码改动     | `RepoDTO` / `RepoInfoEntity` / `SpaceRepoDTO` / `BatchEditRepoInfoDTO`、`RepoServiceImpl` 新增/编辑/批量编辑、`RepoInfoMapper.xml`、`db.changelog.xml`、`RepoExportDelegateImpl` 导出列 |
| `openlibing-gateway`                    | 依赖但无需改动 | 复用现有 `/project-repo/add-repo`、`/update-repo`、`/batch-update-repo`、`/query-repo` 路由与 `repo_manage:update` 权限锚点，不新增路径、不改鉴权规则                                   |
| `openlibing-framework`                  | 依赖但无需改动 | 不改 `menu_url_info`、`repo_info` 主数据定义、导出底座；`repo_info` 表变更只由 coderepo 自身 Liquibase 管理                                                                             |
| `openlibing-common`                     | 依赖但无需改动 | 复用 `DataResult`、Bean Validation 与现有异常处理，不新增公共能力                                                                                                                       |
| Nacos / APIG / RabbitMQ / OBS / xxl-job | 不涉及         | 无新增配置、无新增对外接口、无异步事件与定时任务                                                                                                                                        |
| RDS MySQL                               | 需数据变更     | `repo_info` 新增 `operation_remark VARCHAR(200) NULL`，Liquibase 迁移，无存量回填                                                                                                       |
| `openlibing-docs`                       | 需文档         | 本 SPEC；若 Phase 3 生成前端接口说明文档，归档为 `api.md`                                                                                                                               |

### 1.2 总体方案

复用现有代码仓新增、编辑、批量编辑、列表查询与导出接口，不新增 HTTP 接口：

1. `repo_info` 新增可空列 `operation_remark`，Java 字段统一命名 `operationRemark`，与现有 `isParticipateOperation` 紧邻。
2. `RepoDTO` 增加 `operationRemark`；新增/编辑接口（`add-repo`、`update-repo`）通过同一字段接收备注。
3. 批量编辑复用现有 `isEditIsParticipateOperation` 维度，备注与开关在同一表单项内联动；选择「否」时统一填写备注，选择「是」时清空，不新增独立备注编辑维度。
4. `SpaceRepoDTO` 增加 `operationRemark`，列表接口回显，供列表备注列展示与编辑弹窗反显（当前无独立代码仓详情页，编辑弹窗即查看入口）。
5. 前端新增/编辑弹窗：备注项仅在开关为「否」时展示，必填、最多 200 字；切换为「是」时清空并隐藏。
6. 前端批量编辑弹窗：左侧字段列表只保留一个「是否参与运营」；勾选后默认「是」，与单个新增一致；选择「否」时同项展示备注并必填，选择「是」时隐藏并清空。
7. 代码仓列表导出 Excel 追加「不参与运营备注」列，与列表接口共用 `SpaceRepoDTO.operationRemark`，不新增导出查询。
8. 代码仓列表在「是否参与运营」列后新增「不参与运营备注」列：空值显示 `--`，超长省略并悬浮查看；列默认勾选，不参与筛选、排序。

### 1.3 关键决策

| 决策                   | 结论                                                                                                   | 理由                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| 字段命名               | 新增专用 `operationRemark` / `operation_remark`                                                        | `RepoDTO.remark` 是现存未使用字段（仅分支 VO 使用同名概念），语义泛化；复用会与后续通用备注混淆。本次不删除、不改动该字段 |
| 开关为「是」时备注处理 | 落库为 `NULL`                                                                                          | 与「选择是时就没有备注」一致，避免残留脏数据                                                                              |
| 存量数据               | 不批量补录、不迁移                                                                                     | 需求明确「不编辑不受影响」；仅在实际编辑保存时强制                                                                        |
| 校验落点               | 后端为最终闸门，前端做即时交互校验                                                                     | 防止绕过前端直接调接口；前端保证可操作性与提示                                                                            |
| 批量备注修改           | 通过「是否参与运营」批量项完成，不新增独立编辑维度                                                     | 避免同一备注出现两个编辑入口；左侧只需一个开关，备注在选择「否」时同项展示                                                |
| 列表 / 导出            | 列表新增「不参与运营备注」列（位于「是否参与运营」之后），不参与筛选排序；导出新增「不参与运营备注」列 | 备注需要在列表直接可见；为兼容既有列顺序，导出仍追加在最后一列                                                            |
| 权限                   | 复用代码仓编辑权限                                                                                     | 备注属于仓库配置的一部分，不引入新权限锚点                                                                                |

### 1.4 发布顺序与兼容性

- 推荐前端与后端同版本发布；若必须分批，先发前端：旧后端会忽略新增字段，不阻断保存；若先后端，旧前端的存量「否」仓库编辑会被新校验拦截并提示补充备注。
- 新前端 + 旧后端：备注可录入但不落库，后端上线后自动生效。
- 旧前端 + 新后端：仅影响存量「否」仓库的编辑保存（会提示补充备注），新增仓默认「是」不受影响。

### 1.5 需求设计检查结论（requirement-design-check）

| 检查项              | 结论                                                                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 架构与跨仓影响面    | 已逐仓判定，见 1.1；仅 `openlibing-web`、`openlibing-coderepo` 需代码改动，网关/框架/common 无改动                                        |
| 筛选 / 排序 / 分页  | 不适用：备注不参与列表筛选、排序，分页契约不变                                                                                            |
| 列表展示            | 「不参与运营备注」列位于「是否参与运营」之后，空值显示 `--`，超长省略并悬浮查看；默认勾选，老用户通过新增列逻辑自动补选                   |
| 二级页面 URL 直达   | 不适用：不新增页面；复用代码仓编辑弹窗，数据由列表接口回显                                                                                |
| 接口精简            | 复用现有新增/编辑/批量编辑/查询接口，不新增接口、不新增权限锚点                                                                           |
| 批量能力            | 扩展现有 `batch-update-repo`，复用 `List<Integer> repoIds` 批量传参与单条 SQL 更新；备注与开关在同一「是否参与运营」编辑项内联动          |
| 身份参数            | 沿用网关注入的 `userId` / `userName`，前端契约不变                                                                                        |
| 主键 / ID           | 不适用：不新增表，沿用 `repo_id`                                                                                                          |
| 表结构与索引        | 新增 1 个可空 `VARCHAR(200)` 列，无索引；无复合索引长度风险                                                                               |
| 存量数据取值        | 不批量回填；存量行保持 `NULL`，仅在用户编辑且开关为「否」时强制补填                                                                       |
| 可扩展性            | 不适用：单值文本字段，无集合顺序与结构演进问题                                                                                            |
| 展示 / 筛选口径一致 | 不适用：无新增筛选；单条与批量使用同一后端校验方法，口径一致                                                                              |
| 导出                | 导出与列表查询共用同一 `SpaceRepoDTO` 数据源；备注列追加在末尾，既有列顺序不变                                                            |
| 接口授权            | 沿用 `repo_manage:update` 与 `verifyPermissionsByProduct`；批量备注与开关在同一次更新中写入，未设置开关且所选仓库存在「否且无备注」时拦截 |
| 敏感数据            | 不涉及令牌/密钥/个人信息；备注按纯文本处理，不写日志正文                                                                                  |
| 外部回调 / 幂等     | 不适用：无回调、无 MQ、无重试链路                                                                                                         |
| 资源上限            | 备注长度上限 200 字符；批量入参规模沿用现有批量编辑接口行为，本次不新增批量上限                                                           |
| 状态字段自愈        | 不适用：备注为普通文本，无状态语义                                                                                                        |

## 2. 实现逻辑设计

### 2.1 统一校验规则

后端新增私有方法（`RepoServiceImpl`）：

```java
/**
 * 校验备注
 *
 * @param isParticipateOperation 本次生效的开关值
 * @param operationRemark 备注内容
 * @return 校验结果
 */
private DataResult<Void> validateOperationRemark(
    Boolean isParticipateOperation, String operationRemark)
```

规则：

1. `isParticipateOperation == false`：`StringUtils.trimToNull(operationRemark)` 为空 → 失败，提示「选择不参与运营时，请填写不参与运营备注」。
2. `operationRemark` 非空且长度 > 200 → 失败，提示「不参与运营备注不能超过200个字符」。
3. 其余情况通过；真正落库前统一 `trim()`。
4. 控制字符由 `RepoDTO.operationRemark` 上的 `@Pattern(regexp = "^[^\\p{Cntrl}]*$")` 兜底（`ValidationGroups.Insert` / `Update` 继承 `Default`，按现有分组生效）。

「本次生效的开关值」口径：

- 新增：`repoDTO.getIsParticipateOperation() != null ? 值 : true`（与现有默认值一致）。
- 编辑：`repoDTO.getIsParticipateOperation() != null ? 值 : 数据库现值`（与现有「未传保留原值」逻辑一致）。
- 批量：以 `isEditIsParticipateOperation` + `repoDTO.getIsParticipateOperation()` 为准。

### 2.2 新增代码仓

`RepoController.addRepoInfo` → `RepoServiceImpl.addRepoInfo`：

1. `validateRepoData` 通过后，计算生效开关值并调用 `validateOperationRemark`，失败直接返回 `DataResult.failureMessage`。
2. `createAndSaveRepoInfo` 在设置 `isParticipateOperation` 后写入备注：
   - 生效值为 `false`：`setOperationRemark(StringUtils.trimToNull(repoDTO.getOperationRemark()))`；
   - 生效值为 `true`：`setOperationRemark(null)`。
3. `insertRepo` 增加 `operation_remark` 列与 `#{operationRemark}` 值。

### 2.3 编辑代码仓

`RepoController.updateRepoInfo` → `RepoServiceImpl.updateRepoInfo`：

1. `validateAndGetRepoInfo` 取到 `dataEntity` 后，按「提交值优先、未传取现值」计算生效开关值。
2. 调用 `validateOperationRemark`，失败返回提示；不进入更新事务。
3. `buildRepoInfoEntity` 中：
   - 保留现有逻辑：`isParticipateOperation` 未传时取数据库现值；
   - 设置 `updateEntity.setIsEditOperationRemark(true)`（新增的 `@TableField(exist = false)` 瞬态标记）；
   - 生效值为 `false` → 写入 trim 后的备注；生效值为 `true` → 写入 `null`。
4. `RepoInfoMapper.updateRepo` 增加：

```xml
<if test="isEditOperationRemark == true">
    operation_remark = #{operationRemark},
</if>
```

> 说明：`isEditOperationRemark` 用于区分「不更新备注」与「显式清空备注」。其他直接调用 `repoInfoMapper.updateRepo` 的内部链路（令牌刷新、状态同步、SIG 同步等）不会设置该标记，因此不会误清空备注。

### 2.4 批量编辑代码仓

`BatchEditRepoInfoDTO` 不新增字段，复用现有 `isEditIsParticipateOperation` 维度；备注通过 `repoDTO.operationRemark` 与开关一起提交。

`prepare()` 调整：

1. `isEditIsParticipateOperation == true` 且开关值为 `false` 且备注为空 → 抛「选择不参与运营时，请填写不参与运营备注！」。
2. 备注长度 > 200 → 抛「不参与运营备注不能超过200个字符！」。

`batchUpdateRepoInfo` 流程：

1. 已通过 `queryByIds` 取到 `repoInfoEntities`，先做横向越权校验（现有逻辑不变）。
2. 若 `isEditIsParticipateOperation == true`：按联动口径校验备注；开关为 `false` 时必填，为 `true` 时忽略备注并将其置空。
3. 若 `isEditIsParticipateOperation != true`：本次不改开关，也不改备注；若所选仓库中存在「否」且备注为空的仓库 → 返回「所选仓库中存在不参与运营但未填写备注的仓库，请先补充备注」。用户如需批量补充备注，应勾选「是否参与运营」并选择「否」。
4. `UpdateWrapper` 增加：

```java
.set(isEditIsParticipateOperation, "is_participate_operation", repoDTO.getIsParticipateOperation())
.set(isEditIsParticipateOperation && Boolean.FALSE.equals(repoDTO.getIsParticipateOperation()),
     "operation_remark", StringUtils.trimToNull(repoDTO.getOperationRemark()))
.set(isEditIsParticipateOperation && Boolean.TRUE.equals(repoDTO.getIsParticipateOperation()),
     "operation_remark", null)
```

5. 现有 `updateCount != repoIds.size()` 校验保持不变。

### 2.5 列表查询、列表不参与运营备注列与编辑反显

- `buildSpaceRepoDTO` 增加 `spaceEntity.setOperationRemark(dto.getOperationRemark())`。
- `repoInfoQuerySelect` 与 `repoInfoQuerySelectAliased` 增加 `operation_remark`。
- `repoInfoMap` 增加 `operation_remark` → `operationRemark` 映射。
- 前端 `allColumns` 在「是否参与运营」之后新增 `{ group: '仓库配置', label: '不参与运营备注', prop: 'operationRemark' }`。
- 列表表格在「是否参与运营」列后新增不参与运营备注列：`v-if="checkedColumnKeys.includes('operationRemark')"`、`show-overflow-tooltip`，空值显示 `--`。
- 新列通过现有 `getStoredColumnKeys` 的 newKeys 逻辑对老用户默认勾选；`getStoredColumnOrder` 会按列定义顺序将其插入到「是否参与运营」之后。
- 前端编辑弹窗通过列表行 `Object.assign(formData, row)` 自动反显 `operationRemark`。

### 2.6 前端新增 / 编辑弹窗

文件：`apps/web-openlibing/src/views/Repos/index.vue`

1. `FORM_FIELD_KEYS` 增加 `operationRemark`，避免编辑行额外字段清理时被误删。
2. 新增表单默认值 `operationRemark: ''`；编辑模式由列表行 `Object.assign(formData, row)` 反显，行数据缺省时显式置空。
3. 在「是否参与运营」表单项后新增备注项：
   - 标签统一为「不参与运营备注」，与批量编辑保持一致；
   - `v-if="formData.isParticipateOperation === false"`；
   - `el-input`，`maxlength="200"`、`show-word-limit`，占位提示统一使用「请输入不参与运营备注」；
   - `prop="operationRemark"`。
4. `rules` 增加自定义校验：开关为「否」且备注 trim 后为空 → 报错「请填写不参与运营备注」。
5. `watch(formData.isParticipateOperation)`：切换为「是」时置空 `operationRemark` 并清除校验态；切换为「否」时允许输入并保持必填。
6. `getSavePayload` 已整体展开 `formData`，备注随请求上送；开关为「是」时备注为空，后端负责清空。
7. `buildFormConfig`（跨项目配置一致性比对）不纳入备注，与 `accessToken`、`remark` 的现有排除口径一致。

### 2.7 前端批量编辑弹窗

文件：`apps/web-openlibing/src/views/Repos/dialog/batchEditDialog.vue`

1. `schema` 不新增独立备注字段，左侧字段列表仍只有「是否参与运营」；`isParticipateOperation` 在基线 `beta_gamma` 上已为 `defaultValue: true`（commit 1e973a4e2a，2026-11-16），本需求保持该默认值不变；右侧对 `key === 'isParticipateOperation'` 使用自定义渲染。
2. `formValues` 增加 `operationRemark: ''`（仅作为开关的附属值，不进入 `schema`、不进入 `selectedKeys`）。
3. 交互与布局规则：
   - 勾选「是否参与运营」后，在现有 `form-item-wrap` 容器（`<div class="form-item-wrap">`）内展示开关行，默认选中「是」；
   - 选择「否」：在同一个 `form-item-wrap` 容器内追加「不参与运营备注」行（同为 `<el-form-item>`），两行使用相同的 `label-width` 固定值（替换基线的 `auto`），保证「是否参与运营」与「不参与运营备注」标签左边缘对齐；备注必填，最多 200 字；
   - 输入框占位统一为「请输入不参与运营备注」；
   - 选择「是」：不展示备注行，并清空备注值；
   - 未勾选「是否参与运营」：不展示开关与备注。
4. 保存前校验：
   - 勾选开关且值为「否」且备注为空 → 提示「选择不参与运营时，请填写不参与运营备注」并阻止提交；
   - 未勾选开关且所选仓库中存在「否」且备注为空的仓库 → 提示「所选仓库中存在不参与运营但未填写备注的仓库，请先勾选「是否参与运营」并选择「否」补充备注」并阻止提交。
5. `confirm()`：`schema` 遍历仍生成 `isEditIsParticipateOperation`；选中开关时手动补充 `repoDTO.operationRemark = 值为否 ? trim 后的备注 : ''`，不新增其他编辑标记。
6. 「全选」只包含现有字段（备注不是独立字段），无需额外排除逻辑。

### 2.8 边界与异常

| 场景                                         | 处理                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| 备注仅空白字符                               | 按空处理，开关为「否」时校验失败                                       |
| 备注超过 200 字                              | 前端 `maxlength` 限制；后端长度校验兜底                                |
| 备注含控制字符                               | `@Pattern` 拒绝                                                        |
| 存量「否」仓库无备注，编辑任意字段           | 校验失败并提示补充；补充后保存成功                                     |
| 存量「否」仓库无备注，系统内部链路更新       | 不经过 `updateRepoInfo`，不受影响、不强制补录                          |
| 编辑时开关未传                               | 取数据库现值判定；若现值为「否」仍要求备注                             |
| 开关由「否」改「是」                         | 备注置 `NULL`，不再展示                                                |
| 批量编辑其他属性且所选仓库存在「否且无备注」 | 拦截并提示勾选「是否参与运营」设为「否」补充备注                       |
| 批量开关改「是」                             | 所选仓库备注全部置 `NULL`                                              |
| 并发编辑                                     | 不使用乐观锁；以最后一次保存提交的开关与备注为准，与现有代码仓编辑一致 |

### 2.9 导出代码仓列表

文件：`com.openlibing.coderepo.business.service.impl.RepoExportDelegateImpl`

1. `TABLE_HEADERS` 末尾追加「不参与运营备注」，新列索引为 32；既有 0–31 列顺序保持不变，避免影响用户已有导出模板与下游脚本。
2. `fillDataRow` 末尾追加 `setCellValue(row, col, defaultDisplay(dto.getOperationRemark()))`；`NULL` / 空白统一显示占位符 `--`。
3. 数据来源复用 `SpaceRepoDTO.operationRemark`，与列表查询同源，不新增导出 SQL。
4. 备注为用户输入，写入单元格复用现有 `setCellValue` → `escapeFormulaInjection`：以 `= + - @ Tab CR LF` 开头的值前置单引号，防止 Excel 公式注入。
5. 同步更新 `RepoExportDelegateImpl` 类注释中的列索引清单（新增 32 不参与运营备注），并更新 `RepoExportDelegateImplTest`：校验表头最后一列为「不参与运营备注」，覆盖有值/空值两种单元格输出。

## 3. 类设计

### 3.1 后端

| 类                                                                                            | 改动                                                                                                                                                                                |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `com.openlibing.coderepo.business.dto.space.RepoDTO`                                          | 新增 `String operationRemark`，加 `@Size(max = 200, groups = ValidationGroups.Default.class)` 与 `@Pattern(groups = ValidationGroups.Default.class, regexp = "^[^\\p{Cntrl}]*$")`   |
| `com.openlibing.coderepo.business.entity.space.RepoInfoEntity`                                | 新增 `String operationRemark`；新增 `@TableField(exist = false) Boolean isEditOperationRemark = false`                                                                              |
| `com.openlibing.coderepo.business.dto.space.SpaceRepoDTO`                                     | 新增 `String operationRemark`                                                                                                                                                       |
| `com.openlibing.coderepo.business.dto.repo.BatchEditRepoInfoDTO`                              | 不新增字段；`prepare()` 增加「开关为否时备注必填」与长度校验                                                                                                                        |
| `com.openlibing.coderepo.business.service.impl.RepoServiceImpl`                               | 新增 `validateOperationRemark`；`addRepoInfo` / `createAndSaveRepoInfo` / `updateRepoInfo` / `buildRepoInfoEntity` / `batchUpdateRepoInfo` / `buildSpaceRepoDTO` 增加备注赋值与校验 |
| `com.openlibing.coderepo.business.service.impl.RepoExportDelegateImpl`                        | `TABLE_HEADERS` 末尾新增「不参与运营备注」；`fillDataRow` 写入 `operationRemark`（空值显示 `--`）                                                                                   |
| `com.openlibing.coderepo.business.mapper.RepoInfoMapper`                                      | 无方法签名变更，沿用 `insertRepo` / `updateRepo`                                                                                                                                    |
| `src/main/resources/mapper/RepoInfoMapper.xml`                                                | `repoInfoMap`、`repoInfoQuerySelect`、`repoInfoQuerySelectAliased`、`insertRepo`、`updateRepo` 增加 `operation_remark`                                                              |
| `src/main/resources/db/changelog/db.changelog.xml`                                            | 新增 Liquibase changeSet                                                                                                                                                            |
| `src/test/java/com/openlibing/coderepo/business/service/impl/RepoExportDelegateImplTest.java` | 新增不参与运营备注列表头与单元格断言                                                                                                                                                |

### 3.2 前端

| 文件                                                             | 改动                                                                                                                      |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/Repos/index.vue`                  | `FORM_FIELD_KEYS`、表单默认值、不参与运营备注表单项、动态校验、开关 watch、保存入参、列表 `allColumns` 与不参与运营备注列 |
| `apps/web-openlibing/src/views/Repos/dialog/batchEditDialog.vue` | 「是否参与运营」表单项内条件渲染备注输入、保存前校验、`confirm` 补充 `operationRemark`                                    |
| `apps/web-openlibing/src/api/*`                                  | 无改动，沿用 `addRepo` / `updateRepo` / `batchUpdateRepo`                                                                 |

## 4. 数据模型设计

### 4.1 表结构变更

`repo_info` 新增列：

| 列名               | 类型           | 可空 | 默认值 | 说明                                                                            |
| ------------------ | -------------- | ---- | ------ | ------------------------------------------------------------------------------- |
| `operation_remark` | `VARCHAR(200)` | 是   | 无     | 不参与运营备注；仅当 `is_participate_operation = 0` 时有值，`NULL`/空表示无备注 |

Liquibase changeSet（追加到 `db.changelog.xml` 末尾，沿用现有风格）：

```xml
<!-- 不参与运营备注：开关为否时必填，关为是时清空；存量数据不补录 -->
<changeSet id="20261113_add_operation_remark_to_repo_info" author="ai-assisted">
    <preConditions onFail="MARK_RAN">
        <tableExists tableName="repo_info"/>
        <not>
            <columnExists tableName="repo_info" columnName="operation_remark"/>
        </not>
    </preConditions>
    <addColumn tableName="repo_info">
        <column name="operation_remark" type="VARCHAR(200)" remarks="不参与运营备注（is_participate_operation=0 时必填）">
            <constraints nullable="true"/>
        </column>
    </addColumn>
    <rollback>
        <dropColumn tableName="repo_info" columnName="operation_remark"/>
    </rollback>
</changeSet>
```

### 4.2 存量数据

- 存量行 `operation_remark` 为 `NULL`，不执行 UPDATE 回填。
- 前端展示空备注；仅当用户编辑保存且开关为「否」时要求补填。
- 存量「是」仓库即使有历史脏值，下一次保存也会被置为 `NULL`。

### 4.3 索引与查询

- 不新增索引：备注不参与筛选、排序、分组。
- 列表与导出查询仅多返回一列 `VARCHAR(200)`，不引入额外查询。

## 5. 性能设计

| 项          | 评估                                                                              |
| ----------- | --------------------------------------------------------------------------------- |
| 列表查询    | `repo_info` 单行多读取最多 200 字符，QPS 与现有列表一致，无额外 JOIN / 子查询     |
| 新增 / 编辑 | 单行 UPDATE 多一个可空列，耗时增量可忽略                                          |
| 批量编辑    | 仍为单条 `UPDATE ... WHERE repo_id IN (...)`，不产生 N 次更新；备注不引入额外查询 |
| 导出        | SXSSF 流式写出，每行多写 1 个最长 200 字符的单元格，耗时可忽略；不新增 SQL 查询   |
| 内存 / CPU  | 无新增集合、缓存或循环；不触碰 CCE 资源配额                                       |
| 并发        | 依赖现有数据库行锁与接口并发模型，不新增分布式锁                                  |

结论：无性能风险，不需要容量调整。

## 6. API 接口设计

不新增接口，仅扩展既有接口字段与导出列。

### 6.1 新增代码仓

`POST /openlibing-coderepo/project-repo/add-repo`（请求头/网关注入 `userId`、`userName` 不变）

新增请求字段：

| 字段              | 类型   | 必填     | 说明                                                                 |
| ----------------- | ------ | -------- | -------------------------------------------------------------------- |
| `operationRemark` | string | 条件必填 | `isParticipateOperation=false` 时必填，最多 200 字；为 `true` 时忽略 |

失败提示：`选择不参与运营时，请填写不参与运营备注`、`不参与运营备注不能超过200个字符`。

### 6.2 编辑代码仓

`POST /openlibing-coderepo/project-repo/update-repo`

新增字段同上；判定使用「提交的开关值，未提交则取仓库现值」。开关最终为 `true` 时备注置空。

### 6.3 批量编辑代码仓

`POST /openlibing-coderepo/project-repo/batch-update-repo`

新增/复用字段：

| 字段                      | 类型   | 必填     | 说明                                                                                                       |
| ------------------------- | ------ | -------- | ---------------------------------------------------------------------------------------------------------- |
| `repoDTO.operationRemark` | string | 条件必填 | 仅当 `isEditIsParticipateOperation=true` 且开关为「否」时提交，必填，最多 200 字；开关为「是」时忽略并清空 |

失败提示：

- `选择不参与运营时，请填写不参与运营备注！`
- `不参与运营备注不能超过200个字符！`
- `所选仓库中存在不参与运营但未填写备注的仓库，请先补充备注`

### 6.4 查询代码仓列表

`POST /openlibing-coderepo/project-repo/query-repo`

响应 `data.data[].operationRemark` 新增字段（string，可为空），供列表「不参与运营备注」列展示与编辑弹窗反显。列表在「是否参与运营」列后展示不参与运营备注；筛选、排序、分页契约不变。

### 6.5 导出代码仓列表

`POST /openlibing-coderepo/project-repo/export-repo`

请求参数与筛选条件不变；响应 Excel 在最后一列新增「不参与运营备注」：

- 有备注时输出原文；
- `NULL` / 空白时输出 `--`；
- 既有列顺序与列含义不变，不影响已有导出模板。

### 6.6 网关与权限

- 路由、鉴权、限流、CSRF 均复用现状，无新增路径。
- 权限锚点沿用 `repo_manage:update`（新增、编辑、批量编辑现有校验不变）。
- 不新增 `menu_url_info` 配置。

## 7. 安全设计

| 维度           | 设计                                                                                                                                         |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 权限           | 沿用代码仓新增/编辑/批量编辑的现有横向越权校验（`verifyPermissionsByProduct`），不新增或放宽权限                                             |
| 输入校验       | 长度 ≤ 200；拒绝控制字符；服务端 trim 后判空；前端 `maxlength` 仅作体验优化，不作为安全边界                                                  |
| XSS            | 备注按纯文本渲染，前端使用插值/`el-input`，禁止 `v-html`；后端不做 HTML 转义，保持原始文本                                                   |
| SQL 注入       | Mapper 全部使用 `#{}` 参数绑定；批量更新使用 `UpdateWrapper.set(column, value)`，列名为代码常量                                              |
| Excel 公式注入 | 备注导出复用 `RepoExportDelegateImpl.setCellValue` 的 `escapeFormulaInjection`，以 `= + - @ Tab CR LF` 开头的值前置单引号                    |
| 敏感信息       | 备注为运营说明，不涉及令牌、密钥、个人敏感信息；不写入日志正文                                                                               |
| 越权修改备注   | 备注写入与「是否参与运营」在同一次批量更新中完成，沿用仓库归属校验与 `repo_manage:update` 权限；未设置开关且所选仓库存在「否且无备注」时拦截 |
| 审计           | 沿用 `@LogApi` 的新增/编辑/批量编辑操作日志，不新增日志字段                                                                                  |
| 容量           | 单字段 200 字符上限；批量入参规模沿用现有批量编辑接口行为，本次不新增批量上限                                                                |
