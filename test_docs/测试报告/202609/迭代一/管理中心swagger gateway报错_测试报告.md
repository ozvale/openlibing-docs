# 管理中心swagger gateway报错 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/102
* **需求名称**: 管理中心swagger gateway报错
* **开发责任人**: chentao
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


**1.管理中心swagger gateway报错**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/102
* **步骤一**：点击右上角头像进入管理中心
* **预期结果**: 进入管理中心
* **测试结果**： Passed
* **步骤二**：在管理中心-权限管理-swagger接口里切换至openlibing-gateway
* **预期结果**: gateway页面不报错，正常显示，可操作，无异常
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb1v00011m9783th&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
