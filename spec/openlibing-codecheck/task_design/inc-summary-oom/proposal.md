# inc-summary-oom

## 需求背景

生产环境 openlibing-codecheck-prod 服务反复 OOM 重启（每个 Pod 存活约 40-60 分钟）。业务 Issue：https://gitcode.com/openlibing/openlibing-codecheck/issues/175

根因：`IncSummaryOperation.getIncSummaryList()`（L383-390）的 count 查询用 `getMappedResults().size()` 把匹配集合全量文档（单社区几十万~百万条）反序列化驻留堆内只为取个数，单次调用瞬时分配 1-3GB，击穿默认 2GB 堆。生产证据：Pod gfrmw 2026-08-20 12:58:36 OOM（日志 L3783 记录 OOM 接口为 `/ci-portal/v1/codecheck/inc/v1/task/result/summary`，栈顶类 `java.util.Arrays`）；前一 Pod 20:34 同接口同模式 OOM。放大器：同方法分页参数为 null 时数据查询会二次全量加载。

## 功能描述

- 修 `getIncSummaryList`：count 改 `$count` aggregation（服务端计数，结果与原实现等价，零行为变化）；分页参数加默认值（pageNum=1、pageSize=20）
- 顺手修 `getSummaryList`（L306-313）同款 count 写法（保留 group 折叠语义，零行为变化）
- 不做：不改 JVM 参数、不改接口契约（PageVo 响应结构不变）、不改其他查询方法

## 验收标准

> 实现状态（2026-08-27 更新）：实现已在业务仓独立开展并完成——分支 `fix-inc-summary-oom`（提交 `01fce77e`），已合入 `develop_202608_iter2`（merge commit `9cc39be8`）。标准 1-3 已由单测/构建验证；标准 4（生产观察）待生产发布后跟踪。

- [x] count 结果与修复前一致（$count 语义等价）（单测验证）
- [x] 不传分页参数时返回默认第一页（20 条），不再全量加载（单测验证）
- [x] 编译通过 + 相关单测通过（`IncSummaryOperationTest` 5 tests, 0 failures；`mvn package -DskipTests` 通过）
- [ ] 生产观察：大数据量社区调用该接口不再触发 OOM（待生产发布后跟踪）

## 影响范围

- 仓：openlibing-codecheck（单文件 `IncSummaryOperation.java`，可能加单测文件）
- 接口：`/v1/codecheck/inc/v1/task/result/summary`（行为变化仅限"不传分页参数"场景：原全量返回 → 现返回默认第一页）
- 数据：只读查询优化，无写入路径变化
