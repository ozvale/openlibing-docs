# batch-acl-add

## 需求背景

新增 harbor 机器时，需要将已有所有机器批量添加到该 harbor 的 ACL 规则中。当前 `add_port_acl_to_core_switcher` 仅支持单源 IP 调用，黄区需多次循环调用，效率低且无法保证原子性。需提供一个异步批量接口，黄区一次性传入按 `acl_number` 分组的多源 IP + 单目标 IP + 端口范围，infra-manager 内部并发处理并异步回调结果。

## 功能描述

### 做什么

- 新增异步接口 `POST /switcher/src/acl/port/add`
- 接收按 `acl_number` 分组的多源 IP + 单目标 IP + 端口范围
- 后台线程对每个 (acl_number, src_ip) 组合调用 `add_port_acl_to_core_switcher`
- 完成后回调黄区，返回按 `acl_number` 分组的 ruleId 列表

### 不做什么

- 不修改 `add_port_acl_to_core_switcher` 内部逻辑（仅复用）
- 不支持单个源 IP 失败后回滚已添加规则
- 不修改现有 `/switcher/core/acl/port/add` 同步接口

### 接口契约

**入参** `POST /switcher/src/acl/port/add`

```json
{
  "task_id": "12345",
  "machines": [
    {"acl_number": "3998", "ip": ["1.1.1.1", "1.1.1.2"]},
    {"acl_number": "3999", "ip": ["1.1.1.3", "1.1.1.4"]}
  ],
  "dst_ip": "10.0.0.100",
  "dst_port_range": "{[443,443]}"
}
```

**回参**

```json
{"code": 200, "msg": "Async batch add ACL started", "data": "success"}
```

**回调** `POST /callback/switcher/src/acl/port/add`

```json
{
  "taskId": "12345",
  "result": "success"/"failed",
  "details": [
    {"acl_number": "3998", "ruleId": [10001, 10002, 10003, 10004]},
    {"acl_number": "3999", "ruleId": [10005, 10006, 10007, 10008]}
  ],
  "msg": ""
}
```

## 验收标准

- [ ] `POST /switcher/src/acl/port/add` 接收合法入参立即返回 `{code:200, data:"success"}`
- [ ] 接口立即返回，后台异步执行 ACL 添加
- [ ] 每个源 IP 在正向 ACL 与回传 ACL（3998）各生成一条规则
- [ ] ruleId 起点为 10000（沿用 `add_port_acl_to_core_switcher` 现有逻辑）
- [ ] 回调 `details` 按 `acl_number` 分组，每组 `ruleId` 包含该组所有源 IP 的全部 ruleId（flatten）
- [ ] 单组失败不影响其他组，最终 `result` 任一失败即 `failed`
- [ ] 回调通过 `sign_request` 发送到 Apollo 配置的 `SWITCHER_ACL_PORT_ADD_CALLBACK_URL`

## 影响范围

- 新增文件改动：`hidevlab_blue_service.py`（新增路由 + 异步任务函数）、`base/config.py`（新增 Apollo 配置项）
- 复用：`service/network_isolation.py#add_port_acl_to_core_switcher`（不修改）
- 网络：核心交换机 ACL 规则增加（操作面影响，非代码影响）
