# query-acl-vc-security-group

## 需求背景

`hidevlab-infra-manager-service` 是 HiDevLab 实验室平台的基础设施管理服务（Blue Service Agent），充当上层业务平台与底层华为基础设施（BMS / FusionCompute / 交换机 / 防火墙 / VPN / OBS / K8s）之间的自动化执行代理。服务无状态、无 DB。

在既有能力中，核心交换机 ACL 与 FusionCompute（VC）安全组的配置写操作已具备，但缺少**查询能力**，导致上层平台无法在校验、巡检、可视化展示等场景中获取当前生效的 ACL 规则与安全组配置。本变更补齐这一缺口，并在交付主查询能力后，针对分页读取场景做了功能增强与缺陷修复。

## 功能描述

本任务分三个阶段交付（对应 3 个业务 Issue / 3 个业务 PR）：

### 阶段 1（主需求，Issue #31 / PR #48）

**做什么**：

- 支持查询核心交换机 ACL 规则配置
- 支持查询 VC（FusionCompute）安全组配置
- 在主路由层 `hidevlab_blue_service.py` 暴露查询接口
- 新增业务层 `service/fc_security.py` 承载 VC 安全组查询逻辑
- 扩展 `service/network_isolation.py` 支持核心交换机 ACL 查询
- 在 `base/config.py` 增补相关配置项

**不做什么**：

- 不改动 ACL / 安全组的写操作流程
- 不引入 DB 持久化（服务保持无状态）
- 不调整鉴权链路（沿用 `utils/auth_filter` 既有机制）

### 阶段 2（补充，Issue #35 / PR #52）

**做什么**：为 VC 安全组查询增加分页读取能力，避免单次拉取数据量过大造成接口超时或内存压力。

### 阶段 3（缺陷修复，Issue #36 / PR #53）

**做什么**：修复分页读取在数据量较大时漏页的问题，提供一次性获取所有分页的兜底路径。

## 验收标准

- [ ] 核心交换机 ACL 规则配置可通过新增查询接口获取，返回结构符合既有 DTO 约定
- [ ] VC 安全组配置可通过新增查询接口获取
- [ ] VC 安全组查询支持分页读取（阶段 2）
- [ ] 分页读取可一次性获取所有分页，不漏页（阶段 3）
- [ ] 新增接口受 `utils/auth_filter` 鉴权保护，未授权请求被拒绝
- [ ] 日志通过 `base/logging_handler` 输出，敏感字段经 `utils/security` 脱敏
- [ ] 不破坏既有 ACL 写操作与安全组写操作
- [ ] CI 流水线通过（`ci-pipeline-passed` 标签）

## 影响范围

| 维度 | 范围 |
| --- | --- |
| 业务仓 | `hidevlab-infra-manager-service`（单仓） |
| 模块 | 主路由层 + 业务层（fc_security / network_isolation）+ 基础层 config |
| 文件 | 5 个（详见 design.md） |
| 改动规模 | +748 / -57 行（阶段 1: +591/-8；阶段 2: +75/-25；阶段 3: +82/-24） |
| 接口 | 新增查询接口，无外部契约破坏 |
| 数据模型 | 无 schema 变更（服务无 DB） |
| 跨仓影响 | 无 |
| 部署影响 | 无（无状态服务，配置项增补向后兼容） |
