# query-acl-vc-security-group — 技术设计

## 方案概述

在 Blue Service Agent 既有分层架构（路由层 → 业务层 → 基础层 → 工具层）上**新增查询通路**，不动写链路：

- 路由层 `hidevlab_blue_service.py` 新增查询接口，复用 `utils/auth_filter` 鉴权
- 业务层新增 `service/fc_security.py` 承载 FusionCompute 安全组查询
- 业务层 `service/network_isolation.py` 扩展核心交换机 ACL 查询方法
- 基础层 `base/config.py` 增补 VC / 交换机查询相关配置项
- `service/virtual_machine.py` 微调以适配查询返回结构

## 架构决策

### 决策 1：新增 `fc_security.py` 而非塞进 `virtual_machine.py`

**选择**：新建独立业务模块 `service/fc_security.py` 承载 FusionCompute 安全组相关查询。

**原因**：`virtual_machine.py` 已承载 VM/K8s/安全组写操作，职责偏重；查询逻辑独立成模块便于后续扩展（如安全组规则批量查询、差异比对）。

### 决策 2：分页读取采用"按页迭代 + 一次性全量"双模式

**选择**：阶段 2 先实现按页迭代（`page` + `size` 参数），阶段 3 在发现漏页缺陷后补一次性全量获取模式。

**原因**：

- 按页迭代适配前端分页 UI，减少单次接口压力
- 全量模式适配巡检/导出场景，规避客户端漏页风险
- 双模式共存，调用方按场景选择

### 决策 3：查询接口与写接口共用鉴权链路

**选择**：复用 `utils/auth_filter`（token + HW 签名），不为查询接口单独开鉴权策略。

**原因**：ACL / 安全组配置属于敏感运维数据，需保持与写操作同等的鉴权强度。

## 涉及文件

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `base/config.py` | 修改（+1 行） | 增补查询相关配置项 |
| `hidevlab_blue_service.py` | 修改（+231/-） | 新增 ACL 查询与 VC 安全组查询接口路由 |
| `service/fc_security.py` | 新增（+325 行） | FusionCompute 安全组查询业务逻辑（含分页迭代 + 全量获取） |
| `service/network_isolation.py` | 修改（+33/-） | 扩展核心交换机 ACL 查询方法 |
| `service/virtual_machine.py` | 修改（+9/-） | 适配查询返回结构 |

## 风险 & 缓解

| 风险 | 等级 | 缓解 |
| --- | --- | --- |
| 分页读取在数据量大时漏页 | 中（阶段 3 已修复） | 阶段 3 引入一次性全量获取模式作为兜底 |
| 单次全量获取可能超时 | 低 | 调用方按场景选择分页或全量；后续可加超时配置 |
| 查询接口被滥用导致基础设施压力 | 低 | 复用 `auth_filter` 鉴权；后续可加速率限制 |
| 敏感配置泄露 | 低 | 沿用 `utils/security` 脱敏；日志走 `logging_handler` |

## 跨仓影响

无。本变更全部限制在 `hidevlab-infra-manager-service` 单仓内，不涉及其他业务仓的接口契约或数据结构变化。上层平台通过既有调用方式即可使用新增查询接口。
