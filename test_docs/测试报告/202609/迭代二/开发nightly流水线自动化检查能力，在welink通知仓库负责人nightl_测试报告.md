# 开发nightly流水线自动化检查能力，在welink通知仓库负责人nightly流水线结果 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/73
- **需求名称**: 开发nightly流水线自动化检查能力，在welink通知仓库负责人nightly流水线结果
- **开发责任人**: linyapeng
- **测试责任人**: dongsicheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**
- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**：
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.开发nightly流水线自动化检查能力，在welink通知仓库负责人nightly流水线结果**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/73
- **步骤一**：进入任意仓库-actions流水线，检查nightly-schedule-scan流水线
- **预期结果**: 流水线任务通过定时任务自动触发或手动触发，扫描完毕后在welink发布扫描结果，通知负责人
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb1n00011nbkhc6s&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                                                                                                             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | -------------------------------------------------------------------------------------------------------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 1        | 在漏洞挖掘列表页中无法操作修改漏洞的确认状态和修复状态，仅能查看漏洞信息。在0day漏洞对应的条目中才能同步修改漏洞挖掘的状态 | 1      | 0        | Pass             |
