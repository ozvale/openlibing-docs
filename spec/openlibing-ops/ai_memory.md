# openlibing-ops AI Memory

本文档保存 `openlibing-ops` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-ops` 负责 OpenLibing AI 能力的 Web 侧交互。后续系统级职责、页面边界、接口契约、权限控制和用户体验规范需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及页面路由、权限、接口字段、用户可见交互时，必须在需求设计中说明影响范围。
- 前端需求完成后，必须在 `archive.md` 记录最终交互、验证方式、AI 错误和人工修正。
- **测试报告增量采集的重试判定**（test-report-store-consume）：三平台源表（codearts/gitcode/github）均为 Doris UNIQUE KEY（MOW），流水线**重试后三 ID 不变但 `end_time` 更新（覆盖原行，不新增）**；CodeArts 因 `step_daily_build_number` 递增拼接 jobId 变化天然区分。增量判定 =「状态完成 + 时间窗口 + 反查 + **`source_end_time` 时间比较**」：raw 表记采集时源表 `end_time`，工作流①反查 `未落库 OR 源表.end_time > 已落库 source_end_time`；工作流②同样 `未清洗 OR raw.source_end_time > 已清洗 source_end_time`。**三平台 end_time 字段**：codearts=`pipeline_end_time`、github=`updated_at`（run 级）、gitcode=`end_time`。source_end_time 允许 NULL（安全降级为只采一次），但**已落库 NULL 行不会被重采**（`end_time > NULL` 恒不成立）。
- **SeaTunnel 自定义 transform 透传 Doris datetime 列**：source SQL 从 Doris 读出的 datetime 列是 `LocalDateTime` 对象；transform 输出列若声明为 `BasicType.STRING_TYPE` 透传该值，JDBC sink 会报 `JDBC-10 Data type cast failed`（`ClassCastException: LocalDateTime cannot be cast to String`）。**输出列类型必须用 `LocalTimeType.LOCAL_DATE_TIME_TYPE`**，且入参/透传都用 `Object` 承接。
- **Doris 3.4.x UNIQUE KEY 表必须显式 `DISTRIBUTED BY`**（test-report-store-consume 实测）：缺省直接报语法错误（`Syntax error ... Encountered: INTEGER LITERAL`，报错位置看似在列定义行，易误判为列语法问题）。所有 Doris UNIQUE KEY 建表 DDL 必须带 `DISTRIBUTED BY HASH(列) BUCKETS n` + MOW PROPERTIES（`enable_unique_key_merge_on_write=true`）。
- **DS 手动触发工作流必须显式 `tenantCode=dolphinscheduler`**（wl_test 实测）：API 触发（`executors/start-workflow-instance`）不传 tenantCode 时默认 `default` 租户，SEATUNNEL 任务**提交即失败**（任务实例 `startTime=null`、`logPath=null`，工作流 1s 失败，无明显日志）。用 `wuliang` 账号 + `tenantCode=dolphinscheduler` 才能跑 SeaTunnel；同理 POST/PUT DS 接口的 form 参数放 body（`application/x-www-form-urlencoded`）可避免 URL 超长（414）。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| **SeaTunnel transform 输出列类型与透传值不符导致 sink 转换失败**：`TestReportReader` 新增 `sourceEndTime` 输出列声明为 `BasicType.STRING_TYPE`，但 source SQL 透传的 Doris datetime 值是 `LocalDateTime` 对象，JDBC sink 报 `JDBC-10 Data type cast failed`（`ClassCastException: LocalDateTime cannot be cast to String`）。 | transform 透传源表 datetime 列时，输出列类型必须声明为 `LocalTimeType.LOCAL_DATE_TIME_TYPE`（非 STRING），入参读取/透传用 `Object` 承接；改完需重新构建 jar 并**手动部署到测试环境**（上传 OBS 桶 + 重启 SeaTunnel 服务）后再验证。 | test-report-store-consume |
| **SQL 汇总 CTE 以 `sdi_repo_info` 起表导致 N 倍笛卡尔积**：项目下 N 行仓库，JOIN `sdi_version_pipeline_base_info`（M 行流水线）后 `SUM(可加项)` 不去重被 ×N（项目下仓库数），`COUNT(DISTINCT ...)` 反而正常去重，分子被放大 N 倍；`GROUP BY` 无法消除。MindIE 实测版本可用度 10%→80%+、P0 通过数 118→1062。 | ① 写库 SQL 与汇总接口 mapper 的 CTE 统一以"指标所在细粒度表"起表：版本/P0 都是流水线维度，起表应为 `sdi_version_pipeline_base_info`，**不要**先经 `sdi_repo_info`。② `open_source` 显式写死（如 `lead`）或透传 `#{req.openSource}`，**不要**通过 `JOIN sdi_repo_info` 隐式带出。③ 涉及多项目下"项目维度聚合"指标时，凡起表行数 ≠ 实际指标粒度行数都必须做"项目下推算 N"心算复核。 | feat-pr-dashboard-metrics（#38） |
| **排序白名单漏配导致前端排序无响应**：前端按字段名（如 `avgCheckDuration`）调排序接口，后端 `SORT_FIELD_MAPPING` 未配该字段，接口不报错但结果不排序。 | 新增/修改前端排序字段时必须**同步**检查后端 `*SortField`/`SORT_FIELD_MAPPING`/`ORDER_BY` 白名单；为排序字段新增单测（`testGetSortField_xxx`）作为最便宜的护栏。 | feat-pr-dashboard-metrics（#43） |
