# resource-schedule-cbb AI 记忆

> 仅沉淀经过验证且会复用的规则。非通用的一次性细节不收录。

## 调度并发与资源校验

### 1. 资源池锁用 `resPoolIds`，入参校验必须覆盖它

`EnvCreateRequest` 同时有 `resPoolNames`（人读名）和 `resPoolIds`（锁 key）。`RedisLockService.acquireLocks` 用 `resPoolIds` 加锁 `schedule:pool:{poolId}`。`ScheduleUtil.checkCommonRequest` 曾只校验 `resPoolNames`，导致宿主只传 `resPoolNames` 不传 `resPoolIds` 时 `acquireLocks([])` 返回空 `failedPools`、被当成功 → 整个调度无锁跑，并发任务全部抢同一台机器。

**规则**：任何加锁前的入参校验，必须校验锁 key 本身（`resPoolIds`）非空，不能只校验它的人读别名（`resPoolNames`）。`acquireScheduleLock` 入口也应独立做空拒绝（双保险，防 `validateRequest` 调用顺序变化或方法被其他路径复用）。

验证：`ScheduleUtilTest.testValidateRequest_EmptyResPoolIds_Throws` / `testValidateRequest_EmptyListResPoolIds_Throws`。

### 2. 资源检查函数的返回值不能同时当"不检查哨兵"和"回写值"

`GreedyAlgo.hasEnoughResources` 在 `requiredNpuNum > 0` 时曾返回 `{remNpu, 0, 0}`，用 `0` 表示"不检查 CPU/内存"。但 `allocateContainer` 把同一个 `0` 当剩余值回写 `server.setIdleCpuCoreNum(0)` / `setIdleMemorySize(0)`，把空闲 CPU/内存清零，污染优先级排序（`compareServerPriority` NPU→CPU→内存升序，清零后该机恒排最前）和非 NPU 容器分配（公式 `remCpu = idleCpu - reqCpu - idleNpu * maxCpu` 用了清零的 `idleCpu`）。

**规则**：函数返回值若同时用于"守卫检查"（`< 0` 判断）和"回写"（`set` 回 Server），不能用 `0` 当"不检查"哨兵——`0` 不触发 `< 0` 守卫，但会被当真实值回写。应返回当前真实值（如 `server.getIdleCpuCoreNum()`），守卫靠"真实值恒 >= 0、不触发"来跳过，回写则保持不变。

验证：`GreedyAlgoTest.testSelect_withNpu_doesNotZeroCpuAndMemory`。

## 环境与工具

### 3. `gitcode.exe` wrapper 启动失败时用 Python 入口绕过

`gitcode-cli`（pip 包）安装后生成的 `gitcode.exe`（在 `Python314\Scripts\`）可能因内嵌 python 路径损坏而启动报"应用程序错误"。此时 `where.exe gitcode` 能找到它但执行失败。

**绕过**：用 `py -3.14 -c "import sys; sys.argv=['gitcode']+sys.argv[1:]; from gc_cli.wrapper import main; main()"` 直接调 Python 入口。或写个 wrapper 脚本 `gitcode.py`：

```python
import sys
sys.argv = ['gitcode'] + sys.argv[1:]
from gc_cli.wrapper import main
main()
```

用 `py -3.14 gitcode.py <subcommand> ...` 调用。

**彻底修**：`py -3.14 -m pip install --force-reinstall gitcode-cli` 重新生成 wrapper。

### 4. `gitcode pr create` 0.6.1 支持 `--body-file`，但无 `--label`

`pr create` 0.6.1 有 `--body-file`（可传中文，UTF-8 不乱码），但无 `--label`。加标签用 `pr edit <PR#> -R owner/repo --labels ai-assisted` 两步走。`issue create` 用 `-R owner/repo` 指定仓库。
