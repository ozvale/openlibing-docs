# 测试报告持久化存储与消费 需求提案

> 关联需求：https://gitcode.com/openlibing/openlibing-ops/issues/123
> 版本：v3（2026-09-08，采集改为 **raw→sdi 两段式**：先入 `raw_test_report` 原始 JSON，再清洗成每模板一张 sdi 表）
> 状态：设计待确认（供项目经理确认）

## 1. 需求背景

OpenLibing 平台需要新增「测试报告上报」能力：业务（测试）团队把按约定 JSON schema 解析好的**结构化测试报告**（外层列表、内层字典，一条数据 = 一条测试任务 + 执行结果）上传到华为云 OBS 桶；平台侧采集入库到 Doris，并提供 **REST API + MCP** 两种消费能力。

- 测试报告 = 多种模板的结构化测试数据，**一模板一表**（明细事实，非文档）。
- 平台**首次建设 MCP 消费体系**（已有实现方式 POC，基于 Spring AI 1.1.8 实测通过）。

## 2. 需求范围（PM 对齐后调整）

| 能力 | 落点 | 说明 |
| --- | --- | --- |
| OBS 采集入库 | **DolphinScheduler + SeaTunnel** | 新增 **两个 DS 工作流**：①「测试报告原始数据采集」轻量 `TestReportReader` transform（复用 `ParseTestcase` 的 OBS 读取，整份读原始 JSON）→ `raw_test_report`；②「测试报告数据清洗」`JsonArrayExpand` + `Sql` 纯配置（**不新增解析插件**）→ 每模板一张 `sdi_rd_efc_test_report_<模板名>`；**不再使用 xxl-job** |
| metadata xml 归属解析 | **既有链路已覆盖** | DS 正式环境已有 SeaTunnel 任务解析存储，归属字段从现有表 JOIN 补齐 |
| Doris 表 | raw 层 + sdi 清洗层 | raw 层统一 `raw_test_report`（原始 JSON 整份，仿 `raw_workflow_source_github`）；sdi 层一模板一表 `sdi_rd_efc_test_report_<模板名>`（rd_efc 中缀），UNIQUE KEY 兜底幂等 |
| REST API 消费 | openlibing-ops（8098） | 独立 `ReportController`：模板元数据 + 数据查询（repo/时间/自定义字段过滤、分页），读 sdi 表 |
| MCP 消费 | openlibing-ops（内嵌 /mcp） | Spring AI 1.1.8 + Streamable HTTP，只读查询 Tool，读 sdi 表 |
| 不参与 | openlibing-sync / openlibing-metric | sync 采集迁出；metric 仅 POC 验证 MCP 机制 |

本期以 **1 个模板（`triton_model_performance`）跑通全链路**，按「模板登记制」通用框架实现，后续模板零代码/低代码扩展。

## 3. 验收标准

1. **采集（DS + SeaTunnel，raw→sdi 两段式）**：
   - 工作流①「测试报告原始数据采集」（**cron 每小时**）：从 OBS `op-case-result` 桶按模板登记范围（`pipeline_ids`，一对多，经 Doris 登记表 `dm_rd_efc_template_registry` 过滤）读取测试报告 JSON → `TestReportReader` **整份读原始 JSON**（复用 `ParseTestcase` OBS 读取，不解析）→ 写 `raw_test_report`；**增量 = 时间窗口（默认 24h，参数化）+ raw 表反查**，不新增台账表；raw 表四元组 UNIQUE KEY 兜底。
   - 工作流②「测试报告数据清洗」（**cron 每小时**）：读 `raw_test_report` → `JsonArrayExpand` 展开外层数组（带 `record_seq`）+ `Sql` 归属字段提取 → 写 `sdi_rd_efc_test_report_<模板名>`；**增量 = 时间窗口 + sdi 表反查**；sdi 表五元组 UNIQUE KEY 行级去重兜底。
2. **Doris 表**：`raw_test_report`（四元组唯一键）+ `sdi_rd_efc_test_report_triton_model_performance`（五元组唯一键）建表完成（DBA 执行）。
3. **ops REST**：
   - `POST /report/template/list`：返回模板名 + 字段元数据 + `repoUrls`（DISTINCT 仓库列表），不暴露内部表字段。
   - `POST /report/data/query`：按 `modelCode` + `repoUrl` + 时间范围 + 自定义字段筛选（数组 + 操作符 eq/ne/gt/gte/lt/lte/like/in，AND 组合）分页查询，字段/操作符白名单校验。
4. **ops MCP**：`/mcp` Streamable HTTP 端点可用，`tools/list` 可见只读查询工具，`tools/call` 返回与 REST 一致。
5. **验证**：造测试数据调通「DS 工作流①采集 → raw 落库 → DS 工作流②清洗 → sdi 落库 → REST 查询 → MCP 调用」全链路；`raw_test_report.data_json` 与 OBS 原文一致（可追溯/重放）；ops `mvn compile/test` 通过。
6. **规则沉淀**：AGENTS.md 补充「后续需求不使用 xxl-job，用 DS + SeaTunnel」规则。

## 4. 待确认项

见 design.md 第 10 节（T1~T11），重点：**T2 TestReportReader 轻量 transform 开发**（插件仓 `nane/openlibing-seatunnel` 已定位，**独立包 `transform/readtestreport`**，可参照/复用 `parsetestcase` 的 OBS 读取，仅输出原文；sdi 清洗段纯配置无新增插件；**个人仓需与仓主 nane 确认协作方式**）、T3 已确认（采集范围来源 = Doris 专用登记表 `dm_rd_efc_template_registry`）、T4 GitHub/GitCode 流水线来源表、T5 已确认（DS 工作流由用户创建，先在测试环境验证再发布）、T10 已确认（暂定 24h，后续可调参数重跑补采）。
