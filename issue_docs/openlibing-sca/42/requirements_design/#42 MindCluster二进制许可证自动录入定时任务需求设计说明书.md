# #42 MindCluster二进制许可证自动录入定时任务需求设计说明书

## 1. 基础信息

* **需求链接**: **[TODO]**
* **需求名称**: **MindCluster二进制许可证自动录入与合规性检查定时任务**
* **开发责任人**: **[TODO]**

---

## 2. 需求场景说明

> 在MindCluster产品发布新版本后，SCA平台需要自动获取其对应二进制制品的许可证信息并录入系统，同时执行许可证合规性检查。当前该流程依赖人工触发或手动操作，存在录入滞后、遗漏和合规风险。通过定时任务自动完成从SBOM平台获取版本配置、查询制品、导出SBOM、解析许可证并录入的全流程，确保MindCluster各版本/产品/OS/架构/构建来源组合的许可证数据及时、完整地进入SCA系统。

**场景描述**：MindCluster产品在SBOM平台上维护了多维度配置树（版本号→软件名→操作系统→系统架构→构建来源），SCA平台需要定时遍历该配置树的所有叶子节点，逐一查询对应制品、获取SBOM文件、解析SPDX许可证信息并录入数据库，同时执行许可证合规性检查。

---

## 3 需求验收标准

> 明确需求完成的标志，必须是可量化、可测试的。

- [x] 定时任务按配置的cron表达式（默认每1分钟）自动执行
- [x] 多实例部署时通过分布式锁保证同一环境仅一个实例执行，避免重复录入
- [x] 能正确遍历MindCluster配置树，获取所有版本×产品×OS×架构×构建来源的组合
- [x] 对每个组合查询SBOM制品并获取name字段，name为空时跳过并记录warn日志
- [x] 能从SBOM导出的tar包中提取SPDX JSON格式的许可证数据
- [x] 许可证数据成功录入`tbl_binary_pro_info`表（`enter`方法）
- [x] 许可证合规性检查数据成功录入`tbl_license_compliance`表（`enter2`方法）
- [x] 已录入的版本（通过SPDXID去重）不会重复录入
- [x] 单个版本处理异常不影响其他版本继续处理
- [x] 分布式锁在任务完成或异常时均能正确释放

---

## 4. 需求设计与分解

### 4.1 核心逻辑方案

定时任务`autoMindClusterLicenseSchedule`的核心数据流如下：

```
┌─────────────────────────────────────────────────────────────────┐
│                   Spring @Scheduled 触发                        │
│              cron: job.cron.auto.mindcluster.binary.license.task│
│                    默认: 0 0/1 * * * ?                          │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 获取分布式锁                                            │
│  lockKey = "autoMindClusterLicenseSchedule_{env}"               │
│  Redisson tryLock(wait=5s, leaseTime=-1 看门狗续期)              │
│  获取失败 → 跳过执行，记录info日志                                │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: 获取MindCluster版本列表                                 │
│  binaryLicenseEnterUtils.getMindClusterVersion("MindCluster")   │
│  → 调用 openlibingSbomClient.queryProductConfig("MindCluster")  │
│  → 递归遍历配置树 valueToNextConfig                              │
│  → 返回 List<MindClusterBinaryLicenseDto>                       │
│     (version, productName, os, arch, buildFrom)                 │
│  列表为空 → 直接返回                                             │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: 遍历每个版本组合                                        │
│  for (MindClusterBinaryLicenseDto dto : versionList)            │
│    ├─ 构建 attributes Map: version/productName/os/arch/buildFrom│
│    ├─ 调用 openlibingSbomClient.queryProduct("MindCluster", attr)│
│    ├─ 校验响应: code==200 && data!=null                          │
│    ├─ 解析 data.name 字段                                        │
│    ├─ 调用 binaryLicenseEnterUtils.getLicenseFromSbom(name)     │
│    │    → openlibingSbomClient.exportSbom(name,"spdx","2.2","json")│
│    │    → 从tar包提取 SPDX JSON                                   │
│    ├─ 调用 binaryLicenseEnterUtils.enter(sbomData, "MindCluster", version)│
│    │    → 解析packages → 写入 tbl_binary_pro_info                 │
│    └─ 调用 binaryLicenseEnterUtils.enter2(sbomData, "MindCluster", version)│
│         → 解析packages → 写入 tbl_license_compliance              │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: finally 释放分布式锁                                    │
│  lockService.releaseLock(lockKey)                               │
│  异步释放，避免阻塞                                               │
└─────────────────────────────────────────────────────────────────┘
```

**关键设计决策**：

1. **分布式锁**：使用Redisson分布式锁，lockKey拼接环境变量`env`实现多环境隔离；`leaseTime=-1`启用看门狗自动续期，防止任务执行时间超过锁过期时间导致并发问题；finally块确保锁一定释放。
2. **配置树遍历**：MindCluster在SBOM平台的配置为多层级树结构（version→productName→os→arch→buildFrom），通过递归`traverseMindClusterConfigTree`方法将所有叶子节点展平为`MindClusterBinaryLicenseDto`列表。
3. **双次录入**：`enter`负责许可证信息录入（写入`tbl_binary_pro_info`），`enter2`负责许可证合规性检查录入（写入`tbl_license_compliance`），两者均通过SPDXID去重避免重复录入。
4. **容错设计**：单个版本处理异常（JSON解析异常、运行时异常）通过try-catch捕获后continue，不影响其他版本；queryProduct失败同样continue跳过。
5. **JSON解析双重序列化**：`response.getData()`先通过`JSON.toJSONString`（fastjson）序列化为字符串，再通过`ObjectMapper.readTree`（Jackson）解析为JsonNode，这是因为Feign返回的data对象类型不确定，需要统一转为JSON树结构进行字段提取。

### 4.2 数据库设计

**表名：tbl_binary_pro_info**（许可证信息表，已有表，`enter`方法写入）

| 字段名               | 数据类型         | 约束 | 描述     |
|-------------------|--------------|------|--------|
| id                | VARCHAR(36)  | PRIMARY KEY | 主键UUID |
| spdx_id           | VARCHAR(128) | UNIQUE | SPDX文档唯一标识，用于去重 |
| repo_id           | VARCHAR(36)  | - | 仓库ID |
| community         | VARCHAR(64)  | - | 社区/产品类型（如MindCluster） |
| version           | VARCHAR(64)  | - | 版本号 |
| related_element   | VARCHAR(256) | - | 包SPDXID |
| host_license      | VARCHAR(256) | - | 声明许可证 |
| delete_flag       | TINYINT(1)   | DEFAULT 0 | 是否删除 |
| create_time       | DATETIME     | - | 创建时间 |
| update_time       | DATETIME     | - | 修改时间 |

**表名：tbl_license_compliance**（许可证合规性检查表，已有表，`enter2`方法写入）

| 字段名               | 数据类型         | 约束 | 描述     |
|-------------------|--------------|------|--------|
| id                | INT(32)      | PRIMARY KEY, AUTO_INCREMENT | 主键ID |
| spdx_id           | VARCHAR(128) | - | SPDX文档唯一标识，用于去重 |
| community         | VARCHAR(64)  | - | 社区/产品类型 |
| version           | VARCHAR(64)  | - | 版本号 |
| package_name      | VARCHAR(256) | - | 包名称 |
| license_declared  | VARCHAR(256) | - | 声明许可证 |
| license_concluded | VARCHAR(256) | - | 结论许可证 |
| compliance_status | VARCHAR(32)  | - | 合规状态 |
| delete_flag       | TINYINT(1)   | DEFAULT 0 | 是否删除 |
| create_time       | DATETIME     | - | 创建时间 |
| update_time       | DATETIME     | - | 修改时间 |

### 4.3 接口设计

本需求为定时任务，不直接暴露HTTP接口，但依赖以下SBOM平台远程接口：

##### 4.3.1 查询产品配置接口
- **URL**: `GET /sbom-api/queryProductConfig`
- **参数**: productType: String - 产品类型（如"MindCluster"）
- **返回**: `ResponseEntity` - 包含多层级配置树的响应对象
- **调用方**: `BinaryLicenseEnterUtils.getMindClusterVersion()`

##### 4.3.2 查询产品接口
- **URL**: `POST /sbom-api/queryProduct`
- **参数**:
    - productType: String - 产品类型
    - attributes: Map<String, String> - 查询属性（version/productName/os/arch/buildFrom）
- **返回**: `ResponseEntity` - 包含制品信息的响应对象，data.name为制品名称
- **调用方**: `MindClusterLicenseSchedule.autoMindClusterLicenseSchedule()`

##### 4.3.3 导出SBOM接口
- **URL**: `POST /sbom-api/exportSbom`
- **参数**:
    - productName: String - 制品名称
    - spec: String - 规范类型（固定"spdx"）
    - specVersion: String - 规范版本（固定"2.2"）
    - format: String - 格式（固定"json"）
- **返回**: `byte[]` - SBOM tar包字节数组
- **调用方**: `BinaryLicenseEnterUtils.getLicenseFromSbom()`

### 4.4 apoll配置清单

| 配置项                             | 说明          | 默认值                                  |
|---------------------------------|-------------|--------------------------------------|
| job.cron.auto.mindcluster.binary.license.task | MindCluster许可证录入定时任务cron表达式 | 0 0/1 * * * ? （每1分钟） |
| spring.profiles.active          | 当前环境标识，用于分布式锁key隔离 | - |
| sca.to.sbom.url                 | SBOM平台服务地址 | - |

### 4.5 任务清单

| 任务 ID              | 任务描述 (Task Description)            | 预期产出 (Deliverables) | 预期工作量（人天）   |
|--------------------|------------------------------------|---------------------|-------------|
| **task1** | 实现MindClusterLicenseSchedule定时任务主逻辑 | 定时任务类代码 | **1** |
| **task2** | 实现getMindClusterVersion配置树遍历与展平 | BinaryLicenseEnterUtils新增方法 | **1** |
| **task3** | 实现enter2许可证合规性检查录入 | BinaryLicenseEnterUtils新增方法 | **1.5** |
| **task4** | 编写单元测试（锁竞争/正常流程/异常容错/多版本） | 测试类代码 | **1** |

---

## 5. 需求相关性分析

### A. 安全相关性分析

**[无需打标]**

* [ ] **边界变更**：新增公网端口、修改防火墙规则、变更网关配置。
* [ ] **凭证处理**：涉及密钥（Secret/Key）、Token、证书的存储或分发。
* [ ] **权限调整**：修改权限模型、服务账号（SA）权限或鉴权逻辑。
* [ ] **供应链**：引入新的第三方二进制文件、SDK 或重大版本依赖升级。
* [ ] **隐私风险评估**：涉及用户个人数据的处理。
* [ ] **AI使用**：涉及AIGC能力应用，并提供服务。

### B. 架构设计相关性分析

**[无需打标]**

* [ ] A环节判定需要完成安全设计
* [ ] 改变了现有系统的物理/逻辑拓扑
* [ ] 新增或大幅修改对外暴露的 API/CLI 接口
* [ ] 引入了新的中间件、数据库或三方核心组件

### C. 系统集成测试相关性分析

**[无需打标]**

* [ ] 上述环节判定需要执行安全设计或架构设计。
* [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [ ] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑。

### D. 用户体验相关性分析

**[无需打标]**

* [ ] **交互逻辑变更**：涉及 Web 门户、控制台或命令行工具的交互流程调整。
* [ ] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。
* [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [ ] **无障碍与多语种**：涉及国际化支持、辅助功能或不同终端的适配。

### 5.1 需求相关性分析汇总结果

* [ ] need_security (需架构设计（含安全威胁分析和安全设计）)
* [ ] need_design (需架构设计)
* [ ] need_itest (需执行测试策略设计和全链路集成测试)
* [ ] need_ux (需架构设计（含UX设计)）
* [x] need_light (上述均未勾选，走快速合入通道)

---

## 6. 关键代码引用

| 组件 | 文件路径 |
|------|---------|
| 定时任务入口 | [MindClusterLicenseSchedule.java](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/common/schedule/MindClusterLicenseSchedule.java#L66-L119) |
| 版本配置树遍历 | [BinaryLicenseEnterUtils.getMindClusterVersion()](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java#L509-L536) |
| 许可证录入 | [BinaryLicenseEnterUtils.enter()](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java#L104) |
| 合规性检查录入 | [BinaryLicenseEnterUtils.enter2()](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java#L580) |
| SBOM导出 | [BinaryLicenseEnterUtils.getLicenseFromSbom()](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java#L390-L406) |
| 分布式锁服务 | [DistributedLockService.java](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/common/config/DistributedLockService.java) |
| SBOM Feign客户端 | [OpenlibingSbomClient.java](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/common/feign/OpenlibingSbomClient.java) |
| DTO定义 | [MindClusterBinaryLicenseDto.java](file:///d:/openlibing/openlibing-sca/src/main/java/com/openlibing/sca/common/domain/MindClusterBinaryLicenseDto.java) |
| 单元测试 | [MindClusterLicenseScheduleTest.java](file:///d:/openlibing/openlibing-sca/src/test/java/com/openlibing/sca/common/schedule/MindClusterLicenseScheduleTest.java) |
