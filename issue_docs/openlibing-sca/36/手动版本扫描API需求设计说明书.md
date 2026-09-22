# #36 手动版本扫描API需求设计说明书

## 1. 基础信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/36
* **需求名称**: 新增手动版本扫描管理接口（CRUD + 启动扫描）
* **开发责任人**: musheng

---

## 2. 需求场景说明

前端管理社区版本扫描并没有触发的场景，缺少完整的 CRUD + 扫描触发能力。需要补全完整的 REST 接口，使前端可以新增、查询版本扫描记录。

## 3 需求验收标准

- 新增记录接口：能够向 `tbl_manual_version_scan` 表插入一条记录，初始状态 `scanResult=null`、`scanId=null`
- 条件查询接口：支持按 `communityId`（精确）、`repoName`（模糊）、`repoUrl`（模糊）、`platform`（精确）查询记录
- 删除记录接口：能够按主键 ID 删除记录
- 启动扫描接口：调用后能够触发版本扫描，记录状态更新为 `scanResult=0`（扫描中），并返回 `scanId`
- 扫描完成回调：扫描成功后 `scanResult` 更新为 `1`，扫描失败后 `scanResult` 更新为 `-1`
- 回调更新不影响现有版本扫描流程

## 4. 需求设计与分解

| 功能点 | 描述 | 接口路径 | 方法 |
|-------|------|---------|------|
| 新增记录 | 向 tbl_manual_version_scan 表插入一条扫描记录 | /manual/version/scan/add | POST |
| 条件查询 | 按 communityId/repoName/repoUrl/platform 查询记录 | /manual/version/scan/list | POST |
| 删除记录 | 按主键 ID 删除记录 | /manual/version/scan/delete | POST |
| 启动版本扫描 | 触发版本扫描任务，更新记录状态 | /manual/version/scan/start | POST |
| 扫描结果回调 | 扫描完成后更新 scanResult 状态 | - | - |

### 4.1 核心逻辑方案

#### 4.1.1 架构设计

遵循项目现有分层架构：

```
Controller (REST) → Service (业务逻辑) → Mapper (DAO) → MySQL
                                         ↓
                              IntegrationApiService.startVersionScan()
                                         ↓
                                    RabbitMQ → doScanV3()
                                         ↓
                              saveVersionScanResult() → 回调更新
```

- **Controller 层**：`ManualVersionScanController` 提供 4 个 REST 接口
- **Service 层**：`ManualVersionScanServiceImpl` 实现业务逻辑，注入 `TblManualVersionScanMapper` 和 `IntegrationApiService`
- **DAO 层**：`TblManualVersionScanMapper` 对接 MySQL，方法与已有 XML 对应，新增 `updateByScanId` 方法
- **回调层**：在 `IntegrationApiServiceImpl.saveVersionScanResult` 中新增回调更新逻辑；在 `IntegrationApiListener` 异常路径中同步更新失败状态

#### 4.1.2 数据库设计

**表名：tbl_manual_version_scan**

| 字段名 | 数据类型 | 约束 | 描述 |
|-------|---------|------|------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| community_id | VARCHAR(64) | NOT NULL | 社区ID |
| repo_url | VARCHAR(128) | - | 仓库地址 |
| repo_name | VARCHAR(64) | - | 仓库名称 |
| repo_id | VARCHAR(64) | - | 仓库ID |
| branch | VARCHAR(64) | - | 分支 |
| scan_result | INT(2) | - | 扫描结果 (null/0/1/-1) |
| platform | VARCHAR(32) | - | 平台 |
| scan_id | VARCHAR(64) | - | 扫描ID |
| is_scan | INT(2) | - | 是否接入版本扫描 |
| created | DATETIME | - | 创建时间 |
| modified | DATETIME | - | 更新时间 |
| scan_time | DATETIME | - | 开始扫描时间 |

**scanResult 状态定义**

| 值 | 含义 | 设置时机 |
|----|------|----------|
| null | 未扫描 | 新增记录时 |
| 0 | 扫描中 | startScan 接口调用后 |
| 1 | 扫描完成 | saveVersionScanResult 回调 |
| -1 | 扫描失败 | IntegrationApiListener 异常回调 |

**状态流转**

```
null ──startScan──▶ 0 (扫描中) ──saveVersionScanResult──▶ 1 (扫描完成)
                                 ──异常路径──────────────▶ -1 (扫描失败)
```

#### 4.1.3 接口设计

##### 4.1.3.1 新增记录接口
- **URL**: `/manual/version/scan/add`
- **方法**: POST
- **参数**:
    - communityId: String - 社区ID
    - repoUrl: String - 仓库地址
    - repoName: String - 仓库名称
    - repoId: String - 仓库ID
    - branch: String - 分支
    - platform: String - 平台
    - isScan: Integer - 是否接入版本扫描
- **返回**: `ResponseEntity.success()`
- **逻辑**: 设置 created/modified 为当前时间，scanResult=null，scanId=null

##### 4.1.3.2 条件查询接口
- **URL**: `/manual/version/scan/list`
- **方法**: POST
- **参数**:
    - communityId: String - 社区ID（精确匹配）
    - repoName: String - 仓库名称（模糊匹配）
    - repoUrl: String - 仓库地址（模糊匹配）
    - platform: String - 平台（精确匹配）
- **返回**: `ResponseEntity(200, "查询成功", list, list.size())`

##### 4.1.3.3 删除记录接口
- **URL**: `/manual/version/scan/delete`
- **方法**: POST
- **参数**:
    - id: Integer - 记录主键ID
- **返回**: `ResponseEntity.success()`

##### 4.1.3.4 启动版本扫描接口
- **URL**: `/manual/version/scan/start`
- **方法**: POST
- **参数**:
    - id: Integer - 记录ID
    - repoUrl: String - 仓库地址
    - branch: String - 分支
    - projectName: String - 项目名称
- **返回**: `ResponseEntity.success(scanId)`
- **逻辑**:
  1. 构建 `VersionScanPo(repoUrl, branch, projectName)`
  2. 调用 `integrationApiService.startVersionScan(po)` 获取 scanId
  3. 更新记录：scanId=scanId, scanResult=0, modified=now, scanTime=now

#### 4.1.4 回调设计

##### 4.1.4.1 扫描成功回调
- **位置**: `IntegrationApiServiceImpl.saveVersionScanResult`
- **逻辑**: 在 `tblScanDMMapper.upload(scan)` 之后，调用 `tblManualVersionScanMapper.updateByScanId(scanRequestVO.getScanId(), 1)` 更新 scanResult=1

##### 4.1.4.2 扫描失败回调
- **位置**: `IntegrationApiListener` 异常处理路径
- **逻辑**: 调用 `tblManualVersionScanMapper.updateByScanId(scanId, -1)` 更新 scanResult=-1

##### 4.1.4.3 新增 Mapper SQL
```xml
<update id="updateByScanId">
    UPDATE tbl_manual_version_scan
    SET scan_result = #{scanResult}, modified = NOW()
    WHERE scan_id = #{scanId}
</update>
```

### 4.2 apoll配置清单

不涉及

### 4.3 任务清单

| 任务 ID | 任务描述 (Task Description) | 预期产出 (Deliverables) | 预期工作量（人天） |
|-------|-------------------------|---------------------|-----------|
| **1** | 创建 TblManualVersionScan 实体类 | Entity 代码 | 0.5       |
| **2** | 创建 TblManualVersionScanMapper 接口及 updateByScanId XML | Mapper 接口 + XML | 0.5       |
| **3** | 创建 ManualVersionScanService 接口及实现类 | Service 接口 + 实现类 | 2         |
| **4** | 创建 ManualVersionScanController | Controller 代码 | 1         |
| **5** | 修改 saveVersionScanResult 新增回调更新 | 回调逻辑代码 | 0.5       |
| **6** | 修改 IntegrationApiListener 新增异常回调 | 异常回调代码 | 0.5       |

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
* [ ] 新增或大幅修改对外暴露的 API/CLI 接口
* [ ] 引入了新的中间件、数据库或三方核心组件

### C. 系统集成测试相关性分析

> *若涉及以下任一项，打标 `need_itest`标签，PR必须关联特性issue的测试策略和测试报告文档。 **如勾选需要给出原因**。

* [ ] 上述环节判定需要执行安全设计或架构设计。
* [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [ ] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑。

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
* [ ] need_ux (需架构设计（含UX设计)）
* [ ] need_light (上述均未勾选，走快速合入通道)

---
