# archive: 代码度量分支表快照列（metrics-latest-snapshot）

> 归档时间：2026-10-30 ｜ 业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/257 ｜ 交付 PR：https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/278

## 1. 需求与方案回顾

分支管理查询接口拼装 5 个代码度量指标（代码规模 / 平均代码行数 / 平均圈复杂度 / 总代码重复率 / 总文件重复率）时，每次请求拉取涉及仓**所有分支 × 所有历史扫描**记录（含 `metrics_data_json` 大 JSON 列）并在内存跨记录补齐、排序、分页，性能随历史数据线性劣化。

**最终方案**：5 个指标物化为 `repo_branch` 分支表冗余快照列（对齐 UT 行覆盖率先例）——查询零拼接、度量排序下推 SQL；写入侧上报入库后同步刷列（只看最新成功记录）；存量由 XxlJob 刷数任务按**存量清洗补齐语义**（从新到旧先到先得、5 键集齐提前收敛）刷入。`code_metrics_record` 与 `metrics_data_json` 原文零改写，详情页与 codecheck 机机接口不受影响。

## 2. 交付物

| 项          | 内容                                                                                                                                                                    |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 交付 PR     | [#278](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/278)（feat-metrics-latest-snapshot → release_20261029_iter2）                                  |
| 关联 Issue  | [#257](https://gitcode.com/openlibing/openlibing-coderepo/issues/257)（PR 合入自动关闭）                                                                                |
| 主要 commit | 24e3596b（初始实现）→ 71ec5cb1（同步 master）→ e2a4a9fc（检视修复第一轮 6 条）→ 3a95c7a9 / dd02246e（检视修复第二轮 2 条）→ 58c3236f / 0de08308（release 分支冲突合并） |
| 测试分支    | develop_202610_iter2 已合入同源代码（1ad7c476），BETA 部署验证通过                                                                                                      |
| spec 三件套 | proposal.md / design.md / tasks.md（本目录，tasks 17 项全部完成）                                                                                                       |

## 3. 验证结论

- **本地**：全量单测 1355 个通过（`Tests run: 1355, Failures: 0, Errors: 0`）；pre-commit 全部改动文件通过
- **BETA 功能验证**（develop_202610_iter2）：写入刷列（上报后 `repo_branch` 快照列同步刷新，含 atomgit/gitcode 跨域名多项目行）、刷数补齐（存量分支 5 列收敛）、度量排序（SQL 下推）、点击指标跳转详情，全部通过
- **量级实测**（BETA 只读库）：刷数目标 14215 分支全量约秒级，单分支全历史查询与 LIMIT 1 耗时无差异（RTT 主导），`uk_git_branch_run` 唯一索引命中
- **PR CI**：编译构建 / 安全编码扫描 / 病毒扫描 / 开发者测试全绿

> **验证范围说明**：本地"全量单测 1355 通过"为 feat 分支 e2a4a9fc 时期结果；BETA 功能验证基于 develop_202610_iter2 融合形态；release_20261029_iter2 双路径交付形态未做独立运行时验证，由单测与 PR CI 覆盖。另见 §7.1——iter2 基线自带 3 个红测试（同事 `25ffa0572` 引入，与本次改动无关），阻塞 iter2 的 UT 门禁。

## 4. 检视意见处理记录（两轮 13 条）

**第一轮 11 条**（commit e2a4a9fc 采纳 6 条）：branch_type 口径统一、非空 jobParam 必须解析出 gitUrl、fastjson 字面量 null 防护、刷数失败返回 -1 单独统计告警、刷数目标 (repo_url, branch_name) 去重、恒真断言改真断言。**保持现状 5 条**（逐条追评技术论证）：列表 runId 不落列（前端回填 + 兜底定位，记录降级语义）、NULL 排序语义等价性、刷数历史查询无 LIMIT（实测 RTT 主导，游标分批记长尾预案）、刷数目标无分批（14215 行秒级）、DECIMAL(10,2) 精度（对齐 UT 先例，详情展示文件级明细无同屏对比）。

**第二轮 2 条**（均采纳）：gitUrl-only 整仓刷数被误杀（3a95c7a9，删除过界的 branchName 非空校验 + 补 4 个 handler 测试）；stripTrailingZeros 整十/整百值科学计数法（dd02246e，strip 后 scale<0 收回 setScale(0)，`100.00 → 100`，并补 BigDecimal 断言堵住测试盲区——原测试用 Long 绕过了该分支）。

## 5. 分支融合记录（iter2 / release / feat 三方）

- **develop_202610_iter2**：同事将 staticAlertCount 落列并统一 SQL 分页（`25ffa0572`），iter2 演进为**全 SQL 分页**形态；feat 的快照列与 SQL 下推语义直接融合，最终 iter2 为三路径中最简形态
- **release_20261029_iter2**：独立演进为**分批 top-N 内存排序**架构（fix-pagination-resource-abuse 等），冲突合并时保留双路径：度量排序走 feat 的 SQL 下推、staticAlertCount 走 release 的分批内存堆排，双向孤儿方法（`paginateProjectBranchList` / `extractMetricSortValue` / 仓库列表 staticAlertCount 旧 Feign 实现 304 行）清理
- 完整代码以 PR #278 合入 release_20261029_iter2 为准

## 6. 过程踩坑（经验沉淀）

1. **BETA MQ 共享队列被本地服务抢消费**：写入侧"时灵时不灵"、BETA 日志无消费痕迹——同事本地 coderepo 连了 BETA RabbitMQ，消息被轮询到本地实例（无写入侧代码）。排查入口：消费必打日志缺失即怀疑外部消费者，MQ 管理台看 consumer 列表。本地调试须隔离队列名
2. **共享集成分支被 force push**：`20261029_iter2_zhanghao` 曾被强推退化，影响部署源判断（本次为虚惊，实际部署源是 iter2）；团队应约定共享分支禁 force push
3. **iter2 与 release 双集成分支演进分叉**：同一功能（分支列表排序）两侧走了不同实现路线，合并时须做语义级融合决策（保留互补路径、清理孤儿方法），不能机械取单边
4. **mock 测试盲区**：`Long` 类型入参绕过 `BigDecimal` 分支导致科学计数法缺陷逃逸；检视修复引入的校验要对照既有合法用法（gitUrl-only 模式）回归

## 7. 遗留事项

1. iter2 基线自带 3 个红测试（`queryProjectBranch_SortByStaticAlertCount_*`，残留旧链路 stub/verify，同事 `25ffa0572` 引入）——已反馈待原作者修复，阻塞 iter2 的 UT 门禁
2. 上线后建议尽快手动触发全量刷数（XxlJob `branchMetricsSyncHandler` 空参）：补齐语义下任何时刻刷数均为当时最新正确值，尽快刷仅为缩短存量列漏显窗口（漏显非错值）
3. 长尾预案（已记录设计文档，暂不启用）：刷数历史查询游标分批、targets 按 branch_id 分批——单分支记录数/仓库数极端膨胀时启用
