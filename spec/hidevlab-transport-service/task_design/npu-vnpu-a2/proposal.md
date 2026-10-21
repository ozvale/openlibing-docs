# A2 NPU 硬虚拟化 vNPU 切分/合并与 transport 脚本接入

关联业务 Issue：openlibing/hidevlab-transport-service#120

## 需求背景

A2（Ascend 910B）宿主机需要通过 AVI 硬切分把一张物理 NPU 拆成多个 vNPU，供多个 IDE 容器独占使用。
当前 transport 宿主机脚本只按 `/dev/davinci*` 整卡分配：

- 不识别已切分的父芯片，可能把切分中的父卡当整卡分配；
- 不支持“按模板完整切分 K 个实例”，也不支持整组合并；
- 只有主机级全局 NPU 锁，没有父子芯片粒度锁和分配账本；
- 容器 stop 后仍持有设备，删除后 vNPU 无回收路径。

设计依据：`designs/NPU切分/A2-NPU硬虚拟化与transport脚本实现指南.md`。

## 功能描述

### 做什么

1. 新增 `script/lib_npu.sh`：拓扑发现与解析、模板能力校验、完整切分、整组合并、分配预留与原子账本、容器锁/兼容全局锁/父芯片多锁、Docker 占用结构化解析、启动对账与恢复、错误码与结构化日志。
2. `script/lib_container.sh`：`parse_config` 增加 `npu_mode`（缺省 `phy`，允许 `phy`/`vnpu`）与 `vnpu_template` 严格解析；`create_container` 的 NPU 分配接入 lib_npu；A5 / 950DT / `npu_dual_chips` 路径保持原行为。
3. `script/resource_start_docker.sh`：容器生命周期锁内完成“同名幂等检查 → 规划 → 加锁复查 → 切分/合并 → 预留 → docker run → inspect → 提交归属”。
4. `script/resource_restart_container.sh`：absent 走统一分配；stopped/created 校验归属并按记录恢复 vNPU 后 `docker start`；running 幂等校验；原 vNPU 已释放/换模板返回明确错误。
5. 惰性回收：**不改 `resource_delete_docker.sh`**；切分/合并只在 start/restart 请求路径内发生。
6. 模拟测试：伪 `npu-smi` / `docker` 覆盖发现、完整切分、部分失败回滚、合并、复用、互斥、幂等、查询异常。

### 不做什么

- 不做“删除容器后立即合并”；不修改删除脚本与 `docker_manager.py` 删除兜底。
- 不引入 NPU-Agent，不新增 transport HTTP API。
- 不启用软切分、`device-share`、时间片超分、Ascend Docker Runtime 动态虚拟化。
- 不改 A5 / 950DT / 双芯整卡的整卡分配算法。
- 真实 NPU 上机验收不在本轮范围。

## 验收标准

- [ ] 创建/重启请求仅新增 `npu_mode`（`phy`/`vnpu`）与 `vnpu_template` 两个 key；`vnpu` 时按 `count + vnpu_template` 分配，调用方不指定卡号/vNPU ID。
- [ ] 申请 1 个实例时，新父芯片按模板完整切分 K 个，仅绑定 1 个。
- [ ] 已有同模板完整分区优先复用空闲实例，不重复 create。
- [ ] 不能完整铺满的模板（含 `_m`/`_nm`）创建前返回 `TEMPLATE_CANNOT_FULLY_TILE`，不改拓扑。
- [ ] 切分中途失败只回滚本事务新建且无引用实例；回滚失败标记 `RECOVERY_REQUIRED`，不返回成功。
- [ ] 合并前检查驱动状态、Docker 全量容器（含 stopped/created）、账本预留、黑名单；任一占用即拒绝。
- [ ] 整卡与子 vNPU 互斥；多芯片请求按序加锁，不交付部分数量。
- [ ] 容器写入 `managed-by` / `request-id` / 模式 / 模板 / 父芯片 / vnpu_id / generation 标签；账本原子落盘。
- [ ] 重复请求幂等；同名不同规格返回冲突且不删除健康容器。
- [ ] stopped 容器仍引用 vNPU 时不合并；restart 可恢复；记录冲突返回 `RECOVERY_REQUIRED`。
- [ ] Docker / npu-smi 查询失败不按“空闲”处理。
- [ ] 旧整卡、A5、950DT、双芯整卡、黑名单行为不回归；`bash -n` 与模拟测试通过。

## 影响范围

| 文件                                              | 操作                            |
| ------------------------------------------------- | ------------------------------- |
| `script/lib_npu.sh`                               | 新增                            |
| `script/lib_container.sh`                         | 修改（配置解析 + 创建流程接入） |
| `script/resource_start_docker.sh`                 | 修改（事务顺序与错误 marker）   |
| `script/resource_restart_container.sh`            | 修改（归属校验/恢复后再 start） |
| `tests/test_lib_npu.py`、`tests/npu_sim/cases.sh` | 新增（模拟测试）                |

发布要求：`lib_npu.sh` 必须随 `docker_config` 同步下发到宿主机共享目录，否则入口脚本 source 失败。

## 本轮评审修复范围（用户于 2026-10-22 确认）

按 Full 模式修复 PR #186 评审发现的解析、查询失败、父子互斥、回滚、完整恢复、请求规格及模板准入问题；将模拟测试与官方输出 fixture 纳入 CI。仅开放 A2 非双芯硬切分；双芯仅在业务 docs 提供建议，保持原物理整卡算法。保留 d5ace80 的整卡申请前空闲分区回收优化及现有驱动占用检查。

新增验收：未知实例不可删除，完整拓扑丢失后恢复全部账本 ID，代际/双芯组合不可降级，Docker 结果未知不释放，经过验证的宿主机能力配置方可启用模板。真实硬件验收由后续用户自测完成。
