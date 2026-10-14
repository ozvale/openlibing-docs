# design.md — oneway-acl-add

## 技术方案

### 总体

在 `service/network_isolation.py` 新增 `add_oneway_acl_in_core_switcher(switcher_ip, src_ip, dst_ip, acl_number)`，在 `hidevlab_blue_service.py` 新增路由 `POST /switcher/core/cross/oneway/add`。整体复用 `add_batch_acl_in_core_switcher` 的"先回读快照 → 计算 → 单次 SSH 批量下发 → 回读校验"流程，但规则模型为单向一对（正向全通 + 反向 TCP 回传）。

### 规则模型

```
正向：rule <id> permit ip source <src_ip> 0 destination <dst_ip> 0
反向：rule <id> permit tcp source <dst_ip> 0 destination <src_ip> 0 tcp-flag ack
```

- 两侧均按单主机精确匹配（wildcard `0`），不支持 /24 网段模式
- 反向规则与现有 `add_port_acl_to_core_switcher` 的回传规则形式一致（`tcp-flag ack` 仅匹配带 ACK 标志的 TCP 报文，即回复报文；新连接首包 SYN 无 ACK 被拒绝）
- 正向与反向写入同一 `acl_number`（用户确认的设计决策，便于统一查询/删除）

### 执行流程

1. **参数校验**：`_is_valid_ipv4` 校验 src/dst 合法性
2. **回读快照**：`get_acls(with_detail=True)` 一次读取 ACL 全量规则明细（交互式 PTY + 分页处理 + 截断自检，由 `_get_acl_raw_output` 保证可靠性）
   - 从明细中按规则文本子串匹配正向/反向命令，命中则复用其 rule id（幂等）
   - 收集**所有协议**的 rule id（`permit ip` / `permit tcp` 等），避免新 ID 与 tcp 规则撞 ID
3. **ID 分配**：仅对不存在的规则分配新 ID，`get_portable_rule_id` 在存量 ID 空隙中找连续段（与 `add_batch_acl_in_core_switcher` 一致）
4. **下发**：`sys → acl number <acl> → rule ... → commit → quit` 单次 `switcher_exec_commands` 执行（多命令拼接已在生产验证）
5. **回读校验**：再次 `get_acls(with_detail=True)`，比对分配 ID 上的实际规则内容（不只查 ID 存在，防止撞 ID 被旧规则占位误判成功）
6. **返回**：`(True, [正向 rule_id, 反向 rule_id])` 或 `(False, 错误信息)`

### 路由层

- `ip_list` 必须为长度 2 的非空列表，否则返回参数错误
- `switch_ip` 有值时作为目标交换机，无值时用 `CORE_SWITCH`；凭据沿用 `CORE_SWITCH_USERNAME` / `CORE_SWITCH_PASSWORD`
- 日志脱敏：`mask_ips` 掩盖 IP 列表、`mask_ip_partial` 掩盖来源 IP 与交换机 IP
- 响应格式与 `/switcher/core/cross/add` 一致：成功返回 `{"rule_id": [正向id, 反向id]}`

### 幂等性说明

- 正向规则匹配文本：`permit ip source <src> 0 destination <dst> 0`
- 反向规则匹配文本：`permit tcp source <dst> 0 destination <src> 0 tcp-flag ack`
- 两条规则独立判断存在性：仅缺哪条补哪条

## 影响范围

| 文件 | 改动 |
| --- | --- |
| `service/network_isolation.py` | 新增 `add_oneway_acl_in_core_switcher`（约 80 行） |
| `hidevlab_blue_service.py` | 新增 import + 路由 `add_oneway_cross_acl`（约 30 行） |

不修改任何现有函数，无存量接口行为变化。

## 风险与约束

- 反向回传仅覆盖 TCP；UDP/ICMP 回传不放行（无状态交换机无法区分回复与新请求），需在接口文档中明示
- `switch_ip` 指定的交换机必须与 CORE_SWITCH 使用相同凭据
- 依赖 `display acl` 回读可靠性（分页/截断处理已由 `_get_acl_raw_output` 兜底，读取失败直接判失败不下发）
