# #1 需求分析说明书

## 1. 基础信息

* **需求链接**: **[TODO]**
* **需求名称**: **[TODO]** 流水线统计功能优化与NightlyPipeline功能新增
* **开发责任人**: **[TODO]**

---

## 2. 需求场景说明

> 描述"在什么情况下，为了解决什么问题，用户需要做什么"。

**[TODO]** 为了更直观地了解流水线运行情况，SRE团队需要一个看板来展示流水线的运行数据，包括运行次数、成功率、平均时长等指标。同时，开发团队需要查看流水线的详细运行信息，以便及时发现和解决问题。

## 3. 需求验收标准

> 明确需求完成的标志，必须是可量化、可测试的。

**[TODO]**

- 流水线看板能够正常显示指定时间范围内的流水线运行数据
- 流水线详细信息能够正确展示各阶段的运行时间和状态
- 时长统计单位从毫秒改为分钟，数据显示准确
- 系统能够处理异常场景，如参数错误、数据为空等
- 接口响应时间不超过2秒

---

## 4. 需求设计与分解

> 说明：基于初步方案，将需求拆解为可实施的原子 Task。后续的流程判定将严格依据这些 Task 的影响范围进行。

### 4.1 核心逻辑方案

> 简述实现逻辑（如：数据流向、模块改动、新增配置项等），可以使用**流程图、时序图**辅助说明，作为任务拆解的理论依据。图片文字形式不限。

**[TODO]** 通过新增NightlyPipelineDashboard和NightlyPipelineDetail相关的请求/响应类、Mapper、Service和Controller，实现流水线数据的查询和统计。数据流向为：Controller接收请求 → Service处理业务逻辑 → Mapper查询数据库 → 返回响应数据。同时，优化PipelineHandleImpl中的逻辑，将时长统计单位从毫秒改为分钟。

### 4.2 数据库设计
**表名：DmRdEfcBuildDimNightlyPipelineDay**

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT(32) | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| pipeline_id | VARCHAR(255) | NOT NULL | 流水线ID |
| pipeline_name | VARCHAR(255) | NOT NULL | 流水线名称 |
| pipeline_run_count | INT(32) | NOT NULL | 流水线运行次数 |
| pipeline_run_success_count | INT(32) | NOT NULL | 流水线成功次数 |
| e2e_duration_minutes | DECIMAL(10,2) | NOT NULL | 端到端时长（分钟） |
| build_avg_time_minutes | DECIMAL(10,2) | NOT NULL | 构建平均时长（分钟） |
| test_avg_time_minutes | DECIMAL(10,2) | NOT NULL | 测试平均时长（分钟） |
| pipeline_run_endtime | DATE | NOT NULL | 流水线运行结束时间 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| update_time | DATETIME | NOT NULL | 更新时间 |

**表名：NightlyPipelineDashboard**

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT(32) | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| case_run_id | VARCHAR(255) | NOT NULL | 测试用例运行ID |
| pipeline_id | VARCHAR(255) | NOT NULL | 流水线ID |
| pipeline_name | VARCHAR(255) | NOT NULL | 流水线名称 |
| status | VARCHAR(50) | NOT NULL | 状态 |
| duration | DECIMAL(10,2) | NOT NULL | 时长（分钟） |
| rate | DECIMAL(5,2) | NOT NULL | 比率 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| update_time | DATETIME | NOT NULL | 更新时间 |

### 4.3 接口设计
##### 4.3.1 流水线看板接口
- **URL**: `/pipeline/version/chart`
- **方法**: POST
- **参数**:
    - projectId: Integer - 项目ID
    - startTime: String - 开始时间
    - endTime: String - 结束时间
    - isAllDay: Integer - 是否只查询工作日
- **返回**: `Result<VersionPipelineChartResp>` - 流水线图表数据

##### 4.3.2 NightlyPipeline Dashboard接口
- **URL**: `/common/metric`
- **方法**: POST
- **参数**:
    - category: String - 类别（nightlyPipeline）
- **返回**: `Result<List<MetricColumnResp>>` - 指标结果

### 4.4 apoll配置清单
| 配置项 | 说明 | 默认值 |
|-------|------|-------|
| pipeline.query.timeout | 流水线查询超时时间 | 30000 |
| pipeline.page.size | 流水线分页大小 | 10 |

### 4.5 任务清单

| 任务 ID | 任务描述 (Task Description) | 预期产出 (Deliverables) | 预期工作量（人天） |
|--------|---------------------------|---------------------|------------------|
| **task1** | **新增NightlyPipeline Dashboard功能** | Dashboard相关类和Mapper | **1** |
| **task2** | **新增NightlyPipeline Detail功能** | Detail相关类和Mapper | **1** |
| **task3** | **优化流水线统计逻辑** | 优化后的PipelineHandleImpl | **1** |
| **task4** | **将时长统计单位从毫秒改为分钟** | 单位转换相关代码 | **0.5** |
| **task5** | **修复数据查询逻辑和字段映射** | 修复后的查询逻辑 | **0.5** |
| **task6** | **编写测试用例** | 测试代码 | **1** |

---

## 5. 需求相关性分析

> **操作说明**：根据上述拆解出的 Task，识别其变更行为。任何一项勾选为"是"：打上对应issue标签，必须执行对应的流程门禁。全部未勾选：该需求自动判定为轻量化特性，打上need_light标签。

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
* [ ] 新增或大幅修改对外暴露的 API/CLI 接口
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
* [ ] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。
* [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [ ] **无障碍与多语种**：涉及国际化（i18n）支持、辅助功能或不同终端（移动端/桌面端）的适配。

### 5.1 需求相关性分析汇总结果

**[TODO]**

* [ ] need_security (需架构设计（含安全威胁分析和安全设计）)
* [ ] need_design (需架构设计)
* [ ] need_itest (需执行测试策略设计和全链路集成测试)
* [ ] need_ux (需架构设计（含UX设计)）
* [x] need_light (上述均未勾选，走快速合入通道)