# tasks.md — 测试报告持久化存储与消费（ops 侧实施清单）

> 关联：design.md / proposal.md；本文件为 **Phase 2 实现计划**，覆盖 openlibing-ops 的 REST + MCP 消费编码任务。
> 采集侧（DS + SeaTunnel）不在此清单（见 design.md 第 7 章，由 T2/T4/T5 推进）。

## 流程模式

- 推荐：**Standard**（单仓 openlibing-ops；新增外部接口 /report/* 与 MCP 工具；跨 api/app/domain 多层；含动态 SQL 白名单安全点；无数据模型变更）
- 分支：`wl_fork` 上基于 origin/main 最新建 `feat-test-report-consume`

## 修改文件清单

### A. REST 消费（/report/*，独立 ReportController，不走 common 三件套）

| # | 文件 | 说明 |
| --- | --- | --- |
| A1 | `api/request/report/ReportDataQueryReq.java` | modelCode/repoUrl/startTime/endTime/timeField/filters[]/page/pageSize |
| A2 | `api/request/report/ReportFilterReq.java` | filters 元素：field/op/value |
| A3 | `api/response/report/ReportTemplateListResp.java` | modelCode/modelName/description/repoUrls/columns[] |
| A4 | `api/response/report/ReportColumnResp.java` | columnName/columnComment/dataType/required |
| A5 | `api/controller/ReportController.java` | POST `/report/template/list`、POST `/report/data/query` |
| A6 | `app/service/report/ReportQueryService.java` | 编排：模板列表（登记表 + Doris information_schema + DISTINCT repo_url）；数据查询（表名/列名双白名单 + 操作符白名单 + 动态 WHERE + 分页） |
| A7 | `domain/mapper/report/ReportTemplateModelMapper.java` | MySQL 查 `tbl_third_api_data_model`（app_code=openlibing 的启用模板） |
| A8 | `domain/mapper/report/DorisMetaMapper.java` | Doris 查 `information_schema.columns`（列白名单/必填）+ `SELECT DISTINCT repo_url` |
| A9 | `domain/mapper/report/ReportDataMapper.java` + `resources/mapper/report/ReportDataMapper.xml` | Doris 动态表名查询：`${tableName}`（登记表白名单）+ 白名单列动态 WHERE + LIMIT 分页 |

### B. MCP 消费（内嵌 Spring AI 1.1.8）

| # | 文件 | 说明 |
| --- | --- | --- |
| B1 | `pom.xml` | `<dependencyManagement>` 加 `spring-ai-bom:1.1.8`；`<dependencies>` 加 `spring-ai-starter-mcp-server-webmvc` |
| B2 | `api/mcp/McpServerConfig.java` | `@Bean reportMcpToolsProvider`（`MethodToolCallbackProvider`，方法名避开类名） |
| B3 | `api/mcp/ReportMcpTools.java` | `@Tool` 暴露只读查询（listTemplates/queryReportData），复用 ReportQueryService，**方法级 `@DataSource`** |
| B4 | `application.yaml` | `spring.ai.mcp.server`（name/protocol=STREAMABLE） |

### C. 测试

| # | 文件 | 说明 |
| --- | --- | --- |
| C1 | `ReportDataQueryReqTest` / 白名单工具单测 | op/timeField/列名白名单校验 |
| C2 | `ReportQueryServiceTest` | Mock Mapper 的模板列表与数据查询编排 |
| C3 | `ReportMcpToolsTest` | @Tool 方法参数/返回值契约 |

## 验证方式

1. `mvn compile`（Maven Wrapper 全路径 mvn.cmd，openlibing-ops 根目录）
2. 新增单测 `mvn test -Dtest=...` 通过
3. spotless 格式化（`mvn spotless:apply`）+ 自检清单（注入/硬编码/风格）

## 生成前约束（自检）

- 动态 SQL：表名仅允许登记表 `table_name` 命中值；列名仅允许 information_schema 白名单；op 白名单 eq/ne/gt/gte/lt/lte/like/in
- MCP 工具方法级 `@DataSource`（查登记表 MYSQL、查模板表 DORIS）
- 只修改 openlibing-ops 与 openlibing-docs 范围
- 注释中文、命名遵循现有风格（google-java-format）
