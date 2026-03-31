# 【漏洞看板】欧拉社区邮件通知整改及sig组、责任团队定时读取 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/14
- **需求名称**: 【漏洞看板】欧拉社区邮件通知整改及sig组、责任团队定时读取
- **开发责任人**: wurongqiang
- **测试责任人**: linyapeng
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

**1. 欧拉社区邮件通知整改**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/14
- **步骤一**: 接收欧拉社区的邮件通知。
- **预期结果**: 显示邮件内容。
- **测试结果**： Passed
- **步骤二**: 检查表格1。
- **预期结果**:
  - 显示原表格1的“合计”内容； 
  - 原先的表头“超期数/超期率、未修复数/未修复率、未闭环数/未闭环率、漏洞总数”拆分为“超期数、超期率、未修复数、未修复率、未闭环数、未闭环率、漏洞总数”，由4项拆分为7项。 
  - 数据范围由全量数据变为最近3个月的数据
- **测试结果**： Passed
- **步骤三**: 检查表格2。
- **预期结果**:
  - 显示原先表格1的“9分以上”、“7-9分”、“7分以下”内容
  - 原先的表头“超期数/超期率、未修复数/未修复率、未闭环数/未闭环率、漏洞总数”拆分为“超期数、超期率、未修复数、未修复率、未闭环数、未闭环率、漏洞总数”，由4项拆分为7项。
  - 数据范围由全量数据变为最近3个月的数据
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb1n00011709qaqn&case_id=vb1n000119b1kma2&detail=base

**2. 自动定时同步sig组信息和责任团队的信息**: 检查atomgit平台的sig组信息是否同步到漏洞视图。

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/14
- **预期结果**: atomgit平台的sig组信息增量同步到漏洞视图。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb1n00011709qaqn&case_id=vb1o000119b20ji6&detail=base
---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述 | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------|-----|------|----------------|
| **功能测试**    | 2    | 欧拉社区邮件通知整改及sig组、责任团队定时读取    | 2   | 0    | Pass           |
