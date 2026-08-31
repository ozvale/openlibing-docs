# summary-multi-repo-export（CodeCheck 子页面仓库多选与列表全量导出）

## 需求背景

门禁检查与版本级检查两个页面的 CodeCheck 子页面，仓库下拉筛选框目前只支持单选代码仓，用户查看多仓库汇总情况时需逐仓查询；列表无导出能力，用户无法离线分析全量检查数据。

业务 Issue：https://gitcode.com/openlibing/openlibing-codecheck/issues/174

## 功能描述

> 范围变更（2026-08-25）：用户确认取消"列表全量导出"需求，仅保留仓库多选筛选。

- 做：
  1. 门禁检查 / 版本级检查页面 CodeCheck 子页的仓库下拉筛选框支持多选代码仓，列表按所选仓库集合过滤；多选时分支下拉展示所选仓库分支的去重并集（分支仍单选）。
- 不做：
  - 列表全量导出（已取消）
  - 分支多选
  - 导出中心 / 导出记录页面
  - AntiPoison（反投毒）子页改造

## 验收标准

- [ ] 门禁检查 CodeCheck 子页仓库下拉可多选，列表按仓库集合过滤，单选场景向后兼容
- [ ] 版本级检查 CodeCheck 子页仓库下拉可多选，列表按仓库集合过滤，单选场景向后兼容
- [ ] 多选仓库时分支下拉展示所选仓库分支的去重并集，分支筛选仍生效

## 影响范围

- openlibing-codecheck：QuerySummaryModel 查询模型（+repoNames）、IncSummaryOperation / CommonOperation 查询条件
- openlibing-web：CodeCheckPages 的 shared.ts / GatingCheck.vue / StaticCheck.vue / IncrementCheckList.vue / StaticCheckList.vue

## 模式结论（Phase 0，2026-08-25 范围缩小后更新）

```yaml
workflow_mode: Standard
scope_snapshot: >
  跨 openlibing-codecheck + openlibing-web 两仓；仅查询参数扩展（repoNames 集合 +
  前端两页面下拉多选交互）；无新增接口、无数据模型变更、无异步基建
decision_basis: 范围缩小后预计 ~120 行；无关键系统边界变化；跨仓但无接口/数据/安全影响
confirmed_by: user（导出取消指令，模式降级 Standard 待确认）
```
