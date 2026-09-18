# 自动化 QEMU 部署创建接口支持指定机器 IP — 实现任务

业务 Issue：[#31](https://gitcode.com/openlibing/openlibing-simulation/issues/31)（早期记录 [#30](https://gitcode.com/openlibing/openlibing-simulation/issues/30)）
技术设计：见同目录 `design.md`（**资源余量判定只在异步阶段、由 SQL 完成，同步不判**）

## 进度: 0/21 complete

### 数据库层

- [ ] D1: 新增 Liquibase changeSet，为 `t_qemu_task_config` 增加 `server_ip` 列
      （`VARCHAR(64)`，可空，默认 NULL；只追加 changeSet，不改动既有 changeSet；
      **不需要**改 `db.changelog.xml`，其第 15 行已 include `t_qemu_task_config.xml`）
      参考：`resources/db/changelog/v1.0.0/t_qemu_task_config.xml`

### DTO / 实体层

- [ ] E1: `entity/dto/QemuTaskConfigCreateDTO.java` 新增 `serverIp` 字段
      （可选；`@Pattern` 校验 IPv4 格式，允许为空/不传）
- [ ] E2: `entity/qemu/QemuTaskConfigEntity.java` 新增 `serverIp` 字段
- [ ] E3: `QemuTaskServiceImpl#mapConfigDtoToEntity` 新增 `entity.setServerIp(dto.getServerIp())`
      （该方法为逐字段白名单拷贝，必须显式补一行）
- [ ] E4: `entity/nodemanage/SimulationDeployResultEntity.java` 新增 `serverIp` 字段
      （异步链路承载指定 IP；**注意别改错同名类** `entity/qemu/SimulationDeployResultEntity.java`，后者全仓无引用）

> 本次**不需要**改 `ServerBasicInfoEntity`：余量判定由 SQL 的 `Having` 完成，Java 侧不做比较。

### Mapper 层

- [ ] M1: `resources/mapper/QemuTaskMapper.xml` 的 `insertOrUpdateConfig` 增加 `server_ip`，
      **三处都要改**：insert 列清单、`values(...)`、`on DUPLICATE KEY UPDATE`
- [ ] M2: 新增"按 `taskId` 反查 `server_ip`"的查询 `getSpecifiedServerIpByTaskId`
      （`NodeManageMapper.java` + `NodeManageMapper.xml`，供异步链路读取指定机器；走既有 `task_id` 索引）
- [ ] M3: 新增"指定机器是否存在"的查询 `countServerByIp`（`NodeManageMapper.java` + `NodeManageMapper.xml`）
      `SELECT COUNT(1) FROM t_server_basic_info WHERE is_deleted = "0" AND ip = #{serverIp}`，返回 `int`
      —— **只判存在性，不判资源**
- [ ] M4: 新增"按指定 IP 查机器且资源余量必须足够"的查询 `getServerFreeResourceByIp`
      （`NodeManageMapper.java` + `NodeManageMapper.xml`，入参 `serverIp` / `useCpu` / `useMemory`）
      复用 `getDynamicComputeFreeServerIp` 的聚合口径，`WHERE info.is_deleted='0' AND info.ip = #{serverIp}`，
      并加 `HAVING info.overcommit_cpu >= (COALESCE(SUM(us.cpu),0) + #{useCpu})`
      与 `HAVING info.overcommit_memory >= (COALESCE(SUM(us.memory),0) + #{useMemory})`
      —— **两行 Having 必须与 `NodeManageMapper.xml` #292-293 逐字对齐**；
      **刻意不带** `creator` 过滤，也**不带** `ext.extend_value like '%subScene%'` 与 `architecture` 过滤
- [ ] M5: 新增"按 `engineId + yamlManageId` 解析部署规格"的查询 `getQemuDeploySpec`
      （`NodeManageMapper.java` + `NodeManageMapper.xml`，`resultType` 用 `QemuDynamicEntity`）
      原因：预检在写库前执行，`task.getId()` 尚未赋值、`t_qemu_task_config` 也无对应行，
      不能复用按 `task_id` 查的 `getQemuYamlManage`；
      字段对齐 `getQemuYamlManage`（`eng.engine_type` / `cont.cpu` / `cont.memory` / `cont.id`）

### Service 层（同步预检）

- [ ] S1: `NodeManageServiceImpl` 新增私有方法 `getDeployResultListByConfig(config)`：
      调 `getQemuDeploySpec` 取 `QemuDynamicEntity`，用 `config.getNodeNumber()` 回填 `nodeNumber`，
      再复用既有 `getDeployResultList` / `buildQemuDeployResult`（**不搬迁**既有私有方法）
- [ ] S2: `NodeManageService` + `NodeManageServiceImpl` 新增公开方法
      `checkSpecifiedServer(QemuTaskConfigEntity config, String serverIp)`，**纯读、不加锁**（方案 A），
      **只校验 3 件事**：
      规格不可解析 → 2003 `cannot resolve deploy spec, please check engineId/yamlManageId`；
      部署单元数 != 1 → 2003 `specified server ip only supports single machine deployment`；
      `countServerByIp(serverIp) == 0` → 2003 `specified server ip not found`。
      **不判 CPU / 内存余量**
- [ ] S3: `QemuTaskServiceImpl#saveAutoQemuTask` 插入同步预检调用，位置为 `checkParam`（#261）之后、
      `taskId` 生成（#265）之前（**写库前**，失败时无需回滚已写入的 task / config 行）；
      `serverIp` 为空时跳过，保持原行为

### Service 层（异步选机改造）

- [ ] N1: `NodeManageServiceImpl#createQemuEnv` 在拿到 `simulationDeployResultList` 后，
      调 `getSpecifiedServerIpByTaskId(taskId)` 反查并回填到每个 `SimulationDeployResultEntity.serverIp`
      （为空时打 INFO 日志说明走自动分配）
- [ ] N2: `NodeManageServiceImpl#getServerNodes` 改为双分支：
      `serverIp` 非空时调 `getServerFreeResourceByIp(serverIp, useCpu, useMemory)` 单点取机
      （**不再调 `getDynamicComputeFreeServerIp`**），取不到 → 空列表、取到 → `singletonList`；
      为空时保持原有自动选机逻辑与 SQL 完全不变
- [ ] N3: 指定 IP 分支确认**不对资源做 Java 侧判定**（余量由 M4 的 `Having` 承担），
      且**不加** `creator='triton'` 过滤（`getServerNodes` 第 315 行的硬编码只影响自动选机路径，保持原样）。
      取不到机器时由既有 `serverList.size() == machineCount` 判定给出 `hasEnoughEnv=false`，
      沿用既有 `allocateNode` 失败路径（不写 `t_server_using`、任务置 FAILED）；
      **不新增**异步侧错误文案 / 状态 / 重试分支，仅在 `log.warn` 中带出 `serverIp` + `useCpu` + `useMemory`

### 测试与验证

- [ ] T1: 为同步预检新增单测，覆盖 5 个分支：机器存在且规格正常 / 机器不存在 / 未指定 IP 走原逻辑 /
      部署单元数 != 1 / 规格无法解析；**并补一条反向用例**——机器存在但余量不足时同步仍返回 `code=200`
- [ ] T2: 异步选机单测：指定 IP 且 SQL 返回机器 → `getDynamicComputeFreeServerIp` **未被调用**且落 `t_server_using`；
      指定 IP 但 SQL 返回 null（余量不足 / 机器已删除）→ `hasEnoughEnv=false`、**不写** `t_server_using`、任务置 FAILED；
      未指定 IP → `getDynamicComputeFreeServerIp` 被调用（回归保护）
- [ ] T3: `QemuTaskControllerTest` 补充携带 `config.serverIp` 的 POST 用例
- [ ] T4: `mvn test` 全量通过，并核对 `target/surefire-reports/`
      （注意 `surefire testFailureIgnore=true`，测试失败仍会 `BUILD SUCCESS`）
- [ ] T5: pre-commit（gitleaks + google-java-format）通过；业务 PR 关联 #31 并打 `ai-assisted` 标签

### 涉及文件（预估新增/修改）

新增 Java：无（不建议新建 Service / Controller；`SimulationDeployResultEntity` 为既有类扩展）
新增 XML：无（新增 changeSet 直接追加到既有 `t_qemu_task_config.xml`）
修改 Java：`entity/dto/QemuTaskConfigCreateDTO.java`、`entity/qemu/QemuTaskConfigEntity.java`、
`entity/nodemanage/SimulationDeployResultEntity.java`、`service/NodeManageService.java`、
`service/impl/NodeManageServiceImpl.java`、`service/impl/QemuTaskServiceImpl.java`、`mapper/NodeManageMapper.java`
修改 XML：`QemuTaskMapper.xml`、`NodeManageMapper.xml`、`db/changelog/v1.0.0/t_qemu_task_config.xml`
修改测试：`QemuTaskControllerTest.java` + 同步预检 / 异步选机对应单测类

### 待办（非编码）

- [x] 修订 Issue #31：已去掉"同步校验资源余量 / 同步返回 2003"的表述
      （2026-09-18 完成；主成功场景 2/4、扩展场景 2/5、约束 4/5/7 已同步，实现与文案口径一致）
