# #1 [openlibing漏洞看板SLO管理规则计算调整] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/11
* **需求名称**: openlibing漏洞看板SLO管理规则计算调整
* **开发责任人**: wurq
* **测试责任人**: qq_42806737
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

**1.openlibing的SLO计算规则符合开源漏洞管理策略—配置中心**:查看配置中心中的SLO配置详情
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/11
* **用例链接**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg

**2.openlibing的SLO计算规则符合开源漏洞管理策略—openLiBing平台**:分别计算各级别漏洞的SLO时间（Issue计划完成时间-修复起始时间）
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/11
* **用例链接**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg

**3.更改修复起始时间，issue计划完成时间随之刷新**:选择漏洞，修改修复起始时间
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/11
* **用例链接**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg



---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 3    | 覆盖核心业务逻辑。   | 3   | 0    | Pass           |
          
---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
|  |   |    |               |
