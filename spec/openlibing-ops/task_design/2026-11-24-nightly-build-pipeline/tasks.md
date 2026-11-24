# Nightly 专用 build 流水线适配 — Tasks

> 关联文档：`./spec.md`、`./需求设计说明书.md`
> 代码基线：`openlibing-ops` main
> 进度：11/25 complete（代码与测试）

## 任务依赖

```
Phase 0 前置确认
   └── Phase 1 DDL
         └── Phase 2 DolphinScheduler（base → fact → 逻辑流水线）
               └── Phase 3 openlibing-ops（model → mapper → service）
                     └── Phase 4 测试
                           └── Phase 5 验证
                                 └── Phase 6 发布与观察
```

> 顺序不可颠倒：后端 SQL 引用 `is_build_pipeline`，必须晚于 DDL；后端验证必须晚于 base 任务重跑。

---

## 本次实施进度（2026-11-24）

**已完成**

- Issue：[#395](https://gitcode.com/openlibing/openlibing-ops/issues/395)
- 分支：`feat-nightly-build-pipeline-395`（基于 `origin/main`，commit `c1188b05`）
- 提交：`742eada9 feat(ops): support nightly build pipeline in metrics`
- PR：[!325](https://gitcode.com/openlibing/openlibing-ops/merge_requests/325)（关联 #395，标签 `ai-assisted`）
- Task 1.1：DDL 文件 `openlibing-ops/docs/issue/395/DDL.sql` 已生成，并已在本地 Doris 执行
- Task 2.1 / 2.2 / 2.3：3 个 DolphinScheduler 任务 SQL 已改（待上传并重跑）
- Task 3.1 ~ 3.7：ops 后端模型、service、5 个 mapper 已完成
- Task 4.1 ~ 4.4：测试已更新并通过
  - `mvn test`：1820 tests，0 failures
  - `mvn clean package -DskipTests`：BUILD SUCCESS
  - `pre-commit run --from-ref origin/main --to-ref HEAD`：全部 hooks 通过；已执行 `pre-commit install`

**待执行（依赖环境或用户确认）**

- Phase 0：合入分支最终确认、基础表登记核对
- Phase 2：DolphinScheduler 任务上传与重跑
- Phase 5：页面验证（接口已验证，见下）
- Phase 6：上线与观察（commit / push / PR 已完成）

### 本地服务验证（8098，2026-11-24）

- 服务以 HTTPS 启动，以下接口均返回 `code=200`，无 SQL 报错：
  - `POST /ops-overview/main`：14 个项目，12 个有 Nightly 指标；Ascend-CANN(300057) `nightlyBuildSuccessRate=1.0`、`nightlyVersionAvailabilityRate=1.0`
  - `GET /pipeline/query?projectId=300057`：返回 `isBuildPipeline` 字段（当前均为 0）
  - `POST /pipeline/version/chart`（`category=version`）：9 条流水线，正常返回
  - `POST /common/detail` `nightly-dashboard`：9 行，`versionAvailabilityRate`、`buildSuccessRate` 有值
  - `POST /common/detail` `nightly-dashboard-summary`：`buildSuccessRate=99.52`
  - `POST /common/detail` `ops-nightly-detail`：版本级优先返回 1 行，`buildSuccess=1.0`、`versionAvail=1.0`
  - `POST /common/detail` `version-available-rate`、`project`（`openSource=lead`）：正常返回
- **结论**：本地 `dm_rd_efc_project_pipeline_relation` 中暂无 `*build_pipeline*` 记录，build 专属端到端效果需在重跑 base relation 任务、且 build 流水线已登记并产生运行后再验证。
- 已补充 `/pipeline/version/chart` 返回 `isBuildPipeline` 字段（需重启服务生效）。
- **重启后复验（2026-11-24）**：46 条 Nightly 流水线的列表接口与 chart 接口均返回 `isBuildPipeline` 字段（值均为 0）；build-like 记录 0 条；主表 Nightly 编译成功率/版本可用度与重启前完全一致，无回归。

---

## Phase 0：前置确认

### Task 0.1 确认开发分支与代码基线

- [ ] 确认本需求合入分支：`main` 或 `release_security_202611`
- [ ] 若为 `release_security_202611`，先确认该分支是否已包含 `OpsMainStatMapper` 的 `queryPrStat/queryNightlyStat/queryResourceStat` 拆分；未包含则先同步拆分
- [ ] 记录基线 commit，作为后续 diff 基准

**验收**：分支确认结论写入 PR 描述。

---

### Task 0.2 确认构建流水线已具备统计条件

- [ ] 确认 `Nightly-Version-build_pipeline*` / `Nightly-Component-build_pipeline*` 已登记在 `sdi_version_pipeline_base_info`
- [ ] 确认两条流水线已产生过运行（relation 的 codearts 流水线集合来自 `sdi_rd_efc_pipeline_run_clean_codearts`）
- [ ] 记录实际流水线名称与 `pipeline_id`，确认符合“固定前缀 + 自定义后缀”

```sql
-- 基础表登记核对
SELECT bv.project_id, bv.pipeline_id
FROM sdi_version_pipeline_base_info bv
WHERE bv.pipeline_id IN (
  SELECT pipeline_id
  FROM sdi_rd_efc_pipeline_run_clean_codearts
  WHERE LOWER(TRIM(pipeline_name)) LIKE 'nightly-version-build_pipeline%'
     OR LOWER(TRIM(pipeline_name)) LIKE 'nightly-component-build_pipeline%'
);
```

**验收**：查询结果非空；名称以两个固定前缀开头。

---

### Task 0.3 确认口径与展示预期

- [ ] 与产品确认：构建流水线在列表展示、版本可用度显示 `--`
- [ ] 确认项目级编译成功率沿用“逐流水线率再 AVG”，不改为按任务数加权
- [ ] 确认资源类看板不特殊处理

**验收**：口径确认记录写入 PR 描述或 Issue 评论。

---

## Phase 1：Doris DDL

### Task 1.1 `dm_rd_efc_project_pipeline_relation` 新增标识列

- [ ] 执行 DDL
- [ ] 校验列已存在、默认值为 0
- [ ] 确认 `light_schema_change` 生效，无副本异常

```sql
ALTER TABLE dm_rd_efc_project_pipeline_relation
  ADD COLUMN `is_build_pipeline` tinyint NOT NULL DEFAULT '0'
  COMMENT '是否Nightly专用构建流水线：1是 0否';
```

**验收**：`DESC dm_rd_efc_project_pipeline_relation` 可见 `is_build_pipeline`；存量行值为 0。

**回滚**：`ALTER TABLE ... DROP COLUMN is_build_pipeline;`（仅在 ETL/后端均回滚后执行）

---

## Phase 2：DolphinScheduler 计算任务

### Task 2.1 `[base]项目与流水线关联关系生成`

文件：`DolphinScheduler/[workflow][base]项目与流水线关联关系生成/[job][base]项目与流水线关联关系生成.sql`

- [ ] `INSERT INTO` 改为显式列清单，追加 `is_build_pipeline`
- [ ] codearts PR 分支：`0`
- [ ] codearts 非 PR 分支：前缀匹配表达式
- [ ] gitcode 分支：前缀匹配表达式
- [ ] github 分支：`0`
- [ ] 保留 `pipeline_type` 现有判定（依赖 `sdi_version_pipeline_base_info`）
- [ ] 重跑任务一次

```sql
insert into dm_rd_efc_project_pipeline_relation
(product_id, project_id, platform, pipeline_project, pipeline_id,
 product_name, project_name, pipeline_name, pipeline_type, is_build_pipeline)
```

```sql
-- codearts / gitcode 分支
case when lower(trim(<name_col>)) like 'nightly-version-build_pipeline%'
       or lower(trim(<name_col>)) like 'nightly-component-build_pipeline%'
     then 1 else 0 end as is_build_pipeline
```

**验收**：

```sql
SELECT platform, pipeline_id, pipeline_name, pipeline_type, is_build_pipeline
FROM dm_rd_efc_project_pipeline_relation
WHERE LOWER(TRIM(pipeline_name)) LIKE 'nightly-version-build_pipeline%'
   OR LOWER(TRIM(pipeline_name)) LIKE 'nightly-component-build_pipeline%';
-- 期望：pipeline_type='NIGHTLY'，is_build_pipeline=1
```

**回滚**：回退 SQL 到显式列清单但不写新列（或恢复旧 SQL），重跑任务。

---

### Task 2.2 `[dwi->dwr] Nightly流水线测试用例执行事实表`

文件：`.../[job][dwi-dwr][codearts]Nightly流水线测试用例执行事实表（每条执行记录一行）/[dwr]dwr_rd_efc_build_fact_nightly_test_case_pipeline_run.sql`

- [ ] `filtered_pipelines` 的 `EXISTS` 改为 `INNER JOIN` 聚合子查询，带出 `is_build_pipeline`
- [ ] 最终 `SELECT` 的 `is_version_available` 增加 `WHEN fp.is_build_pipeline = 1 THEN NULL`
- [ ] 确认 `test_case_statistics` / `step_statistics` 引用的列不受影响
- [ ] 重跑任务

```sql
INNER JOIN (
    SELECT pipeline_id, MAX(is_build_pipeline) AS is_build_pipeline
    FROM dm_rd_efc_project_pipeline_relation
    WHERE pipeline_type = 'NIGHTLY'
    GROUP BY pipeline_id
) rel ON rel.pipeline_id = u.pipeline_id
```

```sql
CASE
    WHEN fp.is_build_pipeline = 1 THEN NULL
    WHEN fp.pipeline_end_time >= '2026-09-04' THEN ...v2...
    ELSE ...v1...
END AS is_version_available
```

**验收**：

```sql
SELECT pipeline_id, pipeline_name, build_count, build_pass_count,
       test_count, case_run_count, is_version_available
FROM dwr_rd_efc_build_fact_nightly_test_case_pipeline_run
WHERE LOWER(TRIM(pipeline_name)) LIKE '%build_pipeline%'
LIMIT 50;
-- 期望：build_count>0；test_count/case_run_count 为空；is_version_available 为 NULL
```

---

### Task 2.3 `[dwr->dwr] nightlyl逻辑流水线计算`

文件：`.../[job][dwr-dm]nightly逻辑流水线计算/[job][dwr-dwr]nightlyl逻辑流水线计算.sql`

- [ ] `pipeline_binding` 增加 `MAX(is_build_pipeline) AS is_build_pipeline`
- [ ] alias JOIN 增加 `AND COALESCE(b.is_build_pipeline, 0) = 0`
- [ ] 确认 `WHERE` 条件仍为 `b.pipeline_type = 'NIGHTLY'`
- [ ] 重跑任务

**验收**：

```sql
SELECT pipeline_id, logical_pipeline_id, logical_pipeline_name
FROM dm_rd_efc_nightly_pipeline_logical_run
WHERE LOWER(TRIM(pipeline_name)) LIKE '%build_pipeline%'
LIMIT 20;
-- 期望：logical_pipeline_id = pipeline_id（未被 alias 合并）
```

---

### Task 2.4 回归确认“不改”的 3 个任务

文件：

- `[dm]nightly流水线执行任务每日汇总.sql`
- `[dm]nightly流水线测试用例数据每日汇总.sql`
- `[job][dwr-dm]nightly逻辑流水线日数据计算.sql`

- [ ] 确认未修改
- [ ] 重跑后抽查构建流水线的 DM 行：`build_count` 正常、`is_version_available` 为 NULL
- [ ] 确认 `resource` CTE 仍包含构建流水线（决策 4）

**验收**：DM 日汇总与逻辑日宽表中构建流水线数据形态正确。

---

## Phase 3：openlibing-ops 后端

### Task 3.1 实体与响应新增字段

- [ ] `domain/model/pipeline/DmRdEfcProjectPipelineRelation.java` 新增 `private Integer isBuildPipeline;`
- [ ] `api/response/pipeline/PipelineInfoResp.java` 新增 `private Integer isBuildPipeline;`

**验收**：编译通过；Lombok 正常生成 getter/setter。

---

### Task 3.2 流水线列表与备案集合

文件：`src/main/resources/mapper/DmRdEfcProjectPipelineRelationMapper.xml`

- [ ] `selectNightlyPipelines` 增加 `MAX(r.is_build_pipeline) AS is_build_pipeline`
- [ ] `selectNightlyPipelineNames`（备案）增加 `AND r.is_build_pipeline = 0`
- [ ] 确认 `selectNightlyPipelines` 仍排除 github

**验收**：接口 `/pipeline/version/chart` 返回的 `dataList` 含 `isBuildPipeline`。

---

### Task 3.3 `PipelineHandleImpl` 可用度拆分

文件：`src/main/java/com/openlibing/ops/app/service/pipeline/impl/PipelineHandleImpl.java`

- [ ] `queryVersionPipeline` 映射 `isBuildPipeline`
- [ ] `queryVersionPipelineChart` 拆分 `testPipelineIds`
- [ ] 空集合保护：`testPipelineIds.isEmpty() ? Map.of() : queryVersionAvailabilityRate(...)`
- [ ] `chart.setVersionAvailableRate(...)` 对构建流水线置 `null`
- [ ] `queryPipelineRunData` / `queryTestCaseData` 仍传全量 pipelineIds
- [ ] 使用 `Integer.valueOf(1).equals(...)` 判空安全

**验收**：构建流水线的 `versionAvailableRate` 为 `null`；非构建流水线数值不变。

---

### Task 3.4 `NightlyPipelineDashboardMapper.xml`

文件：`src/main/resources/mapper/NightlyPipelineDashboardMapper.xml`

- [ ] `pipeline_statsCTE` 的 `sdi` 子查询增加 `MAX(r.is_build_pipeline) AS is_build_pipeline`
- [ ] `LEFT JOIN version_availability_stats va` 增加 `AND sdi.is_build_pipeline = 0`
- [ ] `GROUP BY` 增加 `sdi.is_build_pipeline`
- [ ] 确认 `build_success_rate` 仍取自全量 `dr`

**验收**：`category=nightly-dashboard` 返回构建流水线行，`versionAvailabilityRate=null`、`buildSuccessRate` 有值；`nightly-dashboard-summary` 编译成功率包含构建流水线。

---

### Task 3.5 `OpsMainStatMapper.xml` 的 `queryNightlyStat`

文件：`src/main/resources/mapper/OpsMainStatMapper.xml`（L257-L470）

- [ ] `nightly_pipelines_all` 增加 `MAX(r.is_build_pipeline)`
- [ ] `is_version_level` 增加 `AND r.is_build_pipeline = 0`
- [ ] `selected_pipelines` 增加 `a.is_build_pipeline = 1 OR ...`
- [ ] 新增 `nightly_avail_pipelines`（**禁止**命名为 `selected_pipelines_*`）
- [ ] `pipeline_version_avail` 改 `INNER JOIN nightly_avail_pipelines`
- [ ] `pipeline_build_rate` 保持 `FROM selected_pipelines`
- [ ] GitHub 可用度分支保持不变

**验收**：项目级 `nightlyVersionAvailabilityRate` 不回归；`nightlyBuildSuccessRate` 包含构建流水线。

---

### Task 3.6 `OpsNightlyDetailMapper.xml`

文件：`src/main/resources/mapper/OpsNightlyDetailMapper.xml`

- [ ] `<sql id="nightlySelectedPipelinesCte">` 的 `nightly_pipelines_all` 增加 `MAX(r.is_build_pipeline)`
- [ ] `is_version_level` 增加 `AND r.is_build_pipeline = 0`
- [ ] `selected_pipelines` 增加 `p.is_build_pipeline = 1 OR ...`
- [ ] 新增 `nightly_avail_pipelines`
- [ ] `nightlyVersionAvailCte` 两处 `INNER JOIN selected_pipelines` 改为 `nightly_avail_pipelines`
- [ ] 确认 list/count/summary 仍用 `selected_pipelines`

**验收**：`category=nightly-dashboard-detail` 构建流水线 `versionAvail=null`、`buildSuccess` 有值；KPI `avgVersionAvail` 不被稀释。

---

### Task 3.7 `DwiProjectStatisticsMapper.xml`

文件：`src/main/resources/mapper/DwiProjectStatisticsMapper.xml`

- [ ] `case_latest` 的 relation 子查询增加 `AND r.is_build_pipeline = 0`
- [ ] `version_availability_per_pipeline` 的 relation 子查询增加 `AND r.is_build_pipeline = 0`

**验收**：`category=project` 项目级版本可用度不回归。

---

## Phase 4：测试

### Task 4.1 更新 `OpsMainStatMapperXmlTest`

文件：`src/test/java/com/openlibing/ops/domain/mapper/ops/OpsMainStatMapperXmlTest.java`

- [ ] 保持 `countOccurrences("selected_pipelines") == 3`
- [ ] `nightlyPipelinesAll...` 增加 `is_build_pipeline` 断言
- [ ] `selectedPipelines...` 增加 `a.is_build_pipeline = 1` 断言
- [ ] 新增 `nightlyAvailPipelines...`：含 `a.is_build_pipeline = 0`
- [ ] 确认 `resourceMetricCtes...` 仍通过

**验收**：测试全绿。

---

### Task 4.2 更新 `OpsNightlyDetailMapperXmlTest`

文件：`src/test/java/com/openlibing/ops/domain/mapper/ops/OpsNightlyDetailMapperXmlTest.java`

- [ ] 保持 `nightlySelectedPipelinesCte` include 计数为 4
- [ ] 增加 `is_build_pipeline` 与 `nightly_avail_pipelines` 断言
- [ ] 确认 `classification_shouldNotUseNullUnsafeNotLikePredicate` 仍通过（不得出现 `NOT LIKE 'nightly`）

**验收**：测试全绿。

---

### Task 4.3 补充 `PipelineHandleImplTest`

文件：`src/test/java/com/openlibing/ops/app/service/pipeline/impl/PipelineHandleImplTest.java`

- [ ] 新增用例：构建流水线 `versionAvailableRate=null`
- [ ] 新增用例：仅构建流水线时可用度查询不被调用（空集合保护）
- [ ] 确认既有用例无需修改（`isBuildPipeline=null` 视为非构建）

**验收**：测试全绿。

---

### Task 4.4 全量测试

```bash
mvn -pl openlibing-ops test
# 或仓库约定的测试命令
```

- [ ] 单元测试通过
- [ ] XML 结构测试通过
- [ ] 无新增编译告警

---

## Phase 5：验证

### Task 5.1 SQL 验证

- [ ] relation 分类核对（Task 2.1 的 SQL）
- [ ] 事实表形态核对（Task 2.2 的 SQL）
- [ ] 逻辑流水线未被 alias 合并（Task 2.3 的 SQL）
- [ ] 记录改造前后项目级可用度对比样本

**验收**：结果符合 spec.md 第 4 节。

---

### Task 5.2 接口验证

- [ ] `POST /ops-overview/main`：`nightlyVersionAvailabilityRate` 不回归；`nightlyBuildSuccessRate` 变化符合预期
- [ ] `POST /pipeline/version/chart`：构建流水线 `versionAvailableRate=null`，`isBuildPipeline=1`
- [ ] `POST /common/detail`（`nightly-dashboard`）：构建流水线行存在，可用度 `null`
- [ ] `POST /common/detail`（`nightly-dashboard-summary`）：编译成功率包含构建流水线
- [ ] `POST /common/detail`（`nightly-dashboard-detail`）：构建流水线 `versionAvail=null`
- [ ] `POST /common/detail`（`version-available-rate`）：构建流水线不出现/不可下钻
- [ ] `POST /common/detail`（`project`）：项目级版本可用度不回归

**验收**：接口返回与预期一致。

---

### Task 5.3 页面验证

- [ ] Nightly 看板：列表出现构建流水线；版本可用度 `--`；编译成功率/时长有值
- [ ] Nightly 看板：趋势图构建流水线无可用度柱，其余曲线正常
- [ ] 工程能力看板：Nightly 明细构建流水线行存在，可用度 `--`，编译成功率有值
- [ ] 工程能力看板：KPI 卡片 `avgVersionAvail` 未被拉低
- [ ] 资源类看板：无异常变化

**验收**：页面表现与 spec.md 第 4 节一致。

---

## Phase 6：发布与观察

### Task 6.1 提交与 PR

- [ ] 按 commit 规范提交（`feat(ops): ...`）
- [ ] 创建业务 PR，关联 Issue，打 `ai-assisted` 标签
- [ ] PR 描述包含：口径说明、改动文件清单、验证结果、上线顺序

---

### Task 6.2 按顺序上线

1. [ ] Doris DDL
2. [ ] base relation 任务 + 重跑
3. [ ] fact 任务 + 2 个 DM 汇总 + 2 个逻辑流水线任务
4. [ ] `openlibing-ops` 后端
5. [ ] 执行 Phase 5 验证

---

### Task 6.3 观察与回滚预案

- [ ] 上线后 24h 观察：构建流水线分类、可用度、编译成功率
- [ ] 若可用度异常：先回滚后端 → 再回滚 ETL → 最后考虑 DDL
- [ ] 记录回滚步骤与实际执行人

---

## 附：任务与文件对照

| Task | 文件 / 对象                                                                       |
| ---- | --------------------------------------------------------------------------------- |
| 1.1  | `dm_rd_efc_project_pipeline_relation`                                             |
| 2.1  | `[job][base]项目与流水线关联关系生成.sql`                                         |
| 2.2  | `[dwr]dwr_rd_efc_build_fact_nightly_test_case_pipeline_run.sql`                   |
| 2.3  | `[job][dwr-dwr]nightlyl逻辑流水线计算.sql`                                        |
| 2.4  | 2 个 `[dm]nightly...每日汇总.sql`、`[job][dwr-dm]nightly逻辑流水线日数据计算.sql` |
| 3.1  | `DmRdEfcProjectPipelineRelation.java`、`PipelineInfoResp.java`                    |
| 3.2  | `DmRdEfcProjectPipelineRelationMapper.xml`                                        |
| 3.3  | `PipelineHandleImpl.java`                                                         |
| 3.4  | `NightlyPipelineDashboardMapper.xml`                                              |
| 3.5  | `OpsMainStatMapper.xml`                                                           |
| 3.6  | `OpsNightlyDetailMapper.xml`                                                      |
| 3.7  | `DwiProjectStatisticsMapper.xml`                                                  |
| 4.1  | `OpsMainStatMapperXmlTest.java`                                                   |
| 4.2  | `OpsNightlyDetailMapperXmlTest.java`                                              |
| 4.3  | `PipelineHandleImplTest.java`                                                     |
