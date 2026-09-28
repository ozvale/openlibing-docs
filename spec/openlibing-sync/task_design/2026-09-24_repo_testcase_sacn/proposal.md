# 社区代码仓多框架用例全集静态扫描

## 需求背景

为沉淀社区对 OpenLibing 体系的实际使用情况（发现活跃用例、识别异常用例、收集改进建议），需要在 `openlibing-seatunnel-plugins` 仓内新增一个 **SeaTunnel Transform 插件**：对**已落盘到共享存储**的社区代码仓进行**多框架测试用例全集静态扫描**，输出逐用例明细 + 汇总的 JSON 单列，供下游 Doris Sink 写入。

参考插件：`com.openlibing.transform.parsetestcase.ParseTestcaseTransform`（CI 流水线执行期 XML 解析）与 `com.openlibing.transform.parsefilecoverage.ParseFileCoverageTransform`（覆盖率文件解析）。本插件与之**独立**，仅复用其 `model.TestCaseMetadata / TestCaseMeasureData` 类，保证下游 Doris 表 schema 兼容。

`openlibing-pytest-executor` 的 pytest 动态收集（安装 requirements + `pytest --collect-only`）仅适合**受信任受控仓**；社区仓代码不可信、规模大，本插件采用**纯静态解析**（Java 21、JVM 内文本读取），不安装任何仓库依赖、不执行任何仓库代码。

## 功能描述

### 1. 插件类型与职责

- **插件形式**：SeaTunnel Transform 插件（同进程内算子），通过 `@AutoService(Factory.class)` 注册到 SeaTunnel SPI；
- **输入**：一行 SeaTunnel Row，字段含 `repoUrl / repoBranch / scanPath / projectId / platform`（默认字段名可配）；
- **输出**：单列 JSON 字符串 `communityScanMeasureData`，内容为 `model.TestCaseMeasureData`（即 `testCaseMetadataList` + 空 `testCaseResultList`）；
- **不暴露任何 HTTP API**：插件即算子；调度由 **DolphinScheduler 调度平台**定时触发**扫描脚本**（Java 实现），扫描脚本负责遍历不同的代码仓和代码分支，每次遍历调用本功能做具体场景的用例扫描，并将本功能扫描结果解析存数据库；
- **配置**走 SeaTunnel `ReadonlyConfig` + `Options.key(...).stringType().xxx.withDescription(...)`，与 `ParseTestcaseTransformOptions` 同款风格；
- **字段语义**与 `ParseTestcaseTransform` 的 `model.TestCaseMetadata` 完全对齐（复用其类），保证下游同一张 Doris 表可同时承接"仓里定义的用例"与"流水线执行的用例"。

### 2. 模块外部已完成（本插件不感知、不调用）

1. 代码仓**白名单设置**（YAML / JSON 配置，写入 Doris 表）；
2. 代码仓**下载 / 克隆**到本地挂载的共享存储；
3. **代码分支切换**（已切到白名单要求的分支）。

本插件**只读**共享存储的**已落盘**目录，不下载、不克隆、不 `git fetch`。

### 3. 多框架用例静态扫描

- 基于 SeaTunnel Transform 的 SPI：`FrameworkScanner` interface，通过 Java `ServiceLoader` + `META-INF/services/` 加载，支持运行时动态扩展；
- 本期框架：**pytest、unittest、go test、gtest**；
- 后续框架：JUnit4/5、TestNG、Jest/Mocha/Vitest、Rust 等（仅新增 SPI 实现 + 注册，无需改 transform 代码）；
- 框架自动探测：一个仓可命中多个框架，全部扫描、结果带 `frameType` 区分；
- 输出**逐用例明细**：框架、文件、类/命名空间、用例名、起止行、skip 及原因、markers/注解、参数化信息（静态尽力展开，无法求值的保留原始表达式并标记）；
- 安全约束：不执行仓库任何代码、不安装依赖、不导入模块；忽略 `.git/vendor/node_modules/third_party/build/dist/.venv/site-packages/__pycache__` 等目录；单文件大小、单仓文件数、符号链接逃逸均有防护。

### 4. 数据写入

- 本插件**只产出 JSON 单列**，不直连数据库；
- 下游 SeaTunnel Sink 负责将 JSON 解析后写 Doris（沿用 `community_testcase_detail` / `community_testcase_summary` 表，复用 `parsetestcase` 的字段语义）；
- 海量批量场景下，单行 JSON 由下游 sink 用 JSON 解析器展开，天然适配 Doris Stream Load / Routine Load。

### 5. 调度方式（DolphinScheduler + Java 扫描脚本）

- 本插件是**离线批处理**算子，**不**内置定时调度；
- **DolphinScheduler**（定时任务调度管理平台）按**每日**触发**扫描脚本**（Java 实现；具体时刻留待 DolphinScheduler 任务编排时与上游代码同步任务联合配置）：
  - 脚本入口：定时读取 Doris `community_repo_whitelist`（`enabled=1`），按 `(repo, branch, scan_path, project_id, platform)` 展开成 N 个扫描单元；
  - 对**每个扫描单元**，脚本调用 SeaTunnel Java Client 提交一份专用 job：
    - Source：内存 Source / Doris 单行 Source（注入该扫描单元的 5 个字段）；
    - Transform：本插件 `CommunityScan`；
    - Sink：Doris Sink 写 `community_testcase_detail` / `community_testcase_summary`；
  - 脚本从 job 输出中**解析 JSON 单列** `communityScanMeasureData`，按 `testCaseMetadataList` 拆行写入 Doris（`community_testcase_detail`）；
  - 扫描结束后回写白名单行 `last_status / last_commit / last_scan_at`。
- DolphinScheduler 任务定义：
  - 类型：**Java 任务**（调用脚本主类的 `main` / 通过 `-cp` 执行 `jar`）；
  - **调度周期：每日一次**（具体时刻由 DolphinScheduler 编排时决定，本方案不固化）；
  - **调度约束**：
    1. **必须在 DolphinScheduler 上"代码同步任务"执行完成之后**——只有上游任务把代码仓落盘到共享存储，本扫描才有数据可读；
    2. **不与其他代码仓相关任务并发执行**——本任务对共享存储 IO 与 CPU 有较大占用，应串行执行避免争抢；
  - 支持手动触发（补跑 / 重跑指定仓或分支）；
  - 失败重试：脚本内自行控制（≤ 2 次）+ DolphinScheduler 任务级重试。

## 验收标准

- [ ] 插件以 `CommunityScan` 标识注册到 SeaTunnel Factory（`@AutoService(Factory.class)`），SeaTunnel job `.conf` 中可正常引用
- [ ] 输入行 schema 校验：`repoUrl / repoBranch / projectId / platform` 缺一即返回单列 `null` 错误行；`scanPath` 缺省视为整仓
- [ ] 输出 JSON 单列字段语义与 `ParseTestcaseTransform` 产出的 `TestCaseMetadata` 完全一致（同一张 Doris 表可承接）
- [ ] pytest / unittest / go test / gtest 四类框架对样例仓输出正确的逐用例明细（含 skip / 类 / 文件 / 行号）
- [ ] 纯静态执行：全过程不安装仓库依赖、不执行仓库代码、不 `import` 仓库模块；不调用任何外部命令
- [ ] 忽略目录与大小 / 链接 / 编码 / 截断防护生效；`not_synced`（共享存储中目录缺失）与 `path_invalid`（路径逃逸）走单列 null 错误行 + 日志前缀
- [ ] `FrameworkScanner` SPI 注册机制可用：新增框架仅需新增实现类 + `META-INF/services` 一行，**无需修改 transform 主类**
- [ ] 共享存储只读：插件运行期间不修改任何已落盘文件
- [ ] 单行扫描支持超时控制（`timeoutSeconds` 默认 1800s）；超时返回单列 null 错误行
- [ ] 下游 Doris Sink 写入按 `model.TestCaseMeasureData` 字段映射成功；JSON 解析失败回退单列 null

## 相关文档 / 参考插件

- **插件结构参考**：`openlibing-seatunnel-plugins/src/main/java/com/openlibing/transform/parsetestcase/`（`ParseTestcaseTransform` + `Factory` + `Options` + `plugins/TestCaseMetadataParser` + `model/`）
- **数据接入 API**：`spec/openlibing-sync/task_design/2026-04-01_IDE插件用户资源运营数据收集/` 中"统一数据接入能力"（`POST /api/data/ingest`、动态 Doris 写入）
- **已有定时采集框架**：参考 `spec/openlibing-sync/task_design/2026-04-01_IDE插件用户资源运营数据收集/`
- **Issues 采集的多 Token 限流与插件化架构**：参考 `spec/openlibing-sync/task_design/2026-4-14_issues数据采集/architecture.md`
- **用例收集扩展点**：`openlibing-pytest-executor` 的 `src/case_collector/`（`BaseCollector`、`CollectorFactory`）与 metadata XML schema（`frameType/repoUrl/repoBranch/testCases{name,level,type,className,filePath}`）
