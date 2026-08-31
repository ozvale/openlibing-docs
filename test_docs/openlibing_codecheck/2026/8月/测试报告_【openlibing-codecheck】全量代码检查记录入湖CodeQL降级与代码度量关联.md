# 代码检查模块-全量代码检查记录入湖 CodeQL 降级与代码度量关联 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/178
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/178
* **需求名称**: `/machine-api/v1/full-codecheck-record/list` 入湖接口 CodeQL 降级与代码度量 commit_id 精确关联
* **开发责任人**: Chenmingxu
* **测试责任人**: 徐愚冰
* **最终结论:**： 通过
* **测试维度** :
* [x] **功能自检测试**
* [ ] **体验测试**
* [x] **集成测试**
* [ ] **安全与隐私测试**
* [x] **可靠性与韧性测试**
* [x] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1. 降级触发条件验证**:
* 预期结果: 降级触发条件精确命中，原路径行为零变化
* **测试结果**： Passed
* **证明截图**: xxx

**2. CodeQL 记录排除验证**:
* 预期结果: `tool = "CodeQL"` 记录在降级结果中被完全排除
* **测试结果**： Passed
* **证明截图**: xxx

**3. 时间过滤验证**:
* 预期结果: `startTime`/`endTime` 按 `createdAt`/`updatedAt` 正确过滤，两条件互相独立
* **测试结果**： Passed
* **证明截图**: xxx

**4. 出参字段映射验证**:
* 预期结果: 62 字段映射（50 对接 + 12 置 null）与设计映射表完全一致，反查不到置 null
* **测试结果**： Passed
* **证明截图**: xxx

### 2.2 集成测试专项

**5. 度量数据 commit_id 精确关联验证**:
* 预期结果: 度量字段经三元组精确关联取最新一条，机机接口批量查询契约符合设计
* **测试结果**： Passed
* **证明截图**: xxx

### 2.3 可靠性与韧性测试专项

**6. 度量记录缺失与异常场景验证**:
* 预期结果: 各异常场景下接口稳定返回，默认值符合设计
* **测试结果**： Passed
* **证明截图**: xxx

### 2.4 可服务性与可观测性测试专项

**7. 入湖消费方可用性验证**:
* 预期结果: 未接入华为云 CodeCheck 项目入湖数据不再缺失，接口变更对消费方透明
* **测试结果**： Passed
* **证明截图**: xxx

**8. 插件端新字段上报验证**:
* 预期结果: 插件 6 个新度量字段 + commitId 上报口径正确、异常降级不阻断
* **测试结果**： Passed
* **证明截图**: xxx

## 3. 测试结果汇总表

| 测试维度 | 用例总数 | 重点测试点描述 | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| --- | --- | --- | --- | --- | --- |
| **功能测试** | 4 | 降级触发条件、CodeQL 排除、时间过滤、62 字段映射 | 4 | 0 | Pass |
| **集成测试** | 1 | commit_id 度量精确关联 + coderepo 机机接口批量查询 | 1 | 0 | Pass |
| **可靠性与韧性测试** | 1 | 度量缺失默认值、三元组为空跳过、机机接口异常不阻断 | 1 | 0 | Pass |
| **可服务性与可观测性测试** | 2 | 入湖消费方可用性、插件端新字段上报链路 | 2 | 0 | Pass |

## 4. 遗留问题记录

| 序号 | 问题描述 | 严重程度 | 负责人 | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## 5. 补充说明

* 本需求为跨仓联动改造（code-metrics-action + openlibing-coderepo + openlibing-codecheck），设计内容以 Issue #178 正文内嵌设计为准（正文引用的 `spec/openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback/design.md` 尚未合入 docs 仓 master）；coderepo 侧改动（commit_id 落库 + 机机接口）随 openlibing-coderepo#159 交付，本测试文档从端到端视角统一覆盖。
* 编译/单测基线：code-metrics-action npm test 12/12、openlibing-coderepo mvn test 25/25、openlibing-codecheck mvn compile BUILD SUCCESS。
* `newCount` 语义已降级为复用 `issue_snapshot`（原 `new_issue_count` 字段被移除），验证时按此口径判定。
