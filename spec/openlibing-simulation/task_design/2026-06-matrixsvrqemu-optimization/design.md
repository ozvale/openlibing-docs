# 技术方案设计

## 1. 需求分析

### 1.1 需求概述

| 需求点 | 核心目标 | 技术挑战 |
| :--- | :--- | :--- |
| matrixSvrQemu调度优化 | 从配置动态获取baseCpu/baseMemory | 配置解析、默认值回退 |
| 并发安全问题 | 防止机器重复分配 | 分布式锁、任务排队 |
| /manage/task/node接口完善 | 返回List<NodeInfoEntity> | 数据聚合、DTO转换 |

### 1.2 数据结构分析

**SimulationDeployConfigEntity**（配置结构）：
```java
@Data
public class SimulationDeployConfigEntity {
    private String deploymentKey;
    private String deploymentValue;  // 匹配 "matrixSvrQemu"
    private String subScene;
    private List<DynamicParameterEntity> dynamicParameters;
    private List<DeploymentCategoryEntity> deploymentCategories;
}
```

**NodeInfoEntity**（返回结构）：
```java
@Data
public class NodeInfoEntity {
    private String id;
    private String ip;
    private String userName;
    private String password;
    private String port;
    private String architecture;
    private int cpu;
    private int memory;
    private String status;
    private String createBy;
    private String isUse;
    private String resourceType;
    private String deploymentType;
    private String resourcePoolId;
}
```

---

## 2. 技术方案

### 2.1 需求1：matrixSvrQemu调度逻辑优化

**方案描述**：

修改`NodeManageServiceImpl.getQemuEnDynamicValue()`方法，从configJson中解析`deploymentValue="matrixSvrQemu"`对应的配置项，提取`minCpu`和`minMemory`作为baseCpu和baseMemory的动态值。

**核心修改**：

```
原代码逻辑：
┌─────────────────────────────────────┐
│  baseCpu = 32 (固定值)              │
│  baseMemory = 128 (固定值)          │
│  if (kvm) { baseCpu=16, baseMemory=64 } │
└─────────────────────────────────────┘

新代码逻辑：
┌─────────────────────────────────────┐
│  1. 从configJson解析matrixSvrQemu配置  │
│  2. 获取minCpu, minMemory           │
│  3. baseCpu = minCpu (默认32)       │
│  4. baseMemory = minMemory (默认128)│
│  5. if (kvm) { baseCpu/=2, baseMemory/=2 } │
└─────────────────────────────────────┘
```

**修改位置**：`NodeManageServiceImpl.java`第456行附近

**配置解析流程**：
1. 通过`nodeManageMapper.getDeployTagsById("qemu")`获取configJson
2. 解析为`List<SimulationDeployConfigEntity>`
3. 过滤`deploymentValue.equals("matrixSvrQemu")`的配置项
4. 从对应的`DeploymentCategoryEntity`中提取`minCpu`和`minMemory`

---

### 2.2 需求2：机器分配并发安全问题（分布式锁 + 任务排队）

**问题分析**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  并发场景时序图                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  任务A                      数据库                    任务B              │
│    │                          │                         │              │
│    │───1. 查询可用机器────────▶│                         │              │
│    │                          │                         │              │
│    │◀──2. 返回机器1可用────────│                         │              │
│    │                          │                         │              │
│    │                          │◀──1. 查询可用机器───────│              │
│    │                          │                         │              │
│    │                          │───2. 返回机器1可用─────▶│              │
│    │                          │                         │              │
│    │───3. 锁定机器1───────────▶│                         │              │
│    │                          │                         │              │
│    │                          │◀──3. 锁定机器1──────────│              │
│    │                          │                         │              │
│    │  ⚠️  机器1被重复分配！                              │              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**解决方案**：分布式锁 + 任务排队

| 配置项 | 值 | 说明 |
| :--- | :--- | :--- |
| `lock_key` | `node_allocation_lock` | 全局锁的key |
| `lock_timeout` | 10000ms | 锁自动过期时间 |
| `max_wait_time` | 180000ms | 最大等待时间 |
| `retry_interval` | 100ms | 重试间隔时间 |

**核心流程**：

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    分布式锁 + 任务排队流程                                  │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐                                                          │
│  │ 请求任务     │                                                          │
│  └──────┬──────┘                                                          │
│         │                                                                 │
│         ▼                                                                 │
│  ┌─────────────────────────┐                                              │
│  │ 创建任务 taskEntity      │                                              │
│  │ 立即返回给客户端          │  ← 同步返回，不阻塞                          │
│  └──────┬──────────────────┘                                              │
│         │                                                                 │
│         ▼                                                                 │
│  ┌─────────────────────────┐                                              │
│  │ 异步执行：尝试获取分布式锁 │                                              │
│  │ Key: node_allocation_lock │                                            │
│  │ Timeout: 10s            │                                              │
│  └──────┬──────────────────┘                                              │
│         │                                                                 │
│    ┌────┴────┐                                                            │
│    │         │                                                            │
│    ▼         ▼                                                            │
│ 成功        失败                                                           │
│    │         │                                                            │
│    │    ┌────┴─────────┐                                                  │
│    │    │ 等待重试      │  最多等待3分钟                                    │
│    │    │ 间隔100ms     │                                                  │
│    │    └────┬─────────┘                                                  │
│    │         │                                                            │
│    │    ┌────┴────┐                                                       │
│    │    │         │                                                       │
│    │    ▼         ▼                                                       │
│    │  成功    超时                                                        │
│    │    │         │                                                       │
│    │    │         ▼                                                       │
│    │    │   更新任务状态=FAILED                                            │
│    │    │                                                                 │
│    │    └───────┬                                                         │
│    │            │                                                         │
│    ▼            ▼                                                         │
│  ┌─────────────────────────┐                                              │
│  │ 查询可用机器并分配        │                                              │
│  └──────┬──────────────────┘                                              │
│         │                                                                 │
│    ┌────┴────┐                                                            │
│    │         │                                                            │
│    ▼         ▼                                                            │
│ 成功        失败                                                           │
│    │         │                                                            │
│    │         │                                                            │
│    └────┬────┘                                                            │
│         │                                                                 │
│         ▼                                                                 │
│  ┌─────────────────────────┐                                              │
│  │ 释放分布式锁             │  ✓ 无论成功失败都释放                          │
│  │ DEL node_allocation_lock │                                            │
│  └──────┬──────────────────┘                                              │
│         │                                                                 │
│         ▼                                                                 │
│  ┌─────────────────────────┐                                              │
│  │ 更新任务状态              │                                              │
│  │ 成功: task.status=SUCCESS │                                            │
│  │ 失败: task.status=FAILED  │                                            │
│  └─────────────────────────┘                                              │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

**`createOffcloudPolicyEnv`方法改造**：

基于现有方法签名和逻辑，仅将机器分配部分（`checkEnvEnough`）移入异步执行，并加分布式锁控制：

```java
private EnvironmentTaskEntity createOffcloudPolicyEnv(
        List<SimulationDeployResultEntity> simulationDeployResultList,
        SimulationVerificationTaskBaseEntity simulationTask) {
    
    // ===== 原有逻辑保持不变：创建任务实体并入库 =====
    String taskId = CommmonUtils.getUuid();
    EnvironmentTaskEntity taskEntity = new EnvironmentTaskEntity(
        taskId, simulationTask.getName(), "0", "OFFCLOUD",
        simulationTask.getCreateBy(), "0");
    nodeManageMapper.insterOrUpdateServerTask(taskEntity);
    
    // ===== 异步执行：获取分布式锁 + 机器分配 =====
    CompletableFuture.runAsync(() -> {
        String lockValue = "task_" + taskId;
        String lockKey = "node_allocation_lock";
        long maxWaitTime = 180000;  // 3分钟
        long retryInterval = 100;   // 100ms重试间隔
        long lockTimeout = 10000;   // 10秒锁超时
        
        try {
            // 1. 尝试获取分布式锁，最多等待3分钟
            boolean lockAcquired = false;
            long startTime = System.currentTimeMillis();
            while (System.currentTimeMillis() - startTime < maxWaitTime) {
                lockAcquired = distributedLockService.tryLock(lockKey, lockValue, lockTimeout);
                if (lockAcquired) {
                    break;
                }
                try {
                    Thread.sleep(retryInterval);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    nodeManageMapper.updateEnvTaskStatus(taskId, "3");
                    return;
                }
            }
            
            if (!lockAcquired) {
                log.warn("Timeout waiting for node allocation lock, task: {}", taskId);
                nodeManageMapper.updateEnvTaskStatus(taskId, "3");
                nodeManageMapper.updateEnvTaskErrorMessage(taskId, "等待机器分配锁超时");
                return;
            }
            
            // 2. 获取锁成功，执行原有机器分配逻辑
            String simulationSceneId = simulationTask.getSimulationSceneId();
            Boolean isEnoughEnv = true;
            if ("qemu".equals(simulationSceneId) && simulationDeployResultList.size() > 1) {
                isEnoughEnv = false;
            } else {
                isEnoughEnv = checkEnvEnough(simulationDeployResultList, simulationTask, taskId, false);
            }
            
            if (!isEnoughEnv) {
                // 环境创建失败，回退之前预支的环境信息
                nodeManageMapper.deleteUsingEnvByTaskId(taskId);
                nodeManageMapper.updateEnvTaskStatus(taskId, "3");
                String errorMessage = nodeManageMapper.getErrorMessageByEnvTaskId(taskId);
                if ("checkDisc".equals(errorMessage)) {
                    errorMessage = "未找到符合磁盘的机器";
                } else {
                    errorMessage = "未找到符合cpu内存的机器";
                }
                nodeManageMapper.updateEnvTaskErrorMessage(taskId, errorMessage);
                nodeManageMapper.updateTaskLogInfo(simulationTask.getId(), errorMessage);
            } else {
                nodeManageMapper.updateEnvTaskStatus(taskId, "4");
            }
            
        } catch (Exception e) {
            log.error("Error allocating node for task: {}", taskId, e);
            nodeManageMapper.updateEnvTaskStatus(taskId, "3");
            nodeManageMapper.updateEnvTaskErrorMessage(taskId, e.getMessage());
        } finally {
            // 3. 无论成功失败，都释放锁
            distributedLockService.unlock(lockKey, lockValue);
            log.info("Released node allocation lock for task: {}", taskId);
        }
    }, taskExecutor);
    
    // ===== 立即返回taskEntity（状态为"0"，异步更新） =====
    return taskEntity;
}
```

**分布式锁服务接口**：

```java
public interface DistributedLockService {
    boolean tryLock(String key, String value, long expireTimeMs);
    boolean unlock(String key, String value);
    long getLockRemainingTime(String key);
}
```

---

### 2.3 需求3：/manage/task/node接口完善

**说明**：不改动现有接口定义，**仅在 `getOffCloudById` 方法内添加机器查询逻辑**。

**实现方案**：

在 `getOffCloudById` 方法内部添加以下代码片段：

```java
// ========== 机器查询逻辑（在getOffCloudById方法内添加）==========
List<NodeInfoEntity> nodeList = null;
if (environmentId != null) {
    // 直接使用JOIN查询，返回List<NodeInfoEntity>
    nodeList = serverUsingMapper.selectNodeListByTaskId(environmentId);
    
    // 密码脱敏
    if (nodeList != null) {
        for (NodeInfoEntity node : nodeList) {
            node.setPassword("******");
        }
    }
}
// nodeList 可用于组装返回结果
// ============================================================
```

**Mapper层新增方法**：

```xml
<!-- ServerUsingMapper（使用已有t_server_using表，JOIN查询） -->
<select id="selectNodeListByTaskId" resultType="NodeInfoEntity">
    SELECT 
        sbi.id,
        sbi.ip,
        sbi.user_name AS userName,
        sbi.password,
        sbi.port,
        sbi.architecture,
        sbi.cpu,
        sbi.memory,
        sbi.status,
        sbi.create_by AS createBy,
        sbi.is_use AS isUse,
        sbi.resource_type AS resourceType,
        sbi.deployment_type AS deploymentType,
        sbi.resource_pool_id AS resourcePoolId
    FROM t_server_using su
    JOIN server_basic_info sbi ON su.server_id = sbi.id
    WHERE su.task_id = #{taskId} 
      AND su.status = 'ALLOCATED'
</select>
```

---

## 3. 数据库变更

### 3.1 数据库变更

**说明**：使用已有的 `t_server_using` 表存储任务-机器关联关系，无需新增表，也无需修改 `server_basic_info` 表。

**表关系示意**：

```
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│   t_server_task │        │  t_server_using │        │server_basic_info│
│                 │        │                 │        │                 │
│  id = task-001  │ ─────▶ │  task_id       │ ─────▶ │  id             │
│  ...            │        │  server_id     │        │  ip, cpu, memory│
│                 │        │  ...           │        │  ...            │
└─────────────────┘        └─────────────────┘        └─────────────────┘
```

---

## 4. 监控指标

| 指标 | 计算方式 | 告警阈值 |
| :--- | :--- | :--- |
| **锁获取成功率** | 成功次数 / 总请求次数 | <99% |
| **平均等待时间** | 总等待时间 / 总请求次数 | >5秒 |
| **锁过期次数** | 释放锁时锁不存在的次数 | >10次/小时 |
| **最大等待时间** | 单次请求的最大等待时间 | >180秒 |
| **任务分配成功率** | 成功次数 / 总任务数 | <99% |

---

## 5. 异常处理

| 异常场景 | 处理方式 | 恢复策略 |
| :--- | :--- | :--- |
| **获取锁超时（3分钟）** | 抛出RuntimeException | 客户端重试 |
| **任务执行异常** | 捕获异常，记录日志 | 更新任务状态为FAILED |
| **锁过期（10秒）** | 自动释放（Redis PX） | 下一个任务可以获取锁 |
| **机器状态检查失败** | 返回false，记录日志 | 任务状态为FAILED |
| **无可用机器** | 返回false，记录日志 | 任务状态为FAILED |
