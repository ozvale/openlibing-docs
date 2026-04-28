# 1 sca频繁误报优化 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/34
- **需求名称**: sca扫描频繁误报优化
- **开发责任人**: musheng
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.扫描之前存在较多误报代码片段的pr\_误报减少**:扫描之前存在较多误报代码片段的pr

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/34
- **预期结果**: 误报减少（误报依然存在但不会频繁误报）
- **测试结果**： Passed
- **证明截图**: 1.[修复前存在误报](https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/49/69/1776251484969919304.png) 2.[修复后误报减少](https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/92/68/1776251549268791971.png)

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 1        | 覆盖核心业务逻辑与 API 契约。 | 1      | 0        | Pass             |
