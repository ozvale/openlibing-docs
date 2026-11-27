# 制品信息列表新增制品发布时间与任务完成时间 — 技术设计

## 方案概述

发布时间落 `raw_sbom` 新增列 `publish_time`，写入点在发布链路 `publishSbom`（新建 INSERT 前写 + 已有复用行原子 UPDATE 刷新），口径为"制品最近一次开始发布（写入）的时刻"；完成时间直接复用 `raw_sbom.update_time`。查询链路 `ProductRepository.queryProductListMultiFilter`（native SQL）的 `rs` 子查询补取两字段、SELECT 透出 `publishTime` / `finishTime`，`ProductSortField` 白名单扩展两个排序分支（`CASE WHEN` + `NULLS LAST`）。前端复用软件包列表 `useProductColumnSetting` 组合式函数接入「列配置」，可配置范围从制品发布时间（含）起，动态属性列锁定恒展示，各社区配置按 `userId_projectName` 维度隔离。存量数据借 `job_execution_id` 关联 batch 历史表回填。

## 架构决策

### 决策 1：发布时间写入点在发布链路而非解析启动

口径要求"包含 WAIT 状态的时刻 + 重复发布刷新"，解析启动（置 RUNNING）不满足前者。`raw_sbom` 行按唯一索引 `raw_sbom_uk (value_type, product_id)` 复用，发布链路 `SbomServiceImpl.publishSbom` 恰好覆盖两条写路径，各补一处：

1. **新建**（`findByValueTypeAndProductId` 未命中）：INSERT 前补 `rawSbom.setPublishTime(now)`，随首次 save 落库，初始状态即 WAIT；
2. **已有复用**：`RawSbomRepository.updateRawSbomIfStatusAllowed` 原子覆盖 UPDATE（条件仅允许 NULL/FINISH/FAILED_FINISH/WAIT 状态，RUNNING 中发布 0 行更新抛异常）的 SET 段追加 `publish_time = now()`。该 SQL 为原生 SQL 不走 JPA 实体回调，必须显式 SET（与 SET 段既有的 `update_time = now()` 同模式）。

语义自洽性：

- RUNNING 中发布被拒 → 发布未生效、时间不刷新；
- FAILED 恢复重置 WAIT 后若未重新发布即被解析拾取 → `publish_time` 保持上次发布时刻（无新发布行为，符合口径）；
- 漏洞刷新（VUL_REFRESHING → FINISH）只改 `task_status` 并刷 `update_time`，`publish_time` 不受污染；
- `SelectWaitRawSbomStep` 不改动，batch 模块整体无改动。

**finishTime 口径闭合**：完成时间取 `raw_sbom.update_time`（`@UpdateTimestamp` 维护）。当前代码 `updateRawSbomIfStatusAllowed` 的 SET 段已显式包含 `update_time = now()`（已核实 `RawSbomRepository.java` 实际实现），重新发布（覆盖成功）后 finishTime 自动刷新为本次发布时刻，无需新增改动；WAIT（待解析）/RUNNING（解析中）制品的 finishTime 显示"最近一次状态更新时刻"，与需求口径一致，前端仅对 null（无任何状态记录）显示 `--`。

### 决策 2：查询与排序在既有 native SQL 上最小扩展（无 join）

`ProductRepository.queryProductListMultiFilter` 的 `rs` 子查询（`DISTINCT ON (product_id)` 取最新一条 raw_sbom）补取 `publish_time`；SELECT 补 `rs.publish_time AS "publishTime", rs.update_time AS "finishTime"`；`countQuery` 不动。

- `ProductWithStatisticsView`（native 投影接口）新增 `getPublishTime()` / `getFinishTime()`（列别名对应）；
- `ProductWithStatisticsVo` 新增 `publishTime` / `finishTime` 字段（`LocalDateTime`）；
- `ProductSortField` 枚举新增 `PUBLISH_TIME` / `FINISH_TIME`；ORDER BY 新增两个 `CASE WHEN :sortField = '...' AND :sortDir = ...` 分支，均 `NULLS LAST`（无解析记录制品排最后），兜底分支 `p.name COLLATE "C" ASC` 不变。

无解析记录的制品（`rs` 子查询不命中）两字段为 null，前端 `--` 占位。

### 决策 3：前端列配置复用 useProductColumnSetting 零改动接入

- 列定义 computed `productTableColumns`：基础列（制品名称/组件名/版本号/更多）标记 `disabled: true`；动态属性列 `attr_<name>`（`productDynamicFields` 渲染，位于发布时间之前）同样标记 `disabled: true` 锁定（可配置范围从制品发布时间起）；可配置列 = publishTime / finishTime / scanStatus / dependencyCount / licenseCount / vulCount 6 列；
- `groupOrder = ['基础信息', '解析与统计']`；`storagePrefix = 'sbom_product_column_v1'`（与软件包列表 `sbom_composition_column_v1` 隔离）；`storageScope` 复用 `userId_projectName` 维度 computed（与软件包列表同源）——不同社区列集合不同、配置天然隔离互不影响；
- 弹层模板（全选 + 分组勾选 + 已选列拖拽 lane + 恢复默认，即时生效）内联复制软件包列表同款，不做子组件抽取，保持单文件既有风格；
- 列表两列新增位置：动态属性列之后、解析状态之前；空值 `--`；两列 `sortable="custom"` 接入既有 `handleProductSortChange` 链路（排序箭头独立点击）。

### 决策 4：DDL 手工执行 + 存量回填只补空值幂等

生产 `spring.jpa.hibernate.ddl-auto=none`，加列需手工 DDL，执行顺序 **DDL → 发版 → 存量回填**（先发版使新代码立即接管写入：发版窗口内发布的制品由新代码写入准确值，不会被回填触碰；回填只处理存量空值，发版窗口期数据不缺失）：

```sql
ALTER TABLE raw_sbom ADD COLUMN IF NOT EXISTS publish_time TIMESTAMP;
```

存量回填（借 `job_execution_id` 关联 batch 历史表取最近一次解析启动时间近似发布时刻，发布→拾取通常秒级、口径偏差可接受）：

```sql
UPDATE raw_sbom r
SET    publish_time = e.start_time
FROM   sbom_batch_job_execution e
WHERE  r.job_execution_id = e.job_execution_id
  AND  r.publish_time IS NULL
  AND  e.start_time IS NOT NULL
  AND (r.task_status IS NULL OR r.task_status <> 'WAIT');
```

- 只补空值（`publish_time IS NULL`），幂等可重跑，不会覆盖业务已写入的值；
- 排除 `task_status = 'WAIT'` 行：重新发布（覆盖成功）后的行处于 WAIT，其 `job_execution_id` 仍指向上一次执行，回填会写入早于真实发布时刻一个完整解析周期的错误值；排除后这些行保持 null，待下次发布由新代码写入准确值（与孤儿引用同一处理原则）。`task_status IS NULL`（历史无状态记录）与 RUNNING/FINISH_PARSE/FINISH/FAILED/FAILED_FINISH 行的 `job_execution_id` 即其最近一次执行，近似语义一致（偏差为一次排队时长），纳入回填；
- 未覆盖行（batch 历史已清理的孤儿引用，gamma 实测 487/653；从未解析无 `job_execution_id` 的行；WAIT 行）保持 null，前端 `--`，下次发布即有准确值；
- 回填后量化校验：回填前后各执行一次 `SELECT count(*) FROM raw_sbom WHERE publish_time IS NULL` 对照（预期从全量降至 孤儿引用 + 从未解析 + WAIT 行数之和）；孤儿引用核对 `SELECT count(*) FROM raw_sbom r LEFT JOIN sbom_batch_job_execution e ON r.job_execution_id = e.job_execution_id WHERE r.publish_time IS NULL AND e.job_execution_id IS NULL`。

## API 接口设计

`POST /openlibing-sbom/sbom-api/queryProductListMultiFilter`（既有接口，无新增接口）：

- 出参 `ProductWithStatisticsVo` 新增 `publishTime`（制品发布时间，`publish_time`）、`finishTime`（任务完成时间，`update_time`），格式与既有时间字段一致；
- 入参 `sortField` 白名单扩展 `publishTime` / `finishTime`（`ProductSortField` 枚举），`sortDir` 沿用 asc/desc；
- 错误码无变化；非法 sortField 沿用既有白名单拒绝逻辑。

## 性能设计

- 查询无新增 join（`rs` 子查询在既有 SQL 内，走 `raw_sbom_uk` 唯一索引；`sbom_batch_job_execution` 仅存量回填脚本一次性离线使用，不在在线查询链路）；gamma 实测（openLiBing 25 / openEuler 569 制品）：页面口径 5.9ms → 3.0ms、排序 2.3ms、全量 pageSize=1000 4.8ms，均在个位数毫秒级；
- 排序 CASE 分支在分页（LIMIT/OFFSET）内执行，深分页风险与既有列一致；
- 发布链路新增写入（一次 UPDATE 多 SET 一个字段）无额外往返。

## 安全设计

- 无新增接口与鉴权面：沿用 `queryProductListMultiFilter` 既有权限（Controller 侧 productType/userId 校验不变）；
- 输入面无变化：`sortField` 沿用 `ProductSortField` 白名单，无注入风险（native SQL 参数绑定 + 枚举校验）；
- 时间字段为服务端生成（`now()` / `@UpdateTimestamp`），前端只读展示，无敏感信息。

## 跨仓影响

`openlibing-web`（apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/）：

- `index.vue`：制品表新增两列（含 tooltip 口径说明）、`productTableColumns` computed + `useProductColumnSetting` 接入 + 「列配置」按钮与弹层模板、排序接入；
- 列配置组合式函数 `productColumnSetting.js` 零改动复用。
