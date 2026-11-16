# ConfirmReview 双写一致性收敛（#95 第二轮）— 实现任务

## 进度: 7/7 complete

- [x] Task 1: 引入 MongoUpdateOp record（reviewId/query/update），全链路替换 List<Pair>，载荷序列化增加可选 "r" 字段
- [x] Task 2: P1-1 — replay 陈旧载荷过滤：filterStaleCompensationOps + isStaleUpdate + resolveOpReview + 分块加载 MySQL 现势（selectLogSnapshotsByIds ≤100/块）
- [x] Task 3: P2-1 — findBulkWriteErrors 分区：executeMongoUpdatesWithOutbox 共享写出器（非 11000 失败 op 补偿 + 冲突降级 + 降级失败并入）；replay 侧混合错误整条重试
- [x] Task 4: P1-2 — patchRevoke @Transactional + 写序修正 + buildRevokeMongoOp + collectRevokePropagationOps（去吞异常）；reviewReferral @Transactional + 收集 op + 共享写出器
- [x] Task 5: P2-2 — autoPathReview 批次 REQUIRES_NEW 模板；robotAutoConfirm 去事务 + scanConfirmParseV3 REQUIRED 模板；executeUpdate 日志提前
- [x] Task 6: 测试 — 适配既有用例（executeUpdate 签名/Pair captor/patchRevoke/reviewReferral/autoPathReview）+ 新增用例集 3（3.2 补偿窗口内撤销、陈旧转审跳过、混合错误补偿、撤销/转审落补偿、MySQL 先行写序、批次独立提交）
- [x] Task 7: 验证 — mvn compile + ConfirmReviewServceImplTest 全量（68/68 通过）+ 自检清单

## 交付记录

- 业务仓 commit `909a173e`（主代码 561 行）、`b9174698`（测试 564 行），分支 `ms_scan`，Refs #95
- 全量测试 1946 例：仅 2 个环境依赖存量失败（IntegrationApiServiceImplTest#testCheckFileNum 网络外呼、OpenPersonDMScanDMServiceImplTest Python 脚本），基线复跑同样失败，与本轮无关
