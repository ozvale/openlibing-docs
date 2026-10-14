# oneway-acl-add

## 需求背景

现有接口 `POST /switcher/core/cross/add` 实现的是**双向** ACL 打通（A→B 与 B→A 各生成一条 `permit ip` 规则）。部分网络隔离场景只需要**单向**访问：源侧可主动访问目的侧，目的侧仅允许回传报文、不允许主动发起连接。同时，此类场景的目标交换机不总是默认 CORE_SWITCH，需要调用方指定登录的交换机 IP。

Issue: openlibing/hidevlab-infra-manager-service#60

## 功能描述

### 做什么

- 新增同步接口 `POST /switcher/core/cross/oneway/add`
- `ip_list` 固定两个值：`[源IP, 目的IP]`
- 正向规则：`permit ip source <src_ip> 0 destination <dst_ip> 0`（全部协议放行）
- 反向回传规则：`permit tcp source <dst_ip> 0 destination <src_ip> 0 tcp-flag ack`（仅放行 TCP 回复报文，目的侧无法主动发起 TCP 新连接）
- 正向与反向规则写入同一入参 `acl_number` 指定的 ACL（缺省 ACL_NUMBER）
- 新增参数 `switch_ip`：有值时登录该 IP 对应交换机，无值时登录 CORE_SWITCH（凭据沿用 CORE_SWITCH_USERNAME/PASSWORD）
- 幂等：下发前回读 ACL，已存在的规则复用已有 rule id，不重复下发

### 不做什么

- 不支持 /24 网段模式（两侧均按单主机精确匹配，wildcard 0）
- 不修改现有 `/switcher/core/cross/add` 双向接口
- 不提供异步回调（同步接口，与被基于接口一致）
- 反向规则不放行 UDP/ICMP 回传（无状态交换机无法区分 UDP 回复与新请求）

### 接口契约

**入参** `POST /switcher/core/cross/oneway/add`

```json
{
  "ip_list": ["1.1.1.1", "2.2.2.2"],
  "acl_number": "3999",
  "switch_ip": "10.0.0.254"
}
```

- `ip_list`：必填，固定两个元素 `[源IP, 目的IP]`
- `acl_number`：ACL 编号，规则写入该 ACL
- `switch_ip`：可选，登录的交换机 IP；不传时登录 CORE_SWITCH

**回参**

```json
{"code": 200, "msg": "success", "data": {"switch_ip": "10.0.0.254", "rule_id": [101, 102]}}
```

`switch_ip` 为实际下发规则的交换机 IP（入参 `switch_ip` 有值时为该值，无值时为 CORE_SWITCH）；`rule_id` 为 `[正向 rule_id, 反向 rule_id]`。失败时 `code` 为参数错误码，`msg` 为失败原因。

## 验收标准

- [ ] 接口按语义下发正向 + 反向两条规则，写入同一 `acl_number` 的 ACL
- [ ] 重复调用同一 (src, dst) 不产生重复规则，返回已有 rule id（幂等）
- [ ] `switch_ip` 生效：传值登录指定交换机，不传登录 CORE_SWITCH
- [ ] 回读校验：下发后回读 ACL 比对规则内容，不一致判定失败
- [ ] 日志中 IP 脱敏（mask_ips / mask_ip_partial）
- [ ] 输出接口文档

## 影响范围

- 修改文件：`service/network_isolation.py`（新增 `add_oneway_acl_in_core_switcher`）、`hidevlab_blue_service.py`（新增路由 + import）
- 复用：`get_acls` / `get_portable_rule_id` / `switcher_exec_commands`（不修改）
- 网络：目标交换机指定 ACL 规则增加（操作面影响，非代码影响）
