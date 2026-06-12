# 昇腾社区版本看板，支持二进制license扫描 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/42
* **需求名称**: 昇腾社区版本看板，支持二进制license扫描
* **开发责任人**: musheng
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


**1.查看昇腾MindCluster社区项目合规页面中的二进制包级兼容性和二进制License合规性页签_页面正常展示数据**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/42
* **步骤一**：访问mindcluster社区下，合法合规中的项目合规页面
* **预期结果**: 页面正常显示
* **测试结果**： Passed
* **步骤二**：查看二进制包级兼容性页签，选择一个版本
* **预期结果**: 正常显示对应数据
* **测试结果**： Passed
* **步骤三**：查看二进制License合规性页签，选择一个版本
* **预期结果**: 正常显示对应数据
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1n00011f1ar6ok&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
