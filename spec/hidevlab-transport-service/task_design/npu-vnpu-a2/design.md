# A2 NPU 硬虚拟化 vNPU — 技术设计

## 方案概述

在宿主机脚本层新增 `script/lib_npu.sh`，以“**静态 AVI 硬切分 + 原生 Docker 显式设备映射**”为核心：
先按实际 template 复用足量空闲实例；没有时按调用方 `count + template` 选择父芯片 → 使用同模板创建至资源耗尽 → 分配预留 → `docker run` 绑定 →
inspect 确认后提交账本。合并与重切只发生在后续 start/restart 请求事务内（惰性回收）。

不改删除脚本、不改 transport API、不引入常驻 Agent。

## 架构决策

| 决策       | 选择                                                                                                                 | 原因                                    |
| ---------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| 切分方式   | `npu-smi set -t create-vnpu` 逐个创建，每次回读                                                                      | 官方 A2 不支持批量；一次成功 ≠ 完整切分 |
| 完整性判据 | 实际创建至驱动明确报告资源不足，或 16 个合法实例 ID 全部用尽；逐次回读、模板一致、记录实际份数                       | 不推导固定 K，不要求 Free Memory=0      |
| 合并定义   | 确认全空闲后逐个 `destroy-vnpu`，最终实例数为 0                                                                      | 无 `merge-vnpu`，也不是显存拼接         |
| 锁粒度     | 容器锁 → 兼容全局锁 → 父芯片锁（数值升序），持锁至 Docker 结果与账本确认                                             | 解决合并/获取竞争；迁移期兼容旧整卡路径 |
| 锁文件     | `/var/lock/hidevlab-npu/`，root 目录，解锁只关 FD 不删文件                                                           | 避免 inode 替换失去互斥                 |
| 账本       | `/var/lib/hidevlab-npu/chips/<device>-<chip>.json`，临时文件 + fsync + 原子 rename                                   | 抗进程崩溃；`generation` 防 ID 复用错配 |
| 占用判定   | `docker ps -aq` + 结构化 `docker inspect`（Devices/Binds/Privileged/Runtime/DeviceRequests）                         | 停止容器仍持有设备；无法确认时保守拒绝  |
| 回收时机   | start/restart 请求内：复用 → 空闲整卡切分 → 全空闲异模板分区合并重切；整卡请求先遍历并回收全空闲切分父卡，再分配整卡 | 用户要求不接删除钩子                    |
| 多 vNPU    | 同父芯片空闲的匹配实例数满足 N，只绑定请求数量；无额外多实例验证开关                                                 | 分配与工作负载兼容性分别验收            |
| 旧路径     | A5 / 950DT / `npu_dual_chips` 保持原逻辑；A2 物理整卡改走 lib_npu 以识别切分父卡                                     | 控制回归面                              |
| 主机配置   | 只校验 `vnpu-mode=Container`；恢复开关只查询并告警，不按请求修改                                                     | 避免影响其他芯片的恢复配置              |

## 请求契约

```json
{
  "container_name": "ide-example",
  "request_id": "req-example",
  "resources": {
    "npu_gen": "A2",
    "npu_num": 1,
    "npu_mode": "vnpu",
    "vnpu_template": "vir05_1c_16g"
  }
}
```

- 对外契约仅新增两个 key：`resources.npu_mode`（`phy` / `vnpu`）与 `resources.vnpu_template`。
- `npu_mode` 缺省 `phy`；`npu_num=0` 不分配。`physical` 仅作为内部/历史别名兼容。
- `vnpu` 必须有模板；`phy` 携带模板返回 `INVALID_TEMPLATE`。
- `npu_num` 必须为非负整数；模板名只允许 `[A-Za-z0-9_]+`，且必须出现在目标设备的 `template-info` 清单中。
- 同名 vNPU 容器在创建和重启入口均比较请求 mode/count/template；不一致返回 NPU_SPEC_CONFLICT。
- vnpu 仅支持 A2 非双芯；A5/950DT/其他代际禁止降级为整卡。双芯只补充文档建议，不改原物理整卡算法。

## 实际拓扑与完整切分

以用户 2026-10-22 明确的流程为准，替代此前固定 K/已验证能力配置方案。

- 枚举物理字符设备后使用 phyid-remap 查询设备/芯片/物理编号，与 info -m 核对；不把 Logic ID 当作 phy_id。不支持查询时可选用管理员核对的映射文件 `/etc/software-market/npu-capabilities.json`（HIDEVLAB_NPU_CAPABILITIES 可指定路径）。不再需要模板 plans、资源预算、K、verified 或 evidence。
- VNPU 优先搜索实际实例的 template 和可用数量；不要求原拓扑完整切满。锁内接管未登记拓扑，按实例保存模板和已有容器引用，允许复用混合父卡的匹配空闲实例，不改变其他实例。
- 新切分先校验目标设备 template-info，再使用同一 template 逐个创建并回读。明确资源不足且实例集合未改变、芯片健康时才正常结束；最多 16 个合法实例 ID。_m/_nm 也以设备清单为准，不按后缀拒绝。
- 内存 Free 含系统占用，不据此除以模板内存决定份数。未知错误、假成功、拓扑查询失败不能当作切满；回滚限于本事务明确创建的实例，不明结果隔离。
- PHY 请求先回收全机符合空闲条件的分区，包括未登记的分区。容器（含停止态）、驱动、宿主机占用、预留、异常状态仍阻止销毁；前置回收失败不静默进入创建。
- 芯片真实型号必须为 A2，且同一设备仅有一个计算芯片（排除 MCU）。不支持的代际及双芯请求明确拒绝。
- 创建/restart 成功前读取当前容器实际映射；transport 按容器名过滤绑定标记并核对模式、数量和父子 ID，缺失/冲突时失败。纯镜像恢复 restartPullOnly 不启动容器，回调为空绑定。

操作说明与可选映射文件格式见业务仓 docs/npu-a2-avi-operations.md；真实耗尽提示、驱动/CANN/镜像兼容性仍须上机验收。

## 锁与临界区

```
npu_lock_container (sha256(container_name))
  npu_lock_global (/var/lock/resource_start_docker_npu.lock)
    npu_lock_chips (device-chip 数值升序)
      重新发现拓扑 + Docker 全量引用 + 账本
      切分 / 合并 / 重切并回读
      写 RESERVED
      docker run / docker start
      docker inspect 校验绑定
      写 BOUND
    逆序解锁
```

`flock -x -w <timeout>`；锁文件不删除。创建、重启与幂等复用通过同一事务顺序取锁；不支持远端 Docker daemon，A2 使用 runc 显式设备映射。
迁移期继续持全局锁，确保与旧整卡路径互斥。

## 账本结构

```json
{
  "schema_version": 1,
  "device_id": 0,
  "chip_id": 0,
  "phy_id": 0,
  "generation": 7,
  "topology_state": "SPLIT_READY",
  "template": "vir05_1c_16g",
  "expected_instances": 4,
  "transaction": {
    "owner_boot_id": "...",
    "pid": 1234,
    "phase": "BOUND",
    "created_ids": [100]
  },
  "instances": [
    {
      "vnpu_id": 100,
      "template": "vir05_1c_16g",
      "state": "BOUND",
      "container_id": "abc",
      "request_id": "req-example"
    }
  ],
  "updated_at": "2026-10-21T10:00:00Z"
}
```

状态机：`PHYSICAL_READY → SPLITTING → SPLIT_READY → MERGING → PHYSICAL_READY`，异常分支 `RECOVERY_REQUIRED`；
实例：`FREE → RESERVED → BOUND`；接管时驱动在用但无法确认 Docker 归属的实例记为 `EXTERNAL`，不可分配/销毁。

## 涉及文件

| 文件                                   | 操作 | 说明                                                                                           |
| -------------------------------------- | ---- | ---------------------------------------------------------------------------------------------- |
| `script/lib_npu.sh`                    | 新增 | 全部 NPU 拓扑/锁/账本/分配/恢复逻辑                                                            |
| `script/lib_container.sh`              | 修改 | `parse_config` 新字段；`create_container` 生命周期锁、幂等检查、接入 lib_npu；旧路径保留       |
| `script/resource_start_docker.sh`      | 修改 | 输出 NPU 错误码；保持 marker 协议                                                              |
| `script/resource_restart_container.sh` | 修改 | stopped/created/running 的归属校验与恢复                                                       |
| `service/docker_manager.py`            | 修改 | 解析 `NPU_BIND_INFO`，在创建/重启回调中新增 `containers[]`（`phyDavinciId` / `vnpuDavinciId`） |
| `tests/npu_sim/cases.sh`               | 新增 | 伪 `npu-smi`/`docker`/`flock` 的模拟用例                                                       |
| `tests/test_lib_npu.py`                | 新增 | pytest 包装器（Linux/CI 执行，非 Linux 跳过）                                                  |

## 风险 & 缓解

| 风险                                | 缓解                                                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 真实 `npu-smi` 输出格式与假设不一致 | 解析器同时支持 key:value 块与表格；解析失败返回 `NPU_QUERY_FAILED`，不返回空池；首轮上机以真实输出补 fixture |
| 旧版本脚本与新脚本并行              | 迁移期保留全局锁；父芯片锁覆盖整卡与 vNPU；文档要求整体发布并排空在飞任务                                    |
| `docker rm -f` 误删健康同名容器     | vnpu 模式先做规格与绑定幂等检查；只在规格冲突时返回错误                                                      |
| 停止容器仍引用设备                  | 占用扫描包含全部容器状态；合并前强校验                                                                       |
| 重启后设备主次设备号变化            | 只校验路径不足以判定恢复成功；恢复后要求上机验证框架可见性（列为上机项）                                     |
| 无 flock 环境                       | 生产要求 util-linux flock；缺失直接返回 `NPU_LOCK_TIMEOUT`，不降级无锁                                       |

## 跨仓影响

- 管理面仅需新增 `resources.npu_mode`（`phy`/`vnpu`）与 `resources.vnpu_template`（`vnpu` 必填）两个字段；`request_id` 为可选既有字段。
- 发布需同步 `lib_npu.sh` 到宿主机 `{share}/docker_config/`。

## PR #186 评审修订（2026-10-22）

- 官方表格按表头解析；总数/记录数一致，状态/容器字段完整；未知格式不返回空池。
- Docker 逐对象 inspect 校验退出码与身份，禁止接受部分快照。
- 合并/回滚检查驱动、Docker、账本和宿主机使用；合并可接管真实空闲拓扑，回滚限定 transaction.created_ids。
- 复用与整卡两方向均检查父子引用、broad access、芯片健康和预留；切分/重切及绑定确认足额数量。
- 完整恢复父芯片的所有账本实例（包括 FREE 兄弟），核对 generation/模板/归属及 Docker 绑定，再允许 start。
- Docker run 或确认结果未知时保留预留并标记 RECOVERY_REQUIRED。
- 安全自检覆盖本机 daemon、runc、用户环境变量参数边界及能力文件写权限。
- 不接删除钩子，不修改双芯物理整卡分配算法；不执行主机配置变更或硬件切分。
