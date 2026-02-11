# #1 [需求名称] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/21
* **需求名称**: openLiBing二阶段安全与隐私整改
* **开发责任人**: linyapeng/fanyuan/sunchenglong/chaizongxiang/musheng
* **测试责任人**: alice5426_qing
* **最终结论：**： 通过
* **测试维度** ：
* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [X] **安全与隐私测试**：
* [X] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

#### 2.1.1 整改管理中心页面接口权限

**1.账号纳管操作记录日志**: 查看账号纳管的所有操作，添加账号、更新账号、授权操作、删除账号、登录操作，检查所有操作是否记录日志
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 账号纳管的增、删、改、授权、登录操作记录日志
* **测试结果**：Passed
* **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1o000114vepp4n&detail=result

**2.账号纳管操作执行正常**：正常执行账号纳管的添加账号/更新账号/授权/删除账号/登录账号等操作，检查功能是否可以正常使用
* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 账号纳管的增、删、改、授权、登录操作正常执行
* **测试结果**：Passed
* **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1o000114vepp4n&detail=result

**3.开源项目运营看板接口响应校验**: 按照接口文档进行调用。系统管理员查看开源项目运营看板的修改备注/查询看板数据/导出看板数据接口响应

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 开源项目运营看板接口，统一返回200
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1n00011522pkb2&detail=result

**4.管理中心运营看板操作记录日志**: 对管理中心的开源项目运营看板，进行操作，如修改备注、导出看板数据。检查响应操作信息是否记录日志

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**:开源项目运营看板修改备注、导出操作记录日志
* **测试结果**：Passed
* **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb21000114vu1lro&detail=result

**5.录入仓库开放小眼睛复制明文数据失败**: 查看录入代码仓的公共账号令牌，打开小眼睛，查看复制操作

* **对应task(issueID)链接:**https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 公共账号令牌明文查看时，复制明文内容信息失败
* **测试结果**：Passed
* **证明截图**:https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb21000114vv1u8v&detail=base

**6.第三方软件依赖完整性验证**：查看流水线构建日志，检查三方软件依赖完整性校验情况

* **对应task(issueID)链接:**https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 三方软件依赖完整性校验完成
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb210001152tbelh&detail=base

### 2.2 安全与隐私测试专项

**1.防爆破机制校验**: 模拟系统管理员正常执行账号纳管新增账号操作，设置租户名/IAM用户名正确，登录密码错误，多次请求。查看新增接口是否限制新增操作

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 多次新增账号错误后，接口限制新增操作
* **测试结果**：Passed
* **证明截图**：https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1n000114vii35q&detail=base

**2.鉴权校验**: 模拟无 token、过期 token、普通用户
token请求开源项目运营看板接口。查看开源项目运营看板接口/openlibing-ops/ops/repo/all、/openlibing-ops/ops/common/export/project响应

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 开源项目运营看板接口统一返回403/401
* **测试结果**：Passed
* **证明截图**：https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1n000115004g8g&detail=base

### 2.3 可靠性与韧性测试

**1.单点爆破验证**: 模拟单用户并发请求账号纳管的添加账号接口，查看接口是否作防爆破机制，以及服务是否宕机

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/21
* **预期结果**: 添加账号接口具有防爆破机制，以及服务正常运行未停止服务
* **测试结果**：Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb21000114vcksrg&case_id=vb1n000114vii35q&detail=base

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 6    | 覆盖核心业务逻辑与 API 契约。   | 6   | 0    | Pass           |
| **体验测试**    | 0    | 判定产品是否能让用户快速的接受和使用。 | 0   | 0    | /              |
| **集成测试**    | 0    | 跨组件调用及上下游数据流转。      | 0   | 0    | /              |
| **安全与隐私测试** | 2    | 漏洞扫描、凭证加密及日志脱敏。     | 2   | 0    | Pass           |
| **可靠性与韧性测试** | 1    | 漏洞扫描、凭证加密及日志脱敏。     | 1   | 0    | Pass           |
---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| **[Bug-#01]** | xxx  | 中    | 修复               |
