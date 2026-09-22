# #1 [欧拉社区邮件通知新增责任团队统计看板] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/8
* **需求名称**: 欧拉社区邮件通知新增责任团队统计看板
* **开发责任人**: wurq
* **测试责任人**: qq_42806737
* **最终结论：**： 
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

**1.通知邮件中新增“责任团队CVE数据汇总”表**:在邮件中查找“责任团队CVE数据汇总”表，查看表格中的漏洞数据
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/8
* **用例链接**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg

**2.通知邮件中新增“未闭环漏洞统计”表**:在邮件中查找“未闭环漏洞统计”表，查看表格中的漏洞数据
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/8
* **用例链接**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg

**3.通知邮件中删除“近两月待修复漏洞汇总”表**:在邮件中查找“近两月待修复漏洞汇总”表
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/8
* **用例链接**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg



---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 3    | 覆盖核心业务逻辑与 API 契约。   | 3   | 0    | Pass           |

---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| |   |     |          |
