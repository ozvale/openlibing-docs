# #1 【合法合规】SCANOSS扫描优化，提供配置项扫描时排除配置的选项 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/26
- **需求名称**: 【合法合规】SCANOSS扫描优化，提供配置项扫描时排除配置的选项
- **开发责任人**: musheng,jiangzhichao
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

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
- **测试结果**： Passed
- **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/63/04/1773623746304238401.png
- **步骤二**：添加SCANOSS屏蔽规则：对于拥有多个开源软件路径的风险项添加其中一个开源软件路径，并重新触发测试pr的流水线
- **预期结果**: 对应该开源软件路径的风险项不再显示
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/62/69/1773623806269701900.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/24/48/1773624112448244148.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/47/70/1773624884770113353.png
- **步骤三**：添加SCANOSS屏蔽规则：对于拥有多个开源软件路径的风险项添加全部开源软件路径，并重新触发测试pr的流水线
- **预期结果**: 对应该开源软件路径的风险项不再显示
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/63/04/1773623746304238401.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/74/62/1773625137462563480.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/65/44/1773628196544534098.png
- **步骤四**：添加SCANOSS屏蔽规则：添加开源软件路径和开源软件文件名，并重新触发测试pr的流水线
- **预期结果**: 开源软件文件名正确则对应该开源软件路径和开源软件文件名的某一个风险项被过滤
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/16/56/1773624191656345592.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/26/47/1773624252647076410.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/78/80/1773624927880284713.png
- **步骤五**：添加SCANOSS屏蔽规则：添加开源软件路径，并重新触发测试pr的流水线
- **预期结果**: 对应开源软件路径的所有风险项被过滤
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/78/42/1773624297842746587.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/94/95/1773624329495702016.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/78/95/1773624967895809868.png

**3.SCANOSS扫描结果返回所有的匹配项**: 查看合法合规页面告警详情\_存在风险项匹配TOP5

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/26
- **步骤一**：查看版本扫描风险详情
- **预期结果**: 如果风险项的扫描结果匹配多条，展示TOP5，并且符合筛选逻辑
- **测试结果**： Passed
- **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/87/67/1774505168767736680.png
- **步骤二**：查看pr扫描风险详情
- **预期结果**: 如果风险项的扫描结果匹配多条，展示TOP5，并且符合筛选逻辑
- **测试结果**： Passed
- **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/66/71/1774497656671655336.png

**4.openlibing-sca门禁版本级clean code整改**: 在合法合规页面执行正常的用户操作\_cleancode功能正常

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/26
- **步骤一**：合法合规页面执行版本扫描
- **预期结果**: 页面展示扫描成功
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/73/14/1774691377314161038.png
- **步骤二**：查对版本扫描的风险项进行批量分析，并发起审核
- **预期结果**: 审核通过后风险项消失
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/71/18/1774691387118674855.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/18/22/1774691391822965171.png
- **步骤三**：在社区审核中添加SCANASS规则屏蔽对应的风险项，重新执行扫描
- **预期结果**: 对应屏蔽的风险项消失
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/57/10/1774691405710362803.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/99/34/1774691409934849483.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/58/31/1774691415831914320.png
- **步骤四**：在页面中执行一些用户操作，如筛选、导出等等基本操作
- **预期结果**: 基本功能正常
- **测试结果**： Passed
- **证明截图**:

---

## 3. 测试结果汇总表

| 测试维度           | 用例总数 | 重点测试点描述                         | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------------ | -------- | -------------------------------------- | ------ | -------- | ---------------- |
| **功能测试**       | 4        | 覆盖核心业务逻辑与 API 契约。          | 4      | 0        | Pass             |
| **体验测试**       | 0        | 判定产品是否能让用户快速的接受和使用。 | 0      | 0        | Pass             |
| **集成测试**       | 0        | 跨组件调用及上下游数据流转。           | 0      | 0        | Pass             |
| **安全与隐私测试** | 0        | 漏洞扫描、凭证加密及日志脱敏。         | 0      | 0        | Pass             |
