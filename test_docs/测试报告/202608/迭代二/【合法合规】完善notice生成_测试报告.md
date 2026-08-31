# 【合法合规】完善notice生成 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/60
- **需求名称**: 【合法合规】完善notice生成
- **开发责任人**: musheng
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

**1.调用notice生成接口_notice内容包含标头和下载列表**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/60
- **步骤一**：请求生成notice接口
- **预期结果**: 接口执行成功
- **测试结果**： Passed
- **步骤二**：进入openlibing华为云obs服务
- **预期结果**: 存在notice-beta桶
- **测试结果**： Passed
- **步骤三**：进入notice-beta文件夹，并下载opensource.md后缀名的文件
- **预期结果**: 文件中包含开源声明的标头以及文件末尾包含软件下载列表
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1o00011lam4c56&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 1        | 覆盖核心业务逻辑与 API 契约。 | 1      | 0        | Pass             |
