# gitcode sca版本扫描插件开发 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/73
* **需求名称**: gitcode sca版本扫描插件开发
* **开发责任人**: musheng
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


**1.gitcode sca版本扫描插件开发**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/73
* **步骤一**：任意选择一个gitcode仓库，并创建自己分支，依据malicious-code-scan-action中的code-version-scan-action文件夹下的文档，添加yml文件，并手动执行流水线
* **预期结果**: 在流水线执行结果中的下方，生成SCA合法合规版本扫描结果，结果为通过
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb1o00011m9lav5b&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
