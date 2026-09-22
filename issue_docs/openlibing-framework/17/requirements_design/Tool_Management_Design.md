# #1 openLiBing工具箱管理-支持工具上传下载和在线工具

## 1. 基础信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/46
* **需求名称**:openLiBing工具箱管理-支持工具上传下载和在线工具
* **开发责任人**: zhuangzt

---

## 2. 需求场景说明

> 工具管理模块包含工具申请、工具信息管理、工具标签管理三个核心功能模块，需要设计对应的控制器接口，支撑前端完成工具的全生命周期管理。

---

## 3. 需求验收标准

> 工具申请流程：用户提交工具申请→审核人审核→审核通过后工具上架
>
> 工具信息管理：支持工具的增删改查、版本管理、图标管理
>
> 工具标签管理：支持标签的增删改查，用于工具分类

---

## 4. 需求设计与分解

> 1. 工具申请管理：提供工具申请的提交、查询、修改、撤销、审核等功能
>
> 2. 工具信息管理：提供工具信息的查询、修改、删除，工具版本管理，图标管理，软件包下载等功能
>
> 3. 工具标签管理：提供标签的增删改查功能

### 4.1 核心逻辑方案

> **1. 工具申请管理**
>
> 步骤1：用户提交工具申请（包含工具基本信息、图标、软件包）
>
> 步骤2：系统保存申请信息到tool_apply表，状态为待审核
>
> 步骤3：审核人获取待审核列表，进行审核操作
>
> 步骤4：审核通过后，工具信息同步到tool_info表，状态更新为已上架
>
> 步骤5：用户可撤销待审核状态的申请

> **2. 工具信息管理**
>
> 步骤1：支持按工具名称/ID查询工具基本信息
>
> 步骤2：支持修改工具基本信息和版本信息
>
> 步骤3：支持上传/更新工具图标
>
> 步骤4：支持下载工具软件包
>
> 步骤5：支持删除工具及工具版本

> **3. 工具标签管理**
>
> 步骤1：支持新增、修改、删除标签
>
> 步骤2：支持标签列表查询和下拉选择
>
> 步骤3：删除标签时级联删除关联的工具标签配置

### 4.2 数据库设计

**表名：tool_apply（工具申请表）**

| 字段名 | 数据类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| id | varchar(36) | PRIMARY KEY | 申请单ID |
| tool_name | varchar(100) | NOT NULL | 工具名称 |
| tool_desc | varchar(500) | NULL | 工具描述 |
| tool_type | varchar(50) | NULL | 工具类型 |
| project_id | int | NOT NULL | 项目ID |
| status | varchar(20) | NOT NULL | 状态（待审核/已通过/已拒绝/已撤销） |
| apply_user_id | varchar(36) | NOT NULL | 申请人ID |
| apply_user_name | varchar(50) | NOT NULL | 申请人名称 |
| reviewer_id | varchar(36) | NULL | 审核人ID |
| reviewer_name | varchar(50) | NULL | 审核人名称 |
| review_time | datetime | NULL | 审核时间 |
| review_comment | varchar(500) | NULL | 审核意见 |
| create_time | datetime | NOT NULL | 创建时间 |
| update_time | datetime | NULL | 更新时间 |

**表名：tool_info（工具信息表）**

| 字段名 | 数据类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| id | varchar(36) | PRIMARY KEY | 工具ID |
| tool_name | varchar(100) | NOT NULL | 工具名称 |
| tool_desc | varchar(500) | NULL | 工具描述 |
| tool_type | varchar(50) | NULL | 工具类型 |
| tool_version | varchar(50) | NULL | 当前版本 |
| status | varchar(20) | NOT NULL | 状态（上架/下架） |
| create_by | varchar(36) | NOT NULL | 创建人 |
| create_time | datetime | NOT NULL | 创建时间 |
| update_by | varchar(36) | NULL | 更新人 |
| update_time | datetime | NULL | 更新时间 |

**表名：tool_label_info（工具标签表）**

| 字段名 | 数据类型 | 约束 | 描述 |
| --- | --- | --- | --- |
| id | varchar(36) | PRIMARY KEY | 标签ID |
| label | varchar(50) | NOT NULL | 标签名称 |
| create_by | varchar(36) | NOT NULL | 创建人 |
| create_time | datetime | NOT NULL | 创建时间 |
| update_by | varchar(36) | NULL | 更新人 |
| update_time | datetime | NULL | 更新时间 |

### 4.3 接口设计

##### 4.3.1 ToolApplyController（工具申请控制器）

| API路径 | HTTP方法 | 功能描述 |
| --- | --- | --- |
| `/tool-apply/get-reviewer` | GET | 获取工具审核人列表 |
| `/tool-apply/save-tool-icon` | POST | 保存工具申请-工具图标 |
| `/tool-apply/save-tool-software-pack` | POST | 保存工具申请-安装包 |
| `/tool-apply/save-tool-apply` | POST | 保存工具申请 |
| `/tool-apply/get-tool-apply-by-id` | GET | 根据ID获取工具申请信息 |
| `/tool-apply/get-tool-apply-info` | POST | 分页获取工具申请/审核列表 |
| `/tool-apply/update-tool-apply` | POST | 修改工具申请 |
| `/tool-apply/undo-apply` | POST | 撤销工具申请 |
| `/tool-apply/review` | POST | 审核工具申请 |

**GET /tool-apply/get-reviewer**
- **参数**:
    - userId: String - 用户ID（必填）
    - projectId: Integer - 项目ID（必填）
- **返回**: `DataResult<List<OpenLiBingUserInfoEntity>>` - 审核人列表

**POST /tool-apply/save-tool-icon**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolName: String - 工具名称（必填）
    - iconFile: MultipartFile - 图标文件（必填）
- **返回**: `DataResult<String>` - 图标存储路径

**POST /tool-apply/save-tool-software-pack**
- **参数**:
    - toolName: String - 工具名称（必填）
    - version: String - 版本号（必填）
    - versionName: String - 版本名称（必填）
    - operatingSystem: String - 操作系统（必填，值范围：windows/linux/mac/harmonyos）
    - softwarePack: MultipartFile - 软件包文件（必填）
- **返回**: `DataResult<String>` - 软件包存储路径

**POST /tool-apply/save-tool-apply**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolApplyDTO: ToolApplyDTO - 工具申请信息（必填）
- **返回**: `DataResult<String>` - 申请单ID

**GET /tool-apply/get-tool-apply-by-id**
- **参数**:
    - userId: String - 用户ID（必填）
    - id: String - 申请单ID（必填）
- **返回**: `DataResult<ToolApplyEntity>` - 工具申请实体

**POST /tool-apply/get-tool-apply-info**
- **参数**:
    - userId: String - 用户ID（必填）
    - queryToolApplyDTO: QueryToolApplyDTO - 查询条件（必填）
- **返回**: `DataResult<Map<String, Object>>` - 分页工具申请列表

**POST /tool-apply/update-tool-apply**
- **参数**:
    - userId: String - 用户ID（必填）
    - updateToolApplyDTO: UpdateToolApplyDTO - 更新信息（必填）
- **返回**: `DataResult<Void>` - 操作结果

**POST /tool-apply/undo-apply**
- **参数**:
    - userId: String - 用户ID（必填）
    - id: String - 申请单ID（必填）
- **返回**: `DataResult<Void>` - 操作结果

**POST /tool-apply/review**
- **参数**:
    - userId: String - 用户ID（必填）
    - reviewToolApplyDTO: ReviewToolApplyDTO - 审核信息（必填）
- **返回**: `DataResult<String>` - 审核结果

##### 4.3.2 ToolInfoController（工具信息控制器）

| API路径 | HTTP方法 | 功能描述 |
| --- | --- | --- |
| `/tool-info/get-by-tool-name` | GET | 根据工具名称/ID获取工具信息 |
| `/tool-info/get-tool-icon` | GET | 获取工具图标 |
| `/tool-info/get-tool-version` | POST | 获取工具版本列表 |
| `/tool-info/get-tool-list` | POST | 获取工具列表 |
| `/tool-info/update-tool-icon` | POST | 更新工具图标 |
| `/tool-info/update-tool-info` | POST | 修改工具信息 |
| `/tool-info/update-tool-version` | POST | 修改工具版本信息 |
| `/tool-info/query-tool-list` | POST | 查询有效工具列表 |
| `/tool-info/get-tool-detail` | GET | 获取工具详情 |
| `/tool-info/download-software-package` | GET | 下载软件包 |
| `/tool-info/delete-tool-info` | POST | 删除工具 |
| `/tool-info/delete-tool-version` | POST | 删除工具版本 |

**GET /tool-info/get-by-tool-name**
- **参数**:
    - toolId: String - 工具ID（二选一）
    - toolName: String - 工具名称（二选一）
- **返回**: `DataResult<ToolInfoEntity>` - 工具信息

**GET /tool-info/get-tool-icon**
- **参数**:
    - toolId: String - 工具ID（二选一）
    - toolName: String - 工具名称（二选一）
- **返回**: 文件流 - 图标文件

**POST /tool-info/get-tool-version**
- **参数**:
    - queryToolVersionDTO: QueryToolVersionDTO - 查询条件（必填）
- **返回**: `DataResult<Map<String, Object>>` - 工具版本列表

**POST /tool-info/get-tool-list**
- **参数**:
    - queryToolInfoDTO: QueryToolInfoDTO - 查询条件（必填）
- **返回**: `DataResult<Map<String, Object>>` - 工具列表

**POST /tool-info/update-tool-icon**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolId: String - 工具ID（必填）
    - iconFile: MultipartFile - 图标文件（必填）
- **返回**: `DataResult<String>` - 操作结果

**POST /tool-info/update-tool-info**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolInfoDTO: ToolInfoDTO - 工具信息（必填）
- **返回**: `DataResult<Void>` - 操作结果

**POST /tool-info/update-tool-version**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolVersionDTO: ToolVersionDTO - 版本信息（必填）
- **返回**: `DataResult<Void>` - 操作结果

**POST /tool-info/query-tool-list**
- **参数**:
    - queryToolListDTO: QueryToolListDTO - 查询条件（必填）
- **返回**: `DataResult<Map<String, Object>>` - 工具列表

**GET /tool-info/get-tool-detail**
- **参数**:
    - toolId: String - 工具ID（必填）
- **返回**: `DataResult<ToolDetailVO>` - 工具详情

**GET /tool-info/download-software-package**
- **参数**:
    - toolVersionId: String - 工具版本ID（必填）
- **返回**: 文件流 - 软件包文件

**POST /tool-info/delete-tool-info**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolId: String - 工具ID（必填）
- **返回**: `DataResult<Void>` - 操作结果

**POST /tool-info/delete-tool-version**
- **参数**:
    - userId: String - 用户ID（必填）
    - toolVersionId: String - 工具版本ID（必填）
- **返回**: `DataResult<Void>` - 操作结果

##### 4.3.3 ToolLabelInfoController（工具标签控制器）

| API路径 | HTTP方法 | 功能描述 |
| --- | --- | --- |
| `/tool-label/query-label` | POST | 分页查询标签列表 |
| `/tool-label/add-label` | POST | 新增标签 |
| `/tool-label/update-label` | POST | 修改标签 |
| `/tool-label/delete-label` | POST | 删除标签 |
| `/tool-label/get/label-select` | GET | 获取标签下拉列表 |

**POST /tool-label/query-label**
- **参数**:
    - userId: String - 用户ID（必填）
    - label: String - 标签名称（可选）
    - pageNum: Integer - 页码（必填，范围：1~Integer.MAX_VALUE）
    - pageSize: Integer - 每页数量（必填，范围：1~100）
- **返回**: `DataResult<Map<String, Object>>` - 分页标签列表

**POST /tool-label/add-label**
- **参数**:
    - userId: String - 用户ID（必填）
    - label: String - 标签名称（必填）
- **返回**: `DataResult<String>` - 标签ID

**POST /tool-label/update-label**
- **参数**:
    - userId: String - 用户ID（必填）
    - label: String - 标签名称（必填）
    - labelId: String - 标签ID（必填）
- **返回**: `DataResult<Void>` - 操作结果

**POST /tool-label/delete-label**
- **参数**:
    - userId: String - 用户ID（必填）
    - labelId: String - 标签ID（必填）
- **返回**: `DataResult<String>` - 操作结果

**GET /tool-label/get/label-select**
- **参数**:
    - label: String - 标签名称（可选）
- **返回**: `DataResult<List<ToolLabelInfoEntity>>` - 标签列表

### 4.4 apoll配置清单

新增apoll配置清单：
| namespaces | 配置项  | 配置说明 |
| --- | --- | --- |
| **framework** | obs.tool-bucket | 二进制工具信息桶 |
| **framework** | send.email.tool-apply.limiter.time | 邮件限制时间 （单位：秒） |
| **framework** | send.email.tool-apply.limiter.number | 邮件限制次数 |

### 4.5 任务清单

| 任务 ID | 任务描述 (Task Description) | 预期产出 (Deliverables) | 预期工作量（人天） |
| --- | --- | --- |-----------|
| **task1** | ToolApplyController接口实现 | 工具申请相关接口代码 | 8         |
| **task2** | ToolInfoController接口实现 | 工具信息相关接口代码 | 7         |
| **task3** | ToolLabelInfoController接口实现 | 工具标签相关接口代码 | 2         |

---

## 5. 需求相关性分析

> **操作说明**：根据上述拆解出的 Task，识别其变更行为。任何一项勾选为“是”：打上对应issue标签，必须执行对应的流程门禁。全部未勾选：该需求自动判定为轻量化特性，打上need_light标签。

### A. 安全相关性分析

> *若涉及以下任一项，打标 `need_security`标签，PR 必须关联特性issue的架构设计文档（含安全设计部分）**如勾选需要给出原因**。

* [ ] **边界变更**：新增公网端口、修改防火墙规则、变更网关配置。
* [ ] **凭证处理**：涉及密钥（Secret/Key）、Token、证书的存储或分发。
* [ ] **权限调整**：修改权限模型、服务账号（SA）权限或鉴权逻辑。
* [ ] **供应链**：引入新的第三方二进制文件、SDK 或重大版本依赖升级。
* [ ] **隐私风险评估**：涉及用户个人数据（Email、手机号、IP、邮箱 等）的处理。
* [ ] **AI使用**：涉及AIGC能力应用，并提供服务。

### B. 架构设计相关性分析

> *若涉及以下任一项，打标 `need_design`标签，PR 必须关联特性issue的架构设计文档。 **如勾选需要给出原因**。

* [ ] A环节判定需要完成安全设计
* [ ] 改变了现有系统的物理/逻辑拓扑
* [x] 新增或大幅修改对外暴露的 API/CLI 接口 原因：新增工具申请、工具信息、工具标签三个模块的接口
* [ ] 引入了新的中间件、数据库或三方核心组件

### C. 系统集成测试相关性分析

> *若涉及以下任一项，打标 `need_itest`标签，PR必须关联特性issue的测试策略和测试报告文档。 **如勾选需要给出原因**。

* [ ] 上述环节判定需要执行安全设计或架构设计。
* [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [x] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑。原因：工具申请、工具信息管理、工具标签管理均涉及完整的CRUD操作流程

### D. 用户体验相关性分析

> *若涉及以下任一项，打标 `need_ux`标签，PR必须关联特性issue的用户体验设计文档。 **如勾选需要给出原因**。

* [x] **交互逻辑变更**：涉及 Web 门户、控制台（Dashboard）或命令行工具（CLI）的交互流程调整。原因：工具申请流程、工具管理界面、标签管理界面均涉及前端交互逻辑
* [ ] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。
* [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [ ] **无障碍与多语种**：涉及国际化（i18n）支持、辅助功能或不同终端（移动端/桌面端）的适配。

### 5.1 需求相关性分析汇总结果

* [x] need_security (需架构设计（含安全威胁分析和安全设计）)
* [x] need_design (需架构设计)
* [x] need_itest (需执行测试策略设计和全链路集成测试)
* [ ] need_ux (需架构设计（含UX设计)）
* [ ] need_light (上述均未勾选，走快速合入通道)