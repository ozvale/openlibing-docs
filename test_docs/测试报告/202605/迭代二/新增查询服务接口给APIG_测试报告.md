# 新增查询服务接口给APIG 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **需求名称**: 新增查询服务接口给APIG
* **开发责任人**: linyapeng
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


**1.使用APIG调用接口_返回内容匹配gateway接口返回内容**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **步骤一**：使用APIG调用接口 openlibing-framework/manage/feedback/getfeedback?pageNum=1&pageSize=10
* **预期结果**: 返回内容匹配gateway接口返回内容
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1o00011denkcj4&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
