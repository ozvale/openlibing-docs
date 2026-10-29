# openLibing-发布管理：发布管理评审专家重名修复 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-platform-release/issues/79
* **需求名称**: openLibing-发布管理：发布管理评审专家重名修复
* **开发责任人**: disiqi
* **测试责任人**: dongsicheng
* **最终结论：**： 通过
* **测试维度** ：
* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**：
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项


**1.发布管理评审专家重名修复**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/79
* **步骤一**：进入发布管理-发布评审页面，并创建一个新的产品
* **预期结果**: 产品创建成功
* **测试结果**： Passed
* **步骤二**：进入发布评审详情，评审方式启用线上评审状态展示安全领域，下拉展开评审专家一栏
* **预期结果**: 展开评审专家下拉栏，每个评审专家名称选项在用户名之后增加了用户ID，用户名ID在账户中心中可查看，由于用户ID唯一，用于解决重名评审专家问题
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb1o00011mbjmdas&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
