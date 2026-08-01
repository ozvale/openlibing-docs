# npu-concurrent-overallocation — 归档

## 关联

- 业务 Issue: https://gitcode.com/resource-platform/resource-schedule-cbb/issues/8
- 业务 PR: https://gitcode.com/resource-platform/resource-schedule-cbb/merge_requests/117
- docs PR: 本归档 PR

## 变更摘要

修复并发调度时 NPU 卡超分配缺陷：三个任务各申请 1 张 NPU 卡时分到同一台只剩 1 张卡的物理机，部署时多个容器抢同一张卡，导致两个失败。

根因是 CBB 调度引擎的并发隔离存在缺陷链：

1. `ScheduleUtil.checkCommonRequest` 只校验 `resPoolNames` 不校验 `resPoolIds`，而资源池锁实际用的是 `resPoolIds`。`acquireLocks([])` 空列表时循环不执行、返回空 `failedPools`，`acquireScheduleLock` 把空当成功 → 整个调度无锁跑，三个 `schedule()` 各起一个 daemon 线程全部绕过锁并发执行。
2. `ScheduleEngine.acquireScheduleLock` 即使 `resPoolIds` 为空也返回 true（语义破裂），该方法被 `ContainerDeployScheduler` 等多路径复用。
3. `GreedyAlgo.hasEnoughResources` NPU 分支返回 `{remNpu, 0, 0}`，`allocateContainer` 把 `0` 回写 Server，清零 `idleCpuCoreNum`/`idleMemorySize`，污染排序与非 NPU 容器分配。

## 交付历程

- commit `c7e1ce6`: fix(npu): prevent lock-bypass over-allocation and CPU/mem corruption
  - `ScheduleUtil.checkCommonRequest` 增 `resPoolIds` 非空校验
  - `ScheduleEngine.acquireScheduleLock` 入口增 `resPoolIds` 空拒绝防御（抛 `PARAM_VALIDATION_FAILED`）
  - `GreedyAlgo.hasEnoughResources` NPU 分支返回真实 CPU/内存值
  - `ScheduleUtilTest` +2、`GreedyAlgoTest` +1 回归测试
- commit `6774167`: chore(pom): bump version to 2.2.11 → 2.2.12

## 用户自测反馈

用户在交付后直接触发归档，未反馈自测问题。PR body 中保留了两项待自测项（并发场景验证、正常调度回归），由用户在合入前自行验证。

## 最终验证

- `mvn test -Dtest=ScheduleUtilTest,GreedyAlgoTest`：43/43 全绿
- 全量 `mvn test`：受影响类全绿（3 个 `BmsScheduleTest` 失败是 base `release_202607` 已有，`git stash` 验证过与本次改动无关）
- pre-commit 敏感信息扫描通过
- PR CI：passed

## 设计偏差与取舍

- **未修"漏洞 2"（SPI 不做原子扣减）**：经分析确认，只要资源池锁生效（`resPoolIds` 非空），`SPI.allocate` 在锁内同步持久化，下一个任务拿锁后查到的是新数据。根因是锁被绕过（漏洞 1），不是 SPI 不持久化。本次只修 CBB 能防住的漏洞 1+3，漏洞 2 属宿主 SPI 实现责任。
- **未给 `AllocateResourceRequest` 加 CAS 字段**：若要彻底兜底（即使锁失效也不超分配），需给 SPI 接口加 expected `idleNpuNum` 字段做 `UPDATE ... WHERE idleNpuNum = expected`。这属于 SPI 接口变更（Full 模式），本次不做，留作后续演进。
- **`hasEnoughResources` 只修清零，不加 CPU/内存校验**：NPU 卡自带 CPU/内存预算（`npuSpecs` 的 `maxCpu`/`maxRam`），容器用 NPU 时不消耗 free CPU/RAM。现有测试 `testSelect_withNpu_andMemory_distributeCorrectly` 明确断言"NPU 需求时只检查 NPU 不检查内存"是设计意图，本次只堵清零污染，不改这个设计。

## 可复用经验

沉淀到 `spec/resource-schedule-cbb/ai_memory.md`：

1. 资源池锁用 `resPoolIds`，入参校验必须覆盖 `resPoolIds`（不能只校验 `resPoolNames`）。
2. 资源检查函数的返回值若同时用于"守卫检查"和"回写"，不能用 `0` 当"不检查"哨兵——`0` 会被回写清零状态。应返回当前真实值。

## 归档日期

2026-08-01
