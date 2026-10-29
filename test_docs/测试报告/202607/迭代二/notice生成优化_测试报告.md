# notice生成优化 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/54
* **需求名称**: notice生成优化
* **开发责任人**: 穆胜 m30082367
* **测试责任人**: 董思诚 d30085271
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


**1.notice生成优化**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/54
* **步骤一**：使用postman请求接口，传入给定的参数
* **预期结果**: 返回成功执行结果
* **测试结果**： Passed
* **步骤二**：进入openlibing华为云，并进入控制台，搜索obs，进入对象存储服务obs
* **预期结果**: 进入obs页面
* **测试结果**： Passed
* **步骤三**：在obs的列表页中，点击notice-beta
* **预期结果**: 进入notice-beta文件夹
* **测试结果**： Passed
* **步骤四**：进入其中一个文件，并下载merged-Readme.opensource文件，检查内容是否包含入参里传入的软件
* **预期结果**: 文件包含入参里传入的软件
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb2100011h4niej2&case_id=vb1o00011it15oo7&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
