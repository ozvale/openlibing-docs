# 蓝区环境创建并发优化 — 技术设计

## 方案概述

以「目录隔离 + 资源维度分布式锁 + 清理路径校验」三层手段解决同物理机并发部署冲突；运维指标子需求本次回退，不引入 Prometheus 依赖与暴露配置。

## 架构决策

### 1. 任务目录隔离

- 上传与部署路径改为：
  - 任务产物：`{serverDeployPath}/{engineId}/{taskId}/`
  - 脚本：`{serverDeployPath}install/{taskId}/script/`
  - 配置：`{serverDeployPath}install/{taskId}/conf/`
  - 记录字段：`t_server_using.config_path`
- 引擎包目录 `{serverDeployPath}/{engineId}/` 仍按「节点 + 引擎」共享，但共享写操作全部串行（见决策 2）。
- 每次执行脚本前对该任务目录 `rm -rf && mkdir -p`，消除上一轮残留。

### 2. 锁粒度：按物理机 IP 维度

| 场景 | 锁名 | 过期时间 | 等待策略 |
|---|---|---|---|
| 端口扫描与分配 | `qemu_port_ip_{ip}` | 1800s | 最多 120 次 × 10s（约 20 分钟） |
| Docker 镜像加载 | `qemu_image_{ip}_{version}` | 3600s | 最多 300 次 × 10s（约 50 分钟） |
| 引擎/qcow 文件传输 | `qemu_file_{ip}_{engineId}` / `qemu_file_{ip}_{qcowId}` | 3600s | 最多 300 次 × 10s（约 50 分钟） |

- 统一使用 `DistributedLockService.acquireLock` + `releaseLock(lockKey, ownerToken)`，`try/finally` 保证释放，释放前校验 ownerToken。
- 锁前缀常量与业务键分离（`qemu_port_ip_` / `qemu_image_` / `qemu_file_`），避免不同资源类型误共用锁。
- 端口分配把「查询已占用端口 → 扫描 → 写库」整体放进锁内，保证同一 IP 的分配原子性。

### 3. 清理安全化

删除任务目录前依次校验：

1. 精确匹配禁止目录清单（`/`、`/etc`、`/var`、`/home`、`/usr` 等）；
2. canonical path 不落在禁止前缀（`/etc/`、`/var/`、`/tmp/`、`/opt/` 等）；
3. 路径深度至少 3 段（`/{一级}/{二级}/{任务目录}`），防止浅路径误删。

清理为尽力而为：任务目录常由 `root` 创建，普通用户删除失败只记录告警，不阻断关闭流程。

### 4. 数据模型变更

- `t_server_using` 新增 `config_path VARCHAR(1000)`，changeset `20261105_add_config_path_to_t_server_using`（带 `tableExists` + `columnExists` 前置条件，可重复执行）。
- `20261104_delete_qemu_task_view_info_7f3de5c6`：清理一条历史任务视图记录，释放其占用端口；删除不可逆，rollback 为空操作。

### 5. 运维指标：本次回退

- 移除 `micrometer-registry-prometheus` 依赖，移除 `application.yaml` 的 `management.*` 配置。
- 原因：`InternalSimulationAuthFilter` 为全局强校验且只放行 `/simulation/health-check`，`/actuator/prometheus` 恒返回 401；`OperationLogFilter` 在认证前执行，每次抓取写 `MANAGE_LOG`。在认证放行或独立管理端口方案未与 SRE 确认前，暴露端点只增加攻击面，不产生可验收价值。
- 后续接入 AOM 时需同时决策：① 精确放行抓取路径并跳过审计，或 ② 使用独立 `management.server.port`，并按 CCE/AOM 要求配置 `prometheus.io/*` 注解。

## 涉及文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `src/main/java/com/openlibing/simulation/service/impl/QemuTaskServiceImpl.java` | 修改 | 目录隔离、锁常量与获取逻辑、清理安全校验 |
| `src/main/java/com/openlibing/simulation/mapper/QemuTaskMapper.java` | 修改 | 任务路径/配置路径写入 |
| `src/main/resources/mapper/QemuTaskMapper.xml` | 修改 | 对应 SQL |
| `src/main/resources/db/changelog/v1.0.0/t_server_using.xml` | 修改 | 新增 `config_path` changeset |
| `src/main/resources/db/changelog/v1.0.0/t_qemu_task_view_info.xml` | 修改 | 历史脏数据清理 changeset |
| `src/main/java/com/openlibing/simulation/constans/Constans.java`、`CmdConstants.java` | 修改 | 路径模板常量 |
| `pom.xml` | 修改 | 本次移除 `micrometer-registry-prometheus` |
| `src/main/resources/application.yaml` | 修改 | 本次移除 `management.*` |
| `src/test/java/.../QemuTaskServiceImplTest.java` | 修改 | 覆盖锁与目录隔离 |
| `AGENTS.md` | 修改 | 同步移除 micrometer/management 相关描述 |

## 风险 & 缓解

| 风险 | 缓解 |
|---|---|
| 存量部署目录结构变化，历史任务目录无人回收 | 新任务使用新目录；存量任务目录按运维脚本另行清理 |
| 锁过期时间小于真实传输耗时，导致并发进入 | 文件/镜像锁 3600s 且等待上限 50 分钟；超长传输仍需关注告警 |
| 锁获取失败返回失败而非静默继续 | 返回 `false` 并记录 `lockKey`/`taskId`，任务状态置 `FAILED` |
| `flock` 类 OS 级冲突未在本仓覆盖 | 由线下交付的 `install_ub_simulate.sh` 承担，本次不纳入仓库与文档验收 |
| 移除 metrics 依赖后 SRE 期望落空 | 在 PR 与 Issue 评论中明确「子需求 2 本次不交付」及后续接入前置条件 |

## 跨仓影响

- 无跨仓接口契约变更。
- 部署侧 `Deployment` 不再需要 `prometheus.io/*` 注解（本次不暴露指标）。
- 目标机 `install_ub_simulate.sh` 为线下交付物，不入本仓、不在本次验收范围。
