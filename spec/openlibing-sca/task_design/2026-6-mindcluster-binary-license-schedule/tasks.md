# Tasks: MindCluster Binary License Schedule

## Task 1: 定时任务调度与分布式锁 ✅

**文件**: `src/main/java/com/openlibing/sca/common/schedule/MindClusterLicenseSchedule.java`

- [x] 类注解 `@EnableAsync` `@EnableScheduling` `@Component`
- [x] `@Scheduled(cron = "${job.cron.auto.mindcluster.binary.license.task:0 0/1 * * * ?}")`
- [x] 锁键 = `autoMindClusterLicenseSchedule_<env>`，TTL = 5s
- [x] 获取锁失败 → INFO 日志 + return
- [x] `finally` 块释放锁

## Task 2: 版本列表获取 ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java`

- [x] `getMindClusterVersion("MindCluster")` 调用 `openlibingSbomClient.queryProductConfig`
- [x] 递归遍历 `valueToNextConfig` 配置树
- [x] 按 `levelName` 映射字段：version / productName / os / arch / buildFrom
- [x] 叶子节点收集为 `List<MindClusterBinaryLicenseDto>`
- [x] 异常捕获：`IllegalArgumentException` + 通用 `Exception`

## Task 3: 产品查询与名称提取 ✅

**文件**: `src/main/java/com/openlibing/sca/common/schedule/MindClusterLicenseSchedule.java`

- [x] 构建 attributes Map：version, productName, os, arch, buildFrom
- [x] 调用 `openlibingSbomClient.queryProduct("MindCluster", attributes)`
- [x] 响应校验：null / 非200 / data 为 null → WARN + continue
- [x] 解析 `response.data.name`：先 `JSON.toJSONString` 再 Jackson `readTree`
- [x] name 为空 → WARN + continue

## Task 4: 许可证数据导出 ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java`

- [x] `getLicenseFromSbom(name)` 调用 `openlibingSbomClient.exportSbom(name, "spdx", "2.2", "json")`
- [x] 检测 gzip 压缩（magic bytes `0x1f 0x8b`）
- [x] 解压 tar，提取 `.json` 文件内容
- [x] 清理特殊字符（`|`, `｜`, `\r`, `\n`）
- [x] 返回空字符串时上层静默 continue

## Task 5: 二进制许可证录入 (enter) ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java`

- [x] 提取 `SPDXID`，查询 `tbl_binary_pro_info` 幂等判断
- [x] 已存在或 `packages` 为空 → 跳过
- [x] 遍历 packages，提取 `name`、`licenseDeclared`、`externalRefs`
- [x] `saveDependentInfo()` 保存依赖关系 → `tbl_binary_dept_info`
- [x] `saveProInfo()` 保存主包信息 → `tbl_binary_pro_info`
- [x] `DataAccessException` 和通用 `Exception` 分别捕获

## Task 6: 许可证合规性检查 (enter2) ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/utils/binary/BinaryLicenseEnterUtils.java`

- [x] 提取 `SPDXID`，查询 `tbl_license_compliance` 幂等判断
- [x] 已存在或 `packages` 为空 → 跳过
- [x] `checkRpmLicense(licenseDeclared)` 合规性检查
- [x] `licenseCache` 缓存已检查许可证类型
- [x] `seenPackageNames` 去重
- [x] 分页批量插入 `tbl_license_compliance`
- [x] `DataAccessException` 和通用 `Exception` 分别捕获

## Task 7: 异常处理与日志 ✅

**文件**: `src/main/java/com/openlibing/sca/common/schedule/MindClusterLicenseSchedule.java`

- [x] `JsonProcessingException` → ERROR 日志 + continue
- [x] `RuntimeException` → ERROR 日志 + continue
- [x] `queryProduct` 失败 → WARN 日志（含 code + message）
- [x] `data.name` 为空 → WARN 日志
- [x] 锁获取失败 → INFO 日志

## Task 8: 单元测试 ✅

**文件**: `src/test/java/com/openlibing/sca/common/schedule/MindClusterLicenseScheduleTest.java`

- [x] 正常场景：获取锁 → 获取版本列表 → queryProduct → getLicenseFromSbom → enter + enter2
- [x] 多版本场景：验证每个版本都执行 enter + enter2
- [x] 获取锁失败场景
- [x] 版本列表为空场景
- [x] queryProduct 失败场景
- [x] data.name 为空场景
- [x] getLicenseFromSbom 返回空场景
- [x] JSON 解析异常场景
