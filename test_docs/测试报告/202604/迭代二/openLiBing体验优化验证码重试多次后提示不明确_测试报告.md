# 1 openLiBing体验优化验证码重试多次后提示不明确 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/41
- **需求名称**: openLiBing体验优化验证码重试多次后提示不明确
- **开发责任人**: zhuangzhiting
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.多次录入绑定/变更邮箱验证码失败\_提示验证次数到达上限和重试间隔**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/41
- **步骤一**：多次录入绑定/变更邮箱验证码失败
- **预期结果**: 提示验证次数以到达上限请等待五分钟后再试
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/14/00/1776415771400340955.png

**2.多次发送绑定/变更邮箱验证码\_提示操作频繁和重试间隔**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/41
- **步骤一**：多次发送绑定/变更邮箱验证码
- **预期结果**: 提示发送邮件次数过于频繁，请10分钟后再试
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/57/53/1776413765753206650.png

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 2        | 覆盖核心业务逻辑与 API 契约。 | 2      | 0        | Pass             |
