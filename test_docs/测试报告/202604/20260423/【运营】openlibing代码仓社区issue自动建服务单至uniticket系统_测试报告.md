# 【运营】openlibing代码仓社区issue自动建服务单至uniticket系统 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/18
- **需求名称**: openlibing代码仓社区issue自动建服务单至uniticket系统
- **开发责任人**: lizelin
- **测试责任人**: zhaoyanzhen
- **最终结论：**： 通过

* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**：
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.通过接口给指定代码仓配置webhook**
* **用例编号**:397
* 前置条件： 创建测试仓库，将openLiBingCi设置为维护者角色
* 测试步骤：
  1. 调用新增接口/openlibing-framework/manage/ticketIssue/addRepoWebhookCi，给指定仓库配置webhook
* 预期结果：
  * webhook创建成功
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011af941db&case_id=vb1v00011auel6vl&detail=base

**2. 新增issue后UniTicket平台同步创建服务单**:
* **用例编号**:394
* 前置条件： 测试仓库需要将openLiBingCi设置为维护者角色
* 测试步骤：
  1. 使用已绑定w3的gitcode账号在测试仓创建issue，添加infra-tooling标签，查看UniTicket平台，查看工单情况
  2. 使用未绑定w3的gitcode账号在测试仓创建issue，添加infra-tooling标签，查看UniTicket平台，查看工单情况
* 预期结果：
  * 工单创建成功，标题、内容等与issue一致，创建人工号为操作人工号
  * 工单创建成功，标题、内容等与issue一致，创建人工号为webhook默认配置工号
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011af941db&case_id=vb1v00011aue4k4o&detail=base


**3. 已有issue新增infra-tooling标签，UniTicket平台同步创建服务单**:
* **用例编号**:395
* 前置条件： 测试仓库将openLiBingCi设置为维护者角色，且仓库已有未添加infra-tooling标签的issue
* 测试步骤：
  1. 使用已绑定w3的gitcode账号在测试仓已有的issue，添加infra-tooling标签，查看是否有工单同步创建，创建人是指定w3账号。
  2. 使用未绑定w3的gitcode账号在测试仓已有issue，添加infra-tooling标签，查看是否有工单同步创建，创建人是webhook配置的默认账号
* 预期结果：
  * 工单创建成功，标题、内容等与issue一致，创建人工号为操作人工号
  * 工单创建成功，标题、内容等与issue一致，创建人工号为webhook默认配置工号
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011af941db&case_id=vb1o00011auebcnu&detail=base



**4. 已有infra-tooling标签的issue移除并重新添加标签，查看UniTicket平台同步情况**:
* **用例编号**:396
* 前置条件： 测试仓库将openLiBingCi设置为维护者角色，且操作仓库已有添加infra-tooling标签的issue
* 测试步骤：
  1. 在测试仓已有的issue，移除infra-tooling标签
  2. 查看webhook情况
  3. 重新添加infra-tooling标签
  4. 查看webhook情况
* 预期结果：
  * issue标签移除成功
  * webhook返回code为500，失败信息：The label of the issue is incorrect
  * issue标签重新添加成功
  * webhook返回code为500，失败信息中会说明是哪个仓库哪个issueid，already exists
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011af941db&case_id=vb1o00011auehp9a&detail=base
---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                                                  | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|----------|------|----------------------------------------------------------|-----|------|----------------|
| **功能测试** | 4    | 配置webhook、新增issue与服务单同步、已有issue与服务单同步、已有服务单issue变更不影响服务的 | 4   | 0    | Pass           |
