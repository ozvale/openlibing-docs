# openLibing_web框架业务中增加无权限气泡提醒的功能 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/82
* **需求名称**: openLibing_web框架业务中增加无权限气泡提醒的功能
* **开发责任人**: wangfengzhu
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


**1.openLibing_web框架业务中增加无权限气泡提醒的功能**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/82
* **步骤一**：由管理员分配给新账号基础权限，后进入以下页面，检查按钮是否可操作  在关键项目管理： 编辑、成员管理 成员管理： 添加项目成员、编辑成员、删除成员 合法合规：社区管理 发布评审：发布模板、发布设置 漏洞视图：配置、同步漏洞 工具市场：创建工具、工具管理、我的流程
* **预期结果**: 按钮无法操作，并且按钮左侧出现提示气泡，显示缺少权限，并给予权限提示
* **测试结果**： Passed
* **步骤二**：管理员给新账号上述权限，再次检查按钮是否可操作
* **预期结果**: 按钮可以操作
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1n00011krdrmp2&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 页面无异常 | 1 | 0 | Pass |
