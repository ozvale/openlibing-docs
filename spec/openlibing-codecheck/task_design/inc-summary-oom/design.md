# inc-summary-oom — 技术设计

## 方案概述

用 MongoDB `$count` 聚合阶段替换 `getMappedResults().size()` 的全量物化计数，并为 `getIncSummaryList` 数据查询分页参数加默认值，消除增量汇总查询接口的 OOM 触发源。业务 Issue：https://gitcode.com/openlibing/openlibing-codecheck/issues/175

## 架构决策

1. **count 查询独立构建 pipeline，映射类型用 `org.bson.Document`**
   - `$count` 只返回 1 个数字文档，无需 VO 反序列化；用 `getUniqueMappedResult()` 取值，null（空匹配集）兜底为 0
   - 计数值提取用 `Number.longValue()`（兼容服务端返回 Int32/Int64 两种 BSON 类型，避免 `Document.getLong()` 的 ClassCastException）
2. **`getIncSummaryList` count pipeline = [match, $count]**：原 pipeline 的 `sort(DESC, executeTime)` 对计数无意义（无 group，计数与顺序无关），直接去掉，减轻服务端排序开销
3. **`getIncSummaryList` 分页改为无条件应用**：默认 `pageNum=1`、`pageSize=20`（仓库无现成默认值常量，20 为通用默认）。行为变化仅影响"不传分页参数"的调用方（原全量返回 → 现返回第一页），该接口为查询面板接口，全量返回本身即缺陷
4. **`getSummaryList` count pipeline = [match, sort(ASC), group, $count]**：保留 group 前的 sort（`.last()` 取值语义依赖文档顺序，保持 pipeline 前缀与原实现完全一致最安全）；仅去掉 count 无意义的 group 后 `sort(DESC)`。group 折叠后每组一条，$count = 分组数，与原 `getMappedResults().size()` 等价
5. **数据查询 pipeline 不变**（sort + 可选 skip/limit 语义保留），接口契约 `PageVo` 结构不变

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| src/main/java/.../operation/codecheck/IncSummaryOperation.java | 修改 | 两处 count 改 `$count`；`getIncSummaryList` 分页默认值；新增 `org.bson.Document` import |
| src/test/java/.../operation/codecheck/IncSummaryOperationTest.java | 修改 | 更新 `getSummaryList` 测试的 count stub（Document 映射）；新增 `getIncSummaryList` 测试：验证 $count 计数路径 + 不传分页时默认 skip/limit |

## 风险 & 缓解

- 分页默认值对"不传分页参数"的调用方是行为变化 → 已确认修复范围时接受该变化（Issue 验收标准明确）；前端门禁查询正常均传分页
- `$count` 空匹配集返回空结果而非 0 → `getUniqueMappedResult()` null 判断兜底 0
- Mock 测试中两处 aggregate 调用需按映射类型（Document vs VO）区分 stub → 测试中分别 stub 并断言 count 值来自 Document 路径

## 跨仓影响

无。接口契约（PageVo 结构、字段）不变，仅查询实现优化。
