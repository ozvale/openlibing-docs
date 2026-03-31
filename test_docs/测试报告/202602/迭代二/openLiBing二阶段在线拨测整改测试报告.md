# #1 [openLiBing二阶段在线拨测整改] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-ai/issues/12
* **需求名称**: openLiBing二阶段安全与隐私整改
* **开发责任人**: zouzelan
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

**1.管理中心查看各个服务的swagger接口信息**:查看各个服务swagger接口信息
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-ai/issues/12
* **预期结果**:各个服务模块增加swagger接口信息，且各关键接口通过tag进行标识
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb21000116ge20pn&detail=base

**2.普通用户查看swagger接口页面**：普通用户权限访问swagger接口页面，检查是否访问成功
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-ai/issues/12
* **预期结果**:普通用户访问swagger接口页面失败
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1v000116ltebuo&detail=base


---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 2    | 覆盖核心业务逻辑与 API 契约。   | 2   | 0    | Pass           |
| **体验测试**    | 0    | 判定产品是否能让用户快速的接受和使用。 | 0   | 0    | /              |
| **集成测试**    | 0    | 跨组件调用及上下游数据流转。      | 0   | 0    | /              |
| **安全与隐私测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
| **可靠性与韧性测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| **[Bug-#01]** | xxx  | 中    | 修复               |
