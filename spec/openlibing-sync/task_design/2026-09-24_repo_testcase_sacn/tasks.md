# 实现任务清单：社区代码仓多框架用例全集扫描（SeaTunnel Transform 插件）

> 对应设计：`design.md`；需求：`proposal.md`。
> 插件位置：`openlibing-seatunnel-plugins/src/main/java/com/openlibing/transform/communityscan/`
> 参考插件：`com.openlibing.transform.parsetestcase.*` / `com.openlibing.transform.parsefilecoverage.*`
> 调度：**DolphinScheduler** 定时任务管理平台 + **Java 扫描脚本**（独立 jar，部署在调度 worker）

## 阶段 0：原型验证（先行，降低技术风险）

- [ ] 用 2~3 个真实社区仓（Python / Go / C++ 各一）验证四类静态识别规则可行
  - [ ] pytest / unittest：Java 正则 + 缩进感知识别 `def test_*` / `class Test*`、markers、skip、parametrize 字面量展开
  - [ ] go test：`func TestXxx` + `t.Run` 子测试、package namespace
  - [ ] gtest：跨行宏正则 `TEST/TEST_F/TEST_P`、`DISABLED_`、`INSTANTIATE_*` 字面量展开
- [ ] 输出 `TestCaseDescriptor` Java `record` 原型，校验字段与 `model.TestCaseMetadata` 字段映射
- [ ] 输出一页《静态识别已知缺口》（表驱动、跨文件继承、宏包装等），确认验收口径

## 阶段 1：插件骨架与 SPI 定义

- [ ] 新建 `com.openlibing.transform.communityscan` 包及子目录（`model` / `spi` / `scanner` / `plugins` / `engine` / `util`）
- [ ] 新增 `FrameworkType.java`：enum `PYTEST / UNITTEST / GOTEST / GTEST`
- [ ] 新增 `spi/FrameworkScanner.java`：interface（`framework() / filePatterns() / accept(file) / scan(repoRoot, file) / confidence(file)`）
- [ ] 新增 `spi/TestCaseDescriptor.java`：Java 16+ record
- [ ] 新增 `META-INF/services/com.openlibing.transform.communityscan.spi.FrameworkScanner`（先空文件，待阶段 4 填充）
- [ ] `model/` 下引用 / 复用 `parsetestcase.model.TestCaseMetadata / TestCaseMeasureData / TestCaseResult`
- [ ] 单元测试：SPI 接口契约（reflection 验证实现类含 `@AutoService` / `framework()` 唯一性 / `accept` 单调性）

## 阶段 2：Transform 主类与配置（参考 `ParseTestcaseTransform`）

- [ ] 新增 `CommunityScanTransformOptions.java`：9 个 `Options.key(...).xxx.withDescription(...)` 常量
  - required：`sharedRoot / repoUrlField / repoBranchField / projectIdField / platformField`
  - optional：`scanPathField / outputFieldName / enabledFrameworks(List<String>) / timeoutSeconds`
- [ ] 新增 `CommunityScanTransformFactory.java`：`@AutoService(Factory.class)` + `factoryIdentifier() + optionRule() + createTransform()`
- [ ] 新增 `CommunityScanTransform.java`：继承 `AbstractCatalogSupportMapTransform`
  - 构造函数注入 9 个配置项 + 持有 `transient CommunityScanParser parser` / `transient SeaTunnelRowType inputSchema`
  - `open()`：初始化 parser + 记录启动日志（`sharedRoot / enabledFrameworks / timeout`）
  - `close()`：关闭 parser（释放线程池 / IO 资源）
  - `transformRow()`：读 5 个必填字段 → 校验 → `parser.scan(ScanItem.of(...))` → 包装成单列 JSON → `copyRowMeta`
  - 异常分支：`NotSyncedException` / `PathInvalidException` / 其他 → 返回单列 null 错误行 + 日志
  - `transformTableSchema()`：输出 schema = `{outputFieldName: STRING}`
  - `transformTableIdentifier()`：保留输入 table id
  - `serialVersionUID = 1L`（SeaTunnel Hazelcast 集群序列化兼容，与 `ParseTestcaseTransform` 同约定）
- [ ] 新增 `CommunityScanTransform` 单元测试
  - [ ] 必填字段缺失 → 单列 null 错误行
  - [ ] 共享存储目录不存在 → 日志 `[not_synced]` + 单列 null 错误行
  - [ ] 路径逃逸 → 日志 `[path_invalid]` + 单列 null 错误行
  - [ ] 正常扫描 → 单列 JSON（`testCaseMetadataList` 数组非空 / `testCaseResultList` 为空）
  - [ ] `open()` 多次调用幂等

## 阶段 3：编排层 `CommunityScanParser`（参考 `TestCaseMetadataParser`）

- [ ] 新增 `plugins/CommunityScanParser.java implements Closeable`
  - 构造函数：`ServiceLoader.load(FrameworkScanner.class)` + 按 `enabledFrameworks` 过滤 + 创建 `FileWalker` / `FrameworkDetector` / `perRowPool`（`Executors.newCachedThreadPool`）
  - `scan(ScanItem)` 方法：定位共享存储 → 提交线程池 → `Future.get(timeoutSeconds, SECONDS)` → 超时 `future.cancel(true)` → `buildMeasureData` → 返回 `TestCaseMeasureData`
  - `toTestCaseMetadata(ScanItem, TestCaseDescriptor)`：把内部 record 映射成 `model.TestCaseMetadata`，字段对齐 `ParseTestcaseTransform` 输出
  - `close()`：线程池 `shutdownNow`
- [ ] 新增 `util/ScanItem.java`：record（`platform / owner / repo / branch / scanPath / repoUrl / projectId`）
- [ ] 新增 `engine/FrameworkDetector.java`：扫描候选文件，按各 scanner 的 `confidence(file)` 加权，阈值（默认 0.5）以上视为命中
- [ ] 新增 `engine/FileWalker.java` + `util/SkipDirs.java`：受限遍历
  - 跳过 `SkipDirs.DEFAULTS`（`.git / vendor / node_modules / ...`）
  - 单文件 > 1 MiB 跳过 + 计数
  - 二进制 / 空文件嗅探跳过
  - UTF-8 解码失败 `errors="ignore"` 兜底
  - 文件数上限 20000 + 链接越界校验
- [ ] 新增 `util/PathGuard.java`：
  - `resolve(sharedRoot, item)` → `<sharedRoot>/<platform>/<owner>/<repo>@<branch>`
  - `resolveScanPath(repoRoot, scanPath)` → 路径逃逸校验 + 不存在抛 `NotSyncedException`
- [ ] 单元测试：`CommunityScanParser` 全链路（mock `FrameworkScanner` SPI）
  - [ ] 多 framework 命中同一文件，去重规则生效
  - [ ] 单文件超时 → 抛 `ScanException` + cancel 线程
  - [ ] 路径逃逸 / 不存在目录
  - [ ] `TestCaseMetadata` 字段映射（与 `ParseTestcaseTransform` 输出一致）

## 阶段 4：四框架扫描器实现

- [ ] `scanner/PytestScanner implements FrameworkScanner`
  - `framework() = "pytest"`
  - `filePatterns = ["** /test_*.py", "** /*_test.py", "** /tests/**/*.py"]`
  - `accept(file)`：扩展名 `.py` + 名称匹配 `test_*.py` / `*_test.py` / `tests/**/*.py`
  - `scan(repoRoot, file)`：Java 正则 + 缩进感知
    - 模块级 `^def test_\w+`
    - `^class Test\w+(\(\))?:` 块内同缩进 `def test_\w+`
    - 嵌套类递归（同缩进规则）
  - markers：收集 `@pytest.mark.*`、`@pytest.mark.skip / skipif`、`pytest.skip()` 调用
  - `parametrize` 字面量展开，否则 `parametrized=true + extra.param_expr`
- [ ] `scanner/UnittestScanner implements FrameworkScanner`
  - `framework() = "unittest"`
  - 同文件候选
  - 识别 `import unittest` / 别名 + 含 `TestCase` 的类的 `def test_*` 方法
  - skip：`@skip / skipIf / skipUnless`、`self.skipTest()`
- [ ] pytest + unittest 同文件去重规则：`file_path + class_name + case_name` 相同只保留一条，优先 unittest；冲突写 `extra.detected_by`
- [ ] `scanner/GoTestScanner implements FrameworkScanner`
  - `framework() = "gotest"`
  - `accept`：扩展名 `.go` + `*_test.go`
  - `scan`：正则 `func Test\w+\(\w+ \*testing\.T?B?\)`，函数体内 `t.Run("name", ...)` 子用例 → full_name 拼 `TestXxx/sub`
  - namespace：`package xxx` 声明
  - skip：`t.Skip(...)` / `t.SkipNow()`
  - 表驱动用例（`tests := []struct{...}`）不展开，置 `parametrized=true`
- [ ] `scanner/GtestScanner implements FrameworkScanner`
  - `framework() = "gtest"`
  - `accept`：扩展名 `.cpp/.cc/.cxx/.c++/.h/.hpp`
  - `scan`：跨行宏正则（容忍换行 + 宏嵌套）
    - `TEST(suite, name)` / `TEST_F(fixture, name)` / `TEST_P(suite, name)`
    - `INSTANTIATE_TEST_SUITE_P / INSTANTIATE_TEST_CASE_P`：字面量列表按名展开
  - skip：`DISABLED_` 前缀、`GTEST_SKIP()`
- [ ] 填充 `META-INF/services/com.openlibing.transform.communityscan.spi.FrameworkScanner`：注册上述 4 个 scanner 全限定类名
- [ ] 单元测试（每框架）：
  - [ ] 正样本：模块级 / 类内 / 嵌套类 / 子测试 / skip / parametrize / DISABLED_ 等典型用例
  - [ ] 反样本：非测试文件、空文件、UTF-8 异常、二进制文件、巨大文件（>1 MiB）
  - [ ] 跨框架冲突（pytest + unittest 同文件）→ 去重规则
  - [ ] 边界：参数化表驱动 / 宏包装 / 跨行宏

## 阶段 5：DolphinScheduler 集成与 Java 扫描脚本

- [ ] 在 `openlibing-seatunnel-plugins` 仓新增 `com.openlibing.transform.communityscan.scheduler` 包，与 transform 插件同仓同 jar
- [ ] 新增 `CommunityScanJobRunner`（`public static void main`，DolphinScheduler Java 任务入口）
  - 读 Doris `community_repo_whitelist`（`enabled=1`），按 `(repo, branch, scan_path, project_id, platform)` 展开成 N 个扫描单元
  - 对每个扫描单元：构造 SeaTunnel `.conf`（内存 Source 注入 5 个字段）→ 调 **SeaTunnel Java Client** 提交 → 等待完成 → 解析 JSON 单列
  - 遍历 `testCaseMetadataList` 元素，写 Doris `community_testcase_detail`
  - 按 `(repo_id, project_id, branch, framework)` 聚合写 Doris `community_testcase_summary`
  - 回写 `community_repo_whitelist` 行的 `last_status / last_commit / last_scan_at`
  - 失败重试 ≤ 2 次；连续 3 批失败告警（脚本退出码 → DolphinScheduler 告警通道）
- [ ] 提供 SeaTunnel `.conf` 模板（含 Source / Transform / Sink 完整配置，参数化注入扫描单元字段）
- [ ] 在 DolphinScheduler 上注册调度任务
  - 类型：**Java 任务**（通过 `-cp <jar> com.openlibing.transform.communityscan.scheduler.CommunityScanJobRunner` 触发）
  - **调度周期：每日一次**（具体时刻留待 DolphinScheduler 任务编排时决定）
  - **调度约束**（在 DolphinScheduler 上配置任务依赖关系时落实）：
    1. **必须在"代码同步任务"执行完成后才启动**（上游 Upstream 任务 → 本扫描任务，单向 DAG 依赖）；
    2. **不与其他代码仓相关任务并发执行**（独占 worker / 串行队列，避免争抢共享存储 IO 与 CPU）；
  - 手动补跑：参数化 `--repo <repo_url> --branch <branch>` 支持单仓补跑
- [ ] 提供 Doris Source 的 `community_repo_whitelist` 建表 SQL（沿用既有管理表 + 增加 `scan_paths / extra_branches / last_*` 字段）
- [ ] 提供 Doris Sink 的 `community_testcase_detail` / `community_testcase_summary` 建表 SQL（字段与 `model.TestCaseMetadata` 一一对应）
- [ ] 告警通道：DolphinScheduler 告警 + 脚本退出码 → 钉钉 / 邮件（沿用项目现有告警通道）

## 阶段 6：扫描配置（增量跳过 + 周期全量校准）

- [ ] 在 `community_repo_whitelist` 表加 `last_commit / last_scan_at / last_status` 字段
- [ ] Doris Source 增量读取：`last_commit` 未变 + 非强制周 → 工作项记 `status=unchanged`（跳过详情写入）
- [ ] 每周一次（`force_full_every_days=7`）强制全量批次（扫描脚本传 `--full` 参数，Source 忽略 `last_commit`）
- [ ] 失败状态：`scan_failed / not_synced / path_invalid` 三态分别打标 + 告警
- [ ] scanner_version 写入明细（用于口径漂移评审）

## 阶段 7：监控与告警

- [ ] 复用 SeaTunnel 现有 metrics 暴露（`SeaTunnelRow` 处理耗时、错误行计数）
- [ ] 业务级埋点（自定义 metrics）
  - `community_scan_row_total{framework, status}`（success / not_synced / path_invalid / failed）
  - `community_scan_testcase_total{framework}` / `..._skipped_total` / `..._suspect_file_total`
  - `community_scan_duration_seconds{framework}`
- [ ] 告警规则：连续 3 批单仓失败；批次成功率 < 80%（含 not_synced 占比）；JVM 堆 > 80%；`suspect_file_count` 突增
- [ ] Grafana 看板：白名单覆盖率 / 各框架用例数趋势 / skip 率 / 失败仓清单 / suspect 文件清单

## 阶段 8：灰度与上线

- [ ] 灰度：白名单录入 2 个仓（Python / C++ 混合），dry-run 核对 JSON 输出格式
- [ ] 验证多框架场景：①单仓单框架；②单仓多框架（Python 仓 pytest + unittest 混用）；③C++ 仓 gtest 多文件
- [ ] 跑通 SeaTunnel job：Source → `CommunityScan` Transform → Doris Sink 全链路
- [ ] 字段映射核对：sink 写入 `community_testcase_detail` 的字段值与上游白名单字段一致
- [ ] 连续运行 1~2 周（含至少 1 次强制全量批次），评审准确率 / 耗时 / 容量，调整并发与截断阈值
- [ ] 更新 `openlibing-seatunnel-plugins` README 与 `openlibing-sync` 调度 SOP

## 验收对照（proposal 验收标准 → 任务）

| 验收项                                           | 关联任务                           |
| ------------------------------------------------ | ---------------------------------- |
| SeaTunnel Factory 可识别插件标识 `CommunityScan` | 阶段 2                             |
| 输入行 schema 校验 + null 错误行                 | 阶段 2、3                          |
| 输出 JSON 字段与 `ParseTestcaseTransform` 一致   | 阶段 1（复用 model）、3            |
| 四框架逐用例明细正确                             | 阶段 0、4                          |
| 纯静态、无代码执行                               | 阶段 3（engine/util）、4           |
| not_synced / path_invalid 走单列 null + 日志前缀 | 阶段 2、3                          |
| SPI 注册机制可用（新增框架不改 transform）       | 阶段 1、4                          |
| 共享存储只读                                     | 阶段 3（util/PathGuard）           |
| 单行超时控制                                     | 阶段 2（Options）、3（perRowPool） |
| Doris Sink 写入字段映射成功                      | 阶段 5                             |

## 后续可选增强（不在本期范围）

- 平台 API 枚举自动补全白名单：GitCode / AtomGit 组织级全量枚举 → 候选仓自动进入白名单待启用
- JUnit4/5、TestNG、Jest/Mocha/Vitest、Rust 等新扫描器（仅需实现 `FrameworkScanner` SPI 并注册）
- 重点仓在强隔离沙箱中的动态 collect 复核（静态为主 + 动态兜底两阶段）
- 全分支 / MR 级扫描；跨文件基类继承与宏包装的更深静态推断
- AI 可疑用例识别；与 IDE 插件采集、流水线执行上报（复用 `model.TestCaseMetadata` 对齐字段）交叉分析
