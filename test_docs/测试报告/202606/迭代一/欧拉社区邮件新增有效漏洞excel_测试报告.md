# 1 欧拉社区邮件新增有效漏洞excel 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/21
- **需求名称**: 漏洞视图社区漏洞修复多元化数据统计展示
- **开发责任人**: wurongqiang
- **测试责任人**: zhangchuang
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.欧拉社区邮件新增有效漏洞excel_邮件附件包含有效漏洞文件**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/21
- **前置条件**: 可以接收到欧拉社区邮件
- **步骤一**：
  - 1.每天一点欧拉社区自动发送漏洞超期预警邮件后，打开该邮件
- **预期结果**:
  - 1.附件列表除了预警文件还有一个有效漏洞文件
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1v00011f6hnd83&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述           | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|----------|------|-------------------|-----|------|----------------|
| **功能测试** | 1    | 欧拉社区邮件新增有效漏洞excel | 1   | 0    | Pass           |
