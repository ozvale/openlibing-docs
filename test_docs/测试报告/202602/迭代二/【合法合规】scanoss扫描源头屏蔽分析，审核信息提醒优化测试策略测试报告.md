# #1 [scanoss扫描源头屏蔽分析，审核信息提醒优化] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/20
* **需求名称**: 【合法合规】scanoss扫描源头屏蔽分析，审核信息提醒优化
* **开发责任人**: musheng、gaojiangning、caolongheng
* **测试责任人**: alice5426_qing
* **最终结论：**： 通过
* **测试维度** ：
* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**：
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

#### 2.1.1 整改管理中心页面接口权限

**1.审批信息使用角标红色数量显著标识**:查看合法合规审核信息页面的我的申请和待我审核，检查是否存在角标显著标识数量
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/20
* **预期结果**:我的申请和待我审核，存在红色数量的角标信息显著标识
* **测试结果**：Passed
* **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1n000116gtfthh&detail=result

**2.Sca审核时给出供应商和组件名称**:查看合法合规审核信息页面的我的申请和待我审核、审批历史，检查是否存在供应商和组件名称
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/20
* **预期结果**:我的申请和待我审核、审批历史页面，均存在供应商和组件名称信息
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1n000116gfafsi&detail=base

**3.查看scanoss屏蔽规则**: 查看合法合规社区管理页面，检查页面是否可以查看scanoss屏蔽规则
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/20
* **预期结果**: 社区管理页面新增窗口，可以查看scanoss的屏蔽规则
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1o000116jb8u79&detail=result

**4.新增scanoss屏蔽规则**: 查看合法合规社区管理页面，点击编辑SCANOSS规则->添加规则
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/20
* **预期结果**: 新增scanoss规则成功
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1o000116jcjr0n&detail=result

**5.删除scanoss屏蔽规则**: 查看合法合规社区管理页面，点击编辑SCANOSS规则，勾选需要删除的规则，批量删除
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/20
* **预期结果**: 批量删除scanoss规则成功
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb21000114vcksrg&case_id=vb1n000116jdfru3&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 5    | 覆盖核心业务逻辑与页面功能正常可用。  | 5   | 0    | Pass           |
| **体验测试**    | 0    | 判定产品是否能让用户快速的接受和使用。 | 0   | 0    | /              |
| **集成测试**    | 0    | 跨组件调用及上下游数据流转。      | 0   | 0    | /              |
| **安全与隐私测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
| **可靠性与韧性测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| **[Bug-#01]** | xxx  | 中    | 修复               |
