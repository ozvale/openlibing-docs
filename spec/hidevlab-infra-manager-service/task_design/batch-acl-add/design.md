# batch-acl-add — 技术设计

## 方案概述

新增异步 Flask 路由 `/switcher/src/acl/port/add`，立即返回后台任务启动信号；后台线程按 `acl_number` 分组遍历每个源 IP，复用 `add_port_acl_to_core_switcher` 完成正向 ACL + 回传 ACL 规则添加；全部完成后通过 `sign_request` POST 回调到 Apollo 配置的回调 URL，回参按 `acl_number` 分组聚合 ruleId。

## 架构决策

### 决策 1：复用 `add_port_acl_to_core_switcher`，不重写

**原因**：现有函数已处理正向/回传命令生成、规则查重、ID 分配（起点 10000）、SSH 交互。批量接口只需循环调用，不重复造轮子。

### 决策 2：按 `acl_number` 分组聚合，而非按 src_ip

**原因**：用户需求要求回调时按 `acl_number` 分组返回 ruleId，黄区需按 ACL 编号管理规则。

### 决策 3：串行处理每个源 IP，不并发 SSH

**原因**：核心交换机是单一设备，并发 SSH 同一交换机会触发会话冲突。串行处理保证 ACL 命令有序执行。整体耗时 = N 个源 IP × 单次 SSH 时间（约 5-10s）。

### 决策 4：失败不回滚

**原因**：现有 `add_port_acl_to_core_switcher` 不支持事务，回滚需调用 `delete_acl_in_core_switcher`。批量接口在任一失败时仅记录失败信息，由调用方决定是否清理。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `hidevlab_blue_service.py` | 修改 | 新增 `/switcher/src/acl/port/add` 路由 + `async_batch_add_port_acl` 函数 |
| `base/config.py` | 修改 | 新增 Apollo 配置 `SWITCHER_ACL_PORT_ADD_CALLBACK_URL` |

## 核心流程

```
1. 接口入参校验（task_id / machines / dst_ip / dst_port_range）
2. threading.Thread(target=async_batch_add_port_acl, args=(...), daemon=True).start()
3. 立即返回 {code:200, msg:"Async batch add ACL started", data:"success"}

async_batch_add_port_acl(task_id, machines, dst_ip, dst_port_range):
4. 遍历每个 group in machines:
   - acl_number = group["acl_number"]
   - 遍历 src_ip in group["ip"]:
     - rules = [{"dst_ip": dst_ip, "dst_port_range": dst_port_range}]
     - flag, result = add_port_acl_to_core_switcher(CORE_SWITCH, src_ip, rules, acl_number)
     - flag=True: result 是 [[forward_id, reply_id]]，flatten 加入该 acl_number 组的 ruleId
     - flag=False: 记录失败信息，标记 overall_success=False
5. 组装 callback_data:
   {
     "taskId": task_id,
     "result": "success" if overall_success else "failed",
     "details": [{"acl_number": "3998", "ruleId": [...]}, ...],
     "msg": ""
   }
6. sign_request(SWITCHER_ACL_PORT_ADD_CALLBACK_URL, REFERER, data=json.dumps(callback_data))
```

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 回传 ACL 编号硬编码 3998（在 `add_port_acl_to_core_switcher` 内） | 不修改原函数，沿用现有行为；接口入参的 `acl_number` 仅用于正向 ACL |
| 单次 SSH 失败导致部分规则添加 | 失败不回滚，回调 msg 记录失败 IP 与原因，调用方决定清理 |
| Apollo 未配置回调 URL | `sign_request` 仍会执行（与 transport-service 一致风格），由 Apollo 保证配置 |
| 交换机并发 SSH 会话冲突 | 串行处理每个源 IP，不使用 ThreadPoolExecutor |

## 跨仓影响

无跨仓代码影响。与 transport-service 机器巡检接口（同批需求）独立。
