# 完善uniportal账号华为用户身份判断-employeeType 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/80
* **需求名称**: 完善uniportal账号华为用户身份判断-employeeType，黄蓝协同PR任务查看等权限调整
* **开发责任人**: codechentao418
* **测试责任人**: SilverCake
* **最终结论**: 通过
* **测试维度**:
  * [X] **功能自检测试**
  * [ ] **体验测试**
  * [ ] **集成测试**
  * [ ] **安全与隐私测试**
  * [ ] **可靠性与韧性测试**
  * [ ] **可服务性与可观测性测试**
  * [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.老用户未绑定uniportal_绑定uniportal_数据库中记录华为身份**

* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/80
* **前置条件**: 使用未绑定uniportal的openLiBing账号
* **测试步骤**: 绑定uniportal
* **预期结果**: 数据库中记录该账号的华为身份
* **测试结果**: Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1n000115dbinkf&detail=base

**2.老用户绑定uniportal账号-数据库表存入用户的华为用户标识信息**

* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/80
* **前置条件**: 1、openLiBing系统能够正常使用 2、存在未绑定uniportal的老用户账号
* **测试步骤**: 老用户绑定uniportal账号
* **预期结果**: 数据库表对应数据行存入华为用户标识
* **测试结果**: Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1n0001154jo07q&detail=base

**3.通过uniportal渠道进行新用户注册登录-数据库表存入用户的华为用户标识信息**

* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-gateway/issues/80
* **前置条件**: 1、openLiBing系统能够正常使用
* **测试步骤**: 新用户使用uniportal账号登录openLiBing
* **预期结果**: 数据库表存入华为用户标识
* **测试结果**: Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1v0001154h5gbf&detail=base

---

## 3. 测试结果汇总表

| 测试维度 | 用例总数 | 重点测试点描述 | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|---------|---------|---------------|-------|---------|-----------------|
| **功能测试** | 3 | uniportal账号绑定与华为用户身份标识存储 | 3 | 0 | Pass |

---

## 4. 遗留问题与风险说明

| 缺陷 ID | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------|---------|---------|---------------------------|
| 无 | 无 | - | - |