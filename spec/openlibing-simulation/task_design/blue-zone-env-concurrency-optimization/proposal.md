# 蓝区环境创建并发优化（只读交付）

## 需求背景

- 业务 Issue：[#65 【湛卢仿真】蓝区环境创建优化与运维监控能力建设](https://gitcode.com/openlibing/openlibing-simulation/issues/65)。
- 现状问题（蓝区 OFFCLOUD 实验室物理机多任务并发部署）：
  1. 部署脚本、`config.json`、`env.ini` 等文件统一写到 `{deployPath}/{engineId}/` 共享目录，同一引擎并发任务互相覆盖；
  2. 端口扫描与分配不是原子操作，并发任务可能选中同一端口；
  3. 同一节点并发执行 `docker load` / 镜像包与 qcow 文件上传，互相 `rm` 覆盖或竞争同一 tar；
  4. 任务关闭时的目录清理缺少路径约束，存在误删风险。
- 目标：让同一物理机上的多个环境创建任务可安全并行，缩短蓝区环境创建耗时，并为清理流程提供可定位的配置目录。

## 功能描述

做什么：

1. **任务目录隔离**：部署产物从 `{deployPath}/{engineId}/` 迁移到 `{deployPath}/{engineId}/{taskId}/`；脚本、配置分别落到 `install/{taskId}/script/`、`install/{taskId}/conf/`。
2. **按物理机 IP 维度的分布式锁**（复用仓内 `DistributedLockService`，带等待重试）：
   - 端口分配：`qemu_port_ip_{ip}`，锁内完成端口扫描与分配，保证原子性；
   - 镜像加载：`qemu_image_{ip}_{version}`；
   - 文件传输：`qemu_file_{ip}_{engineId}` / `qemu_file_{ip}_{qcowId}`。
3. **部署前目录重建**：任务启动前清理本任务残留目录再重建，避免旧文件影响本次启动。
4. **清理安全化**：删除任务目录前做禁止目录精确匹配、禁止前缀（canonical path）校验与路径深度校验。
5. **数据模型**：`t_server_using` 新增 `config_path` 字段，供清理流程定位 `install/{taskId}/conf`；附带一条历史脏数据（占用端口的任务视图记录）修正 changeset。
6. **单测适配**：`QemuTaskServiceImplTest` 覆盖新增的锁与目录隔离逻辑。

不做什么：

- 不改远端目标机脚本 `install_ub_simulate.sh`（含 `flock` 串行化的操作命令）——该脚本由线下交付并上传，不在本仓源码范围。
- 不改变对外 REST 接口契约、不新增管理端点、不调整认证与审计过滤器行为。

## 验收标准

- [ ] 同一物理机并发任务的文件、脚本、配置落在各自 `{taskId}` 目录，互不覆盖
- [ ] 端口扫描与分配在同一 IP 锁内完成，并发任务不产生重复端口
- [ ] 同一节点同版本镜像加载、同 qcow/引擎文件传输按锁串行，不出现互相 `rm`/覆盖
- [ ] 任务关闭清理只删除任务自身目录，`/`、`/etc`、`/var` 等系统路径被拒绝
- [ ] `t_server_using.config_path` changeset 可在存量库上安全执行（前置条件保护、可重复执行）
- [ ] `mvn clean test` 通过，并核对 `target/surefire-reports/`（surefire 配置了 `testFailureIgnore=true`，不能只看 BUILD 结果）
- [ ] 业务 PR 关联 Issue #65，且打上 `ai-assisted` 标签

## 影响范围

- 仓：`openlibing-simulation`（单仓）。
- 模块：Qemu 任务编排（`QemuTaskServiceImpl`）、Qemu 任务 Mapper、Liquibase changelog、单测。
- 部署侧：蓝区物理机上的 deployPath 目录结构由 `{engineId}/` 变为 `{engineId}/{taskId}/`；存量任务目录不做迁移。
