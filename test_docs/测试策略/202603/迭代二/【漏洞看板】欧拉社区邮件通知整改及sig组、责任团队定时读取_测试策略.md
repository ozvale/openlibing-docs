# 【漏洞看板】欧拉社区邮件通知整改及sig组、责任团队定时读取 测试策略

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/14
- **需求名称**: 欧拉社区邮件通知整改及sig组、责任团队定时读取
- **核心目标**:
  验证功能正确性，以及架构设计中定义的安全与隐私、可靠性与韧性、可服务性与可观测性和性能与伸缩性等非功能专项任务的闭环验收。
- **开发责任人**: wurongqiang
- **测试责任人**: linyapeng

---

## 2. 测试维度确认

> **操作指南**：请依据需求分析阶段的标签勾选。勾选后，必须在“第 3 节”提供对应的测试用例或方案。

- [x] **功能自检测试**

> - **测试重点：** API 契约验证、业务逻辑分支覆盖、边界值测试。
> - **目的：** 确保功能实现符合设计预期。
> - **触发条件：** 强制执行,**可委托开发测试完成，测试完成验收**。

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

> 参考测试设计方向
>
> - API 语义验证：验证 HTTP 状态码（2xx, 4xx, 5xx）的使用是否符合 RESTful 规范。
> - 边界与非法输入：验证大数据量、空字段、特殊字符及非法 JSON 格式的拦截能力。
> - 业务状态机闭环：验证资源从“创建中”到“运行中”再到“已释放”的全生命周期逻辑。

**1. 欧拉社区邮件通知整改**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/14
- **步骤一**: 接收欧拉社区的邮件通知。
- **预期结果**: 显示邮件内容。
- **测试结果**： Passed
- **步骤二**: 检查表格1。
- **预期结果**:
    - 显示原表格1的“合计”内容；
    - 原先的表头“超期数/超期率、未修复数/未修复率、未闭环数/未闭环率、漏洞总数”拆分为“超期数、超期率、未修复数、未修复率、未闭环数、未闭环率、漏洞总数”，由4项拆分为7项。
    - 数据范围由全量数据变为最近3个月的数据
- **测试结果**： Passed
- **步骤三**: 检查表格2。
- **预期结果**:
    - 显示原先表格1的“9分以上”、“7-9分”、“7分以下”内容
    - 原先的表头“超期数/超期率、未修复数/未修复率、未闭环数/未闭环率、漏洞总数”拆分为“超期数、超期率、未修复数、未修复率、未闭环数、未闭环率、漏洞总数”，由4项拆分为7项。
    - 数据范围由全量数据变为最近3个月的数据
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb1n00011709qaqn&case_id=vb1n000119b1kma2&detail=base

**2. 自动定时同步sig组信息和责任团队的信息**: 检查atomgit平台的sig组信息是否同步到漏洞视图。

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/14
- **预期结果**: atomgit平台的sig组信息增量同步到漏洞视图。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb1n00011709qaqn&case_id=vb1o000119b20ji6&detail=base
