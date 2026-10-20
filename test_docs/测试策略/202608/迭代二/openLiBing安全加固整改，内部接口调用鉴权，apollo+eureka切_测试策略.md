# openLiBing安全加固整改，内部接口调用鉴权，apollo+eureka切换华为云CSE服务，命令执行公共组件 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/84
* **需求名称**: openLiBing安全加固整改，内部接口调用鉴权，apollo+eureka切换华为云CSE服务，命令执行公共组件
* **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
* **开发责任人**: disiqi musheng linyapeng zhuangzhiting lidebing wangxing xiaofeng tangyunhui chentao
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


**1.plateform-release、sca、framework、anti-position、common、vulnerability等模块切换华为云CSE服务，指导各个服务修改相关配置**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/84
* **步骤一**：进入华为云控制台，搜索cse，进入注册配置中心，选择到openlibing-nacos-prod实体，配置管理-配置列表，切换命名空间至openlibing-prod
* **预期结果**: 列表中存在各项目的配置项
* **测试结果**： Passed
* **步骤二**：登录openlibing，进入任意页面
* **预期结果**: 页面无异常
* **测试结果**： Passed


**2.plateform-release、sca、framework、anti-position、common、vulnerability等模块安全加固整改，内部接口调用请求头新增静态token**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/84
* **步骤一**：登录openlibing，进入任意页面
* **预期结果**: 页面无异常，无出现任何鉴权问题
* **测试结果**： Passed


**3.common修复重明平台发掘的漏洞及风险配置项修改，openLiBing安全加固，提供安全设计Skill，加入蓝区开发流程**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/84
* **步骤一**：登录openlibing，进入任意页面
* **预期结果**: 页面无异常，无出现任何鉴权问题
* **测试结果**： Passed


---

