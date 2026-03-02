# #1 [全链路https改造] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-cicd/issues/21
* **需求名称**: 全链路https改造
* **开发责任人**: wanxiaochuan
* **测试责任人**: alice5426_qing
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

**1.访问Apollo配置中心**: 查看apollo配置中心，查看访问链接
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-cicd/issues/21
* **预期结果**: Apollo配置中心通过https访问，且访问成功
* **测试结果**：Passed
* **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1v0001152o51s8&detail=result

**2.查看openlibing各服务功能**: 访问openlibing平台，查看各模块功能，检查功能是否可用
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-cicd/issues/21
* **预期结果**: openlibing各模块功能可用，无异常
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1o0001152oqv77&detail=result

**2.mysql、mongodb、redis使用TLS/SSL安全传输协议**: 查看mysql、mongodb、redis的安全配置，是否启用SSl
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-cicd/issues/21
* **预期结果**: mysql、mongodb、redis已启动SSL安全传输协议
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1n0001152sc0bm&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 3    | 覆盖核心业务逻辑与 API 契约。   | 3   | 0    | Pass           |
| **体验测试**    | 0    | 判定产品是否能让用户快速的接受和使用。 | 0   | 0    | /              |
| **集成测试**    | 0    | 跨组件调用及上下游数据流转。      | 0   | 0    | /              |
| **安全与隐私测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
| **可靠性与韧性测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| **[Bug-#01]** | xxx  | 中    | 修复               |
