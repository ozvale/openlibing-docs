# notice自动生成 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/42
* **需求名称**: notice自动生成
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


**1.调用notice生成接口_obs桶中出现对应的opensource文件**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/42
* **步骤一**：调用notice生成接口，传入代码仓、语言、依赖包列表参数（下载地址、版本、名称）
* **预期结果**: 在notice-beta的OBS桶中生成一个代码仓+时间戳命名的opensource文件，文件内容展示了所有传入依赖包的copyright和license信息
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&detail=result&case_id=vb1o00011gakcm3g

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
