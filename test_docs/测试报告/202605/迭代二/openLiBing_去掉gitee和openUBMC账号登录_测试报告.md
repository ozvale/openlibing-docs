# openLiBing_去掉gitee和openUBMC账号登录 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **需求名称**: openLiBing_去掉gitee和openUBMC账号登录
* **开发责任人**: chentao
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


**1.查看IDE插件登录openlibing方式_不支持gitee和openUBMC账号登录**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **步骤一**：查看IDE插件支持的openlibing跳转登录方式
* **预期结果**: 不支持gitee和openUBMC账号登录
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1n00011dta1c8i&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
