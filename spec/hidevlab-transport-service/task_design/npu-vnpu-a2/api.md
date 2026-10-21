# A2 NPU 硬虚拟化（vNPU）transport 接口契约

- 版本：v1（2026-10-21）
- 对接方：管理面（黄区） → transport（宿主机侧脚本）
- 关联需求：openlibing/hidevlab-transport-service#120
- 实现分支：`feat-create-delete-vnpu-A2`
- 设计依据：`openlibing-docs/spec/hidevlab-transport-service/task_design/npu-vnpu-a2/design.md`

本文只描述**黄区需要感知的契约**：请求字段、分配语义、结果与错误码、生命周期约束。
宿主机内部的锁、账本、拓扑状态机不需要黄区实现或解析。

---

## 1. 变更摘要

| 项目         | 变更                                                                                      |
| ------------ | ----------------------------------------------------------------------------------------- |
| 请求新增字段 | 仅两个：`resources.npu_mode`（`phy`/`vnpu`）、`resources.vnpu_template`（仅 `vnpu` 必填） |
| 兼容性       | 不传 `npu_mode` 等价 `phy`；A2 宿主机须完成能力配置                                       |
| 支持的代际   | A2（A5 / 950DT / `npu_dual_chips` 不走 vNPU）                                             |
| 结果通道     | 仍为异步任务 + 回调 `result` / `msg`，`msg` 中出现 `NPU_ERROR: <CODE>: <detail>`          |
| 删除流程     | 未接删除钩子；vNPU 在**后续 start/restart 请求**中惰性回收                                |

---

## 2. 调用入口

### 2.1 创建容器

```
POST /docker/multi/create
Authorization: <transport 现有鉴权头>
Content-Type: application/json
```

```json
{
  "task_id": "task-20261021-001",
  "all_containers": [
    {
      "ip": "10.0.0.11",
      "username": "root",
      "pwd": "******",
      "containers": [
        {
          "container_name": "ide-example",
          "image": "registry.example/ide:1.0",
          "request_id": "req-20261021-001",
          "network": {
            "subnet": "10.10.0.0/24",
            "gateway": "10.10.0.1",
            "container_ip": "10.10.0.20"
          },
          "share_storage": {
            "path": "/data/gluster",
            "member_id": "member-1",
            "public_storage": false,
            "container_storage": false,
            "persistence": false
          },
          "resources": {
            "npu_gen": "A2",
            "npu_num": 1,
            "npu_mode": "vnpu",
            "vnpu_template": "vir05_1c_16g"
          }
        }
      ]
    }
  ]
}
```

立即返回：

```json
{ "code": 200, "msg": "Async multi create started", "data": "success" }
```

实际结果通过 `DOCKER_MULTI_CREATE_CALLBACK_URL` 回调：

```json
{
  "taskId": "task-20261021-001",
  "result": "success | failed",
  "action": "multiContainerCreate",
  "msg": "=============== 容器 ide-example 部署日志 ===============\n...",
  "containers": [
    { "name": "container1", "phyDavinciId": [0], "vnpuDavinciId": [100] },
    { "name": "container2", "phyDavinciId": [1, 2], "vnpuDavinciId": [] }
  ]
}
```

`containers` 按容器逐个上报绑定结果：

| 字段            | 类型   | 说明                                                                   |
| --------------- | ------ | ---------------------------------------------------------------------- |
| `name`          | string | 容器名                                                                 |
| `phyDavinciId`  | int\[] | 实际绑定的物理卡编号（`/dev/davinci{x}`）；vNPU 为父芯片编号；升序去重 |
| `vnpuDavinciId` | int\[] | 实际绑定的 vNPU 编号（`/dev/vdavinci{x}`）；`phy` 模式为空数组         |

任务失败时（任一容器失败会触发全量清理）`containers` 返回 `[]`。

### 2.2 重启容器

```
POST /docker/restart
```

```json
{
  "ip": "10.0.0.11",
  "username": "root",
  "password": "******",
  "task_id": "task-20261021-002",
  "env_id": "env-123",
  "restart_params": {
    "container_name": "ide-example",
    "image": "registry.example/ide:1.0",
    "request_id": "req-20261021-001",
    "resources": {
      "npu_gen": "A2",
      "npu_num": 1,
      "npu_mode": "vnpu",
      "vnpu_template": "vir05_1c_16g"
    }
  }
}
```

> `restart_params` 直接作为宿主机 `config.json`。`host_ip` 由 transport 自动注入，黄区无需传。

回调：

```json
{
  "taskId": "task-20261021-002",
  "envId": "env-123",
  "result": "success | failed",
  "action": "restartContainer | restartPullOnly",
  "msg": "=============== 容器 ide-example 重启日志 ===============\n...",
  "containers": [
    { "name": "ide-example", "phyDavinciId": [0], "vnpuDavinciId": [100] }
  ]
}
```

---

## 3. NPU 资源契约

### 3.1 字段定义

| 字段                       | 类型   | 必填      | 默认                   | 说明                                                                                     |
| -------------------------- | ------ | --------- | ---------------------- | ---------------------------------------------------------------------------------------- |
| `resources.npu_gen`        | string | 否        | `""`                   | 代际标识；vNPU 仅支持 `A2`（A5/950DT 保持整卡旧逻辑）                                    |
| `resources.npu_num`        | int    | 否        | `0`                    | `0` 表示不分配；`phy` 表示整卡张数；`vnpu` 表示独立 vNPU 设备个数                        |
| `resources.npu_mode`       | string | 否        | `phy`                  | 仅允许 `phy` / `vnpu`（`physical` 仅作为内部兼容别名，黄区不要使用）                     |
| `resources.vnpu_template`  | string | vnpu 必填 | `""`                   | AVI 模板名，由管理面下发；必须出现在目标设备 `template-info` 清单中                      |
| `resources.npu_dual_chips` | bool   | 否        | `false`                | 双芯配对整卡；与 `vnpu` 互斥                                                             |
| `request_id`               | string | 否        | `ctr-<container_name>` | 可选，不属于本次新增契约；用于幂等、账本归属、崩溃对账，建议复用；`[A-Za-z0-9._-]{1,64}` |

### 3.2 模式语义

| 模式   | `npu_num` 含义                           | 设备映射                                          |
| ------ | ---------------------------------------- | ------------------------------------------------- |
| `phy`  | 申请几张**物理整卡**                     | `--device /dev/davinci<phy>`                      |
| `vnpu` | 申请几个**独立 vNPU 设备**，不做显存聚合 | `--device /dev/vdavinci<vnpu>:/dev/davinci<vnpu>` |

关键约束：

1. **调用方不指定卡号，也不指定 vNPU ID**；由宿主机选择父芯片并分配。
2. 一个 vNPU 只允许一个容器使用；同一父芯片的整卡与子 vNPU 互斥。
3. `npu_num=N` 不会把 N 个实例合并成一张大卡；`N>1` 表示 N 个独立设备。
4. 首次使用某父芯片时，宿主机按模板**完整切分 K 个实例**，只绑定 N 个，其余保留为空闲。
5. `N <= K`，且 N 个实例必须来自**同一父芯片**；不会跨父芯片拼凑。

### 3.3 模板由管理面下发，K 由宿主机实时计算

`vnpu_template` **必须由管理面在每次 create/restart 请求中下发**，transport 不内置模板白名单、也不假设默认模板。

宿主机收到模板后，在目标父芯片上执行 `npu-smi info -t template-info -i <device>`，解析
`Name / AICORE / Memory / AICPU / VPC / PNGD / VENC / VDEC / JPEGD / JPEGE`，按以下规则决定“如何完整切分”：

1. 模板必须出现在该设备上报的模板清单中，否则 `INVALID_TEMPLATE`；
2. `_m` / `_nm` 模板返回 `TEMPLATE_CANNOT_FULLY_TILE`；
3. A2 AVI 清单同时包含半卡与四分之一卡模板，芯片总量按“最大模板资源 × 2”推断；
   清单只有单一规格时无法证明完整切分，返回 `TEMPLATE_CANNOT_FULLY_TILE`；
4. `K = 总 AICORE / 模板 AICORE`，并要求 `总 Memory / 模板 Memory` 得到相同 K；
5. AICPU/VPC/DVPP 等资源按同一总量校验 `模板资源 × K ≤ 总量`；
6. 切分后回读真实拓扑，实例数与模板必须与 K 一致。

官方 A2 常见模板（**仅作示例，不是代码白名单**）：

| 芯片能力（参考） | 模板示例       | 单实例 AICore / HBM | 通常 K |
| ---------------- | -------------- | ------------------- | ------ |
| 20 AICore / 32GB | `vir05_1c_8g`  | 5 / 8GB             | 4      |
| 20 AICore / 32GB | `vir10_3c_16g` | 10 / 16GB           | 2      |
| 20 AICore / 64GB | `vir05_1c_16g` | 5 / 16GB            | 4      |
| 20 AICore / 64GB | `vir10_3c_32g` | 10 / 32GB           | 2      |
| 24 AICore / 64GB | `vir06_1c_16g` | 6 / 16GB            | 4      |
| 24 AICore / 64GB | `vir12_3c_32g` | 12 / 32GB           | 2      |

补充：

- 管理面只需下发模板名；**不需要**下发 K，也不需要预选卡号。
- 新模板只要驱动 `template-info` 能正确上报资源即可被使用，无需 transport 发版；
  但生产启用前仍需完成一次整组上机验证。
- 驱动输出缺少 AICORE/Memory 字段时返回 `NPU_QUERY_FAILED`，不会按“可切分”猜测。

### 3.4 校验规则（创建前即失败，不改拓扑）

| 请求                                                | 结果                             |
| --------------------------------------------------- | -------------------------------- |
| `npu_mode` 非 `phy` / `vnpu`                        | `INVALID_REQUEST`                |
| `npu_num` 非非负整数                                | `INVALID_REQUEST`                |
| `vnpu` 未传 `vnpu_template`                         | `INVALID_TEMPLATE`               |
| `phy` 传了 `vnpu_template`                          | `INVALID_TEMPLATE`               |
| `vnpu` + `npu_dual_chips=true`                      | `INVALID_REQUEST`                |
| 模板含 `_m` / `_nm`                                 | `TEMPLATE_CANNOT_FULLY_TILE`     |
| 模板不在目标设备 `template-info` 清单中             | `INVALID_TEMPLATE`               |
| 设备模板资源不足以推算完整切分（单一规格/资源超配） | `TEMPLATE_CANNOT_FULLY_TILE`     |
| `npu_num > K`（K 按目标设备实时计算）               | `INSUFFICIENT_NPU`               |
| `npu_num > 1` 且宿主机未完成多 vNPU 验收            | `WORKLOAD_MULTI_VNPU_UNVERIFIED` |

> `npu_num=0` 时不做任何 NPU 分配（`npu_mode`/模板仍会被格式校验）。

---

## 4. 分配与回收语义

### 4.1 分配顺序（宿主机内部，黄区只需了解结果）

vNPU 请求：

1. 优先复用**同模板、已有完整分区、空闲实例足够**的父芯片；
2. 其次选择未切分的空闲父芯片，锁内完整切分；
3. 最后允许合并**整组全空闲**的异模板分区后重切；
4. 仍有任一实例被容器引用（含 stopped/created）或账本预留时，不合并、不换模板。

物理整卡请求：

1. 先遍历机器，把**整组 vNPU 全空闲且无任何容器引用**的切分父芯片逐个合并回物理整卡；
   单个父芯片合并失败会告警并隔离该芯片，不阻断本次申请；
2. 再按正常流程分配未切分的空闲整卡；
3. 多卡请求统一排序加锁、整体复查，不交付部分数量。

### 4.2 同名容器幂等与冲突

| 场景                                                   | 行为                                       |
| ------------------------------------------------------ | ------------------------------------------ |
| `vnpu` 请求，同名容器已存在且 mode/template/count 一致 | 校验绑定后幂等复用；必要时 `docker start`  |
| `vnpu` 请求，同名容器存在但规格不同                    | 返回 `NPU_SPEC_CONFLICT`，**不删除**旧容器 |
| `phy` 请求，同名容器是 vnpu 受管容器                   | 返回 `NPU_SPEC_CONFLICT`                   |
| `phy` 请求，同名非受管容器                             | 保持旧行为（清理后重建）                   |

要求：重试同一请求时请复用相同 `request_id` 与相同规格，才能命中幂等。

### 4.3 重启语义

| 容器状态                                    | 行为                                                                                                            |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| absent                                      | 走统一创建分配器，按本次请求重新分配                                                                            |
| stopped / created                           | 校验原父芯片、模板、generation、Docker 设备映射；必要时按记录 `create-vnpu -v <old_id>` 恢复，再 `docker start` |
| running                                     | 幂等校验归属，不重分配、不重复切分                                                                              |
| 原 vNPU 已释放 / 模板已变 / generation 不符 | 返回 `RECOVERY_REQUIRED`，**不会**偷偷挂其他设备或直接 start                                                    |

### 4.4 停止、删除与回收

- **`docker stop`** **不等于释放**：停止的容器仍持有设备引用，vNPU 不会合并。
- 本轮**未接删除钩子**：删除容器后不会立即合并。
- 惰性回收：下一次 start/restart 请求会先对账，把“无任何容器引用”的 `BOUND/RESERVED` 实例释放；随后按需复用、合并或重切。
- 如果黄区需要“立即把整卡还回整卡池”，当前请显式发起一次物理整卡申请（宿主机在锁内合并全空闲分区），或等待下一次容器请求触发对账。

---

## 5. 结果、日志与错误码

### 5.1 成功标记

宿主机脚本沿用原协议，`msg` 中出现：

```
LAUNCH_SUCCESS: <container_name> (容器已启动)
DEPLOY_SUCCESS: <container_name> (...)
```

### 5.2 davinci 卡绑定回报

回调新增 `containers` 数组，按容器逐个上报：

```json
"containers": [
  {"name": "container1", "phyDavinciId": [0], "vnpuDavinciId": [100]},
  {"name": "container2", "phyDavinciId": [1, 2], "vnpuDavinciId": []}
]
```

字段语义：

| 字段            | 类型   | 说明                                                                       |
| --------------- | ------ | -------------------------------------------------------------------------- |
| `name`          | string | 容器名                                                                     |
| `phyDavinciId`  | int\[] | 物理卡编号（`/dev/davinci{x}`）；`vnpu` 模式为**父物理芯片**编号；升序去重 |
| `vnpuDavinciId` | int\[] | vNPU 编号（`/dev/vdavinci{x}`）；`phy` 模式为空数组                        |

补充：

- 多容器创建时每个容器一条记录；任务失败触发全量清理，返回 `[]`；
- 无 NPU（`npu_num=0`）时两个数组均为空。

宿主机脚本同时输出机器可读标记（`msg` 中可见）：

```
NPU_BIND_INFO: container=ide-example mode=vnpu physical_davinci=0 vnpu_davinci=100
```

### 5.3 失败标记与错误码

失败时 `msg` 中出现：

```
NPU_ERROR: <CODE>: <detail>
DEPLOY_FAILED: <container_name> (<CODE 或原因>)
```

| 错误码                                       | 含义                                                | 黄区建议动作                                  |
| -------------------------------------------- | --------------------------------------------------- | --------------------------------------------- |
| `NPU_LOCK_TIMEOUT`                           | 容器/父芯片锁超时                                   | 稍后重试；持续失败检查同机并发任务            |
| `NPU_QUERY_FAILED`                           | `npu-smi` / Docker 查询失败                         | 不重试创建；检查驱动、Docker daemon、权限     |
| `NPU_BUSY`                                   | 父芯片被引用/预留/外部占用                          | 换机器或稍后重试；不要强制删除容器            |
| `NPU_MODE_INVALID`                           | `vnpu-mode` 不是容器模式                            | 宿主机初始化：`npu-smi set -t vnpu-mode -d 0` |
| `INVALID_REQUEST`                            | 字段/组合非法                                       | 修正请求，不要重试                            |
| `INVALID_TEMPLATE`                           | 模板未知/不在目标设备清单/与模式冲突                | 修正模板                                      |
| `TEMPLATE_CANNOT_FULLY_TILE`                 | 模板不能完整铺满（含 `_m/_nm`、单一规格、资源超配） | 换模板；不要重复重试                          |
| `INSUFFICIENT_NPU`                           | 无满足条件的父芯片/整卡                             | 换机器或等待资源释放                          |
| `TOPOLOGY_INCOMPLETE`                        | 切分/合并后拓扑不符                                 | 停止自动重试，转人工检查                      |
| `RECOVERY_REQUIRED`                          | 归属/generation/拓扑冲突，需人工处理                | 页面提示“需重建/联系运维”，不要盲目 restart   |
| `WORKLOAD_MULTI_VNPU_UNVERIFIED`             | 多 vNPU 场景未验收                                  | 改为 `npu_num=1` 或先完成上机验收             |
| `NPU_SPEC_CONFLICT`                          | 同名容器规格不同                                    | 走显式删除/重建流程，不要直接重试创建         |
| `NPU_BINDING_MISSING`                        | 容器设备映射与预期不符                              | 转人工检查，不要复用该容器                    |
| `NPU_LIB_MISSING`                            | 宿主机未部署 `lib_npu.sh`                           | 补发脚本后再试                                |
| `NPU_STATE_ERROR`                            | 锁/账本目录不可用                                   | 检查宿主机权限与磁盘                          |
| `LEDGER_READ_FAILED` / `LEDGER_WRITE_FAILED` | 账本损坏/写入失败                                   | 转人工检查 `/var/lib/hidevlab-npu`            |

> 错误码只保证出现在 `msg` 文本中；当前 transport 未新增结构化错误字段。

### 5.4 容器标签（供对账，黄区只读）

transport 创建的 NPU 容器会写入：

| 标签                      | 示例               | 说明                                 |
| ------------------------- | ------------------ | ------------------------------------ |
| `hidevlab.managed-by`     | `transport`        | 受管标识                             |
| `hidevlab.npu.mode`       | `vnpu` / `phy`     | 分配模式                             |
| `hidevlab.npu.count`      | `1`                | 申请数量                             |
| `hidevlab.npu.template`   | `vir05_1c_16g`     | vNPU 模板（`phy` 为空）              |
| `hidevlab.npu.parents`    | `0-0`              | 父芯片 `device-chip`，多个用逗号分隔 |
| `hidevlab.npu.vnpu-ids`   | `100`              | 实际 vNPU ID，多个用逗号分隔         |
| `hidevlab.npu.generation` | `1`                | 拓扑代次，防 ID 复用错配             |
| `hidevlab.npu.request-id` | `req-20261021-001` | 请求归属                             |

黄区不要修改这些标签；它们是宿主机崩溃后对账的依据。

---

## 6. 前置条件与部署要求

1. **宿主机初始化**（每台 A2，一次性）：
   - `npu-smi info -t vnpu-mode` 必须为 `Container`；
   - 建议 `npu-smi set -t vnpu-cfg-recover -d 1`，并确认重启后拓扑可恢复；
   - 创建 vNPU 前不得已有残留实例（残留需人工对账）。
2. **脚本下发**：`lib_npu.sh` 必须与 `resource_start_docker.sh` / `resource_restart_container.sh` / `lib_container.sh` 一起同步到宿主机 `{share_storage.path}/share/docker_config/`。
3. **宿主机目录**：transport 需要 root 权限创建 `/var/lock/hidevlab-npu/`、`/var/lib/hidevlab-npu/`。
4. **镜像兼容**：目标镜像必须包含兼容的 CANN/框架；原生 Docker 映射 vNPU 需先完成该镜像的上机验证。
5. **调度排他**：宿主机账本 `/var/lib/hidevlab-npu/` 是 vNPU 归属的权威来源。其他调度系统（如 `deploy-multi-container.yml` 的整卡预约文件）不得把已切分的父芯片当整卡分配；跨系统分配需统一到同一父芯片锁或明确的排他约定。

---

## 7. 已知限制与上机验收项

本轮仅完成脚本层实现与模拟测试，以下必须在上机环境确认：

- 三类 A2 机器的 Chip Name、AICore/HBM、`template-info` 与完整切分 K 实测；
- 原生 Docker + 业务镜像对 vNPU 的枚举、算子执行与显存边界；
- 重启恢复开关对编号、模板、销毁记录的真实效果；
- 同路径实例重建后，容器 cgroup 设备号是否仍可正常使用（必要时进入容器重建流程）；
- 多 vNPU 同容器工作负载的通信与资源语义（未通过前 `npu_num>1` 会被拒绝）；
- `_m`/`_nm` 混合模板方案不在本版支持范围。

---

## 8. 黄区联调 Checklist

- [ ] 创建/重启请求仅新增两个 key：`resources.npu_mode`（`phy`/`vnpu`）与 `resources.vnpu_template`（`vnpu` 必填）。
- [ ] 不传 `npu_mode` 时按 `phy` 处理；`phy` 请求不携带 `vnpu_template`。
- [ ] 不再由黄区预选卡号/vNPU ID。
- [ ] 页面能展示 `NPU_ERROR: <CODE>` 与建议动作。
- [ ] 回调解析 `containers[]` 的 `phyDavinciId` / `vnpuDavinciId`，并展示为 `/dev/davinci{x}`、`/dev/vdavinci{x}`。
- [ ] 删除容器后不假设立即合并；需要整卡时发起物理申请或等待下次请求。
- [ ] 对 `RECOVERY_REQUIRED` / `NPU_SPEC_CONFLICT` 走人工/重建流程，不做无限自动重试。
- [ ] 多 vNPU（`npu_num>1`）通过验收后再开放生产。
- [ ] 与整卡调度系统确认父芯片排他约定。

## 2026-10-22 评审修订约束

- vNPU 仅支持 A2 非双芯；不支持组合明确失败，不降级为整卡。
- 创建和重启均核对已存 mode/count/template；不一致返回 NPU_SPEC_CONFLICT。
- A2 受管节点部署前需配置经核对的物理映射与已验证 template/K/资源；配置缺失或不符时不变更设备。
- 双芯保留现有整卡路径，仅提供后续建议；调度池须与 AVI 分离。
