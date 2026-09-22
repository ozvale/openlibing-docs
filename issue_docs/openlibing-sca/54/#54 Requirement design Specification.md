# #54 文件夹兼容性分析继承逻辑需求分析说明书

## 1. 基础信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/54
* **需求名称**: 文件级兼容性分析继承（License Manual Analysis Inheritance）
* **开发责任人**: qq_39751731

---

## 2. 需求场景说明

> 描述"在什么情况下，为了解决什么问题，用户需要做什么"。

在 SCA License 兼容性分析场景中，系统对仓库中的每个文件自动分析 License 兼容性（是否与仓库 License 兼容）。但自动判定存在误判可能——某些文件实际有风险但系统判定为兼容，或反之。运营人员需要对兼容性分析结果进行人工复核和覆盖。

核心痛点：历史人工分析结果无法复用。同一仓库的同一文件（内容不变）在不同扫描任务中会出现重复的未确认状态，运营人员需要反复对同一个文件做相同的判定。

**解决方案**：引入基于文件内容哈希（fileHash）的人工分析结果继承机制。运营人员在任意一次扫描中提交人工分析后，系统将结果持久化到 MySQL；后续任意扫描（无论同一仓库另一分支、另一版本、甚至另一仓库的相同文件）遇到相同的 fileHash 时，自动继承历史人工判定结果，且人工结论优先级高于自动判定。

## 3 需求验收标准

> 明确需求完成的标志，必须是可量化、可测试的。

- [x] 运营人员可通过 `POST /license/manualAnalysis/batch` 接口批量提交人工分析结果（风险等级 + 说明），同时写入 MongoDB license_issue 和 MySQL `tbl_license_manual_analysis`
- [x] 版本扫描兼容性分析流程中，每个文件自动根据 fileHash 从 `tbl_license_manual_analysis` 继承历史人工分析结果
- [x] 人工分析结果覆盖自动兼容性判定（人工风险等级为"有风险"→compatible="No"，"无风险"→compatible="Yes"）
- [x] 查询接口返回的 manualRiskLevel 字段展示中文描述（"有风险"/"无风险"），而非内部 code
- [x] fileHash 基于文件内容 MD5 计算，非文件名，保证跨路径/跨仓库的继承准确性
- [x] 继承失败不影响扫描主流程（异常被捕获并 warn 日志）

---

## 4. 需求设计与分解

> 说明：基于初步方案，将需求拆解为可实施的原子 Task。后续的流程判定将严格依据这些 Task 的影响范围进行。

### 4.1 核心逻辑方案

#### 数据流向

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          人工分析写入链路                                 │
│                                                                         │
│  运营前端                                                                │
│    │ POST /license/manualAnalysis/batch                                 │
│    ▼                                                                     │
│  LicenseController.batchManualAnalysis                                  │
│    │                                                                     │
│    ▼                                                                     │
│  LicenseServiceImpl.updateLicenseIssueManualAnalysis (per item)          │
│    │                                                                     │
│    ├─ ① MongoDB: license_issue._id + fileHash 联合定位                   │
│    │    ├─ manualRiskLevel (更新)                                        │
│    │    ├─ manualDescription (更新)                                      │
│    │    └─ compatible: 同步覆写 ("Yes"/"No")                             │
│    │                                                                     │
│    └─ ② MySQL: tbl_license_manual_analysis                              │
│         └─ upsertManualAnalysis (按fileHash查→存在update / 不存在insert)  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          人工分析继承链路                                 │
│                                                                         │
│  版本扫描触发兼容性分析                                                    │
│    │ IntegrationApiServiceImpl.processVersionJsonFile                   │
│    │                                                                     │
│    ├─ ① 预处理：computeFileMd5Hashes                                     │
│    │   └─ 遍历 workspace，逐文件计算 MD5 → Map<相对路径, md5>              │
│    │                                                                     │
│    ├─ ② 异步：compatibleVersion                                          │
│    │   └─ processFileLicenses (per file)                                 │
│    │     ├─ 创建 LicenseIssue                                            │
│    │     ├─ 设置预计算的 fileHash                                        │
│    │     ├─ 自动兼容性分析 (repo license vs local licenses)               │
│    │     ├─ ★ inheritManualAnalysis (按 fileHash 查 MySQL 继承)          │
│    │     │   └─ 有人工结果? → 覆盖 manualRiskLevel/compatible             │
│    │     └─ mongoTemplate.save → MongoDB license_issue                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          查询展示链路                                     │
│                                                                         │
│  运营前端                                                                │
│    │ POST /license/licenseIssue/query                                   │
│    ▼                                                                     │
│  LicenseServiceImpl.getLicenseIssue                                      │
│    ├─ MongoDB 分页查询 license_issue                                     │
│    └─ manualRiskLevel code → 中文描述转换 (ManualRiskLevel枚举)           │
│      └─ "0"→"无风险" / "1"→"有风险"                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 核心设计决策

1. **fileHash 使用文件内容 MD5**：非文件名哈希，确保跨路径、跨仓库、跨分支的继承准确性。同一文件内容在不同仓库中哈希值一致。
2. **MD5 预计算**：`compatibleVersion` 异步执行前，批处理入口先遍历 workspace 预计算所有文件 MD5。原因是异步执行时 workspace 可能已被 `analysisVersion` 删除，之后再读文件会失败。
3. **人工优先级高于自动**：`inheritManualAnalysis` 在自动兼容性分析之后执行，以人工结果覆盖自动判定。
4. **继承同步 compatible**：人工风险等级"有风险"→compatible="No"，"无风险"→compatible="Yes"。
5. **继承异常隔离**：`inheritManualAnalysis` 内 try-catch 所有异常，仅 warn 日志，不中断扫描主流程。

### 4.2 数据库设计

**表名：tbl_license_manual_analysis**（MySQL，License 人工分析结果表）

| 字段名 | 数据类型 | 约束 | 描述 |
|--------|---------|------|------|
| id | VARCHAR(64) | PRIMARY KEY, NOT NULL | 主键ID，UUID |
| file_hash | VARCHAR(128) | NOT NULL, INDEX (idx_lma_file_hash) | 文件内容 MD5 哈希，继承匹配的核心 key |
| risk_level | VARCHAR(16) | NOT NULL | 风险等级：0(无风险)/1(有风险) |
| description | VARCHAR(1024) | - | 人工分析说明 |
| analyzed_by | VARCHAR(64) | - | 分析人用户名 |
| scan_id | VARCHAR(64) | - | 关联扫描ID |
| file_path | VARCHAR(512) | - | 文件路径（首次提交时的路径，用于溯源） |
| created_at | DATETIME | - | 创建时间 |
| updated_at | DATETIME | - | 更新时间 |

**索引**：`idx_lma_file_hash` 单列索引覆盖 `file_hash` 查询，支撑 `selectByFileHash` 方法（ORDER BY updated_at DESC LIMIT 1）。

**Liquibase 变更集**：`src/main/resources/db/changelog/mysql/20260724/create-tbl-license-manual-analysis.xml`

### 4.3 接口设计

##### 4.3.1 批量人工分析接口

- **URL**: `/license/manualAnalysis/batch`
- **方法**: POST
- **请求体**: `List<LicenseAnalysisVO>`（JSON 数组，无需外层包装）
    - objectId: String（必填，MongoDB license_issue._id）
    - fileHash: String（必填，文件内容 MD5）
    - file: String（文件路径）
    - manualRiskLevel: String（风险等级 code："0"或"1"）
    - manualDescription: String（分析说明）
- **请求参数**: userName: String（分析人）
- **返回**: `ResponseEntity` - 批量分析完成或失败

##### 4.3.2 License 看板查询接口

- **URL**: `/license/repos`
- **方法**: GET
- **参数**: ScanCommunityDto（社区名称、分页参数等）
- **返回**: `ResponseEntity<List<LicenseInfoVO>>` - License 看板数据（含缓存）

##### 4.3.3 文件扫描结果查询接口

- **URL**: `/license/licenseIssue/query`
- **方法**: POST
- **请求体**: `QueryLicenseVO`
    - id: String（scanId，必填）
    - pageNo: int（页码，必填）
    - pageSize: int（每页条数，必填）
    - compatible: List\<String\>（兼容性筛选）
    - path: String（文件路径前缀匹配）
    - fileName: String（文件名模糊匹配）
- **返回**: `ResponseEntity<DPage<LicenseIssue>>` - 分页结果，manualRiskLevel 字段已转为中文描述

##### 4.3.4 一键刷新缓存接口

- **URL**: `/license/cache/refresh`
- **方法**: POST
- **参数**: 无
- **返回**: `ResponseEntity` - "缓存刷新已触发"（异步执行）

##### 4.3.5 树形展示接口

- **URL**: `/license/tree`
- **方法**: GET
- **参数**: scanId: String（必填）
- **返回**: `ResponseEntity` - License 文件树形数据

##### 4.3.6 导出接口

- **URL**: `/license/export/community`（GET）、`/license/export/unconfirmed`（GET）
- **方法**: GET
- **参数**: community（社区名称）、platform（平台，可选）、userId（用户ID）
- **返回**: `ResponseEntity` - 导出文件名（异步导出）

### 4.4 Apollo 配置清单

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| licenseScanCacheTtlMinutes | License 看板缓存 TTL（分钟） | 120（2小时） |

### 4.5 任务清单

| 任务 ID | 任务描述 (Task Description) | 预期产出 (Deliverables) | 涉及文件 |
|---------|---------------------------|------------------------|----------|
| **task1** | 创建 `tbl_license_manual_analysis` 表及 Mapper | Liquibase changelog + Entity + Mapper 接口 + XML 映射 | `LicenseManualAnalysis.java`、`LicenseManualAnalysisMapper.java`、`LicenseManualAnalysisMapper.xml`、`create-tbl-license-manual-analysis.xml` |
| **task2** | 新增 `ManualRiskLevel` 枚举 | 枚举类 + `getDescriptionByCode` 工具方法 | `ManualRiskLevel.java` |
| **task3** | 新增 `LicenseAnalysisVO` 请求对象 | VO（含 `@NotBlank` 校验） | `LicenseAnalysisVO.java` |
| **task4** | 实现批量人工分析接口 `POST /license/manualAnalysis/batch` | Controller 端点 + Service 方法（MongoDB 更新 + MySQL upsert） | `LicenseController.java`、`LicenseServiceImpl.java` |
| **task5** | 实现 `computeFileMd5Hashes` 预计算方法 | 批处理前遍历 workspace 计算 MD5 Map | `IntegrationApiServiceImpl.java` |
| **task6** | 实现 `inheritManualAnalysis` 继承方法 | 按 fileHash 查 MySQL → 覆盖 LicenseIssue 字段 | `IntegrationApiServiceImpl.java` |
| **task7** | 在 `processFileLicenses` 中集成继承逻辑 | 自动分析后调用 inheritManualAnalysis | `IntegrationApiServiceImpl.java` |
| **task8** | 查询接口 manualRiskLevel 中文描述转换 | `getLicenseIssue` 中使用 `getDescriptionByCode` | `LicenseServiceImpl.java` |

---

## 5. 需求相关性分析

> **操作说明**：根据上述拆解出的 Task，识别其变更行为。任何一项勾选为"是"：打上对应issue标签，必须执行对应的流程门禁。全部未勾选：该需求自动判定为轻量化特性，打上need_light标签。

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
* [ ] 新增或大幅修改对外暴露的 API/CLI 接口（新增 `/license/manualAnalysis/batch` 接口）
* [ ] 引入了新的中间件、数据库或三方核心组件 **[勾选必填]** _原因：新增 MySQL 表 `tbl_license_manual_analysis`，新增 Redis 缓存与定时任务_

### C. 系统集成测试相关性分析

> *若涉及以下任一项，打标 `need_itest`标签，PR必须关联特性issue的测试策略和测试报告文档。 **如勾选需要给出原因**。

* [ ] 上述环节判定需要执行安全设计或架构设计。
* [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [ ] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑（前端→Controller→MongoDB+MySQL 双写→扫描继承→前端展示）。

### D. 用户体验相关性分析

> *若涉及以下任一项，打标 `need_ux`标签，PR必须关联特性issue的用户体验设计文档。 **如勾选需要给出原因**。

* [ ] **交互逻辑变更**：涉及 Web 门户、控制台（Dashboard）或命令行工具（CLI）的交互流程调整。
* [ ] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。
* [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [ ] **无障碍与多语种**：涉及国际化（i18n）支持、辅助功能或不同终端（移动端/桌面端）的适配。

### 5.1 需求相关性分析汇总结果

* [ ] need_security (需架构设计（含安全威胁分析和安全设计）)
* [ ] need_design (需架构设计)
* [ ] need_itest (需执行测试策略设计和全链路集成测试)
* [ ] need_ux (需架构设计（含UX设计）)
* [ ] need_light (上述均未勾选，走快速合入通道)
