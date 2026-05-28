# openlibing_支持在无登录页面可以手动触发登录，添加登录按钮在客服插件下方 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **需求名称**: openlibing_支持在无登录页面可以手动触发登录，添加登录按钮在客服插件下方
* **开发责任人**: ningxinlong
* **测试责任人**: caolongheng
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


**1.使用无登录页面访问openlibing_自动授权登录**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **步骤一**：在公开仓如openlibing-web代码仓，通过gitcode流水线门禁链接访问openlibing
* **预期结果**: 正常访问页面，进行相关操作如执行流水线时启动调整授权
* **测试结果**： Passed
* **步骤二**：在私仓如openlibing-cicd代码仓，通过gitcode流水线门禁链接访问openlibing
* **预期结果**: 自动调整授权登录后正常访问页面
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1n00011dtcvaol&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
