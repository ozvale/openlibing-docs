# 制品信息列表新增制品发布时间与任务完成时间 — 实现任务

## 进度: 0/8 complete

- [ ] Task 1: `RawSbom` 实体新增 `parse_start_time` 字段（TIMESTAMP），附手工 DDL（生产 `ddl-auto=none`）：
      `ALTER TABLE raw_sbom ADD COLUMN IF NOT EXISTS parse_start_time TIMESTAMP;`
- [ ] Task 2: `SbomServiceImpl.publishSbom` 两条写入路径 — 新建 INSERT 前 `setParseStartTime(now)`；已有复用走 `RawSbomRepository.updateRawSbomIfStatusAllowed` 原子 UPDATE，SET 段追加 `parse_start_time = now()`（RUNNING 拒绝语义不变）
- [ ] Task 3: 查询透出 — `ProductRepository.queryProductListMultiFilter` 的 `rs` 子查询（DISTINCT ON product_id）补取 `parse_start_time`，SELECT 补 `rs.parse_start_time AS "publishTime", rs.update_time AS "finishTime"`；`ProductWithStatisticsView` 投影与 `ProductWithStatisticsVo` 新增两字段
- [ ] Task 4: 排序 — `ProductSortField` 枚举新增 `PUBLISH_TIME` / `FINISH_TIME`；ORDER BY 新增两个 `CASE WHEN` 分支（`NULLS LAST`），兜底 `p.name COLLATE "C" ASC` 不变；`countQuery` 不动
- [ ] Task 5: 存量回填 SQL 交付 — 借 `job_execution_id` 关联 `sbom_batch_job_execution.start_time`，只补空值幂等（发版顺序：DDL → 回填 → 发版）
- [ ] Task 6: 前端两列与排序 — `index.vue` 制品表新增「制品发布时间」「任务完成时间」两列（动态属性列之后、解析状态之前，空值 `--`，tooltip 口径说明），`sortable="custom"` 接入既有排序链路（箭头独立点击）
- [ ] Task 7: 前端列配置 — `productTableColumns` computed（锁定列 = 基础列 + 动态属性列 `attr_<name>`；可配置列 = publishTime 起的 6 列）+ `useProductColumnSetting` 接入（`storagePrefix` `sbom_product_column_v1`、`storageScope` userId_projectName 维度、`groupOrder` 基础信息/解析与统计）+ 「列配置」按钮与弹层模板内联同款
- [ ] Task 8: 单测与验证 — publishSbom 新建/复用两路径 + RUNNING 拒绝抛异常；SQL 排序分支（asc/desc + NULL LAST）；漏洞刷新不触碰 parse_start_time

## 验证方式

- `mvn compile`（model / dao / sbom-web）
- 单测按 ai_memory 规则在 Phase 4 生成（Mockito 风格）：publishSbom 覆盖（新建写 WAIT 时刻、复用刷新、RUNNING 拒绝）、`updateRawSbomIfStatusAllowed` 原子语义、排序分支
- gamma 环境联调：上传新制品验证 WAIT 起即有发布时间；重新发布验证刷新；触发漏洞刷新验证 publishTime 不变 finishTime 刷新；列表两列展示/排序/列配置（显隐 + 拖拽 + 恢复默认 + 社区隔离）
- 存量回填后核对覆盖率与空值构成（孤儿引用保持 null）
