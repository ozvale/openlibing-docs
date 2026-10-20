# 生态社区特性运营看板框架特性指标方案调整 — 实现任务

## 进度: 5/5 complete

### Task 1: 指标元数据模型调整

- [x] 特性指标元数据 Entity / DTO 新增 `indicatorType`（NUMBER/RATIO）字段
- [x] 新增 `aggregateMethod`（SUM/AVG/NONE）字段
- [x] 新增 `showInFeatureDetail`（Boolean）字段
- [x] 新增 `allColumnMethod`（SUM/AVG）字段

### Task 2: 目标值模型调整

- [x] 目标值字段改为可选
- [x] 新增 `targetValueDimension`（FEATURE/COMMUNITY）字段
- [x] 新增 `targetValueType`（GROWTH/REDUCTION）字段

### Task 3: 全部列聚合计算收敛

- [x] 全部列聚合逻辑按 `allColumnMethod` 字段执行（SUM/AVG），与 `aggregateMethod` 解耦

### Task 4: 上报接口契约调整

- [x] 特性指标数据上报接口字段同步调整（兼容历史元数据默认值）
- [x] Service 层完成率计算按 `targetValueType` 选择增长/消减公式

### Task 5: 验证

- [x] `mvn spotless:check test-compile` 通过
- [x] PR 合入 `release_20260923_iter2` 分支
