# 自动化 QEMU 部署创建接口支持指定机器 IP — 技术设计

## 方案概述

在 `POST /simulation/qemu/auto/task` 的**同步段**新增"指定机器预检"，并把指定 IP 持久化到
`t_qemu_task_config.server_ip`；异步部署链路按 `taskId` 反查该 IP，在选机环节跳过自动挑选、直接落到指定机器。

关键点：

1. 该接口是异步的（`saveAutoQemuTask` 提交线程池后立即 `return 200`），因此"不满足即接口返回失败"
   只能靠同步段的预检实现。
2. **同步预检只校验"部署规格可解析 / 仅单机部署 / 指定机器存在"三件事**（已确认：同步不判 CPU、内存余量）。
3. **剩余 CPU / 内存是否足够的判定只发生在异步选机阶段，且由 SQL 的 `HAVING` 完成**：
   复用自动选机 `getDynamicComputeFreeServerIp` 完全相同的聚合口径，Java 侧不写余量比较逻辑；
   取不到机器 → `serverList` 为空 → `hasEnoughEnv=false` → 既有"任务置 FAILED"路径。

## 架构决策

### 关键决策及原因

| 决策点                  | 方案                                                                                                                                                                                                 | 原因                                                                                                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **校验时机**            | `saveAutoQemuTask` 同步段，位于 `checkParam`（#261）之后、`insertOrUpdateTask`（#287）之前                                                                                                           | 异步链路已 `return 200`，只有同步段才能满足"不满足接口返回失败"                                                                                                                |
| **校验性质**            | 同步段为**纯读预检**，不写库、不加锁                                                                                                                                                                 | 放在写库前，失败时不需要回滚已写入的 task / config 行；也避免引入新的删除方法                                                                                                  |
| **同步预检范围**        | 只校验：部署规格可解析、部署单元数 == 1、指定 IP 的机器存在（`t_server_basic_info.is_deleted='0'`）                                                                                                  | **已确认：同步不判 CPU / 内存余量**                                                                                                                                            |
| **资源余量判定位置**    | **只在异步选机阶段判**，且由 SQL 的 `Having` 完成，Java 侧不写余量比较                                                                                                                               | 已确认；与自动选机 `getDynamicComputeFreeServerIp` 复用同一口径，不新增第二套判定实现                                                                                          |
| **资源不足时的表现**    | 异步 `getServerNodes` 取不到机器 → `serverList` 为空 → 既有 `serverList.size() == machineCount` 判定给出 `hasEnoughEnv=false` → 既有 `allocateNode` 失败路径（不写 `t_server_using`、任务置 FAILED） | 复用既有链路，**不新增**异步侧错误文案 / 状态 / 重试分支                                                                                                                       |
| **失败契约**            | 同步失败 `code = 2003`，错误信息入 `message`，`data` 为空（3 类原因，见第 5 节）                                                                                                                     | 已确认需求口径；`2003` 为本仓新增业务码。**注意：资源不足不再同步返回 2003**，需同步修订 Issue #31 扩展场景 2                                                                  |
| **响应码风格**          | 裸数字，**不引入** `ResponseCodeEnum`                                                                                                                                                                | 该枚举全仓零引用，实际约定是 `new ResponseEntity(code, msg, data)`；引入会造成两套并存                                                                                         |
| **IP 落库位置**         | `t_qemu_task_config.server_ip`（`VARCHAR(64)`，可空）                                                                                                                                                | 已确认；异步链路按 `taskId` 反查，任务主表不动                                                                                                                                 |
| **指定机器数量**        | 仅单台（字段类型 `String`）                                                                                                                                                                          | 已确认                                                                                                                                                                         |
| **并发控制**            | 轻量预检，**不加锁**（方案 A）                                                                                                                                                                       | 已确认；接受"预检通过 → 异步占位时被抢占"的窗口，该窗口由异步选机的 SQL 资源筛选自然兜住（不会超分部署）                                                                       |
| **指定机器的过滤条件**  | **不带** `creator='triton'` 过滤                                                                                                                                                                     | 已确认；`creator='triton'` 是自动选机 SQL 的硬编码，与"指定机器"语义无关                                                                                                       |
| **指定 IP 分支的口径**  | 只按 `info.ip = #{serverIp}` 取机 + 同口径资源筛选，**跳过** `subScene`、`architecture` 过滤                                                                                                         | 用户显式指定机器 = 用户对机型负责                                                                                                                                              |
| **所需规格的来源**      | 新增按 `engineId + yamlManageId` 解析的查询，**不能**用 `getQemuYamlManage(taskId)`                                                                                                                  | 预检发生在写库之前：此时 `task.getId()` 尚未赋值（#265 才生成），`t_qemu_task_config` 行也不存在，按 `task_id` 的查询必然查空                                                  |
| **IP 在异步链路的传递** | 复用 `entity/nodemanage/SimulationDeployResultEntity` 承载，**不改方法签名**                                                                                                                         | 该实体已贯穿 `createOffcloudPolicyEnv → allocateNodeWithLock → allocateNode → checkEnvEnough → exclusiveIsEnoughEnv → getServerNodes` 全链，加 1 个字段即可，避免 5 处签名变更 |
| **多机场景**            | 指定 IP 时若部署单元数 != 1 或存在无法识别的引擎 → 同步直接返回 2003                                                                                                                                 | 与"只支持单台"口径一致，不做"部分指定"                                                                                                                                         |

### 技术选型

- **DDL**：Liquibase `addColumn`，追加 changeSet 到既有 `t_qemu_task_config.xml`，随应用启动执行（本仓既有 changeSet 同机制）
- **预检查询**：纯 MyBatis XML，复用现有 `t_server_basic_info LEFT JOIN t_server_using` 的聚合口径
- **不新增**：依赖、Java 类、数据源、changelog 挂载（`db.changelog.xml` 第 15 行已 include `t_qemu_task_config.xml`，无需改动）；
  也不需要给 `ServerBasicInfoEntity` 加字段（余量判定在 SQL 里完成，Java 侧不比较）

## 涉及文件

| 文件                                                    | 操作 | 说明                                                                                                                              |
| ------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------- |
| `resources/db/changelog/v1.0.0/t_qemu_task_config.xml`  | 修改 | 追加 changeSet：`t_qemu_task_config` 新增 `server_ip` 列                                                                          |
| `entity/dto/QemuTaskConfigCreateDTO.java`               | 修改 | 新增 `serverIp`（可选，IPv4 `@Pattern`）                                                                                          |
| `entity/qemu/QemuTaskConfigEntity.java`                 | 修改 | 新增 `serverIp`                                                                                                                   |
| `entity/nodemanage/SimulationDeployResultEntity.java`   | 修改 | 新增 `serverIp`（承载指定 IP 到选机环节）                                                                                         |
| `service/impl/QemuTaskServiceImpl.java`                 | 修改 | `mapConfigDtoToEntity` 补白名单拷贝；`saveAutoQemuTask` 新增同步预检                                                              |
| `service/NodeManageService.java`                        | 修改 | 新增公开方法 `checkSpecifiedServer(config, serverIp)`                                                                             |
| `service/impl/NodeManageServiceImpl.java`               | 修改 | 实现上述公开方法 + 私有辅助 `getDeployResultListByConfig`；`createQemuEnv` 反查并回填 IP；`getServerNodes` 增加"指定 IP 优先"分支 |
| `mapper/QemuTaskMapper.xml`                             | 修改 | `insertOrUpdateConfig` 的 insert 列 / `values` / `on DUPLICATE KEY UPDATE` 三处补 `server_ip`                                     |
| `mapper/NodeManageMapper.java` + `NodeManageMapper.xml` | 修改 | 新增 `getSpecifiedServerIpByTaskId`、`countServerByIp`、`getServerFreeResourceByIp`、`getQemuDeploySpec` 四个查询                 |
| `test/.../QemuTaskControllerTest.java`                  | 修改 | 补携带 `config.serverIp` 的用例                                                                                                   |
| 同步预检单测类                                          | 新增 | 覆盖 3 个分支                                                                                                                     |

> **注意**：仓内有**两个同名** `SimulationDeployResultEntity`。本次要用的是
> `entity/nodemanage/SimulationDeployResultEntity.java`（含 `useCpu` / `useMemory` / `subscene` / `deployType` 等），
> `entity/qemu/SimulationDeployResultEntity.java` 全仓无任何引用，不要改错。

## 数据流程

```
POST /simulation/qemu/auto/task  (config.serverIp 可选)
      │
      ▼
QemuTaskServiceImpl.saveAutoQemuTask                       #248
      │
      ├─ ① mapConfigDtoToEntity：serverIp 白名单拷贝        #259 / #3809
      ├─ ② checkParam                                       #261
      │        └─ 校验失败 ── 400 ──▶ 返回
      │
      ├─ ③ 【新增】指定机器同步预检（纯读、不加锁）          ← 决策：方案 A
      │      │                                               只校验规格 / 单机 / 存在
      │      ├─ serverIp 为空 ──────────────▶ 跳过，走原有自动分配
      │      │
      │      └─ serverIp 非空
      │            └─ nodeManageService.checkSpecifiedServer(config, serverIp)
      │                  ├─ getQemuDeploySpec(engineId, yamlManageId)
      │                  │     └─ 查不到 / 引擎类型无法识别 ────────────▶ 2003
      │                  ├─ 部署单元数 != 1 ──────────────────────────▶ 2003
      │                  └─ countServerByIp(serverIp) == 0 ────────────▶ 2003
      │            └─ 不通过 ──▶ return ResponseEntity(2003, msg)   ← 未写库，无残留
      │
      ├─ ④ 生成 taskId                                       #265
      ├─ ⑤ 落库：insertOrUpdateTask #287 + insertOrUpdateConfig #292（含 server_ip）
      ├─ ⑥ TASK_EXECUTOR.execute(executeTask)                #293
      └─ ⑦ return ResponseEntity(200, "success", task)       #294
                    │
                    ▼ （异步）
            executeTask → saveNodeManage → NodeManageServiceImpl.saveNodeManageTask   #74
                    │
                    └─ createQemuEnv                                  #109
                          ├─ getDeployResultList(taskId 口径)          #119
                          ├─ 【新增】getSpecifiedServerIpByTaskId(taskId)
                          │     └─ 回填到每个 SimulationDeployResultEntity.serverIp
                          └─ createOffcloudPolicyEnv                   #144
                                └─ allocateNodeWithLock（全局锁 node_allocation_lock，保持原样）
                                      └─ allocateNode → checkEnvEnough → exclusiveIsEnoughEnv
                                            └─ getServerNodes                        #312
                                                  ├─ serverIp 非空
                                                  │     └─ 【新增】getServerFreeResourceByIp(serverIp, useCpu, useMemory)
                                                  │            └─ SQL 的 Having 在此完成"余量是否足够"判定
                                                  │                 ├─ 取不到 ──▶ 空列表
                                                  │                 └─ 取到 ──▶ singletonList(server)
                                                  └─ serverIp 为空  ──▶ 原逻辑 getDynamicComputeFreeServerIp("triton", ...)
                                                        │
                                                        ▼
                                          serverList.size() != machineCount ?
                                                        ├─ 是 ──▶ hasEnoughEnv = false
                                                        │        → allocateNode 既有失败路径：
                                                        │          deleteUsingEnvByTaskId + 任务置 FAILED
                                                        │          + "未找到符合cpu内存的机器"
                                                        └─ 否 ──▶ 写 t_server_using（cpu/memory 口径不变）
                                                        │
                                                        ▼
                                                  deployTask → getServer(envId) → getUsingServer(envId)
                                                        │
                                                        ▼
                                                  部署到 t_server_using 中的那台机器（本需求天然满足，无需改动）
```

## 关键技术实现

### 1. DDL：`t_qemu_task_config` 新增 `server_ip`

追加到 `resources/db/changelog/v1.0.0/t_qemu_task_config.xml` 文件末尾，沿用该文件既有风格
（`preConditions onFail="MARK_RAN"` + `addColumn` + `rollback`）：

```xml
<!-- 添加新字段：server_ip（指定部署机器IP） -->
<changeSet id="20260915_add_server_ip_to_t_qemu_task_config" author="ligao">
    <!-- 前置条件：表必须存在 -->
    <preConditions onFail="MARK_RAN">
        <tableExists tableName="t_qemu_task_config"/>
    </preConditions>

    <addColumn tableName="t_qemu_task_config">
        <column name="server_ip" type="VARCHAR(64)" remarks="指定部署机器IP，为空表示由系统自动分配"/>
    </addColumn>

    <!-- 回滚操作：删除新增字段 -->
    <rollback>
        <dropColumn tableName="t_qemu_task_config" columnName="server_ip"/>
    </rollback>
</changeSet>
```

注意：**不改动**该文件已有 changeSet；**不需要**修改 `db.changelog.xml`（第 15 行已 include 该文件）。

### 2. 入参、落库与白名单拷贝

`QemuTaskConfigCreateDTO` 新增（与既有 `qcowId` 等字段风格一致）：

```java
/**
 * 指定部署机器 IP（可选，仅支持单台；为空时由系统自动分配）
 */
@Pattern(regexp = "^((25[0-5]|2[0-4]\\d|[01]?\\d?\\d)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d?\\d)$",
        message = "serverIp must be a valid IPv4 address")
private String serverIp;
```

`QemuTaskConfigEntity` 新增 `private String serverIp;`，并在 `mapConfigDtoToEntity`（#3809-3832，逐字段白名单拷贝）
末尾补一行：

```java
entity.setServerIp(dto.getServerIp());
```

`QemuTaskMapper.xml` 的 `insertOrUpdateConfig`（#138-161）需在**三处**补列：insert 列清单、`values(...)`、
`on DUPLICATE KEY UPDATE` 列表。

```xml
insert into t_qemu_task_config (
id,task_id,engine_id,engine_type,is_deleted,preset_password,vm_num,yaml_manage_id,basic_container_name,
gateway,container_num,network_config_info,execute_command,patch_id,log_info,node_number,scene,numa_cpu,server_ip) values
(...,#{nodeNumber},#{scene},#{numaCpu},#{serverIp})
on DUPLICATE KEY UPDATE
...
numa_cpu = values(numa_cpu),
server_ip = values(server_ip)
```

### 3. 部署规格解析（同步预检的前置条件）

同步预检需要判断"是否只支持单机部署"，因此要知道本次请求会产出几个部署单元。
部署单元的产出逻辑在 `NodeManageServiceImpl#getDeployResultList`（#346-372）+
`buildQemuDeployResult`（#381-404）：

| 引擎类型（`t_engine_basic_info.engine_type`） | useCpu                                 | useMemory                    |
| --------------------------------------------- | -------------------------------------- | ---------------------------- |
| `lingQuQemu` / `npuQemu`                      | `t_qemu_yaml_content.cpu`              | `t_qemu_yaml_content.memory` |
| `matrixSvrQemu`                               | `16 * nodeNumber`                      | `64 * nodeNumber`            |
| 其他                                          | 无法识别 → 部署单元 `machineCount = 0` | —                            |

**为什么不能复用 `getQemuYamlManage(taskId)`**：该查询的数据源是 `t_qemu_task_config` 自身
（`WHERE con.task_id = #{taskId}`），而预检在写库之前执行——此时 `task.getId()` 还是 `null`（#265 才生成 id），
表中也没有对应行，查询必然为空。因此在 `NodeManageMapper.xml` 新增一个**同口径、不同数据源**的查询：

```xml
<!-- 按 engineId + yamlManageId 解析部署规格（同步预检用；口径对齐 getQemuYamlManage） -->
<select id="getQemuDeploySpec" resultType="com.openlibing.simulation.entity.nodemanage.QemuDynamicEntity">
    SELECT eng.engine_type TYPE, cont.cpu, cont.memory, eng.architecture, cont.id yamlContentId
    FROM t_engine_basic_info eng
             JOIN t_qemu_yaml_manage man ON man.id = #{yamlManageId}
             LEFT JOIN t_qemu_yaml_content cont ON cont.yaml_id = man.id
    WHERE eng.id = #{engineId}
    ORDER BY cont.cpu DESC
</select>
```

- `node_number` 不在本查询中：`buildQemuDeployResult` 用的是 `con.node_number`，同步阶段该值来自入参
  `config.getNodeNumber()`（`checkParam` 已保证非空且为 2/4/8），在 Java 侧回填即可。
- `engineId` 一定可用：`checkParam` 的 `validateEngine`（#3701-3721）在只传 `engineName` 时会回填
  `config.setEngineId(...)`。
- 查不到行（`yamlManageId` 不存在 / 引擎不存在）→ 返回空列表 → 判定为"规格无法解析"。

### 4. 同步预检（核心）

在 `saveAutoQemuTask` 的 `checkParam` 之后（#264 之后）、`taskId` 生成（#265）之前插入：

```java
ResponseEntity responseEntity = checkParam(task);
if (responseEntity.getCode() != 200) {
    return responseEntity;
}
// 【新增】指定机器同步预检（方案 A：轻量预检、纯读、不加锁；只校验规格 / 单机 / 存在）
QemuTaskConfigEntity preCheckConfig = task.getConfig();
String serverIp = preCheckConfig.getServerIp();
if (StringUtils.isNotBlank(serverIp)) {
    ResponseEntity preCheck = nodeManageService.checkSpecifiedServer(preCheckConfig, serverIp);
    if (preCheck.getCode() != 200) {
        return preCheck;   // code = 2003，message 为具体原因
    }
}
```

`NodeManageService` 新增公开方法：

```java
/**
 * 指定机器同步预检：校验部署规格可解析、仅单机部署、指定 IP 的机器存在。
 *
 * <p>注意：CPU / 内存余量不在此处判定，改由异步选机阶段的 SQL（getServerFreeResourceByIp 的 Having）判定，
 * 不足时走既有"环境不足 → 任务置 FAILED"路径。
 *
 * @param config   任务配置实体（提供 engineId / yamlManageId / nodeNumber 以解析部署规格）
 * @param serverIp 指定机器 IP
 * @return code=200 表示通过；code=2003 表示不通过，message 为原因
 */
ResponseEntity checkSpecifiedServer(QemuTaskConfigEntity config, String serverIp);
```

`NodeManageServiceImpl` 实现（复用本类既有私有方法 `getDeployResultList` / `buildQemuDeployResult`，不搬迁）：

```java
@Override
public ResponseEntity checkSpecifiedServer(QemuTaskConfigEntity config, String serverIp) {
    // 1) 部署规格必须可解析（此时任务行尚未落库，不能用 getQemuYamlManage(taskId)）
    List<SimulationDeployResultEntity> deployList = getDeployResultListByConfig(config);
    if (CollectionUtils.isEmpty(deployList)
            || deployList.stream().anyMatch(deploy -> deploy.getMachineCount() <= 0)) {
        return new ResponseEntity(2003, "cannot resolve deploy spec, please check engineId/yamlManageId");
    }
    // 2) 只支持单机部署（含 leader/worker 多部署单元场景）
    if (deployList.size() != 1) {
        return new ResponseEntity(2003, "specified server ip only supports single machine deployment");
    }
    // 3) 指定机器必须存在；资源余量不在此处判定（交由异步选机阶段按 SQL 同口径判定）
    if (nodeManageMapper.countServerByIp(serverIp) == 0) {
        return new ResponseEntity(2003, "specified server ip not found");
    }
    return new ResponseEntity(200, Constans.SUCCESS);
}
```

私有辅助方法（把"按 config 解析规格"与既有 `getDeployResultList` 串起来，仅做提取复用）：

```java
private List<SimulationDeployResultEntity> getDeployResultListByConfig(QemuTaskConfigEntity config) {
    List<QemuDynamicEntity> qemuDynamics =
            nodeManageMapper.getQemuDeploySpec(config.getEngineId(), config.getYamlManageId());
    if (CollectionUtils.isEmpty(qemuDynamics)) {
        return new ArrayList<>();
    }
    Integer nodeNumber = config.getNodeNumber();
    if (nodeNumber != null) {
        qemuDynamics.forEach(dynamic -> dynamic.setNodeNumber(nodeNumber));
    }
    return getDeployResultList(qemuDynamics, config.getEngineType());
}
```

> `getDeployResultList(qemuDynamics, engineType)` 的 `engineType` 形参在既有实现中并未被使用
> （实际读的是 `qemuDynamic.getType()`），这里传 `config.getEngineType()` 仅为语义完整，不改既有方法。

### 5. 错误码与响应契约（2003）

`ResponseEntity` 沿用既有四字段结构（`code` / `message` / `data` / `total`），仅构造器、无静态工厂：

```java
return new ResponseEntity(2003, "specified server ip not found");
```

同步预检共 **3 类**失败消息（英文，与 `checkParam` 既有风格一致）：

| 场景                                                               | code | message                                                          |
| ------------------------------------------------------------------ | ---- | ---------------------------------------------------------------- |
| 规格无法解析（`engineId`/`yamlManageId` 查不到，或引擎类型不支持） | 2003 | `cannot resolve deploy spec, please check engineId/yamlManageId` |
| 部署单元数 != 1（如 leader/worker 多机场景）                       | 2003 | `specified server ip only supports single machine deployment`    |
| 指定 IP 的机器不存在（`t_server_basic_info` 中查不到或已删除）     | 2003 | `specified server ip not found`                                  |

**资源不足不在同步失败契约内**：接口会返回 200，随后在异步阶段任务被置 FAILED（错误文案沿用既有
`未找到符合cpu内存的机器`）。这与 Issue #31 扩展场景 2 的原文不一致，**需同步修订 Issue 文案**（见第 8 节）。

请求 / 响应示例：

```json
POST /simulation/qemu/auto/task
{
  "name": "auto_qemu_demo",
  "eimulationSceneId": "18",
  "productName": "MindIE",
  "community": "MindIE",
  "config": {
    "nodeNumber": 2,
    "scene": "matrix",
    "numaCpu": "2,8",
    "serverIp": "10.1.2.3"
  }
}
```

```json
{
  "code": 2003,
  "message": "specified server ip not found",
  "data": null,
  "total": 0
}
```

### 6. 异步选机改造：指定 IP 优先 + SQL 侧资源判定

`entity/nodemanage/SimulationDeployResultEntity` 新增 `private String serverIp;`
（该实体已贯穿到 `getServerNodes`，无需改方法签名）。

`createQemuEnv`（#109-135）在拿到 `simulationDeployResultList` 后反查并回填：

```java
List<SimulationDeployResultEntity> simulationDeployResultList = getDeployResultList(qemuDynamics, engineType);
if (CollectionUtils.isEmpty(simulationDeployResultList)) {
    return envTask;
}
// 【新增】按 taskId 反查指定机器 IP，并回填到部署结果
String specifiedServerIp = nodeManageMapper.getSpecifiedServerIpByTaskId(taskId);
if (StringUtils.isNotBlank(specifiedServerIp)) {
    simulationDeployResultList.forEach(item -> item.setServerIp(specifiedServerIp));
} else {
    log.info("no specified server ip, use auto allocation, taskId={}", taskId);
}
```

`getServerNodes`（#312-337）改为双分支，指定 IP 分支的余量判定**由 SQL 的 `Having` 完成**：

```java
private boolean getServerNodes(List<ServerUsingEntity> serverUsingList,
    SimulationDeployResultEntity simulationDeploy, List<String> nodeIds, String creatBy) {
    List<ServerBasicInfoEntity> serverList;
    String serverIp = simulationDeploy.getServerIp();
    if (StringUtils.isNotBlank(serverIp)) {
        // 指定机器：按 IP 单点取机；资源余量是否足够由 SQL 的 Having 判定（与自动选机完全同口径）
        log.info("getServerNodes use specified server ip, serverIp={}", serverIp);
        ServerBasicInfoEntity server = nodeManageMapper.getServerFreeResourceByIp(
                serverIp, simulationDeploy.getUseCpu(), simulationDeploy.getUseMemory());
        if (server == null) {
            // 覆盖三种情况：机器已被删除 / 剩余 CPU 或内存不足（含同步预检通过后被抢占）
            log.warn("specified server not available, serverIp={}, useCpu={}, useMemory={}",
                    serverIp, simulationDeploy.getUseCpu(), simulationDeploy.getUseMemory());
            serverList = new ArrayList<>();
        } else {
            serverList = Collections.singletonList(server);
        }
    } else {
        // 原逻辑：自动挑选
        serverList = nodeManageMapper.getDynamicComputeFreeServerIp("triton", simulationDeploy, nodeIds);
    }
    // 以下判定与 t_server_using 写入逻辑保持完全不变
    int machineCount = simulationDeploy.getMachineCount();
    ...
}
```

取不到机器时返回空列表，即由**既有的** `serverList.size() == machineCount` 判定得出 `hasEnoughEnv = false`，
后续沿既有路径：`allocateNode`（#227-238）→ `deleteUsingEnvByTaskId` + `updateEnvTaskStatus(taskId, "3")`

- 错误文案"未找到符合cpu内存的机器" + `updateTaskLogInfo`。**不新增异步侧重试 / 新文案 / 新状态**。

### 7. 四个新增查询

```xml
<!-- 按 taskId 反查指定机器 IP -->
<select id="getSpecifiedServerIpByTaskId" resultType="java.lang.String">
    SELECT server_ip
    FROM t_qemu_task_config
    WHERE task_id = #{taskId}
      AND is_deleted = "0"
    LIMIT 1
</select>

<!-- 指定机器是否存在（同步预检用，只判存在性，不判资源） -->
<select id="countServerByIp" resultType="int">
    SELECT COUNT(1)
    FROM t_server_basic_info
    WHERE is_deleted = "0"
      AND ip = #{serverIp}
</select>

<!-- 按 IP 查单台机器，且资源余量必须足够（异步选机用；Having 与 getDynamicComputeFreeServerIp 完全同口径） -->
<select id="getServerFreeResourceByIp"
        resultType="com.openlibing.simulation.entity.nodemanage.ServerBasicInfoEntity">
    SELECT info.id,
           info.ip,
           info.`cpu`,
           info.memory,
           info.architecture,
           info.overcommit_cpu    overcommitCpu,
           info.overcommit_memory overcommitMemory,
           COALESCE(SUM(us.cpu), 0)    AS cpuTotal,
           COALESCE(SUM(us.memory), 0) AS memoryTOtal
    FROM t_server_basic_info info
             LEFT JOIN t_server_using us ON us.server_id = info.id AND us.is_deleted = "0"
    WHERE info.is_deleted = "0"
      AND info.ip = #{serverIp}
    GROUP BY info.id
    HAVING info.overcommit_cpu >= (COALESCE(SUM(us.cpu), 0) + #{useCpu})
       AND info.overcommit_memory >= (COALESCE(SUM(us.memory), 0) + #{useMemory})
</select>
```

- `Having` 两行与 `getDynamicComputeFreeServerIp`（`NodeManageMapper.xml` #292-293）逐字对齐；
  左值不套 `COALESCE`（`NULL >= x` 为 NULL → 行被排除），与该查询行为一致。
- 相比自动选机 SQL，**刻意去掉** `creator`、`ext.extend_value like '%subScene%'`、`architecture` 三个过滤（决策见架构决策表）。
- `getQemuDeploySpec` 见第 3 节。

### 8. 需求偏差：Issue #31 已修订（2026-09-18 完成）

初版 Issue 文案与"只在异步判"口径冲突，已通过 `gitcode issue edit 31` 修订并复核，当前文案与本次实现一致：

| Issue #31 初稿                                                                                                                              | 修订后（现行文案）                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 主成功场景 2：系统在同步阶段执行预检：校验指定 IP 的机器存在，**且剩余 CPU/内存满足部署需求**                                               | 同步阶段只校验"规格可解析 / 单机部署 / 机器存在"；资源余量在异步选机阶段判定       |
| 扩展场景 2：指定 IP 的机器剩余 CPU 或内存不足 → 接口**同步**返回 `code=2003`，message=`the specified server has insufficient cpu or memory` | 同步仍返回 200；异步阶段任务被置 FAILED，错误文案沿用既有"未找到符合cpu内存的机器" |

同批修订的还有：主成功场景 4（补异步资源校验）、扩展场景 5（改为"抢占 / 机器被删除"）、
约束 4 / 5 / 7（同步预检不含资源余量、异步复用既有 SQL 的 `HAVING` 口径、资源查询移至异步）。
`the specified server has insufficient cpu or memory` 这条同步失败契约已随之移除，
上游不应按"同步 2003"实现重试逻辑。

## 风险 & 缓解

| 风险                                    | 影响                                                                | 缓解措施                                                                                                                                               |
| --------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **资源不足不再同步返回失败**            | 上游收到 200 后需靠任务状态判断成败；若上游只认同步码，会误判为成功 | 已确认取舍；Issue #31 已按此口径修订（第 8 节），仍需通知上游；任务置 FAILED 时会写 `error_message` 与任务日志，可供上游轮询                           |
| **同步 / 异步判定内容不一致**           | 同步只保证"机器存在"，异步可能因余量不足失败                        | 属预期行为（决策如此）；异步失败文案沿用既有，不新增分支                                                                                               |
| **预检通过后被抢占**（方案 A 固有窗口） | 接口返回 200，但异步阶段环境分配失败                                | 异步 `getServerFreeResourceByIp` 自带 SQL 资源筛选，取不到即空列表 → `hasEnoughEnv=false` → 既有"任务置 FAILED"路径；**不会超分**写入 `t_server_using` |
| **`Having` 口径与自动选机漂移**         | 指定机器的资源判定与自动选机结论不一致                              | 两处 `Having` 逐字对齐；`getServerFreeResourceByIp` 的余量列与过滤条件注释标注来源行号，口径演进时须同步改两处                                         |
| **规格解析出现第三份实现**              | `getQemuDeploySpec` 与 `getQemuYamlManage` 口径漂移，单机数判断出错 | 两者字段清单对齐（`eng.engine_type` / `cont.cpu` / `cont.memory` / `cont.id`），仅数据源不同                                                           |
| **异步链路漏传 IP（静默降级）**         | 接口照常 200，但实际走自动选机                                      | 复用 `SimulationDeployResultEntity` 单点承载，避免多次签名变更；反查为空时打 INFO 日志；单测覆盖"指定 IP 时 `getDynamicComputeFreeServerIp` 不被调用"  |
| **`insertOrUpdateConfig` 漏改一处**     | `server_ip` 未落库 → 异步反查为空 → 静默降级                        | 三处（列清单 / `values` / `on DUPLICATE KEY UPDATE`）必须同改；单测断言落库后反查能取到 IP                                                             |
| **异步失败原因不可区分**                | 日志无法区分"机器不存在 / 资源不足 / 抢占"                          | `log.warn` 中带出 `serverIp` + `useCpu` + `useMemory`，并注明三种可能                                                                                  |
| **DDL 在生产执行**                      | 列不存在导致 SQL 报错                                               | Liquibase 随应用启动执行（既有机制）；上线前确认生产 Liquibase 未被禁用                                                                                |
| **`serverIp` 被用于越权指定机器**       | 调用方可部署到任意机器                                              | 沿用 `InternalSimulationAuthFilter` 认证；是否需要对可指定机器做归属校验（如 `creator`）本次**不做**，如需另开需求                                     |

## 跨仓影响

### openlibing-docs 文档仓

- 新增 `spec/openlibing-simulation/task_design/qemu-auto-task-specify-ip/{proposal,design,tasks}.md`
- 需新建分支提交（不得混入当期 release 报告 PR）
- PR 标题建议 `docs(spec/openlibing-simulation): qemu-auto-task-specify-ip`，关联业务仓 Issue #31，加 `ai-assisted` 标签

### 上游调用方（接口契约变更）

- `config.serverIp` 为**可选新增字段**，不传时行为与改造前完全一致 → **向后兼容**，无需上游同步改造
- 新增失败码 `2003`（3 类原因）：上游若对 `code` 做白名单判断，需放行 2003（当前失败码为 400/500，本次新增一类）
- **行为变更提示**：资源不足不再体现在同步响应码中，上游需按任务状态判断成败（若依赖"同步失败即重试"，需调整）

## 测试策略

### 单元测试（同步预检，3 个分支）

| 用例                 | 输入                                      | 期望                                                        |
| -------------------- | ----------------------------------------- | ----------------------------------------------------------- |
| 指定 IP 且机器存在   | `serverIp` 有效，`countServerByIp` 返回 1 | `code=200`，且 `insertOrUpdateConfig` 落库含 `server_ip`    |
| 指定 IP 但机器不存在 | `countServerByIp` 返回 0                  | `code=2003`，message `specified server ip not found`        |
| 未指定 IP            | `serverIp` 为空                           | `code=200`，且**不调用** `checkSpecifiedServer`（走原逻辑） |

补充两个边界分支（建议一并覆盖）：

| 用例            | 输入                               | 期望                                                              |
| --------------- | ---------------------------------- | ----------------------------------------------------------------- |
| 部署单元数 != 1 | mock `getQemuDeploySpec` 返回 2 条 | `code=2003`，message 含 `only supports single machine deployment` |
| 规格无法解析    | mock 返回空列表 / `machineCount=0` | `code=2003`，message 含 `cannot resolve deploy spec`              |

**注意**：同步预检不应校验资源余量，需补一条反向用例——机器存在但余量不足时，同步仍返回 `code=200`。

### 单元测试（异步选机）

| 用例                       | 输入                            | 期望                                                                             |
| -------------------------- | ------------------------------- | -------------------------------------------------------------------------------- |
| 指定 IP 且余量充足         | `serverIp` 非空 + SQL 返回机器  | `getDynamicComputeFreeServerIp` **未被调用**；落 `t_server_using`                |
| 指定 IP 但余量不足（抢占） | `serverIp` 非空 + SQL 返回 null | `hasEnoughEnv=false`；**不写** `t_server_using`；任务被置 FAILED（`status="3"`） |
| 指定 IP 但机器已被删除     | `serverIp` 非空 + SQL 返回 null | 同上（空列表 → FAILED）                                                          |
| 未指定 IP                  | `serverIp` 为空                 | `getDynamicComputeFreeServerIp` 被调用（回归保护）                               |

### Controller 测试

- `QemuTaskControllerTest` 补 1-2 个携带 `config.serverIp` 的 POST 用例

### 验证命令与注意事项

```bash
mvn clean test
```

**注意**：本仓 `surefire` 配置了 `testFailureIgnore=true`，测试失败仍会 `BUILD SUCCESS`，
必须核对 `target/surefire-reports/` 是否有失败项，不能只看构建结果。另需通过 pre-commit（gitleaks + google-java-format）。

## 监控与日志

**关键日志点**：

- 同步预检不通过：`log.warn`，含 `serverIp` + 失败原因（3 类之一）
- 异步反查：`taskId` → 反查到的 `serverIp`；为空时打印"未指定机器，走自动分配"
- 异步取不到机器：`log.warn`，含 `serverIp` + `useCpu` + `useMemory`，并注明"机器已被删除 / 余量不足（含抢占）"
- 选机分支：明确打印走的是"指定机器"还是"自动分配"，便于识别静默降级

**日志级别**：正常流程 INFO；异步指定机器取不到按 WARN；
"请求指定了 IP 但异步反查为空"按 ERROR 处理。

## 遗留项

1. **Issue #31 文案需修订**：主成功场景 2 与扩展场景 2 与本次实现（资源不足只在异步暴露）不一致，见第 8 节。
2. **`creator='triton'` 硬编码**：`getServerNodes` 第 315 行的形参 `creatBy` 未被使用，实际恒传字面量 `"triton"`。
   本次不改（属既有问题，只保证指定 IP 分支不受其影响），建议后续单独提优化。
3. **`getEngineTypeByTaskId` 结果未被使用**：`NodeManageMapper#getEngineTypeByTaskId`（`NodeManageMapper.java` #46）
   被 `createQemuEnv` #113 调用后传给 `getDeployResultList`，但后者实现内并未使用该形参（实际读 `qemuDynamic.getType()`）。
   本次不动，避免扩大改动面。
4. **异步失败文案不区分"资源不足"与"机器不存在"**：沿用既有"未找到符合cpu内存的机器"，如需精细区分另开需求。
5. **越权指定机器**：本次未校验调用方是否有权指定某台机器；如需，另开需求。
6. **方案 B（锁内校验 + 占位）**：本次未采纳；若后续发现预检窗口导致的实际问题，可作为演进方向。
