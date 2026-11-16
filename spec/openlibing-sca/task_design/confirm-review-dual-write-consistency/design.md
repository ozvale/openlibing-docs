# ConfirmReview 双写一致性收敛（#95 第二轮）— 技术设计

## 方案概述

在既有 outbox（`tbl_confirm_review_mongo_compensation` + `MongoCompensationSchedule`）之上，补齐载荷新鲜度校验、撤销/转审链路接入、混合错误分区补偿与批次级事务隔离，四个问题共用「MySQL 先行 → Mongo bulk 最后 → 失败落补偿」的统一写序。

## 架构决策

### D1 载荷 op 打标 + replay 按 MySQL 现势校验（P1-1）

- 序列化 schema 从 `{"ops":[{"q","u"}]}` 升级为 `{"ops":[{"q","u","r"}]}`，`r` 为来源审核单 id；直接回写 op 与继承传播 op（`_id $in` 查询，无法从 query 反查来源）统一打标。
- replay 时以 `reviewIds` 分块（≤100，复用 `selectLogSnapshotsByIds`）加载 MySQL 现势，逐 op 校验：`$set.reviewStatus` 或非空 `$set.reviewUserId` 与 MySQL 当前值不一致 → 判陈旧，跳过并 WARN 留痕（替代评审给出的两个修法之一「重建载荷」：跳过即可收敛——任何改变 MySQL 状态的后续操作自带写路径/补偿）。
- 兼容旧格式（无 `r`）：按 query 中 `_id`/`objectId` 反查 mongId 兜底；无法映射维持原重放行为。
- 校验字段限定 `reviewStatus` + `reviewUserId`（非空才比）：撤销载荷的 `$set.reviewUserId=null` 不参与比较（MySQL 侧撤销不清审核人，语义不对齐）；批复载荷不含 `reviewUserId`。

### D2 撤销/转审/传播接入 outbox + 写序修正（P1-2）

- `patchRevoke`、`reviewReferral` 加 `@Transactional`。
- 写序统一：MySQL `updateById`（循环内）→ 日志 `patchInsert` → Mongo bulk（`executeMongoUpdatesWithOutbox` 共享写出器：bulk + E11000 降级 + 失败分区补偿）。修正原 `patchRevoke` 的 Mongo 先行反向漂移。
- `propagateRevokeToInheritScans` 改为 `collectRevokePropagationOps`：不再直接写、不再吞异常——写操作并入同一批 bulk/补偿；范围解析读失败让撤销整体回滚（fail-closed，两侧都未变更优于静默丢失传播）。
- `reviewReferral` 的 Mongo 失败从「异常中断」改为「落补偿」——与批复方向语义一致（在线操作成功、5 分钟内重放收敛）。

### D3 混合 bulk 错误分区（P2-1）

- `findBulkWriteErrors(Throwable)` 沿 cause 链提取 `MongoBulkWriteException.getWriteErrors()`（null=非批量写异常，如超时）。
- 在线写出器：非 11000 失败 op 单独落补偿（仅失败子集）；11000 冲突走降级重试，降级失败并入补偿；整批异常（null）补偿全部。
- replay 侧：存在非 11000 失败 → 整条重试（$set 幂等）；仅 11000 → 降级重试。

### D4 批次独立事务（P2-2）

- `autoPathReview` 去掉方法级 `@Transactional`，每 100 条批次以 `TransactionTemplate`（**REQUIRES_NEW**）独立提交：批次 N 失败仅回滚批次 N，前序批次已一致性提交（MySQL 已提交 + Mongo 已生效）。REQUIRES_NEW 防御未来外层事务调用方重新引入整段回滚。
- `robotAutoConfirm` 去掉 `@Transactional`（否则外层事务重新包住批次模板失效），`scanConfirmParseV3` 调用用 REQUIRED 模板包裹为独立建单事务。
- `executeUpdate` 内日志 `patchInsert` 提前到 Mongo bulk 之前：Mongo 写成为事务内最后一步，缩小「Mongo 已写而事务回滚」残余窗口（批 K 提交失败仍存在极窄窗口，接受）。

## 涉及文件

| 文件                                                     | 操作 | 说明                                                                                        |
| -------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------- |
| `analysis/service/impl/ConfirmReviewServceImpl.java`     | 修改 | MongoUpdateOp record、staleness 过滤、共享写出器、patchRevoke/reviewReferral 重构、批次事务 |
| `analysis/service/impl/ConfirmReviewServceImplTest.java` | 修改 | 既有用例适配 + 新增用例集 3                                                                 |

无 mapper/实体/Liquibase 变更（复用 `selectLogSnapshotsByIds` 与既有补偿表）。

## 风险 & 缓解

| 风险                                         | 缓解                                                                                   |
| -------------------------------------------- | -------------------------------------------------------------------------------------- |
| 载荷 schema 变更影响存量 PENDING 记录        | `r` 为可选字段，旧载荷走 mongId 兜底映射，行为不回退                                   |
| 撤销传播读失败从「吞异常继续」变「整体失败」 | fail-closed 是一致性目标方向；Mongo 读故障时撤销本就不可信，用户重试即可；日志明确指引 |
| referral Mongo 失败不再抛异常，用户看到成功  | 与批复方向 outbox 语义一致；补偿 5 分钟内重放，FAILED 转人工有日志与表记录             |
| REQUIRES_NEW 挂起外层事务                    | 当前所有调用方（IntegrationApiServiceImpl/controller）均无外层事务；防御性选择         |

## 跨仓影响

无。仅 `openlibing-sca` 单仓。
