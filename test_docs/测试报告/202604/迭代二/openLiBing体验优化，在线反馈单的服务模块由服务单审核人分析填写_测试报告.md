# 1 openLiBing体验优化，在线反馈单的服务模块由服务单审核人分析填写 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/41
- **需求名称**: openLiBing体验优化，在线反馈单的服务模块由服务单审核人分析填写
- **开发责任人**: linyapeng，liting
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.创建反馈单\_服务审核人收到审核消息**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/41
- **步骤一**：创建服务单，并填写内容
- **预期结果**: 服务审核人（feedback_manager）收到审核消息
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/95/26/1777001669526315741.png
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/32/90/1777001723290558189.png

  **2.服务审核人指定服务名称和开发人员分配服务单\_开发人员收到消息通知**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/41
- **步骤一**：服务审核人点击服务单页面的查看详情按钮
- **预期结果**: 出现服务模块和开发责任人下拉选
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/97/03/1777002259703873856.png

- **步骤二**：点击服务模块下拉选
- **预期结果**: 接口返回全量的服务名称
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/06/86/1777004870686910839.png
- **步骤三**：点击开发责任人下拉选
- **预期结果**: 接口返回具有feedback_maintainer角色的人员列表
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/01/38/1777004730138395979.png
- **步骤四**：点击保存按钮
- **预期结果**: 开发责任人收到消息通知
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/72/65/1777004927265396569.png

**3.页面其他变动**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/41
- **步骤一**：点击处理服务页面的服务模块下拉选
- **预期结果**: 接口返回全量的服务模块名称
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/84/97/1777005358497710447.png
- **步骤一**：点击服务单进展页面
- **预期结果**: 出现问题类型和状态筛选框（移除了服务名称和评审人）
- **测试结果**： Passed
- **证明截图**:
  https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/22/53/1777005312253888328.png

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 3        | 覆盖核心业务逻辑与 API 契约。 | 3      | 0        | Pass             |
