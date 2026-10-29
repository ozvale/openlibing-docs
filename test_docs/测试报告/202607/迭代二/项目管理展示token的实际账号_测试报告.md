# 项目管理展示token的实际账号 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/61
* **需求名称**: 项目管理展示token的实际账号
* **开发责任人**: liting、zhuangzhiting
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


**1.点击编辑项目按钮_展示 token 的实际账号**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/61
* **步骤一**：1、点击新建项目，勾选对应代码托管平台（gitee，gitcode，github） 2、填写对应的账号令牌并创建项目
* **预期结果**: 1、只有账号令牌为必填项 2、项目创建成功
* **测试结果**： Passed
* **步骤二**：1、编辑测试项目，查看表单 2、更换对应账户的名称
* **预期结果**: 1、对应的第三方平台的账号用户名根据token自动回写， 账号用户名不可编辑 2、回显的用户名同步更新
* **测试结果**： Passed
* **步骤三**：1、编辑弹窗中切换「是否对接 Gitee」、「是否对接 GitCode」、「是否对接 GitHub」开关
* **预期结果**: 1、相关表单项正确显示/隐藏。 2、对接平台的项目，打开编辑弹窗后开关状态回显正确
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb2100011h4niej2&case_id=vb1n00011it2guv4&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
