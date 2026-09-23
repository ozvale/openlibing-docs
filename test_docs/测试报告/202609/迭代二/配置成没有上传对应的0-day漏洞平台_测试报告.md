# 配置成没有上传对应的0-day漏洞平台 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability-hunting/issues/61
- **需求名称**: 配置成没有上传对应的0-day漏洞平台
- **开发责任人**: liujiaqi
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

**1.漏洞挖掘页面对漏洞进行0day同步操作_无法同步完成功能下线**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability-hunting/issues/61
- **步骤一**：访问漏洞挖掘页面
- **预期结果**: 首页正常渲染，可以看到对应项目的漏洞信息
- **测试结果**： Passed
- **步骤二**：查看漏洞表格的操作列
- **预期结果**: 操作列无同步到0day的按钮
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011m6houbb&case_id=vb1v00011nd7edgd&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 1        | 覆盖核心业务逻辑与 API 契约。 | 1      | 0        | Pass             |
