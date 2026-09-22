# #1 流水线测试用例数据完善需求分析说明书

## 1. 基础信息

* **需求链接**: **[TODO]**
* **需求名称**: **流水线测试用例数据完善**_增强流水线测试用例相关接口的数据展示能力_
* **开发责任人**: **[TODO]**_caoxiaolin & shichenchen_

---

## 2. 需求场景说明

> 描述“在什么情况下，为了解决什么问题，用户需要做什么”。

**[TODO]**

在DevOps平台中，用户需要查看流水线测试用例的详细信息和统计数据，以便评估流水线的质量和效率。当前系统中的测试用例数据展示不够完整，缺少关键字段和统计指标，导致用户无法全面了解测试用例的执行情况。为了解决这个问题，需要完善流水线测试用例相关接口，增加更多字段和统计指标，提高数据的可读性和实用性。

## 3 需求验收标准

> 明确需求完成的标志，必须是可量化、可测试的。

**[TODO]**

- [x] /repo/detail接口的test-case-detail请求中成功增加pipelineRunUrl字段
- [x] /repo/detail接口的test-case-detail请求中成功增加pipelineRunNum字段
- [x] /repo/detail接口的test-case-detail请求中成功增加pipelineRunNum、repoBranch、caseNumber、caseLevel、result、repoUrl进行过滤，pipelineRunNum、repoBranch、caseNumber、caseLevel、result、time支持排序
- [x] /repo/detail接口的test-case-detail请求中成功增加jobName字段
- [x] /repo/detail接口的test-case-detail请求中成功增加jobName过滤和支持排序
- [x] pipeline/version/chart接口的version请求中成功增加测试用例通过率的内容数据
- [x] /repo/detail接口的version、pipeline和test-case-detail请求中成功增加用例上线数
- [x] pipeline/version/chart接口的version请求中成功增加用例上线数
- [x] dwr_rd_efc_build_fact_nightly_test_case_pipeline_run表中成功增加case_release_count和case_release_count_p0字段
- [x] 所有测试用例相关的比率字段都成功乘以100，方便前端直接展示百分比
- [x] 所有修改的功能通过单元测试，项目编译通过

---

## 4. 需求设计与分解

> 说明：基于初步方案，将需求拆解为可实施的原子 Task。后续的流程判定将严格依据这些 Task 的影响范围进行。

### 4.1 核心逻辑方案

> 简述实现逻辑（如：数据流向、模块改动、新增配置项等），作为任务拆解的理论依据。图片文字形式不限。

**[TODO]**

通过扩展数据模型、Mapper接口和服务层实现，为流水线测试用例相关接口增加新的字段和功能。主要包括：
1. 在数据模型中添加新的字段，如pipelineRunUrl、pipelineRunNum、jobName、caseReleaseCount等
2. 在Mapper XML中修改查询语句，添加新字段的映射和查询逻辑
3. 在服务层实现中添加新字段的处理逻辑，如构建pipelineRunUrl、设置jobName等
4. 在响应类中添加新字段，确保前端能够接收到新的数据
5. 修改查询条件，支持新的过滤和排序功能
6. 将比率字段乘以100，方便前端直接展示百分比

### 4.2 任务清单

| 任务 ID              | 任务描述 (Task Description)            | 预期产出 (Deliverables) | 预期工作量（人天）   |
|--------------------|------------------------------------|---------------------|-------------|
| **task1** | **为test-case-detail请求增加pipelineRunUrl字段** | 修改TestCaseDetailResp、DwiRdEfcTestCaseResultServiceImpl等文件 | **1** |
| **task2** | **为test-case-detail请求增加pipelineRunNum字段** | 修改TestCaseDetailResp、DwiRdEfcTestCaseResultServiceImpl等文件 | **1** |
| **task3** | **为test-case-detail请求增加过滤和排序功能** | 修改TestCaseDetailReq、DwiRdEfcTestCaseResultMapper等文件 | **1** |
| **task4** | **为test-case-detail请求增加jobName字段** | 修改TestCaseDetailResp、DwiRdEfcTestCaseResultServiceImpl等文件 | **1** |
| **task5** | **为test-case-detail请求增加jobName过滤和排序** | 修改TestCaseDetailReq、DwiRdEfcTestCaseResultMapper等文件 | **1** |
| **task6** | **为version/chart的version请求增加测试用例通过率** | 修改VersionPipelineChartResp、PipelineHandleImpl等文件 | **1** |
| **task7** | **为多个接口增加用例上线数功能** | 修改DwrRdEfcBuildFactNightlyTestCasePipelineRun、DmRdEfcBuildDimTestCaseNightlyPipelineDay等文件 | **1** |
| **task8** | **将测试用例相关比率字段乘以100** | 修改DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper等文件 | **1** |

---

## 5. 需求相关性分析

> **操作说明**：根据上述拆解出的 Task，识别其变更行为。任何一项勾选为“是”：打上对应issue标签，必须执行对应的流程门禁。全部未勾选：该需求自动判定为轻量化特性，打上need_light标签。

### A. 安全相关性分析

> *若涉及以下任一项，打标 `need_security`标签，PR 必须关联特性issue的架构设计文档（含安全设计部分）**如勾选需要给出原因**。

**[TODO]**

* [ ] **边界变更**：新增公网端口、修改防火墙规则、变更网关配置。
* [ ] **凭证处理**：涉及密钥（Secret/Key）、Token、证书的存储或分发。
* [ ] **权限调整**：修改权限模型、服务账号（SA）权限或鉴权逻辑。
* [ ] **供应链**：引入新的第三方二进制文件、SDK 或重大版本依赖升级。
* [ ] **隐私风险评估**：涉及用户个人数据（Email、手机号、IP、邮箱 等）的处理。
* [ ] **AI使用**：涉及AIGC能力应用，并提供服务。

### B. 架构设计相关性分析

> *若涉及以下任一项，打标 `need_design`标签，PR 必须关联特性issue的架构设计文档。 **如勾选需要给出原因**。

**[TODO]**

* [ ] A环节判定需要完成安全设计
* [ ] 改变了现有系统的物理/逻辑拓扑
* [x] 新增或大幅修改对外暴露的 API/CLI 接口 **[勾选必填]**_原因：为多个接口增加了新字段和功能_
* [ ] 引入了新的中间件、数据库或三方核心组件 **[勾选必填]**_原因：如：引入了新的中间件、数据库或三方核心组件_

### C. 系统集成测试相关性分析

> *若涉及以下任一项，打标 `need_itest`标签，PR必须关联特性issue的测试策略和测试报告文档。 **如勾选需要给出原因**。

**[TODO]**

* [ ] 上述环节判定需要执行安全设计或架构设计。
* [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [ ] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑。

### D. 用户体验相关性分析

> *若涉及以下任一项，打标 `need_ux`标签，PR必须关联特性issue的用户体验设计文档。 **如勾选需要给出原因**。

**[TODO]**

* [ ] **交互逻辑变更**：涉及 Web 门户、控制台（Dashboard）或命令行工具（CLI）的交互流程调整。
* [x] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。 **[勾选必填]**_原因：增加了新的字段和查询条件，可能影响接口响应时间_
* [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [ ] **无障碍与多语种**：涉及国际化（i18n）支持、辅助功能或不同终端（移动端/桌面端）的适配。

### 5.1 需求相关性分析汇总结果

**[TODO]**

* [ ] need_security (需架构设计（含安全威胁分析和安全设计）)
* [x] need_design (需架构设计)
* [ ] need_itest (需执行测试策略设计和全链路集成测试)
* [x] need_ux (需架构设计（含UX设计))
* [ ] need_light (上述均未勾选，走快速合入通道)

---

## 6. 价值识别与业务评估

> **判定准则**：基础设施接纳需求必须具备明确的 ROI（投资回报比）或合规必要性。

| 维度        | 评估问题                            | 结论/说明               |
|-----------|---------------------------------|---------------------|
| **范围判定**  | 该需求是否属于基础设施范围内？                 | **是**               |
| **规划一致性** | 该需求是否是否在年度技术规划中？                | **是**               |
| **优先级**   | 该需求优先级评估（高/中/低）？                | **高**               |
| **通用性**   | 该需求是否解决 3 个以上业务方的共性痛点？          | **是**               |
| **必要性**   | 现有组件通过配置变更是否无法实现目标或没有不用开发的替代方案？ | **是**               |
| **工作量**   | 预计总工作量 **8** 人天？        | **8** 人天            |
| **价值评估**  | 实现后能减少多少手动操作或提升多少系统稳定性？         | **提升了流水线测试用例数据的完整性和可读性，帮助用户更好地评估流水线质量和效率**  |

> **状态定义：** **Accept (准入)** | **Reject (驳回)** |  **Pending (待议)**

**建议结论**： **Accept**

**原因描述:** **该需求完善了流水线测试用例相关接口的数据展示能力，增加了多个关键字段和统计指标，提高了数据的可读性和实用性，帮助用户更好地评估流水线的质量和效率，符合DevOps平台的演进目标。**

---