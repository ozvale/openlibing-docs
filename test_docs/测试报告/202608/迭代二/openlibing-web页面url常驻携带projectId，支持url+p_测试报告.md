# openlibing-web页面url常驻携带projectId，支持url+projectId、url+projectName自动切换项目的能力 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/82
* **需求名称**: openlibing-web页面url常驻携带projectId，支持url+projectId、url+projectName自动切换项目的能力
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


**1.openlibing-web页面url常驻携带projectId，支持url+projectId、url+projectName自动切换项目的能力**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/82
* **步骤一**：查看浏览器地址栏
* **预期结果**: 地址栏项目地址为url＋projectId
* **测试结果**： Passed
* **步骤二**：点击左上角切换项目
* **预期结果**: 地址栏仍为url＋projectId
* **测试结果**： Passed
* **步骤三**：分别输入projectId以及projectName进行项目切换。  1.输入存在的projectId或存在的projectName  2.输入不存在的projectId或不存在的projectName  3.输入存在但不是同一个项目的projectId和projectName  4.输入存在的projectId和不存在的projectName或存在的projectName和不存在的projectId
* **预期结果**: 1.切换到对应的项目  2.项目不切换  3.切换到projectName对应的项目  4.切换到存在的那个项目
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb2100011lb3kbsn&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 页面无异常 | 1 | 0 | Pass |
