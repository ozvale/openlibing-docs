# GitCode 流水线代码化开发插件支持防投毒门禁检查插件 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/43
* **需求名称**: GitCode 流水线代码化开发插件支持防投毒门禁检查插件
* **开发责任人**: lidebing
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


**1.在测试代码仓库Action下手动触发Anti-Poison PR Scan扫描流水线_得到扫描结果**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/43
* **步骤一**：在测试代码仓库 Actions下填写对应的参数手动运行SCA PR Scan扫描流水线
* **预期结果**: 流水线进入运行状态，运行结束后状态变为成功或者失败（代表扫描的结果是否存在问题）
* **测试结果**： Passed
* **步骤二**：查看运行结果
* **预期结果**: Anti-Poison PR Scan summary中正确展示对应的扫描结果
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
