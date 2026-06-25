
# 需求背景与验收标准

## 1. 需求背景

### 1.1 业务场景概述
本需求涉及仿真平台中 QEMU 任务调度的核心功能优化，包含以下三个独立但关联的需求点：

| 序号 | 需求点 | 描述 |
| :--- | :--- | :--- |
| 1 | matrixSvrQemu调度逻辑优化 | 当前`baseCpu`和`baseMemory`为硬编码固定值，需改为从配置动态获取 |
| 2 | 机器分配并发安全问题 | 接口并发调用可能导致同一机器被重复分配，需分析并解决 |
| 3 | /manage/task/node接口完善 | 补充接口实现，返回`List<NodeInfoEntity>`格式数据 |

### 1.2 现状分析

**问题1：硬编码配置**
- 当前位置：`NodeManageServiceImpl.java:456-460`
- 问题：`baseCpu=32`、`baseMemory=128`（kvm模式下`baseCpu=16`、`baseMemory=64`）为硬编码
- 影响：无法灵活配置，每次调整需修改代码重新部署

**问题2：并发安全**
- 风险场景：多个任务同时调用`/manage/task`接口分配机器
- 问题根因：查询可用机器和更新机器状态之间存在时间窗口，高并发下可能导致同一机器被多次分配

**问题3：接口不完整**
- `/manage/task/node`接口已有定义但实现不完整
- 返回格式不符合预期，需调整为`List<NodeInfoEntity>`

---

## 2. 验收标准

### 2.1 需求1验收标准

| 验证项 | 预期结果 | 测试方法 |
| :--- | :--- | :--- |
| baseCpu动态获取 | 从configJson的SimulationDeployConfigEntity中deploymentValue=matrixSvrQemu的minCpu读取 | 配置不同minCpu值，验证调度结果 |
| baseMemory动态获取 | 从configJson的SimulationDeployConfigEntity中deploymentValue=matrixSvrQemu的minMemory读取 | 配置不同minMemory值，验证调度结果 |
| kvm模式适配 | 当executeCommand包含"kvm"时，使用minCpu/2和minMemory/2 | 配置kvm模式参数，验证计算结果 |
| 兼容回退 | 配置读取失败时回退到默认值(baseCpu=32, baseMemory=128) | 构造配置异常场景，验证系统稳定性 |

### 2.2 需求2验收标准

| 验证项 | 预期结果 | 测试方法 |
| :--- | :--- | :--- |
| 并发分配唯一性 | 100个并发请求分配机器，无重复分配现象 | 压测工具模拟高并发场景 |
| 锁机制有效性 | 机器分配过程中被锁定，其他任务无法抢占 | 日志分析+代码审查 |
| 锁超时释放 | 异常情况下锁能自动释放，不影响机器复用 | 模拟任务中断场景 |
| 性能影响 | 加锁后接口响应时间增加不超过20% | 性能基准测试对比 |

### 2.3 需求3验收标准

| 验证项 | 预期结果 | 测试方法 |
| :--- | :--- | :--- |
| 返回格式正确性 | 响应data字段为`List<NodeInfoEntity>`类型 | 接口调用+JSON结构验证 |
| 字段完整性 | 每个NodeInfoEntity包含id、ip、userName、password、port、architecture、cpu、memory、status、createBy、isUse、resourceType、deploymentType、resourcePoolId | 接口调用+字段校验 |
| 任务关联正确性 | 返回的节点列表与指定任务ID关联 | 多任务场景交叉验证 |
| 异常处理 | 无效taskId返回空列表而非错误 | 边界条件测试 |

---

## 3. 依赖与前置条件

### 3.1 依赖清单

| 依赖项 | 版本/状态 | 说明 |
| :--- | :--- | :--- |
| configJson配置 | 已存在 | 包含SimulationDeployConfigEntity结构 |
| NodeInfoEntity | 已定义 | 位于`entity/nodemanage/NodeInfoEntity.java` |
| 分布式锁服务 | 已存在 | `DistributedLockService` |
| NodeManageMapper | 已存在 | 数据库访问层 |

### 3.2 前置条件

- [ ] 确认configJson中matrixSvrQemu配置包含minCpu和minMemory字段
- [ ] 确认分布式锁服务可用且配置正确
- [ ] 确认NodeInfoEntity结构满足接口返回需求

---

## 4. 风险评估

| 风险项 | 风险等级 | 影响 | 缓解措施 |
| :--- | :--- | :--- | :--- |
| 配置变更导致调度异常 | 中 | 可能导致资源分配不足或浪费 | 增加配置校验和默认值回退机制 |
| 锁机制引入性能瓶颈 | 中 | 高并发场景下响应变慢 | 采用细粒度锁+合理超时时间 |
| 接口修改影响现有调用方 | 低 | 可能导致调用方解析失败 | 保持接口兼容性，仅扩展返回字段 |
| 分布式锁死锁 | 低 | 极端情况下资源无法释放 | 设置锁超时+定期清理机制 |
