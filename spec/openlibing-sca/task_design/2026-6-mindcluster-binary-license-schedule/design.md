# Design: MindCluster Binary License Schedule

## Architecture

定时任务遵循 Spring Scheduling + 分布式锁的标准模式，编排 SBOM 数据拉取与 SCA 数据写入：

```
MindClusterLicenseSchedule (Cron Trigger)
    │
    ├── DistributedLockService ─── Redis/Mongo
    │
    ├── OpenlibingSbomClient (Feign) ─── SBOM Platform
    │       ├── queryProductConfig(productType)     → GET  /sbom-api/queryProductConfig
    │       ├── queryProduct(productType, attrs)    → POST /sbom-api/queryProduct
    │       └── exportSbom(name, format, ver, type) → GET  /sbom-api/exportSbom
    │
    └── BinaryLicenseEnterUtils
            ├── getMindClusterVersion(productType)  → 遍历配置树
            ├── getLicenseFromSbom(name)            → tar/gz → JSON
            ├── enter(fromSbom, community, version) → tbl_binary_pro_info + tbl_binary_dept_info
            └── enter2(fromSbom, community, version)→ tbl_license_compliance
```

## Component Design

### MindClusterLicenseSchedule

| 属性 | 说明 |
|------|------|
| 类注解 | `@EnableAsync` `@EnableScheduling` `@Component` |
| cron | `${job.cron.auto.mindcluster.binary.license.task:0 0/1 * * * ?}` |
| 锁键 | `autoMindClusterLicenseSchedule_<env>` |
| 锁 TTL | 5 秒 |

**依赖注入**：

| 字段 | 类型 | 注入方式 |
|------|------|----------|
| `env` | `String` | `@Value("${spring.profiles.active}")` |
| `binaryLicenseEnterUtils` | `BinaryLicenseEnterUtils` | `@Autowired` |
| `lockService` | `DistributedLockService` | `@Resource` |
| `openlibingSbomClient` | `OpenlibingSbomClient` | `@Autowired` |

### MindClusterBinaryLicenseDto

| 字段 | 类型 | 说明 |
|------|------|------|
| version | String | 版本号 |
| productName | String | 产品名称 |
| os | String | 操作系统 |
| arch | String | 架构 |
| buildFrom | String | 构建来源 |

注解：`@Data` `@NoArgsConstructor` `@AllArgsConstructor`

### OpenlibingSbomClient 接口

| 方法 | HTTP | 路径 | 参数 | 返回 |
|------|------|------|------|------|
| `queryProductConfig(productType)` | GET | `/sbom-api/queryProductConfig` | `productType` (query) | `ResponseEntity` |
| `queryProduct(productType, attributes)` | POST | `/sbom-api/queryProduct` | `productType` (query), `attributes` (body) | `ResponseEntity` |
| `exportSbom(binaryName, format, version, type)` | GET | `/sbom-api/exportSbom` | 4 个 query 参数 | `byte[]` |

### BinaryLicenseEnterUtils 关键方法

#### getMindClusterVersion(productType)

1. 调用 `openlibingSbomClient.queryProductConfig(productType)` 获取配置树
2. 解析响应为 `JsonNode`，提取根节点 `name` 和 `valueToNextConfig`
3. 递归遍历 `valueToNextConfig`，按 `levelName` 映射到 DTO 字段：
   - `version` → `dto.setVersion(key)`
   - `productName` → `dto.setProductName(key)`
   - `os` → `dto.setOs(key)`
   - `arch` → `dto.setArch(key)`
   - `buildFrom` → `dto.setBuildFrom(key)`
4. 叶子节点（`valueToNextConfig` 为空或无子节点）加入结果列表

#### getLicenseFromSbom(binaryName)

1. 调用 `openlibingSbomClient.exportSbom(binaryName, "spdx", "2.2", "json")` 获取字节数组
2. 检测是否 gzip 压缩（magic bytes `0x1f 0x8b`）
3. 解压后遍历 tar 中的 `.json` 文件，提取第一个 JSON 文件内容
4. 清理 `|`、`｜`、`\r`、`\n` 字符后返回

#### enter(fromSbom, community, valueLabel)

1. 提取 `SPDXID`，查询 `tbl_binary_pro_info` 是否已存在
2. 若已存在或 `packages` 为空，跳过（幂等）
3. 遍历 `packages`，对每个包：
   - 提取 `name`、`licenseDeclared`、`externalRefs`
   - 调用 `saveDependentInfo()` 保存依赖关系
   - 调用 `saveProInfo()` 保存主包信息

#### enter2(fromSbom, community, version)

1. 提取 `SPDXID`，查询 `tbl_license_compliance` 是否已存在
2. 若已存在或 `packages` 为空，跳过
3. 遍历 `packages`，对每个包：
   - 提取 `licenseDeclared` 和 `SPDXID`
   - 调用 `checkRpmLicense(licenseDeclared)` 获取合规性结果
   - 使用 `licenseCache` 缓存已检查的许可证类型
   - 去重：`seenPackageNames` 防止重复包名
4. 分页批量插入 `tbl_license_compliance`

## Data Model

### 涉及数据库表

| 表 | 写入方法 | 说明 |
|----|----------|------|
| `tbl_binary_pro_info` | `enter()` | 二进制主包信息 |
| `tbl_binary_dept_info` | `enter()` | 二进制依赖关系 |
| `tbl_license_compliance` | `enter2()` | 许可证合规性记录 |

### 写入幂等性

- `enter()`：通过 `SPDXID` 查询 `tbl_binary_pro_info`，已存在则跳过
- `enter2()`：通过 `SPDXID` 查询 `tbl_license_compliance`，已存在则跳过

## Execution Flow

```
autoMindClusterLicenseSchedule()
│
├─ acquireLock(lockKey, 5)
│   └─ 失败 → return (日志: "un get lock")
│
├─ getMindClusterVersion("MindCluster")
│   └─ 空列表 → return
│
├─ for each dto in versionList:
│   │
│   ├─ 构建 attributes Map {version, productName, os, arch, buildFrom}
│   │
│   ├─ openlibingSbomClient.queryProduct("MindCluster", attributes)
│   │   └─ 失败 → WARN + continue
│   │
│   ├─ 解析 response.data.name
│   │   └─ 为空 → WARN + continue
│   │
│   ├─ binaryLicenseEnterUtils.getLicenseFromSbom(name)
│   │   └─ 为空 → continue
│   │
│   ├─ binaryLicenseEnterUtils.enter(fromSbom, "MindCluster", version)
│   │
│   └─ binaryLicenseEnterUtils.enter2(fromSbom, "MindCluster", version)
│
└─ finally: releaseLock(lockKey)
```

## Configuration

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `job.cron.auto.mindcluster.binary.license.task` | `0 0/1 * * * ?` | 定时任务 cron 表达式 |
| `spring.profiles.active` | - | 环境标识，用于锁键隔离 |
| `sca.to.sbom.url` | - | SBOM 平台地址 |

## Error Handling Matrix

| 异常场景 | 处理方式 | 日志级别 | 是否中断循环 |
|----------|----------|----------|-------------|
| 获取锁失败 | return | INFO | 终止整轮 |
| versionList 为空 | return | 无 | 终止整轮 |
| queryProduct 返回 null / 非200 / data 为 null | continue | WARN | 跳过当前版本 |
| data.name 为空 | continue | WARN | 跳过当前版本 |
| getLicenseFromSbom 返回空 | continue | 无 | 跳过当前版本 |
| JSON 解析异常 (JsonProcessingException) | catch + continue | ERROR | 跳过当前版本 |
| RuntimeException | catch + continue | ERROR | 跳过当前版本 |
| DataAccessException (enter/enter2 内部) | catch 内部处理 | ERROR | 不中断，但当前版本数据可能不完整 |
