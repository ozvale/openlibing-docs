# /get-user-permission支持按照项目级别获取-gateway适配_账号绑定/解绑 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/102
* **需求名称**: /get-user-permission支持按照项目级别获取-gateway适配_账号绑定/解绑
* **开发责任人**: zhuangzhiting
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


**1./get-user-permission支持按照项目级别获取-gateway适配_账号绑定/解绑**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/102
* **步骤一**：点击右上角进入账号设置
* **预期结果**: 进入账号设置页面
* **测试结果**： Passed
* **步骤二**：使用F12打开开发者工具，检查/get-user-permission接口返回的账号基础信息字段
* **预期结果**: 显示账号的基础信息字段，并记录绑定/解绑前的信息
* **测试结果**： Passed
* **步骤三**：点击账号绑定下中进行绑定第三方账号。依次绑定uniportal账号、gitee账号、gitcode账号
* **预期结果**: 账号的基础信息字段，haveUniportal字段变为true，gitcodeLogin、gitcodeName变为绑定gitcode的用户名和用户账号名，giteeLogin、giteeName变为绑定gitee用户名和用户账号名
* **测试结果**： Passed
* **步骤四**：点击账号绑定列表中的，解除绑定按钮，依次解绑上一步绑定的账号
* **预期结果**: 账号的基础信息字段，haveUniportal字段变为false，gitcodeLogin、gitcodeName置为空，giteeLogin、giteeName变为空
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb2100011mu94nv4&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 在漏洞挖掘列表页中无法操作修改漏洞的确认状态和修复状态，仅能查看漏洞信息。在0day漏洞对应的条目中才能同步修改漏洞挖掘的状态 | 1 | 0 | Pass |
