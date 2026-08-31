# openlibing-web页面url常驻携带projectId，支持url+projectId、url+projectName自动切换项目的能力 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/82
* **需求名称**: openlibing-web页面url常驻携带projectId，支持url+projectId、url+projectName自动切换项目的能力
* **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
* **开发责任人**: jiangzhichao
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


**1.openlibing-web页面url常驻携带projectId，支持url+projectId、url+projectName自动切换项目的能力**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/82
* **步骤一**：查看浏览器地址栏
* **预期结果**: 地址栏项目地址为url＋projectId
* **测试结果**： Passed
* **步骤二**：点击左上角切换项目
* **预期结果**: 地址栏仍为url＋projectId
* **测试结果**： Passed
* **步骤三**：分别输入projectId以及projectName进行项目切换。  1.输入存在的projectId或存在的projectName  2.输入不存在的projectId或不存在的projectName  3.输入存在但不是同一个项目的projectId和projectName  4.输入存在的projectId和不存在的projectName或存在的projectName和不存在的projectId
* **预期结果**: 1.切换到对应的项目  2.项目不切换  3.切换到projectName对应的项目  4.切换到存在的那个项目
* **测试结果**： Passed


---

