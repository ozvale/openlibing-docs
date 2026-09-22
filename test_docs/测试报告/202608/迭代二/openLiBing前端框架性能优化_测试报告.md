# openLiBing前端框架性能优化 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/82
* **需求名称**: openLiBing前端框架性能优化
* **开发责任人**: jiangzhichao
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


**1.openLiBing前端框架性能优化**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/82
* **步骤一**：进入系统，打开浏览器开发者工具，进入网络标签，并刷新检测接口耗时
* **预期结果**: 比对发版前后，发版后最长耗时，比发版前最短耗时小，整体调用接口耗时减少
* **测试结果**： Passed
* **步骤二**：任意进入界面
* **预期结果**: 页面显示正常显示，无异常
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1v00011kqkpe4d&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 页面无异常 | 1 | 0 | Pass |
