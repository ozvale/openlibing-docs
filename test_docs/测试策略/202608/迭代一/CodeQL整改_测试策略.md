# CodeQL整改 测试策略设计说明书

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/60
- **需求名称**: CodeQL整改
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: wangtian、musheng
- **测试责任人**: caolongheng

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
> - **目的：** 确保功能实现符合设计预期。
> - **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

---

## 3. 专项验证设计和执行详情

> 测试自检
>
> - [x] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果？
> - [x] **证据留存**: 关键测试（如性能、安全扫描）是否附带了截图或报告链接？

### 3.1 功能测试专项

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

---
