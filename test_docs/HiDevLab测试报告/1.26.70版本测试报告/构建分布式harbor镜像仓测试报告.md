# #1 [构建分布式harbor镜像仓] 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/hidevlab-infra-manager-service/issues/49
* **需求名称**: [需求]: 构建分布式harbor镜像仓
* **开发责任人**: 周建成
* **测试责任人**: 张晓璐
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

**1.多机多卡性能优化**:验证harbor服务器页面基础功能（UI检查、筛选排序）；新增功能（字段校验、新增后镜像仓的使用）；镜像推送逻辑验证（首次推送镜像到剩余磁盘空间最大的harbor）;存量harbor迁移与查询（查询的降级逻辑）
* **对应task(issueID)链接:**: https://gitcode.com/openlibing/hidevlab-infra-manager-service/issues/49
* **预期结果**: 基础功能正确；新增功能正确，镜像推送逻辑正确，存量数据迁移到正确表，存量harbor 查询逻辑正确
* **测试结果**：Passed
* **证明截图**: https://clouddragon.huawei.com/cloudtest/project/g93d08446a01c4a818fe4d9e72ca8ea38/services/9b367f94a4414f438f1ed404346aeaff/manualtaskDetail?stage=Iota,Kappa&taskUri=v8v900011l5cvml5&branchUri=v8r100011jmkc8p8&iterationUri=v8sf00011jmkchck&serviceId=9b367f94a4414f438f1ed404346aeaff&taskType=static%20task&isParent=true


---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|---------------|
| **功能测试**    | 14    | 覆盖核心业务逻辑与 API 契约。   | 11   | 0    | Pass          |
| **体验测试**    | 0    | 判定产品是否能让用户快速的接受和使用。 | 0   | 0    | /             |
| **集成测试**    | 0    | 跨组件调用及上下游数据流转。      | 0   | 0    | /             |
| **安全与隐私测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /              |
| **可靠性与韧性测试** | 0    | 漏洞扫描、凭证加密及日志脱敏。     | 0   | 0    | /             |
---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |



