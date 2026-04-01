# openLiBing提供通用版本发布工程平台，支撑社区版本在线发布，流程可追溯 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-platform-release/issues/23
* **需求名称**: openlibing-platform-release 发布评审功能
* **开发责任人**: lidebin
* **测试责任人**: fanshijing
* **最终结论：**: 通过
* **测试维度** :
* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.发布评审通过邮件通知**: 验证评审通过后邮件通知功能

* **对应task(issueID)链接:** #344
* **前置条件**: openLiBing系统正常运行
* **测试步骤**:
  1. 创建发布评审单
  2. 对发布评审单进行评审通过操作
  3. 查看评审通过邮件
* **预期结果**:
  1. 成功创建发布评审单
  2. openLiBing邮件通知创建人评审单被通过
  3. 提供评审项评审结果、意见、评审人和超链接
* **测试结果**: Passed
* **执行时间**: 2026/03/31 11:01:42 GMT+08:00
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1s118uvh94rc8i&detail=base

**2.发布评审驳回邮件通知**: 验证评审驳回后邮件通知功能

* **对应task(issueID)链接:** #343
* **前置条件**: openLiBing系统正常运行
* **测试步骤**:
  1. 创建发布评审单
  2. 对发布评审单进行评审驳回操作
  3. 查看评审驳回邮件
* **预期结果**:
  1. 成功创建发布评审单
  2. openLiBing邮件通知创建人评审单被驳回
  3. 提供评审项评审结果、意见、评审人和超链接
* **测试结果**: Passed
* **执行时间**: 2026/03/31 11:01:23 GMT+08:00
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1s000118uvh94r&detail=base

**3.多发布制品评审信息关联**: 验证多个发布制品对应多个评审信息

* **对应task(issueID)链接:** #342
* **前置条件**: openLiBing系统正常运行
* **测试步骤**:
  1. 创建包含多个发布制品的发布评审单
  2. 对发布评审单进行评审操作
* **预期结果**:
  1. 成功创建发布评审单
  2. 每个发布制品都有对应的发布结果
* **测试结果**: Passed
* **执行时间**: 2026/03/30 22:00:04 GMT+08:00
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb21000118uv5lnu&detail=base

### 2.2 体验测试专项

> **不涉及应直接删除**

### 2.3 集成测试专项

> **不涉及应直接删除**

### 2.4 安全与隐私测试专项

> **不涉及应直接删除**

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 3    | 发布评审流程、邮件通知机制、多制品评审关联。   | 3   | 0    | Pass           |

---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| 无 | 无 | - | - |