# /get-user-permission支持按照项目级别获取-gateway适配_账号绑定/解绑 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/102
* **需求名称**: /get-user-permission支持按照项目级别获取-gateway适配_账号绑定/解绑
* **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
* **开发责任人**: zhuangzhiting
* **测试责任人**: dongsicheng

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

* [X] **功能自检测试**

> * **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
>* **目的：** 确保功能实现符合设计预期。
>* **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

---

## 3. 专项验证设计和执行详情

> 测试自检
>* [X] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果？
>* [X] **证据留存**: 关键测试（如性能、安全扫描）是否附带了截图或报告链接？

### 3.1 功能测试专项


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


---

