# A2 NPU 硬虚拟化 vNPU — 实现任务

## 进度: 8/8 complete

- [x] Task 1: 新增 `script/lib_npu.sh` 基础层——路径/日志/错误码、`npu-smi` 查询与解析（设备、芯片、模板、实例、模式、恢复开关）、Docker 全量占用扫描。
- [x] Task 2: `lib_npu.sh` 锁与账本——容器锁、兼容全局锁、父芯片多锁（升序/超时/逆序释放）、账本原子读写与状态机。
- [x] Task 3: `lib_npu.sh` 校验与拓扑操作——请求契约校验、运行时匹配实际 template、逐次创建至资源耗尽（回读/失败回滚）、整组合并（逐个销毁/失败隔离）。
- [x] Task 4: `lib_npu.sh` 分配器——vNPU 复用/空闲芯片切分/异模板合并重切、物理整卡分配（识别切分父卡）、多芯片统一排序加锁、预留/提交/回滚。
- [x] Task 5: `lib_npu.sh` 重启恢复——容器标签与账本对账、缺失实例按记录 `-v` 恢复、冲突返回 `RECOVERY_REQUIRED`。
- [x] Task 6: 接入 `lib_container.sh`——`parse_config` 新字段与严格校验；`create_container` 生命周期锁、vnpu 同名幂等检查、设备参数与容器标签；A5/950DT/双芯路径不变。
- [x] Task 7: 接入 `resource_restart_container.sh`——absent/stopped/created/running 四态处理与错误 marker。
- [x] Task 8: 模拟测试 `tests/npu_sim/cases.sh` + `tests/test_lib_npu.py`，并执行 `bash -n` 与用例。

## 验证方式

- `bash -n script/lib_npu.sh script/lib_container.sh script/resource_start_docker.sh script/resource_restart_container.sh`
- Git Bash 下运行 `tests/npu_sim/cases.sh`（伪 `npu-smi`/`docker`/`flock`）
- Linux CI：`pytest tests/test_lib_npu.py`
- 不执行真实切分/合并/Docker 设备绑定（上机验收项）

## PR #186 评审修复计划

以下为前一轮记录，固定 K/能力配置准入及未知空闲分区处理已由 allocation-flow-plan.md 和当前 design.md 替代。

详见 review-fixes-plan.md；本轮目标在最终验证通过后勾选。

- [x] 官方输出严格解析、总数核对与身份配置
- [x] 完整 Docker 快照、父子引用/广泛授权与驱动占用保护
- [x] 回滚限定事务实例，合并拒绝未知实例
- [x] 完整父芯片恢复、归属与规格冲突、统一锁顺序
- [x] 已验证模板/K/资源准入，仅 A2 非双芯
- [x] 测试/fixture 纳入版本控制，Linux pre-commit hook 接入
- [x] docs/npu-a2-avi-operations.md 双芯建议与能力配置说明
- [x] 全部回归、语法、范围与安全自检（44/44 模拟、语法与 diff 检查通过）

## 用户明确创建流程后的修订

详见 allocation-flow-plan.md，业务 commit 8cc774f。

- [x] PHY 先全机回收无容器/驱动/宿主占用和预留的切分父芯片，支持未登记空闲拓扑，回收失败阻断创建。
- [x] VNPU 按实际模板和空闲数量复用；支持未登记、未切满及混合模板父卡。
- [x] 新切分创建到明确资源耗尽，移除固定 K、容量验证配置、模板后缀和多实例验证开关准入；保存实际份数。
- [x] 驱动自动建立物理映射，可选显式映射文件，不把 Logic ID 当物理 ID。
- [x] 恢复使用保存的每个实例 ID/模板，不重新推算容量。
- [x] 创建/restart 回读当前容器实际映射，transport 按容器名、模式、数量和父子 ID 检查回调完整性。
- [x] Linux 模拟 58/58（含 9 项回调单测），Bash/Python 语法、Ruff 与差异检查通过；真实 A2 验收待用户自测。
