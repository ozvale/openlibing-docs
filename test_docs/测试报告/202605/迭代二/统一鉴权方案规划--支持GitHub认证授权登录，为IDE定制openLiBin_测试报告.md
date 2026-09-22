# 统一鉴权方案规划--支持GitHub认证授权登录，为IDE定制openLiBing登录页面 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **需求名称**: 统一鉴权方案规划--支持GitHub认证授权登录，为IDE定制openLiBing登录页面
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


**1.使用github登录openlibing_登录成功**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **步骤一**：在openlibing首页通过github登录
* **预期结果**: 成功调整openlibing页面，登录成功
* **测试结果**： Passed
* **步骤二**：在账号设置页面查看账号基本信息
* **预期结果**: 明确登录平台、用户名等字段正确反映github信息
* **测试结果**： Passed
* **步骤三**：在账号设置页面绑定github第三方账号
* **预期结果**: 在账号绑定中显示github内容，绑定成功
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dtad8v9&detail=result


**2.查看IDE插件登录openlibing方式_支持github账号登录**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **步骤一**：查看IDE插件登录openlibing方式
* **预期结果**: 支持github账号登录
* **测试结果**： Passed
* **步骤二**：在IDE中使用github登录
* **预期结果**: 登录成功
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dtag394&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 2 | 覆盖核心业务逻辑与 API 契约。 | 2 | 0 | Pass |
