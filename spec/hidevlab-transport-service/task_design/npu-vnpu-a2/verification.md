# A2 vNPU 评审修复验证记录

日期：2026-10-22。业务本轮 commit：95d2e76（本地待用户自测，未推送 PR #186）。关联 openlibing/hidevlab-transport-service#120。

- RED：首批 32 个用例中 11 个按预期失败；后续为健康/本机 daemon/参数边界、外部实例保护和驱动冲突分别补回归并确认失败。
- GREEN：实际业务工作树 `bash tests/npu_sim/cases.sh`，44 PASS / 0 FAIL。包含真实 flock 竞争；所有 NPU/Docker 命令使用 fakebin。
- `bash -n`：lib_npu.sh、lib_container.sh、resource_start_docker.sh、resource_restart_container.sh、cases.sh、review_cases.sh 六文件通过。
- 内嵌 Python、service/docker_manager.py、tests/test_lib_npu.py 语法检查通过；git diff --check 通过。
- Linux pytest 包装未运行：WSL 没有 pytest；其调用的同一 shell 套件已直接运行通过。
- 改动范围安全自检：无新增凭证/依赖，配置路径仅宿主机管理；验证能力文件写权限，Docker 仅本机 Unix socket，A2 显式 runc，环境变量按参数边界传递。账本/驱动/Docker 冲突及未知实例均拒绝变更；未知 run 结果保留预留。
- 范围自检：仅业务仓、关联 docs spec；保留原有 d5ace80 回收优化与驱动占用检查；不改双芯物理整卡算法、不接删除钩子，不混入软共享，不执行 Phase 5。
- 交付限制：宿主机须配置已核对的物理映射和已验证 template/K/资源。sample verified=false，模拟 evidence 不能冒充硬件验收。真实 A2 驱动/CANN/镜像算子、隔离、重启持久化及设备主次编号仍待用户在空闲测试机自测。
