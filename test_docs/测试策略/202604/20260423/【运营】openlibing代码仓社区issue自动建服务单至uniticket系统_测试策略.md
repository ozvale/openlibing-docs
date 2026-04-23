# 【运营】openlibing代码仓社区issue自动建服务单至uniticket系统 测试策略

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/18
- **需求名称**: openlibing代码仓社区issue自动建服务单至uniticket系统示
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: lizelin
- **测试责任人**: zhaoyanzhen

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
> - **目的：** 确保功能实现符合设计预期。
> - **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

> 参考测试设计方向
>
> - API 语义验证：验证 HTTP 状态码（2xx, 4xx, 5xx）的使用是否符合 RESTful 规范。
> - 边界与非法输入：验证大数据量、空字段、特殊字符及非法 JSON 格式的拦截能力。
> - 业务状态机闭环：验证资源从“创建中”到“运行中”再到“已释放”的全生命周期逻辑。

**1. 通过接口给指定代码仓配置webhook**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/18
- **前置条件**:  创建测试仓库，将openLiBingCi设置为维护者角色
- **步骤一**: 调用新增接口/openlibing-framework/manage/ticketIssue/addRepoWebhookCi，给指定仓库配置webhook
- **预期结果**: webhook创建成功。

**2. 新增issue在UniTicket平台同步创建服务单**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/18
- **前置条件**: 测试仓库需要将openLiBingCi设置为维护者角色
- **步骤一**: 使用已绑定w3的gitcode账号在测试仓创建issue，添加infra-tooling标签，查看UniTicket平台，查看工单情况
- **预期结果**: 工单创建成功，标题、内容等与issue一致，创建人工号为操作人工号
- **步骤二**: 使用未绑定w3的gitcode账号在测试仓创建issue，添加infra-tooling标签，查看UniTicket平台，查看工单情况
- **预期结果**: 工单创建成功，标题、内容等与issue一致，创建人工号为webhook默认配置工号


**3. 已有issue新增infra-tooling标签，UniTicket平台同步创建服务单**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/18
- **前置条件**: 测试仓库将openLiBingCi设置为维护者角色，且仓库已有未添加infra-tooling标签的issue
- **步骤一**: 使用已绑定w3的gitcode账号在测试仓已有的issue，添加infra-tooling标签，查看是否有工单同步创建，创建人是指定w3账号。
- **预期结果**: 工单创建成功，标题、内容等与issue一致，创建人工号为操作人工号
- **步骤二**:使用未绑定w3的gitcode账号在测试仓已有issue，添加infra-tooling标签，查看是否有工单同步创建，创建人是webhook配置的默认账号。
- **预期结果**: 工单创建成功，标题、内容等与issue一致，创建人工号为webhook默认配置工号



**4. 已有infra-tooling标签的issue移除并重新添加标签，查看UniTicket平台同步情况**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/18
- **前置条件**: 测试仓库将openLiBingCi设置为维护者角色，且操作仓库已有添加infra-tooling标签的issue
- **步骤一**:在测试仓已有的issue，移除infra-tooling标签
- **预期结果**: issue标签移除成功
- **步骤二**:查看webhook情况
- **预期结果**: webhook返回code为500，失败信息：The label of the issue is incorrect
- **步骤三**:重新添加infra-tooling标签
- **预期结果**: issue标签重新添加成功
- **步骤四**:查看webhook情况
- **预期结果**: webhook返回code为500，失败信息中会说明是哪个仓库哪个issueid，already exists