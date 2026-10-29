# OBS制品仓功能分享链接时保留项目信息方便用户打开到对应的桶 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-platform-release/issues/56
* **需求名称**: OBS制品仓功能分享链接时保留项目信息方便用户打开到对应的桶
* **开发责任人**: wangtian
* **测试责任人**: caolongheng
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


**1.在当前社区为B的情况下访问社区A的OBS桶地址_正确切换到社区A的对应桶**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/56
* **步骤一**：访问社区A的OBS制品仓页面，复制桶某个桶地址
* **预期结果**: 地址中携带projectId和projectName信息
* **测试结果**： Passed
* **步骤二**：切换当前社区为B，访问桶地址
* **预期结果**: 正常打开对应的obs桶，社区切换成功
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb2100011h4niej2&case_id=vb1v00011hotm75r&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 1 | 覆盖核心业务逻辑与 API 契约。 | 1 | 0 | Pass |
