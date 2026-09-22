# 1 标签管理-支持工具标签管理 测试策略

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **需求名称**: openLiBing发布-欧拉发布流程增加require字段收集；通用流程增加页面提示和提升易用性、通过已有tag创建代码仓发行版
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: disiqi,liting,lidebing,gaojiangning
- **测试责任人**: zhangchuang

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
> - **目的：** 确保功能实现符合设计预期。
> - **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

## 3. 专项验证设计和执行详情

> 测试自检
>
> - [x] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果？
> - [x] **证据留存**: 关键测试（如性能、安全扫描）是否附带了截图或报告链接？

### 3.1 功能测试专项

> 参考测试设计方向
>
> - API 语义验证：验证 HTTP 状态码（2xx, 4xx, 5xx）的使用是否符合 RESTful 规范。
> - 边界与非法输入：验证大数据量、空字段、特殊字符及非法 JSON 格式的拦截能力。
> - 业务状态机闭环：验证资源从“创建中”到“运行中”再到“已释放”的全生命周期逻辑。

**1.openlibing发布评审_通过已有tag创建代码仓发行版**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击新建发布评审，填写信息，选择线下评审-制品包-代码仓发行版，选择通过tag创建代码仓的发布评审单所在的代码仓，选择tag名称
- **预期结果**: 输入框弹出列表，显示已存在的预期tag列表

- **步骤二**：选择软件包路径
- **预期结果**: 表格中显示tag名称校验结果

- **步骤三**：点击发起评审，评审人评审通过
- **预期结果**: 发起评审单成功，发布评审通过

**2.openlibing发布评审_线上评审同步病毒扫描和完整性校验执行结果**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击发布设置-安全领域
- **预期结果**: 存在完整性校验和病毒扫描两个，且两个是默认项，不可修改和删除

- **步骤二**：返回后点击新建发布评审，选择线上评审
- **预期结果**: 安全领域中完整性校验和病毒扫描两项默认必选

- **步骤三**：选择制品包-代码发行版，填写信息，选择软件包路径，保存
- **预期结果**: 表格中病毒扫描结果和完整性校验结果显示扫描中，等待后状态回显，显示扫描结果

**3.openlibing发布评审_发布流程交互优化_tag/release旁边出现提示**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：新建发布评审，制品包-代码仓发行版
- **预期结果**: tag/release旁边有问号提示

- **步骤二**：鼠标悬浮问号上
- **预期结果**: 提示"tag和release名称不能和已有的重复"

- **步骤三**：选择源码包
- **预期结果**: 显示问号，鼠标悬浮有提示文字

**4.openlibing发布评审_发布流程交互优化_选择软件包时有提示**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：新建发布评审单，选择制品包，添加软件包路径
- **预期结果**: 出现提示文字"需要先在obs桶模块接入"

**5.openlibing发布评审_发布流程交互优化_新增手动同步桶信息按钮**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击新建发布评审单，选择制品包，选择添加软件包，进入一个桶内
- **预期结果**: 出现刷新按钮

- **步骤二**：点击刷新
- **预期结果**: 桶内信息同步刷新，显示最新桶内信息

**6.openlibing发布评审_发布流程交互优化_评审人进入评审单出现提示**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：评审人点击链接进入发布评审单
- **预期结果**: 出现提示文字，提示需要在评审信息栏中填写评审意见，是否给予通过

**7.openlibing发布评审_通过已有tag创建代码仓发行版_越权失败**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：进入openLiBing项目-发布管理-发布评审
- **预期结果**: 未显示创建评审单按钮

- **步骤二**：管理员为授权项目成员，新建发布评审单，选择一个公共代码仓，选择tag
- **预期结果**: 显示新建发布评审单，tag列表可以显示

- **步骤三**：选择私有代码仓
- **预期结果**: 无法显示tag列表

**8.openlibing发布评审_欧拉update发布流程增加require字段**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击一个评审单
- **预期结果**: 列表中类型除bugfix外新增了requires字段

- **步骤二**：点击进入发布issue页面
- **预期结果**: 统计bugfix的issues列表，新增统计requires的issues列表


