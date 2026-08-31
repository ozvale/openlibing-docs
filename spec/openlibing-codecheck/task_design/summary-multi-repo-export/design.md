# summary-multi-repo-export — 技术设计

> 范围：门禁检查 / 版本级检查 CodeCheck 子页面仓库下拉筛选框多选（导出需求已取消，不在本期范围）。
> 详细设计见 `design-v2.md`。关联 Issue：https://gitcode.com/openlibing/openlibing-codecheck/issues/174

## 方案概述

后端在 `QuerySummaryModel` 增加 `repoNames` 集合参数，`IncSummaryOperation.getCriteria` 与 `CommonOperation.getSummaryCriteria` 两处 Mongo Criteria 支持 `repoNameEn in(repoNames)`（`repoName` 单选向后兼容）；前端两页面仓库下拉改多选（`multiple` + `collapse-tags`），分支下拉选项为所选仓库分支的去重并集，列表查询参数由 `repoName` 改为 `repoNames` 数组。不新增任何接口，复用现有两个列表接口。

## 架构决策

| 决策                                                                                                  | 理由                                                                                     |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 多选用新字段 `repoNames`（List），保留 `repoName`                                                     | 老调用方（APIG 网关、内部单选）零影响；Criteria 中 `repoNames` 优先、为空回退 `repoName` |
| 分支选项为所选仓库分支的去重并集（大小写不敏感排序），仓库变化时清空已选分支                          | 旧分支可能不属于新仓库集合，保留会产生空结果歧义                                         |
| 表单类型 `repoName: string` → `repoNames: string[]` 同步改 shared.ts 与两个列表组件本地副本           | `isFormInlineChanged` 依赖 shared 与本地 formInline 键数量一致                           |
| 多选交互用 `multiple collapse-tags collapse-tags-tooltip`，保留 `filterable`、多选禁用 `allow-create` | 折叠标签避免撑爆筛选栏；保留输入过滤；禁用自定义输入以消除「可选不可查」歧义             |

## 涉及文件

### openlibing-codecheck（base: `origin/develop_20260831_iter2`，分支 `feat-summary-multi-repo-export`）

| 文件                                                    | 操作 | 说明                                                                               |
| ------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------- |
| `business/entity/QuerySummaryModel.java`                | 修改 | + `List<String> repoNames`                                                         |
| `business/operation/codecheck/IncSummaryOperation.java` | 修改 | `getCriteria`：repoNames 非空 → `repoNameEn in(repoNames)`，否则回退 repoName 单值 |
| `business/operation/common/CommonOperation.java`        | 修改 | `getSummaryCriteria`：同上                                                         |

### openlibing-web（base: `origin/master`，分支 `feat-summary-multi-repo-filter`）

| 文件                                                          | 操作 | 说明                                                                |
| ------------------------------------------------------------- | ---- | ------------------------------------------------------------------- |
| `src/views/CodeCheckPages/shared.ts`                          | 修改 | formInline `repoName`→`repoNames: []`；resetFormInline 同步         |
| `src/views/CodeCheckPages/GatingCheck/GatingCheck.vue`        | 修改 | 仓库 select 加 `multiple collapse-tags`；handleRepoChanged 分支并集 |
| `src/views/CodeCheckPages/VersionCheck/StaticCheck.vue`       | 修改 | 同上                                                                |
| `src/views/CodeCheckPages/GatingCheck/IncrementCheckList.vue` | 修改 | 本地 formInline 与查询参数改 repoNames                              |
| `src/views/CodeCheckPages/VersionCheck/StaticCheckList.vue`   | 修改 | 同上                                                                |

## 风险 & 缓解

- 前端 `isFormInlineChanged` 依赖 shared 与本地 formInline 键数量一致：两处 data 定义同步改为 `repoNames: []`
- 子行展开（`getIncChildCheckList`）按行数据查询不经表单，不受影响
- `repoNames` 与 `repoName` 同时传值时 `repoNames` 优先（新前端仅传 `repoNames`，无歧义场景）

## 跨仓影响

- 无接口签名变更：web 与 codecheck 可独立合入；codecheck 先行合入可保证参数即时生效
- 两 PR 引用同一 Issue #174（跨仓完整 URL）

## 验证方式

- 后端：`mvn compile` 编译验证；仓内若有既有单测基建则补 Criteria 构建用例，无则说明原因以人工自测为准
- 前端：lint + type-check；用户在测试环境自测：多选过滤、清空/重置、单选回归、分支并集联动
