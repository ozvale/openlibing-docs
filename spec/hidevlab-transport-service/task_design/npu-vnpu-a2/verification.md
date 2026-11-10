# A2 vNPU 评审修复验证记录

## 当前创建流程修订

日期：2026-10-22。业务 commit：8cc774f48485fc530497168dd4e5414c7aa3c4b4（本地未推送）。关联 openlibing/hidevlab-transport-service#120、PR #186。

- RED：新增流程用例首次运行 7 项失败，验证旧固定 K、未登记分区跳过及最终绑定读取缺失。另分别确认自动物理映射、兄弟实例进程占用、多实例验证开关、设备已支持的 `_m` 模板被拒绝等失败。
- GREEN：WSL Debian 在实际业务工作树执行 `bash tests/npu_sim/cases.sh`，58 PASS / 0 FAIL；包含 9 项实际 transport 回调 helper 单测。完整 create 路径也验证实际父卡和当前容器所用 vNPU ID，不包含空闲兄弟实例。
- 覆盖实际可切三份/六份、退出码为零但 Status: Fail 的耗尽、普通失败回滚、假成功、全机未登记空闲分区回收、占用不合并、回收失败阻断、混合模板复用与恢复、自动映射、驱动/容器归属、真实 flock 竞争。
- 回调覆盖容器名过滤、缺标记失败、模式/数量/父子 ID 检查、冲突快照拒绝、重复相同标记、多实例及旧双芯 PHY 回调兼容。后者仅测试字段校验，不增加双芯切分实现。
- 9 个 Bash 文件语法通过；3 个 Python 文件、NPUPY 和 10 段内嵌 Python 语法通过。Ruff 0.15.15 对修改的 Python 文件规则和格式检查通过，git diff --check 通过。
- 未运行 Linux pytest 包装（WSL 未安装 pytest）；同一 shell 套件已直接执行。未执行真实 NPU/Docker 操作。
- 范围与安全自检：仅指定业务仓及对应 docs；保留全量 Docker 快照、占用保护、事务回滚范围、generation 和本地锁。不新增生产依赖/凭证，不修改双芯分配算法或删除钩子，不执行最终归档。
- 交付限制：实际驱动耗尽提示、phyid-remap 支持、CANN/镜像算子、隔离与重启后设备主次编号仍需用户在 A2 非双芯测试机自测。默认不再需要 capacity plan 或 verified 配置；映射查询不可用时可使用管理员核对的显式映射文件。

## 前一轮记录（部分方案已由当前修订替代）

日期：2026-10-22。业务本轮 commit：95d2e76（本地待用户自测，未推送 PR #186）。关联 openlibing/hidevlab-transport-service#120。

- RED：首批 32 个用例中 11 个按预期失败；后续为健康/本机 daemon/参数边界、外部实例保护和驱动冲突分别补回归并确认失败。
- GREEN：实际业务工作树 `bash tests/npu_sim/cases.sh`，44 PASS / 0 FAIL。包含真实 flock 竞争；所有 NPU/Docker 命令使用 fakebin。
- `bash -n`：lib_npu.sh、lib_container.sh、resource_start_docker.sh、resource_restart_container.sh、cases.sh、review_cases.sh 六文件通过。
- 内嵌 Python、service/docker_manager.py、tests/test_lib_npu.py 语法检查通过；git diff --check 通过。
- Linux pytest 包装未运行：WSL 没有 pytest；其调用的同一 shell 套件已直接运行通过。
- 改动范围安全自检：无新增凭证/依赖，配置路径仅宿主机管理；验证能力文件写权限，Docker 仅本机 Unix socket，A2 显式 runc，环境变量按参数边界传递。账本/驱动/Docker 冲突及未知实例均拒绝变更；未知 run 结果保留预留。
- 范围自检：仅业务仓、关联 docs spec；保留原有 d5ace80 回收优化与驱动占用检查；不改双芯物理整卡算法、不接删除钩子，不混入软共享，不执行 Phase 5。
- 交付限制：宿主机须配置已核对的物理映射和已验证 template/K/资源。sample verified=false，模拟 evidence 不能冒充硬件验收。真实 A2 驱动/CANN/镜像算子、隔离、重启持久化及设备主次编号仍待用户在空闲测试机自测。
