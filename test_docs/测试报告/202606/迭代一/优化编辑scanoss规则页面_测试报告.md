# 优化编辑scanoss规则页面 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/42
* **需求名称**: 优化编辑scanoss规则页面
* **开发责任人**: jiangzhichao
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


**1.scanoss规则页面体验优化**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/42
* **步骤一**：进入社区管理页面选择某个代码仓
* **预期结果**: 展示对应的scanoss屏蔽规则列表
* **测试结果**： Passed
* **步骤二**：查看编辑SCANOSS规则按钮
* **预期结果**: 名称更改为编辑SCANOSS屏蔽规则按钮
* **测试结果**： Passed
* **步骤三**：点击编辑SCANOSS规则按钮
* **预期结果**: 弹窗标题显示编辑SCANOSS屏蔽规则按钮
* **测试结果**： Passed
* **步骤四**：点击添加按钮
* **预期结果**: 弹窗标题显示添加SCANOSS屏蔽规则，对应的表单的placeholder展示说明文字
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1n00011f19p6ve&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
