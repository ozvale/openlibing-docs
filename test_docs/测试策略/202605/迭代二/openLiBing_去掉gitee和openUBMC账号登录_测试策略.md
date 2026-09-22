# openLiBing_去掉gitee和openUBMC账号登录 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **需求名称**: openLiBing_去掉gitee和openUBMC账号登录
* **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
* **开发责任人**: chentao
* **测试责任人**: caolongheng

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


**1.查看IDE插件登录openlibing方式_不支持gitee和openUBMC账号登录**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-gateway/issues/97
* **步骤一**：查看IDE插件支持的openlibing跳转登录方式
* **预期结果**: 不支持gitee和openUBMC账号登录
* **测试结果**： Passed


---

