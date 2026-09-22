# 更新隐私声明文本并在PCMC平台同步更新 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-web/issues/127
- **需求名称**: [需求]: openLiBing隐私政策声明刷新&服务日志入湖&越权整改等安全合规整改
- **开发责任人**: caolongheng
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

**1. 更新隐私声明文本并在PCMC平台同步更新**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-web/issues/127
- **步骤一**: 在openlibing平台检查隐私政策。
- **预期结果**:
  - 隐私政策文本新增了项目管理场景收集个人gitee组织名称数据的说明。
  - 最近更新时间更新为2026年4月；隐私政策版本更新为v202604
- **测试结果**: Passed
- **步骤二**: 在PCMC平台检查openlibing的隐私政策文本。
- **预期结果**: 与openlibing平台文本保持一致。
- **测试结果**: Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb1n00011af941db&case_id=vb1n00011ca68hia&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                           | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|----------|------|-----------------------------------|-----|------|----------------|
| **功能测试** | 1    | 更新隐私声明文本并在PCMC平台同步更新  | 1   | 0    | Pass           |
