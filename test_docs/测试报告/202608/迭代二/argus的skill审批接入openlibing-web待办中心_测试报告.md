# argus的skill审批接入openlibing-web待办中心 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/31
- **需求名称**: argus的skill审批接入openlibing-web待办中心
- **开发责任人**: wangfengzhu、chenanyang
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**
- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**：
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.在Argus的skill市场上传skill_待办中心展示对应的待审核内容和审核历史**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/31
- **步骤一**：检查用户是否具有argus skill市场审批人员角色
- **预期结果**: 无该角色
- **测试结果**： Passed
- **步骤二**：点击漏洞挖掘页面->选择skill市场->新建测试skill
- **预期结果**: skill新建成功进入待审批状态
- **测试结果**： Passed
- **步骤三**：给用户添加argus skill市场审批人员角色后，重新打开待办中心
- **预期结果**: 待我审批页面展示对应的申请列表
- **测试结果**： Passed
- **步骤四**：通过审核或者驳回对应的skill
- **预期结果**: 通过则在skill市场展示对应的上传skill，驳回则skill仍然为草稿状态
- **测试结果**： Passed
- **步骤五**：查看审批历史
- **预期结果**: 展示对应skill的审核历史
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1n00011l32l8mm&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 1        | 覆盖核心业务逻辑与 API 契约。 | 1      | 0        | Pass             |
