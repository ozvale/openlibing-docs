# Proposal: MindCluster Binary License Schedule

## Summary

`MindClusterLicenseSchedule` 是一个定时任务组件，负责自动从 SBOM 平台拉取 MindCluster 产品的二进制许可证信息，录入到 SCA 系统中，并执行许可证合规性检查。该任务以可配置的 cron 表达式驱动（默认每分钟执行一次），通过分布式锁保证多实例部署下的幂等性。

## Motivation

MindCluster 作为公司内部产品，其二进制包的许可证信息需要定期同步到 SCA 平台，以支撑开源合规审计。手动录入效率低且易遗漏，因此需要自动化定时任务：

1. **自动发现版本**：从 SBOM 平台的产品配置树中遍历出所有 MindCluster 版本组合（version × productName × os × arch × buildFrom）
2. **自动录入许可证**：对每个版本组合查询 SBOM 产品、导出 SPDX 许可证数据、解析并写入 SCA 数据库
3. **自动合规性检查**：在许可证录入后立即执行合规性分析，将每个包的许可证声明与合规规则比对

## Scope

### 涉及文件

| 文件 | 角色 |
|------|------|
| `common/schedule/MindClusterLicenseSchedule.java` | 定时任务入口，调度与编排 |
| `analysis/utils/binary/BinaryLicenseEnterUtils.java` | 许可证录入与合规性检查核心工具 |
| `common/feign/OpenlibingSbomClient.java` | SBOM 平台 Feign 客户端 |
| `common/config/DistributedLockService.java` | 分布式锁服务 |
| `common/domain/MindClusterBinaryLicenseDto.java` | 版本组合 DTO |

### 核心方法

- `MindClusterLicenseSchedule.autoMindClusterLicenseSchedule()` — 定时任务主方法
- `BinaryLicenseEnterUtils.getMindClusterVersion(productType)` — 获取版本列表
- `BinaryLicenseEnterUtils.getLicenseFromSbom(name)` — 从 SBOM 导出许可证
- `BinaryLicenseEnterUtils.enter(fromSbom, community, version)` — 录入二进制包信息与兼容性
- `BinaryLicenseEnterUtils.enter2(fromSbom, community, version)` — 录入许可证合规性

### 不在范围内

- 不修改 SBOM 平台侧接口
- 不修改分布式锁实现
- 不涉及 openEuler 等其他产品的许可证录入流程

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   Cron Trigger (每分钟)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  Acquire Distributed   │  lockKey = autoMindClusterLicenseSchedule_<env>
              │  Lock (TTL=5s)         │  失败则跳过本轮
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  getMindClusterVersion │  GET /sbom-api/queryProductConfig?productType=MindCluster
              │  ("MindCluster")       │  递归遍历配置树 → List<MindClusterBinaryLicenseDto>
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  For each versionDto   │  attributes: {version, productName, os, arch, buildFrom}
              │  ┌──────────────────┐  │
              │  │ queryProduct     │  │  POST /sbom-api/queryProduct
              │  │ → extract name   │  │  解析 response.data.name
              │  ├──────────────────┤  │
              │  │ getLicenseFromSbom│  │  GET /sbom-api/exportSbom → tar → extract JSON
              │  ├──────────────────┤  │
              │  │ enter()          │  │  解析 SPDX → 写入 tbl_binary_pro_info + tbl_binary_dept_info
              │  ├──────────────────┤  │
              │  │ enter2()         │  │  解析 SPDX → 写入 tbl_license_compliance
              │  └──────────────────┘  │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  Release Lock          │  finally 块保证释放
              └────────────────────────┘
```

## Key Behaviors

### 1. 分布式锁

- 锁键：`autoMindClusterLicenseSchedule_<env>`（env 来自 `spring.profiles.active`）
- TTL：5 秒
- 获取失败则跳过本轮执行，日志记录 `un get lock`
- `finally` 块保证锁释放

### 2. 版本发现

- 调用 `openlibingSbomClient.queryProductConfig("MindCluster")` 获取产品配置树
- 递归遍历 `valueToNextConfig` 树结构，按层级映射到 DTO 字段（version → productName → os → arch → buildFrom）
- 叶子节点收集为 `List<MindClusterBinaryLicenseDto>`

### 3. 产品查询与许可证导出

- 对每个版本组合调用 `openlibingSbomClient.queryProduct("MindCluster", attributes)` 获取产品详情
- 从响应中提取 `data.name` 字段
- 调用 `openlibingSbomClient.exportSbom(name, "spdx", "2.2", "json")` 导出 SPDX 数据
- 返回的 tar/gz 数据中提取 JSON 文件内容

### 4. 许可证录入（enter）

- 解析 SPDX JSON 的 `SPDXID` 和 `packages` 数组
- 若 `tbl_binary_pro_info` 中已存在该 SPDXID，跳过（幂等）
- 对每个 package 提取 `name`、`licenseDeclared`、`externalRefs`
- 保存依赖关系到 `tbl_binary_dept_info`
- 保存主包信息到 `tbl_binary_pro_info`

### 5. 合规性检查（enter2）

- 解析 SPDX JSON 的 `SPDXID` 和 `packages` 数组
- 若 `tbl_license_compliance` 中已存在该 SPDXID，跳过
- 对每个 package 调用 `checkRpmLicense(licenseDeclared)` 检查合规性
- 批量插入到 `tbl_license_compliance`（分页，每页 PAGE_SIZE 条）

### 6. 错误处理

- `queryProduct` 失败（null / 非200 / data 为 null）：WARN 日志 + continue 跳过当前版本
- `data.name` 为空：WARN 日志 + continue
- `getLicenseFromSbom` 返回空：静默 continue
- JSON 解析异常：ERROR 日志 + catch 后 continue
- RuntimeException：ERROR 日志 + catch 后 continue
- DataAccessException（enter/enter2 内部）：ERROR 日志，不中断循环

## Risks

1. **锁 TTL 过短**：当前 TTL 仅 5 秒，若版本列表较大或 SBOM 响应慢，可能在一轮未完成时锁已过期，导致下一轮重复执行
2. **无重试机制**：`queryProduct` 或 `exportSbom` 失败后直接跳过，不会在后续轮次中优先重试失败项
3. **串行处理**：所有版本组合串行遍历，版本数量多时一轮执行时间可能超过 cron 间隔
4. **双重 JSON 序列化**：`enter` 方法中先 `JSON.toJSONString(response.getData())` 再用 Jackson `readTree` 解析，存在不必要的序列化/反序列化开销
5. **异常粒度**：内层 catch 只捕获 `JsonProcessingException` 和 `RuntimeException`，`enter`/`enter2` 内部的 `DataAccessException` 不会中断外层循环但可能导致部分数据不一致
