# CodeQL整改 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/60
- **需求名称**: CodeQL整改
- **开发责任人**: wangtian、musheng
- **测试责任人**: caolongheng
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

**1.调用CodeQL修改的接口_接口正常**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/60
- **步骤一**：版本扫描->开源片段引用合规->导出 测试接口openlibing-sca/open/scan/export/community/count
- **预期结果**: 接口工作正常
- **测试结果**： Passed
- **步骤二**：版本扫描->风险数据详情->导出 测试接口openlibing-sca/open/scan/putExportXLS
- **预期结果**: 接口工作正常
- **测试结果**： Passed
- **步骤三**：版本扫描->风险数据详情->批量分析 结束后刷新接口 openlibing-sca/scan/refresh/confirmNum
- **预期结果**: 接口工作正常
- **测试结果**： Passed
- **步骤四**：版本扫描->项目合规->导出当前列表 调用接口openlibing-sca/license/export/community
- **预期结果**: 接口工作正常
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1v00011k142b2s&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 1        | 覆盖核心业务逻辑与 API 契约。 | 1      | 0        | Pass             |
