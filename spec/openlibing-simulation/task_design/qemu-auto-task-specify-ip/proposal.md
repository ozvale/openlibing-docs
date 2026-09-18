# 自动化 QEMU 部署创建接口支持指定机器 IP

## 需求背景

- 业务 Issue：[#31](https://gitcode.com/openlibing/openlibing-simulation/issues/31)「【蓝区】openlibing-simulation 支持按指定IP创建UB仿真环境」
  （同一需求的早期提出记录：[#30](https://gitcode.com/openlibing/openlibing-simulation/issues/30)）
  需求原文：`/qemu/auto/task` POST 部署接口中支持向指定的机器 IP 部署，部署之前先检查机器剩余的 CPU、内存能否满足部署，
  如果不满足接口返回失败，如果满足往下继续执行部署逻辑。
- 现状：
  - 入口 `POST /simulation/qemu/auto/task`（`QemuTaskController#saveAutoQemuTask`）的入参 DTO 中**没有任何机器 / IP 字段**，
    机器由服务端从资源池自动挑选（`NodeManageServiceImpl#getServerNodes` →
    `NodeManageMapper#getDynamicComputeFreeServerIp`，SQL 见 `NodeManageMapper.xml`）。
  - 该 SQL 内部已按 `overcommit_cpu / overcommit_memory >= 已用量 + 本次需求` 做资源判定，
    但语义是"筛选可用机器并 `limit machineCount`"，**不支持按指定 IP 单点查询**。
  - 部署链路是**异步**的：`saveAutoQemuTask` 写库后提交线程池（`TASK_EXECUTOR.execute(executeTask)`）并立即 `return 200`；
    选机与资源校验都发生在异步线程内，因此当前接口无法在同步阶段返回失败。
  - 部署执行侧本身与"指定 IP"无关：`deployTask` → `getServer(envId)` → `QemuTaskMapper#getUsingServer(envId)` →
    `getQemuRemoteConnect` 的 `remoteConnect.setIp(server.getIp())`，即**部署目标完全由 `t_server_using` 中落库的机器决定**。
- 目标：调用方可指定一台机器 IP，任务部署到该机器；机器是否存在由同步预检保证，
  剩余 CPU / 内存是否满足在**选机（异步）阶段**按既有资源判定口径保证。

## 功能描述

做什么：

- **入参**：`QemuTaskConfigCreateDTO` 新增 `serverIp`（可选，**只支持单台**）。
  选择放在 config DTO 而非顶层 DTO，因为该值需持久化到 `t_qemu_task_config`，与 config 表的字段映射保持一致。
- **持久化**：`t_qemu_task_config` 新增 `server_ip` 列（可空，不指定时写 NULL），
  经 Liquibase changeSet + `QemuTaskConfigEntity` 字段 + `QemuTaskMapper.xml` 的 `insertOrUpdateConfig` 落库。
  异步链路按 `taskId` 反查该字段，无需改动任务主表。
- **同步预检（不含资源余量，已确认）**：在 `QemuTaskServiceImpl#saveAutoQemuTask` 的同步段插入预检，
  位置为 `checkParam` 之后、`insertOrUpdateTask` 之前（写库前，失败无残留数据）。
  只校验一件事：指定 IP 的机器存在（`t_server_basic_info` 中 `is_deleted='0'` 且有该 IP）。
  预检**不**做部署规格解析、**不**校验部署单元数（当前业务只有单机场景，已确认）。
- **异步资源判定（已确认）**：CPU / 内存余量**只在异步选机阶段判定**，且由 SQL 的 `HAVING` 完成，
  Java 侧不写余量比较逻辑。指定 IP 时用 `getServerFreeResourceByIp` 按 IP 取机，
  其 `HAVING` 与 `getDynamicComputeFreeServerIp` 逐字对齐；取不到机器 → `serverList` 为空 →
  `hasEnoughEnv=false` → 沿用既有"环境不足 → 任务置 FAILED"路径（不写 `t_server_using`）。
- **失败契约（已确认）**：同步预检失败统一返回 **code = 2003**，错误信息写入 `message` 字段，`data` 为空。
  仅 1 类原因：`specified server ip not found`。
  说明：本仓 `ResponseCodeEnum` 枚举**全仓零引用**，实际约定为裸数字 + 字符串，本次沿用既有约定，不引入该枚举。
- **资源判定口径复用**：沿用现有 SQL 语义
  `overcommit_cpu >= COALESCE(SUM(t_server_using.cpu),0) + useCpu`
  且 `overcommit_memory >= COALESCE(SUM(t_server_using.memory),0) + useMemory`；
  左侧为机器可分配上限（`t_server_basic_info.overcommit_cpu / overcommit_memory`），
  右侧"已用量"来源为 `t_server_using`（`is_deleted='0'`）。
- **选机改造**：`NodeManageServiceImpl#getServerNodes` 改为"指定 IP 优先"——
  本次请求指定了 IP 时按 IP 取机（SQL 内完成资源判定）、跳过自动挑选；
  取不到则走既有失败路径。同时移除自动选机 SQL 原有的 `creator='triton'` 硬编码过滤（见设计决策 3）。

不做什么：

- 不支持一次指定多台机器（不做 `serverIps` 列表）。
- 不改部署执行链路（`deployTask`、`uploadSimulator`、`lingquQemuExecute`、`executeScriptAndCheckContainer` 等）。
- 不改未指定 IP 时的自动选机**资源判定口径**（`HAVING` 与 `limit` 逻辑不变）；仅移除 `creator='triton'` 过滤。
- 不改 `t_server_using` 的写入/释放语义，不改 `t_server_basic_info` 等资源表结构（仅 `t_qemu_task_config` 加列）。
- 不引入 MyBatis-Plus、不新建数据源、不引入 `ResponseCodeEnum`。
- 不在 Java 侧新增 CPU / 内存余量比较逻辑（资源判定统一由 SQL 的 `HAVING` 承担）。

## 验收标准

- [ ] `POST /simulation/qemu/auto/task` 的 `config.serverIp` 可传单台机器 IP，为可选字段
- [ ] 传入的 `serverIp` 落库到 `t_qemu_task_config.server_ip`；不传时为 NULL
- [ ] 指定 IP 且该机器不存在 → 同步返回 `code=2003`，`message` 为 `specified server ip not found`，任务不进入部署
- [ ] 指定 IP 且机器存在、余量不足 → 同步返回 `code=200`；异步阶段任务置 FAILED，且**不写** `t_server_using`
- [ ] 指定 IP 且资源充足 → 返回 200，且实际部署落在该 IP 对应的机器上
- [ ] 未指定 `serverIp` 时，接口行为与改造前一致（自动选机，仅不再限定 `creator='triton'`）
- [ ] 同步失败码为 2003（不是 400/500），错误文案落在 `message`
- [ ] 指定机器占用的 CPU / 内存按既有口径写入 `t_server_using`，下次校验不会算错
- [ ] `mvn test` 通过（含新增单测）；`target/surefire-reports/` 无失败项
- [ ] pre-commit 通过（trailing-whitespace / end-of-file-fixer / check-yaml,json,xml / gitleaks / ruff 等，无 google-java-format）
- [ ] 业务 PR 关联 issue #31，打 `ai-assisted` 标签

## 影响范围

- 仓：openlibing-simulation（业务代码 + Liquibase changeSet），openlibing-docs（本 proposal / design / tasks）
- 数据库：`t_qemu_task_config` 新增一列 `server_ip`（向后兼容，可空）
- 涉及文件：见 `tasks.md` 清单
- 不影响：现有任务/节点管理端点与 SQL（未指定 IP 路径）、Dockerfile、pom 依赖、部署执行链路

## 设计决策

1. **资源余量的判定只放在异步阶段（已确认）**
   - 同步预检只保证"机器存在"，**不判 CPU / 内存余量**；因此资源不足时接口返回 200，
     随后由异步选机阶段把任务置 FAILED。
   - 判定实现放在 SQL 的 `HAVING`（`getServerFreeResourceByIp`），与自动选机
     `getDynamicComputeFreeServerIp` 的口径逐字对齐；**Java 侧不写余量比较逻辑**，不新增第二套判定实现。
   - 由此，"同步预检通过 → 异步占位时被抢占"这一窗口被自然兜住：异步取不到机器即失败，**不会超分**写入 `t_server_using`。
   - 代价：上游不能再用同步响应码判断"资源不足"，需按任务状态判断成败（见下方需求偏差说明）。
2. **同步预检，不加锁**（已确认：方案 A 轻量预检）
   现有"选机 + 写 `t_server_using`"由全局锁 `node_allocation_lock` 保护（`allocateNodeWithLock`），
   而同步预检发生在提交异步任务之前、锁之外，因此竞态窗口客观存在，**本次接受该窗口**。
   本次不引入方案 B（同步段在锁内完成"校验 + 写 `t_server_using` 占位"），避免重构
   `allocateNodeWithLock` / `checkEnvEnough` 的既有语义。
3. **指定 IP 时的机器过滤与 `creator` 硬编码清理**（已确认）
   `getServerNodes` 原本把自动选机的 `creatBy` 形参硬编码为字面量 `"triton"`，即自动选机路径恒带 `creator='triton'` 条件。
   指定 IP 的分支改走独立查询（`info.ip = #{ip}`），**不带该过滤**；同时也不带 `ext.extend_value like '%subScene%'`
   与 `architecture` 过滤（用户显式指定机器即视为对机型负责）。
   同时，按"该硬编码已无业务含义"的确认，**自动选机路径的 `creator='triton'` 过滤一并移除**
   （`getDynamicComputeFreeServerIp` 的 `creatBy` 形参及对应 SQL `<if>` 段删除）——这是对既有行为的变更，会扩大自动选机候选范围。
4. **不做单机数校验**（已确认）
   `buildQemuDeployResult` 中 `machineCount` 恒为 1，`getDeployResultList` 会按 `qemuDynamics` 条数产出多条（leader / worker）。
   初版设计据此在同步段校验"部署单元数 == 1"，**现取消**：经确认当前业务**只有单机场景**，
   无需为不存在的场景增加同步分支与额外查询；规格解析失败也会由异步链路自行暴露。
5. **`serverIp` 放置层级**（已确认）
   放在 `QemuTaskConfigCreateDTO`（而非顶层 `QemuTaskCreateDTO`），与 `t_qemu_task_config` 的落库位置对齐。

## 需求偏差说明（Issue #31 已修订，2026-09-18，两轮）

| Issue #31 初稿                                                                                                     | 本次实现                                                                     |
| ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| 主成功场景 2：同步阶段预检"校验指定 IP 的机器存在，**且剩余 CPU/内存满足部署需求**"                                | 同步阶段只校验"指定 IP 的机器存在"                                           |
| 扩展场景 2：资源不足 → 接口**同步**返回 `code=2003`，message=`the specified server has insufficient cpu or memory` | 接口返回 200；异步阶段任务被置 FAILED，文案沿用既有"未找到符合cpu内存的机器" |
| "只支持单台"约束（同步校验部署单元数 == 1）                                                                        | 当前业务只有单机场景，同步不再校验部署单元数（第二轮修订）                   |

已通过 `gitcode issue edit 31` 完成两轮修订：主成功场景 2 / 4、扩展场景 2 / 5、约束 4 / 5 / 7 均已改为
"同步不判资源余量、异步按既有 SQL `HAVING` 口径判定"；第二轮把同步预检收敛为"只校验指定机器存在"。
`the specified server has insufficient cpu or memory` 这条同步失败契约已移除。
上游不应按"同步 2003"实现重试逻辑，需按任务状态判断成败。
