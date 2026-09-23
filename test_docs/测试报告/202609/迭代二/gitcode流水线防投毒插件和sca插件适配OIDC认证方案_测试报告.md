# gitcode流水线防投毒插件和sca插件适配OIDC认证方案 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/73
* **需求名称**: gitcode流水线防投毒插件和sca插件适配OIDC认证方案
* **开发责任人**: musheng
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


**1.gitcode流水线防投毒插件和sca插件适配OIDC认证方案**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/73
* **步骤一**：任意在某个仓库中提交一个PR
* **预期结果**: PR提交后，提交流水线开始执行
* **测试结果**： Passed
* **步骤二**：进入Actions页面，查看两条流水线malicious-code-pr-scan和sca-pr-scan流水线的执行结果
* **预期结果**: 执行结果中存在“OIDC ID Token 申请成功（Actions 兼容流水线 OIDC 接口）”等内容，意味着执行成功
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb2100011n8ges2h&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 在漏洞挖掘列表页中无法操作修改漏洞的确认状态和修复状态，仅能查看漏洞信息。在0day漏洞对应的条目中才能同步修改漏洞挖掘的状态 | 1 | 0 | Pass |
