# A2 vNPU Review Fixes Implementation Plan

> 前一轮评审记录。固定 K/能力验证配置方案已被用户明确的创建流程替代；当前实施与验收见 allocation-flow-plan.md 和 design.md。

> Execution: implement task by task in this session; one new commit per delivery, per workspace rules.

**Goal:** 修复 PR #186 评审缺口，仅开放 A2 非双芯 AVI 硬切分。

**Architecture:** 保留 lib_npu.sh 统一分配器、现有回收优化和账本。查询结果采用严格解析与全量校验；宿主机能力配置记录经过完整切分验证的 template/K/资源，恢复以父芯片为单位执行。双芯不改实现，只提供运维与后续接入建议。

**Tech Stack:** Bash、内嵌 Python 3、Linux flock、伪 npu-smi/Docker、pytest。

## 授权与基线

- 用户于 2026-10-22 确认 Full 模式、现有业务分支和 docs 分支、下列实现范围。
- 业务分支 feat-create-delete-vnpu-A2，基线 d5ace80，整合已有未提交驱动空闲检查。
- docs 分支 spec-hidevlab-transport-service-npu-vnpu-a2；复用业务 Issue openlibing/hidevlab-transport-service#120。
- 用户自测前仅提交本地修复，不创建或更新业务 PR；不执行 Phase 5 归档。

## 实现任务

- [x] 1. 测试先行：将现有 tests/npu_sim 与 pytest 包装纳入版本控制；增加官方 info-vnpu/template 输出 fixture、异常查询、互斥、完整恢复、规格与代际回归，先确认失败原因。
- [x] 2. 严格解析：lib_npu.sh 按表头解析官方表格，核对总数和必填字段；设备映射不允许 info-l 猜测；模板数据不静默补零。
- [x] 3. 查询/占用边界：检查所有 Docker 查询退出码和完整对象集合；驱动、Docker、账本、进程证据不明时拒绝变更；回滚限定本事务 ID。
- [x] 4. 模板准入：用宿主机已验证能力配置取代最大模板×2推断，检查身份、模板/K、真实总资源和组合预算，失败不变更拓扑。
- [x] 5. 分配安全：复用、切分、整卡采用一致父子引用和 broad access 检查；严格复核请求数量；代际/双芯在 vnpu 请求校验处拒绝。
- [x] 6. 容器恢复：lib_container.sh/resource_restart_container.sh 统一规格检查和锁顺序；重建完整父芯片分区并确认归属；Docker 结果未知时保留预留。
- [x] 7. 文档：业务 docs 增加双芯建议及能力配置说明；同步 proposal/design/tasks。
- [x] 8. 验证并交付：WSL Linux 模拟测试、并发/故障回归、bash -n、Python 语法及 diff 检查、改动范围安全自检；业务和 docs 分别提交新 commit。

## 生成约束

仅修改 hidevlab-transport-service 与关联 spec；不改 A5/950DT/双芯整卡算法、删除协议、网络/镜像/存储流程，不做无关格式化。敏感配置不进日志；能力文件由宿主机管理员维护，不接受请求方覆盖。真实 NPU 上机验收保留为用户测试项，模拟结果不作为硬件验证证据。

## 验证命令

Linux: `bash tests/npu_sim/cases.sh`、`python3 -m pytest tests/test_lib_npu.py`；四个脚本 `bash -n`；Python compile；`git diff --check`。新增回归先 RED，再修复至 GREEN；测试用命令均限制为 fakebin，不接触真实硬件或 Docker daemon。
