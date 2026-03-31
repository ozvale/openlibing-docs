# #1 【合法合规】SCANOSS扫描优化，提供配置项扫描时排除配置的选项 测试策略设计说明书

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/26
- **需求名称**: 【合法合规】SCANOSS扫描优化，提供配置项扫描时排除配置的选项
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: musheng,jiangzhichao
- **测试责任人**: caolongheng

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

**1.PR扫描时，提供配置项让scanoss扫描源头分析屏蔽**: 添加SCANOSS规则。

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/26
- **步骤一**：在【开源片段引用合规】页面下点击【版本扫描】或【PR扫描】中的某个pr详情页
- **预期结果**: 在风险列表【组件版本】字段后存在【开源软件路径】字段。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/51/73/1774506995173618974.png
- **步骤二**：在【社区管理】页面某个代码仓下点击【编辑SCANOSS规则】按钮
- **预期结果**: 出现已有的规则列表，且字段为开源软件路径、开源软件文件名、备注、创建者、创建时间。规则表格观感良好，应有数据完备。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/88/47/1774507168847980255.png
- **步骤三**：点击【添加规则】按钮
- **预期结果**: 出现添加规则弹窗，表单拥有开源软件路径(必选)、开源软件文件名和备注的字段。且表单各个按钮（关闭、取消、确定）功能正常。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/12/88/1774507181288065001.png
- **步骤四**：点击【确定】按钮
- **预期结果**: 出现添加结果提醒，规则表格中出现新增规则项。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/95/51/1774507209551092675.png

**2.PR扫描时，提供配置项让scanoss扫描源头分析屏蔽**: 提供配置项让scanoss进行PR扫描时在源头屏蔽\_屏蔽后对应风险消失

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/26
- **步骤一**：确认当前分支的未处理风险项
- **预期结果**: 存在风险项

- **步骤二**：添加SCANOSS屏蔽规则：对于拥有多个开源软件路径的风险项添加其中一个开源软件路径，并重新触发测试pr的流水线
- **预期结果**: 对应该开源软件路径的风险项不再显示
- **测试结果**： Passed

- **步骤三**：添加SCANOSS屏蔽规则：对于拥有多个开源软件路径的风险项添加全部开源软件路径，并重新触发测试pr的流水线
- **预期结果**: 对应该开源软件路径的风险项不再显示
- **测试结果**： Passed

- **步骤四**：添加SCANOSS屏蔽规则：添加开源软件路径和开源软件文件名，并重新触发测试pr的流水线
- **预期结果**: 开源软件文件名正确则对应该开源软件路径和开源软件文件名的某一个风险项被过滤

- **步骤五**：添加SCANOSS屏蔽规则：添加开源软件路径，并重新触发测试pr的流水线
- **预期结果**: 对应开源软件路径的所有风险项被过滤

**3.SCANOSS扫描结果返回所有的匹配项**: 查看合法合规页面告警详情\_存在风险项匹配TOP5

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/26
- **步骤一**：查看版本扫描风险详情
- **预期结果**: 如果风险项的扫描结果匹配多条，展示TOP5
- **步骤二**：查看pr扫描风险详情
- **预期结果**: 如果风险项的扫描结果匹配多条，展示TOP5

**4.openlibing-sca门禁版本级clean code整改**: 在合法合规页面执行正常的用户操作\_cleancode功能正常

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/26
- **步骤一**：合法合规页面执行版本扫描和PR扫描
- **预期结果**: 页面展示扫描成功
- **步骤二**：查对版本扫描和PR扫描的风险项进行批量分析，并发起审核
- **预期结果**: 审核通过后风险项消失
- **步骤三**：在社区审核中添加SCANASS规则屏蔽对应的风险项，重新执行扫描
- **预期结果**: 对应屏蔽的风险项消失
- **步骤四**：在页面中执行一些用户操作，如筛选、导出等等基本操作
- **预期结果**: 基本功能正常
