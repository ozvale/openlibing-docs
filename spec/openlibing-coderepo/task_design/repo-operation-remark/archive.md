# 代码仓不参与运营备注能力 — 归档基线

## 关联

- FE 需求名称：【openLiBing-coderepo】代码仓不参与运营时增加备注能力
- 业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/301
- docs 归档 PR：本 PR（Phase 1.5，5 份 SPEC 一次性归档，使用 `Refs` 关联业务 Issue）
- 目标分支：`openlibing-coderepo` = `master`（实现分支 `repo-operation-remark`，fork 开发）；`openlibing-web` = `beta_gamma`（前端由其他开发人员实现）

## 需求与验收口径

### 需求范围

- 做什么：新增/编辑/批量编辑代码仓时，「是否参与运营」为「否」必须填写不参与运营备注（最多 200 字）；为「是」不展示且不保留；支持单个修改与批量修改；代码仓列表在「是否参与运营」后展示不参与运营备注列；导出代码仓列表包含「不参与运营备注」列；存量数据不做批量补录。
- 不做什么：不参与运营备注列不参与筛选/排序、备注历史留痕与审批、独立备注页面、修改开关本身语义、清理 `RepoDTO.remark`。

### 验收标准摘要

- 新增仓：否 + 空备注保存失败；否 + 备注保存成功；是 + 无备注保存成功。
- 存量仓：当前为否且无备注，编辑任意信息保存失败并提示；补充后成功。
- 存量仓：当前为否已有备注，可正常修改保存。
- 开关否 → 是：备注项消失，原备注不再保留。
- 批量：勾选后默认「是」，与单个新增一致；设为否必填并统一填写/修改备注；设为是清空；未改开关且所选存在「否且无备注」被拦截。
- 导出：Excel 最后一列包含「不参与运营备注」，无备注显示 `--`。
- 列表：不参与运营备注列位于「是否参与运营」之后，有值展示内容、空值显示 `--`，超长省略并可悬浮查看。
- 未被编辑的存量仓不产生任何强制与提示。

## 交付计划

- 预期改动范围：
  - `openlibing-coderepo`：`db.changelog.xml`、`RepoInfoEntity`、`RepoDTO`、`SpaceRepoDTO`、`BatchEditRepoInfoDTO`、`RepoServiceImpl`、`RepoInfoMapper.xml`、`RepoExportDelegateImpl`、`RepoServiceImplTest`、`RepoExportDelegateImplTest`
  - `openlibing-web`：`views/Repos/index.vue`、`views/Repos/dialog/batchEditDialog.vue`
- 任务清单：见 `tasks.md`
- 交付物：业务 PR（目标 Release 分支待 Phase 4 与用户确认）；前端接口说明文档按 Phase 3 检测结果决定是否生成
- 发布注意：推荐前后端同版本发布；若先后端，旧前端的存量「否」仓库编辑会被新校验拦截

## 待回填（开发完成后按需）

- 业务 PR：
- 交付 commit：
- 最终验证结果：
- 设计偏差与取舍：
- 本地预检视结论：
- design.md 覆盖度比对结论：

## 归档日期（基线）

2026-11-13
