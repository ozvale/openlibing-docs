# 操作日志查询性能优化 — 实现任务

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

## 进度: 8/8 complete（Task 6/7 实施后经 PR !560 检视否决撤销，最终交付仅阶段一）

- [x] Task 1: openlibing-cicd — `OperationLogWriteModules` 白名单 TTL 缓存（默认 60s，Apollo `openlibing.cicd.operation-log.whitelist-cache-ttl-seconds`；仅缓存成功非空结果）
- [x] Task 2: openlibing-cicd — 新增 `FilterMetaCache`（LRU 256 + TTL，默认 30s）并接入 `LoggingServiceImpl.queryFilterMeta`（权限校验先于缓存；key 含 projectId+维度+规范化过滤值+selectedValues+时间分钟取整）
- [x] Task 3: openlibing-cicd — 单元测试（缓存命中/过期/禁用/失败闭门/副本防污染）并运行相关验证
- [x] Task 4: openlibing-coderepo — 同构 Task 1（`openlibing.coderepo.operation-log.whitelist-cache-ttl-seconds`）
- [x] Task 5: openlibing-coderepo — 同构 Task 2/3（含单测）
- [x] Task 6: openlibing-framework — ~~新增三合一覆盖索引 changeSet（先建后删）~~ **实施后经 PR !560 检视否决并撤销**：6 列索引键长 5105 字节（5×VARCHAR(255) utf8mb4 单列 1020 + DATETIME 5）超 InnoDB 3072 字节上限，CREATE INDEX 必报 ERROR 1071 且随启动重放阻断启动；分组列位于范围列后亦无法免 temporary。阶段二整体撤销（framework commit `9f347e43`），索引总数维持 6 个
- [x] Task 7: openlibing-framework — ~~`db.changelog.xml` 注册 include~~ 已随 Task 6 撤销一并回退（删除 changeSet 文件 + include 行，pre-commit 全部通过），framework 无任何改动
- [x] Task 8: 增量覆盖率实测（`python .agents/scripts/incremental_coverage.py`，cicd / coderepo ≥80%）+ Phase 3 自检（含接口变动检测：无 HTTP 接口签名变化）；PR !560 检视意见闭环后同步更新本 spec 四件套（阶段二改为撤销记录）

> 覆盖率实测（2026-11-27）：两仓 CI 同口径（`--ignore-absent`，与 ut.yml diff-cover 一致）均为 **100% = 74/74（cicd）、72/72（coderepo）可测改动行全覆盖，未覆盖 0**；本地默认严口径（未采集行计入分母）为 43.02% / 42.60%，差异行均为导入、字段声明、括号等未进入 JaCoCo 报告的非可执行行。证据：`.temp/cicd-incr-cov-ci.json`、`.temp/coderepo-incr-cov-ci.json`。
