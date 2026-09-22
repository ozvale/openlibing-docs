# #1 【需求】代码检查告警屏蔽支持选择sig-info目录级的committer 测试报告

## 1. 基本信息

* **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2097822238
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/23
* **需求名称**: 【需求】代码检查告警屏蔽支持选择sig-info目录级的committer
* **开发责任人**: 董家辉
* **测试责任人**: 徐愚冰
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

**1.未配置sig-info目录级committer的告警屏蔽验证**: 当前版本有未配置sig-info目录级committer的告警，屏蔽查询对应的committer成功。

* **测试步骤**: 1.进入门禁检查/版本级检查指定代码仓的代码问题页面；2.选择一条未配置sig-info目录级committer的告警，点击屏蔽；3.查询可选的committer
* **预期结果**: 可选committer中仅包含代码仓级的committer。
* **测试结果**： Passed
* **证明截图**:  xxx

**2.已配置sig-info目录级committer的单条告警屏蔽验证**: 当前版本有已配置sig-info目录级committer的告警，屏蔽查询对应的committer成功。

* **测试步骤**: 1.进入门禁检查/版本级检查指定代码仓的代码问题页面；2.选择一条已配置sig-info目录级committer的告警，点击屏蔽；3.查询可选的committer
* **预期结果**: 可选committer中包含代码仓级的committer和对应sig-info目录级committer。
* **测试结果**： Passed
* **证明截图**:  xxx

**3.已配置不同sig-info目录级committer的多条告警屏蔽验证**: 当前版本有已配置不同sig-info目录级committer的告警，屏蔽查询对应的committer成功。

* **测试步骤**: 1.进入门禁检查/版本级检查指定代码仓的代码问题页面；2.选择多条配置不同sig-info目录级committer的告警，点击屏蔽；3.查询可选的committer
* **预期结果**: 可选committer中包含代码仓级的committer和涉及sig-info目录级committer的交集。
* **测试结果**： Passed
* **证明截图**:  xxx

**4.未配置及已配置不同sig-info目录级committer的多条告警屏蔽验证**: 当前版本有已配置不同sig-info目录级committer的告警，屏蔽查询对应的committer成功。

* **测试步骤**: 1.进入门禁检查/版本级检查指定代码仓的代码问题页面；2.选择多条配置不同sig-info目录级committer的告警和未配置目录级committer的告警，点击屏蔽；3.查询可选的committer
* **预期结果**: 可选committer中仅包含代码仓级的committer。
* **测试结果**： Passed
* **证明截图**:  xxx
---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 4    | 覆盖核心业务逻辑与 API 契约。   | 4   | 0    | Pass           |
| **体验测试**    | 0    | - | 0   | 0    | Pass           |
| **集成测试**    | 0    | -      | 0   | 0    | Pass           |
| **安全与隐私测试** | 0    | -     | 0   | 0    | Pass           |

---
