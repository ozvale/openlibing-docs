# 1 配置scanoss扫描特定目录或者不扫描指定目录 测试策略

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/36
- **需求名称**: 配置scanoss扫描特定目录或者不扫描指定目录
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: musheng,jiangzhichao
- **测试责任人**: caolongheng

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
> - **目的：** 确保功能实现符合设计预期。
> - **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

## 3. 专项验证设计和执行详情

> 测试自检
>
> - [x] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果？
> - [x] **证据留存**: 关键测试（如性能、安全扫描）是否附带了截图或报告链接？

### 3.1 功能测试专项

> 参考测试设计方向
>
> - API 语义验证：验证 HTTP 状态码（2xx, 4xx, 5xx）的使用是否符合 RESTful 规范。
> - 边界与非法输入：验证大数据量、空字段、特殊字符及非法 JSON 格式的拦截能力。
> - 业务状态机闭环：验证资源从“创建中”到“运行中”再到“已释放”的全生命周期逻辑。

**1.在合法合规页面的社区管理中选择对应的社区点击添加SCANOSS规则_表单中出现过滤目录字段**: 在合法合规页面的社区管理中选择对应的社区点击添加SCANOSS规则

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/36
- **预期结果**: 添加规则表单中出现过滤目录字段。


**2.配置扫描过滤目录_扫描结果中对应目录的文件消失**: 配置扫描过滤目录

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/36
- **步骤一**：在合法合规页面版本扫描下选择openlibing-sca代码release_20260508_fix分支
- **预期结果**: 确认风险项中存在如`src/main/java/com/openlibing/sca/analysis`目录下的文件
- **步骤二**：在合法合规页面pr扫描下选择openlibing-sca代码仓的某个pr
- **预期结果**: 确认风险项中存在如`src/main/java/com/openlibing/sca/analysis`目录下的文件
- **步骤三**：在社区管理页面，编辑openlibing-sca的SCANOSS规则，添加过滤目录src/main/java/com/openlibing/sca/analysis后重启执行对应的版本扫描和pr扫描
- **预期结果**: 版本扫描和pr扫描结果中对应目录下的风险项不再显示

