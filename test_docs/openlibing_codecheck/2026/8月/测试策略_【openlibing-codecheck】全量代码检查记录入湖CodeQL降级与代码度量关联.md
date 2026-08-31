# 代码检查模块-全量代码检查记录入湖 CodeQL 降级与代码度量关联 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/178
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/178
* **需求名称**: `/machine-api/v1/full-codecheck-record/list` 入湖接口 CodeQL 降级与代码度量 commit_id 精确关联
* **核心目标**:
  入湖消费方调用 `/machine-api/v1/full-codecheck-record/list` 时，原实现只查 `task_result_summary` 表；当项目未接入华为云 CodeCheck 该表无数据。本次在原查询无数据且入参含仓库定位字段时**降级走静态告警链路**（`static_alarm_scan_run` + `static_alarm_issue`）组装等价结果；因 CodeQL 法律风险**无条件排除 `tool = "CodeQL"` 记录**；`startTime`/`endTime` 按 `createdAt`/`updatedAt` 过滤；代码度量字段通过 `git_url + branch_name + commit_id` 三元组精确关联 coderepo 度量记录（机机接口 `/project-repo/internal/metrics/code/latest-by-commit/batch`，取 `detection_completed_at` 最新一条），未命中走默认值。涉及三仓联动：code-metrics-action（插件端新增 6 个度量字段 + commitId 上报）、openlibing-coderepo（commit_id 落库 + 机机接口）、openlibing-codecheck（降级组装）。
* **设计文档**: Issue #178 正文（内嵌完整设计：跨仓改动清单 + 62 字段映射表 + 度量关联算法）
* **开发责任人**: Chenmingxu
* **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

* [x] **功能自检测试**
> * **测试重点:** 降级触发条件（`task_result_summary` 无数据 + 至少一个仓库定位字段非空 → 走 `StaticAlarmSummaryOperation`；有数据走原路径）、CodeQL 记录无条件排除、`startTime`/`endTime` 按 `createdAt`/`updatedAt` 过滤（互相独立，只传一个不自动补）、出参 62 字段映射（50 个对接字段取值正确 + 12 个不对接字段置 null）、`repoId`/`projectName`/`hwProjectId` 反查逻辑。
> * **目的:** 确保降级路径触发与组装结果正确、字段映射与设计一致。
> * **触发条件:** 强制执行。

* [ ] **体验测试**
* [x] **集成测试**
> * **测试重点:** 三仓端到端联动——code-metrics-action 插件上报 6 个新度量字段 + commitId → coderepo 落库（`code_metrics_record.commit_id`）→ codecheck 降级查询经 Feign 调用 coderepo 机机接口 `POST /project-repo/internal/metrics/code/latest-by-commit/batch` 批量关联度量；机机接口批量入参校验（@Valid + @Size 1-100）、`status=0` 过滤、未命中项不返回。
> * **目的:** 验证跨仓链路数据流转正确。
> * **触发条件:** 需求标签含 `need_itest`。

* [ ] **安全与隐私测试**
* [x] **可靠性与韧性测试**
> * **测试重点:** 度量关联算法容错——三元组任一为空（常见 `commit_id` 缺失）跳过度量关联走默认值；同一 `(git_url, branch_name, commit_id)` 多条记录取 `detection_completed_at` 最新；未命中时度量字段默认值（数值 0/null、比率 "0"/null、metricInfo null、codeQuality/riskCoefficient 固定 100）；机机接口异常时降级查询不被阻断。
> * **目的:** 确保度量数据缺失场景下接口稳定返回合理默认值。
> * **触发条件:** 涉及核心 Core 服务变更，且架构设计含可靠性与韧性设计。

* [x] **可服务性与可观测性测试**
> * **测试重点:** 入湖消费方（数据湖侧）使用降级后接口拉取全量记录可用性；降级路径与原路径切换对消费方透明（响应结构不变）。
> * **目的:** 确保入湖链路在项目未接入华为云 CodeCheck 时不再缺数。
> * **触发条件:** 涉及对外机机接口变更。

* [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1. 降级触发条件验证**:
* 前置条件: 准备已接入华为云 CodeCheck 的项目（`task_result_summary` 有数据）与未接入的项目（无数据）
* 测试步骤:
    1. 调用 `/machine-api/v1/full-codecheck-record/list` 查询已接入项目，验证走原 `task_result_summary` 路径、结果与优化前一致
    2. 查询未接入项目且入参含仓库定位字段（projectName / repoName / repoUrl / gitUrl / projectId / repoIds 至少一个），验证返回非空结果（来自 `static_alarm_scan_run`）
    3. 未接入项目且入参无任何仓库定位字段，验证不走降级路径
* 预期结果: 降级触发条件精确命中，原路径行为零变化

**2. CodeQL 记录排除验证**:
* 前置条件: 存在 `tool = "CodeQL"` 与其他工具（如开源扫描器）的 `static_alarm_scan_run` 记录
* 测试步骤:
    1. 触发降级查询，验证返回结果中不含任何 `tool = "CodeQL"` 的扫描记录
    2. 验证 `tool .ne "CodeQL"` 条件无条件附加（即使仅查询 CodeQL 数据的入参组合）
* 预期结果: CodeQL 记录在降级结果中被完全排除（法律合规要求）

**3. 时间过滤验证**:
* 前置条件: 存在不同 createdAt/updatedAt 的扫描记录
* 测试步骤:
    1. 传 `startTime`，验证按 `static_alarm_scan_run.createdAt >= startTime` 过滤
    2. 传 `endTime`，验证按 `static_alarm_scan_run.updatedAt <= endTime` 过滤
    3. 只传其中一个，验证不自动补另一个
* 预期结果: 时间过滤口径正确，两个条件互相独立

**4. 出参字段映射验证**:
* 前置条件: 存在静态告警扫描记录及关联 issue、度量数据
* 测试步骤:
    1. 逐项校验 50 个对接字段：`id`/`date`/`dateTime`（耗时秒级）/`repoNameEn`/`executeTime`/`endTime`/`gitBranch`/`checkType`（固定 "source"）/`result`（issue_snapshot > 0 ? failed : pass）/`codeCheckStatus`（SUCCESS/FAILED/PARSING 映射）/`type`（"new"）/`issue`/`solve`/`ignore`（issue 表按 scan_run_id 聚合）/各 snapshot 计数字段（未就绪回退 issue 表聚合）/`repoUrl` 等
    2. 逐项校验 12 个不对接字段置 null（inReviewCount/invalidCount/commentRatio/fileDuplicationTotal/filesTotal/methodLines/methodsTotal/unsafeFunctionsCount/nonHeaderFileDuplicationRate/mrId/prId/mrUrl 等）
    3. 校验 `repoId`（projectId 反查 repo_info）、`projectName`（反查 project 表）、`hwProjectId`（反查 hw_project_info）反查不到时置 null
* 预期结果: 62 字段映射与设计映射表完全一致

### 3.2 集成测试专项

**5. 度量数据 commit_id 精确关联验证**:
* 前置条件: 插件已上报带 commitId 的度量记录，`code_metrics_record.commit_id` 已落库
* 测试步骤:
    1. 触发降级查询，验证度量字段（codeLine/codeLineTotal/commentLines/complexityCount/cyclomaticComplexityPerMethod/cyclomaticComplexityPerFile/duplicatedBlocks/duplicatedLines/duplicationRatio/fileDuplicationRatio/metricInfo）通过 `(repo_url, branch, commit_id)` 三元组精确关联
    2. 同一 commit 因扫描器重跑存在多条记录，验证取 `detection_completed_at` 最新一条
    3. 验证 coderepo 机机接口批量查询：入参 @Valid + @Size 1-100 校验、`status = 0` 过滤失败记录、未命中项不返回
    4. 验证旧单条接口 `/latest-by-commit` 与 `MachineApiCodeMetricsController` 已删除、无残留调用
* 预期结果: 度量关联精准，机机接口契约符合设计

### 3.3 可靠性与韧性测试专项

**6. 度量记录缺失与异常场景验证**:
* 前置条件: 可构造 commit_id 缺失、无度量记录、coderepo 接口异常场景
* 测试步骤:
    1. 三元组任一为空（如 `commit_id` 缺失），验证该 scan_run 跳过度量关联
    2. 未命中度量记录时，验证度量字段默认值：数值 0/null、`duplicationRatio`/`fileDuplicationRatio` 置 "0"/null、`metricInfo` 置 null、`codeQuality`/`riskCoefficient` 固定 100
    3. 模拟 coderepo 机机接口超时/异常，验证降级查询主体结果正常返回、度量字段走默认值不被阻断
* 预期结果: 各异常场景下接口稳定返回，默认值符合设计

### 3.4 可服务性与可观测性测试专项

**7. 入湖消费方可用性验证**:
* 前置条件: 数据湖消费方已对接
* 测试步骤:
    1. 消费方按原调用方式拉取未接入华为云 CodeCheck 项目的全量检查记录，验证可获取非空数据（此前为空）
    2. 验证响应结构与原接口一致，消费方无需改造
* 预期结果: 入湖数据不再缺失，接口变更对消费方透明

**8. 插件端新字段上报验证**:
* 前置条件: code-metrics-action 插件已升级
* 测试步骤:
    1. 流水线触发代码度量扫描，验证 `metrics_data_json` 新增 6 字段（codeLineTotal/commentLines/complexityCount/cyclomaticComplexityPerFile/duplicatedBlocks/duplicatedLines）取值口径正确（scc 汇总/LizardDetector/DuplicationDetector）
    2. 验证 commitId 透传（`ATOMGIT_SHA`，缺失时空串降级不阻断）
    3. 验证文件级明细 `code_metrics_file_detail.metrics_json` 新增 commentLines
* 预期结果: 插件上报链路字段完整、口径正确、异常降级不阻断
