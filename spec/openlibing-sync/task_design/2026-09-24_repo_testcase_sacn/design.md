# 设计方案：社区代码仓多框架用例全集静态扫描（SeaTunnel Transform 插件）

> **模块定位**：作为 `openlibing-seatunnel-plugins` 仓内的新 SeaTunnel Transform 插件，
> 包路径 `com.openlibing.transform.communityscan`（与 `parsetestcase` / `parsefilecoverage` 同级）。
> 输入 = 一行 SeaTunnel Row（含白名单 `repoUrl` / `projectId` / `repoBranch` / `scanPath` 字段），
> 输出 = 单列 JSON 字符串 `communityScanMeasureData`，描述该扫描单元命中的全量测试用例明细与汇总。

> **模块外部已完成**（本插件不感知、不调用）：
>
> 1. 代码仓**白名单设置**（YAML / JSON 配置，写入 Doris 表）；
> 2. 代码仓**下载 / 克隆**到本地挂载的共享存储（`<shared_root>/<platform>/<owner>/<repo>@<branch>/`）；
> 3. **代码分支切换**（已切到白名单要求的分支）。

## 1. 设计目标与关键决策

| # | 决策点 | 结论 |
|---|--------|------|
| 1 | 插件类型 | **SeaTunnel Transform**（同进程内算子），参考 `ParseTestcaseTransform` / `ParseFileCoverageTransform` |
| 1a | 仓库归属 | `openlibing-seatunnel-plugins` 仓 `com.openlibing.transform.communityscan` 包，与 `parsetestcase` / `parsefilecoverage` 同级 |
| 2 | 代码来源 | 插件**只读**本地挂载的共享存储；上游已落盘的目录为唯一输入；不下载、不克隆、不 `git fetch` |
| 3 | 解析方式 | **Java 纯静态解析**（不执行任何仓库代码）：Python / Java 用正则 + 简易 AST 节点匹配；Go 用正则匹配 `func TestXxx(*testing.T)` + 子测试；C/C++ 用跨行宏正则（容忍换行与宏嵌套） |
| 4 | 框架范围 | 本期：**pytest、unittest、go test、gtest**；后续补充 JUnit4/5、TestNG、Jest/Mocha/Vitest 等（仅需新增 `FrameworkScanner` SPI 实现 + `META-INF/services` 注册） |
| 5 | 数据粒度 | **逐用例明细 + 汇总**：明细 = `List<TestCaseMetadata>`；汇总 = `TestCaseMeasureData`（同时含明细数组与框架级计数） |
| 6 | 字段语义 | 明细字段 `frameType/repoUrl/repoBranch/caseFileName/caseFilePath/className/name/level/type` 与 `ParseTestcaseTransform` 产出的 `TestCaseMetadata` 完全对齐（**复用**其 `model.TestCaseMetadata` 类），便于后续把仓里定义了什么用例与流水线上报了什么执行结果做交叉分析 |
| 7 | 配置机制 | 复用 SeaTunnel `ReadonlyConfig` + `Options` + `OptionRule`，**不**使用 Spring `@ConfigurationProperties` |
| 8 | SPI 注册 | 通过 Java `ServiceLoader<FrameworkScanner>` + `META-INF/services/`，在 transform 启动时一次性加载（参考 `ParseFileCoverageTransform` 的 parser 初始化模式） |
| 9 | 输出 | **单列 JSON 字符串**（与 `ParseTestcaseTransform` 一致），下游 SeaTunnel Sink 负责写 Doris；本插件不直连数据库 |

### 1.1 与 `ParseTestcaseTransform` 的关系

两者职责严格区分：

- **`ParseTestcaseTransform`**：解析 CI 流水线**执行期**上报的测试用例 XML（OBS 拉取 → XML 解析 → `TestCaseMeasureData`）；覆盖 3 类 CI 平台（CodeArts / GitCode / GitHub）；输出 `testCaseMetadataList` + `testCaseResultList` 双数组。
- **`CommunityScanTransform`（本插件）**：解析代码仓**静态源码**中的测试用例定义（共享存储读盘 → 文件扫描 → 框架识别 → `TestCaseMeasureData`）；输出明细 + 框架级计数（`testCaseResultList` 为空数组）。

两者复用同一组 `model.TestCaseMetadata / TestCaseResult / TestCaseMeasureData`，保证下游 Doris 表 schema 兼容。本插件**不依赖** `ParseTestcaseTransform` 类，仅依赖其 `model` 包；两插件独立打包独立部署。

## 2. 包结构与文件清单

```
openlibing-seatunnel-plugins/
└── src/main/java/com/openlibing/transform/
    └── communityscan/                                  # 本插件包
        ├── CommunityScanTransform.java                # SeaTunnel Transform 主类（继承 AbstractCatalogSupportMapTransform）
        ├── CommunityScanTransformFactory.java         # @AutoService(Factory.class) 实现 TableTransformFactory
        ├── CommunityScanTransformOptions.java         # Options.key(...).stringType().xxx... 定义
        ├── FrameworkType.java                         # enum: PYTEST / UNITTEST / GOTEST / GTEST
        ├── README.md                                  # 插件配置示例（参考 parsetestcase README.md）
        ├── model/                                     # 复用 parsetestcase 已有的 model 类
        │   ├── TestCaseMeasureData.java               # 输出汇总（testCaseMetadataList + 框架级 counts）
        │   ├── TestCaseMetadata.java                  # 单条用例明细
        │   └── TestCaseResult.java                    # 占位（本插件不产出，预留字段对齐）
        ├── spi/                                       # 框架扫描器 SPI
        │   ├── FrameworkScanner.java                  # interface：framework() / filePatterns() / scan(repoRoot, file)
        │   └── TestCaseDescriptor.java                # 扫描器内使用的不可变 POJO（Java 16+ record）
        ├── scanner/                                   # 各框架实现（@AutoService 注册）
        │   ├── PytestScanner.java
        │   ├── UnittestScanner.java
        │   ├── GoTestScanner.java
        │   └── GtestScanner.java
        ├── plugins/                                   # 编排层（类似 parsetestcase/TestCaseMetadataParser）
        │   └── CommunityScanParser.java               # 主流程编排：白名单读盘 → FrameworkDetector → Scanner SPI 调度 → 输出
        ├── engine/                                    # 调度支撑
        │   ├── FrameworkDetector.java                 # 判定仓命中哪些 framework（置信度）
        │   └── FileWalker.java                        # 受限文件遍历（忽略目录 / 大小 / 链接防护）
        └── util/                                      # 工具
            ├── PathGuard.java                         # 共享存储路径安全校验（Path.normalize / .. 逃逸）
            └── SkipDirs.java                          # 全局忽略目录常量
└── src/main/resources/META-INF/services/
    └── com.openlibing.transform.communityscan.spi.FrameworkScanner
        ├── com.openlibing.transform.communityscan.scanner.PytestScanner
        ├── com.openlibing.transform.communityscan.scanner.UnittestScanner
        ├── com.openlibing.transform.communityscan.scanner.GoTestScanner
        └── com.openlibing.transform.communityscan.scanner.GtestScanner
```

## 3. Transform 主类（SeaTunnel 标准实现）

### 3.1 `CommunityScanTransform`

继承 `AbstractCatalogSupportMapTransform`，与 `ParseTestcaseTransform` 保持同款序列化约定（`serialVersionUID = 1L`）：

```java
@Slf4j
public class CommunityScanTransform extends AbstractCatalogSupportMapTransform {

    public static final String PLUGIN_NAME = "CommunityScan";

    private static final long serialVersionUID = 1L;

    private final String sharedRoot;        // 本地挂载的共享存储根
    private final String repoUrlField;      // 输入列：仓库 URL
    private final String repoBranchField;   // 输入列：仓库分支
    private final String scanPathField;     // 输入列：扫描子路径（"" = 整仓）
    private final String projectIdField;    // 输入列：归属项目
    private final String platformField;     // 输入列：gitcode / atomgit / github / gitlab / other
    private final String outputFieldName;   // 输出列名（默认 communityScanMeasureData）
    private final List<String> enabledFrameworks;  // 本任务启用的框架白名单
    private final int timeoutSeconds;       // 单行超时

    private transient CommunityScanParser parser;
    private transient SeaTunnelRowType inputSchema;

    public CommunityScanTransform(
            @NonNull ReadonlyConfig config, @NonNull CatalogTable catalogTable) {
        super(catalogTable);
        this.sharedRoot = config.get(CommunityScanTransformOptions.SHARED_ROOT);
        this.repoUrlField = config.get(CommunityScanTransformOptions.REPO_URL_FIELD);
        this.repoBranchField = config.get(CommunityScanTransformOptions.REPO_BRANCH_FIELD);
        this.scanPathField = config.get(CommunityScanTransformOptions.SCAN_PATH_FIELD);
        this.projectIdField = config.get(CommunityScanTransformOptions.PROJECT_ID_FIELD);
        this.platformField = config.get(CommunityScanTransformOptions.PLATFORM_FIELD);
        this.outputFieldName = config.get(CommunityScanTransformOptions.OUTPUT_FIELD_NAME);
        this.enabledFrameworks = config.get(CommunityScanTransformOptions.ENABLED_FRAMEWORKS);
        this.timeoutSeconds = config.get(CommunityScanTransformOptions.TIMEOUT_SECONDS);
    }

    @Override public String getPluginName() { return PLUGIN_NAME; }

    @Override public void open() {
        super.open();
        if (parser != null) { log.warn("open() called more than once"); return; }
        this.inputSchema = inputCatalogTable.getTableSchema().toPhysicalRowDataType();
        this.parser = new CommunityScanParser(sharedRoot, enabledFrameworks, timeoutSeconds);
        log.info("CommunityScanTransform opened: sharedRoot={}, enabledFrameworks={}, timeout={}s",
                sharedRoot, enabledFrameworks, timeoutSeconds);
    }

    @Override public void close() {
        if (parser != null) { try { parser.close(); } catch (Exception e) { log.warn("close failed", e); } parser = null; }
        super.close();
    }

    @Override
    protected SeaTunnelRow transformRow(SeaTunnelRow inputRow) {
        if (parser == null) {
            log.error("transformRow called before open() or after close(); returning error row");
            return createErrorRow(inputRow);
        }
        try {
            String repoUrl    = (String) readInputValue(inputRow, inputSchema, repoUrlField);
            String repoBranch = (String) readInputValue(inputRow, inputSchema, repoBranchField);
            String scanPath   = (String) readInputValue(inputRow, inputSchema, scanPathField);
            String projectId  = (String) readInputValue(inputRow, inputSchema, projectIdField);
            String platform   = (String) readInputValue(inputRow, inputSchema, platformField);

            if (repoUrl == null || repoBranch == null || projectId == null || platform == null) {
                log.error("Missing required fields: repoUrl={}, branch={}, projectId={}, platform={}",
                        repoUrl, repoBranch, projectId, platform);
                return createErrorRow(inputRow);
            }

            TestCaseMeasureData data = parser.scan(
                    ScanItem.of(platform, repoUrl, repoBranch, scanPath, projectId));

            Object[] out = new Object[] { JsonUtils.toJsonString(data) };
            SeaTunnelRow outRow = new SeaTunnelRow(out);
            copyRowMeta(inputRow, outRow);
            return outRow;
        } catch (NotSyncedException e) {
            log.warn("[not_synced] repo={} branch={} scanPath={}",
                    e.getRepoId(), e.getBranch(), e.getScanPath());
            return createErrorRow(inputRow);
        } catch (Exception e) {
            log.error("Error scanning repo for transform row", e);
            return createErrorRow(inputRow);
        }
    }

    private SeaTunnelRow createErrorRow(SeaTunnelRow inputRow) {
        SeaTunnelRow err = new SeaTunnelRow(new Object[] { null });
        copyRowMeta(inputRow, err);
        return err;
    }

    private void copyRowMeta(SeaTunnelRow src, SeaTunnelRow dst) {
        dst.setTableId(src.getTableId());
        dst.setRowKind(src.getRowKind());
        dst.setOptions(src.getOptions());
    }

    @Override protected TableSchema transformTableSchema() {
        return TableSchema.builder()
                .column(PhysicalColumn.builder().name(outputFieldName)
                        .dataType(BasicType.STRING_TYPE).build())
                .build();
    }

    @Override protected TableIdentifier transformTableIdentifier() {
        return inputCatalogTable.getTableId();
    }

    private Object readInputValue(SeaTunnelRow row, SeaTunnelRowType schema, String fieldName) {
        int idx = schema.indexOf(fieldName, false);
        if (idx == -1) { log.error("Field {} not found in input schema", fieldName); return null; }
        return row.getField(idx);
    }
}
```

### 3.2 `CommunityScanTransformFactory`

复用 `ParseTestcaseTransformFactory` 模式，`@AutoService(Factory.class)` 由 SeaTunnel 工厂加载机制发现：

```java
@AutoService(Factory.class)
public class CommunityScanTransformFactory implements TableTransformFactory {

    @Override public String factoryIdentifier() { return CommunityScanTransform.PLUGIN_NAME; }

    @Override public OptionRule optionRule() {
        return OptionRule.builder()
                .required(
                        CommunityScanTransformOptions.SHARED_ROOT,
                        CommunityScanTransformOptions.REPO_URL_FIELD,
                        CommunityScanTransformOptions.REPO_BRANCH_FIELD,
                        CommunityScanTransformOptions.PROJECT_ID_FIELD,
                        CommunityScanTransformOptions.PLATFORM_FIELD)
                .optional(
                        CommunityScanTransformOptions.SCAN_PATH_FIELD,
                        CommunityScanTransformOptions.OUTPUT_FIELD_NAME,
                        CommunityScanTransformOptions.ENABLED_FRAMEWORKS,
                        CommunityScanTransformOptions.TIMEOUT_SECONDS)
                .build();
    }

    @Override
    public <T> TableTransform<T> createTransform(TableTransformFactoryContext context) {
        return () -> (SeaTunnelTransform<T>) new CommunityScanTransform(
                context.getOptions(), context.getCatalogTables().get(0));
    }
}
```

### 3.3 `CommunityScanTransformOptions`

SeaTunnel 标准 `Options.key(...).stringType().xxx.withDescription(...)` 风格，参考 `ParseTestcaseTransformOptions`：

```java
public class CommunityScanTransformOptions {

    public static final Option<String> SHARED_ROOT =
        Options.key("sharedRoot")
            .stringType().noDefaultValue()
            .withDescription("本地挂载的共享存储根目录（如 /mnt/community_repos）。"
                    + "上游任务已在本目录下按 <platform>/<owner>/<repo>@<branch>/ 落盘代码仓。");

    public static final Option<String> REPO_URL_FIELD =
        Options.key("repoUrlField")
            .stringType().defaultValue("repoUrl")
            .withDescription("输入行中仓库 URL 字段名（默认 repoUrl）。");

    public static final Option<String> REPO_BRANCH_FIELD =
        Options.key("repoBranchField")
            .stringType().defaultValue("repoBranch")
            .withDescription("输入行中仓库分支字段名（默认 repoBranch）。");

    public static final Option<String> SCAN_PATH_FIELD =
        Options.key("scanPathField")
            .stringType().defaultValue("scanPath")
            .withDescription("输入行中扫描子路径字段名（默认 scanPath，'' = 整仓）。");

    public static final Option<String> PROJECT_ID_FIELD =
        Options.key("projectIdField")
            .stringType().defaultValue("projectId")
            .withDescription("输入行中项目 ID 字段名（默认 projectId），用于两级聚合。");

    public static final Option<String> PLATFORM_FIELD =
        Options.key("platformField")
            .stringType().defaultValue("platform")
            .withDescription("输入行中平台字段名（gitcode / atomgit / github / gitlab / other），用于共享存储子目录定位。");

    public static final Option<List<String>> ENABLED_FRAMEWORKS =
        Options.key("enabledFrameworks")
            .listType().defaultValue(List.of("pytest", "unittest", "gotest", "gtest"))
            .withDescription("本任务启用的框架白名单。默认启用全部本期框架。"
                    + "新增框架只需新增 SPI 实现 + 注册即可被启用，无需改 transform 代码。");

    public static final Option<Integer> TIMEOUT_SECONDS =
        Options.key("timeoutSeconds")
            .intType().defaultValue(1800)
            .withDescription("单行（单扫描单元）超时秒数。默认 1800 秒（30 分钟）。");

    public static final Option<String> OUTPUT_FIELD_NAME =
        Options.key("outputFieldName")
            .stringType().defaultValue("communityScanMeasureData")
            .withDescription("输出 JSON 列名（默认 communityScanMeasureData）。");
}
```

### 3.4 配置文件示例（`CommunityScan`）

```conf
transform {
    CommunityScan {
        sharedRoot      = "/mnt/community_repos"
        repoUrlField    = "repoUrl"
        repoBranchField = "repoBranch"
        scanPathField   = "scanPath"
        projectIdField  = "projectId"
        platformField   = "platform"
        enabledFrameworks = ["pytest", "unittest", "gotest", "gtest"]
        timeoutSeconds    = 1800
        outputFieldName   = "communityScanMeasureData"
    }
}
```

> **调用方**：上述 `.conf` 由 **DolphinScheduler 触发的 Java 扫描脚本**动态生成（每个扫描单元一份 job 配置），脚本再调用 SeaTunnel Java Client 提交。插件本身不感知调度平台。

## 4. 编排层 `CommunityScanParser`

职责等价于 `ParseTestcaseTransform` 中的 `TestCaseMetadataParser`：集中所有 IO + 编排 + 状态管理，transform 只做参数解析 / 行级错误处理。

```java
public class CommunityScanParser implements Closeable {

    private final Path sharedRoot;
    private final List<FrameworkScanner> scanners;        // ServiceLoader 一次性加载
    private final FileWalker walker;                     // 受限文件遍历
    private final FrameworkDetector detector;            // 框架置信度判定
    private final ExecutorService perRowPool;            // 单行超时控制
    private final int timeoutSeconds;

    public CommunityScanParser(String sharedRoot, List<String> enabled, int timeoutSeconds) {
        this.sharedRoot = Paths.get(sharedRoot);
        this.scanners = ServiceLoader.load(FrameworkScanner.class).stream()
                .map(ServiceLoader.Provider::get)
                .filter(s -> enabled.contains(s.framework()))
                .toList();
        this.walker = new FileWalker(SkipDirs.DEFAULTS);
        this.detector = new FrameworkDetector(scanners);
        this.perRowPool = Executors.newCachedThreadPool();
        this.timeoutSeconds = timeoutSeconds;
    }

    /** 单行扫描：定位共享存储 → 文件遍历 → 多 framework 解析 → 组装 MeasureData */
    public TestCaseMeasureData scan(ScanItem item) throws NotSyncedException, ScanException {
        Path repoRoot = PathGuard.resolve(sharedRoot, item);   // 共享存储定位
        Path scanRoot = PathGuard.resolveScanPath(repoRoot, item.scanPath());

        Future<List<TestCaseDescriptor>> future = perRowPool.submit(() -> {
            List<Path> files = walker.walk(scanRoot);          // 受限遍历
            Set<String> hitFrameworks = detector.detect(files); // 框架置信度
            List<TestCaseDescriptor> all = new ArrayList<>();
            for (FrameworkScanner s : scanners) {
                if (!hitFrameworks.contains(s.framework())) continue;
                for (Path f : files) {
                    if (s.accept(f)) all.addAll(s.scan(scanRoot, f));
                }
            }
            return all;
        });

        try {
            List<TestCaseDescriptor> descriptors = future.get(timeoutSeconds, TimeUnit.SECONDS);
            return buildMeasureData(item, descriptors);
        } catch (TimeoutException e) {
            future.cancel(true);
            throw new ScanException("scan timeout after " + timeoutSeconds + "s", e);
        } catch (Exception e) {
            throw new ScanException("scan failed", e);
        }
    }

    private TestCaseMeasureData buildMeasureData(ScanItem item, List<TestCaseDescriptor> descs) {
        List<TestCaseMetadata> metadataList = descs.stream()
                .map(d -> toTestCaseMetadata(item, d))
                .toList();
        // 复用 parsetestcase.model.TestCaseMeasureData（testCaseResultList 留空）
        return new TestCaseMeasureData(metadataList, Collections.emptyList());
    }

    private TestCaseMetadata toTestCaseMetadata(ScanItem item, TestCaseDescriptor d) {
        TestCaseMetadata m = new TestCaseMetadata();
        m.setRepoUrl(item.repoUrl());
        m.setRepoBranch(item.repoBranch());
        m.setFrameType(d.framework());
        m.setCaseFilePath(relativePath(d.filePath()));
        m.setCaseFileName(filename(d.filePath()));
        m.setClassName(d.className());
        m.setCaseNumber(d.name());
        m.setLevel("");      // 静态扫描不感知等级，保留空串
        m.setType(d.type()); // function / method
        m.setObsPath("");    // 本插件不产出 obs 路径
        m.setIsFlaky("false");
        return m;
    }

    @Override public void close() { perRowPool.shutdownNow(); }
}
```

## 5. 框架扫描器 SPI

### 5.1 `FrameworkScanner` 接口

```java
package com.openlibing.transform.communityscan.spi;

public interface FrameworkScanner {
    /** 框架标识，如 pytest / unittest / gotest / gtest */
    String framework();

    /** 候选文件 glob 模式（相对仓根） */
    List<String> filePatterns();

    /** 快速过滤：是否可能解析该文件（按扩展名 / 命名规则） */
    boolean accept(Path file);

    /** 对单个文件做纯静态解析，返回用例列表（纯静态，不执行任何外部命令 / 加载） */
    List<TestCaseDescriptor> scan(Path repoRoot, Path file) throws ScanException;

    /** FrameworkDetector 调用：按文件证据计算置信度 [0,1] */
    double confidence(Path file);
}
```

### 5.2 `TestCaseDescriptor`

```java
public record TestCaseDescriptor(
    String framework,        // pytest / unittest / gotest / gtest
    String name,             // test_xxx / TestXxx
    String className,        // TestDemo / 包名.类名
    String type,             // function / method
    Path filePath,           // 仓内相对路径
    int startLine,
    int endLine,
    boolean skipped,
    String skipReason,
    List<String> markers,    // @pytest.mark.* / tags
    boolean parametrized,
    Map<String, Object> extra
) {}
```

### 5.3 各框架识别规则

| 框架 | 文件候选 | 静态识别要点 | skip / 特征 |
|------|----------|--------------|-------------|
| pytest | `test_*.py`、`*_test.py`、`tests/**/*.py` | **Java 正则 + 缩进感知**：模块级 `^def test_\w+`；`^class Test\w+(\(\))?:` 块内同缩进的 `def test_\w+`；嵌套类递归 | `@pytest.mark.skip/skipif`、`pytest.skip()`；markers 收集全部 `@pytest.mark.*`；`@pytest.mark.parametrize` 字面量参数尽力展开，否则置 `parametrized=true` + 表达式 |
| unittest | 同上 | **Java 正则**：含 `unittest.TestCase` / 导入别名的类的 `def test_*` 方法 | `@skip/skipIf/skipUnless`、`self.skipTest()` |
| go test | `*_test.go` | 正则：`func TestXxx(t *testing.T)`；同函数体内 `t.Run("sub",...)` 作为子用例，full_name 拼为 `TestXxx/sub`；包名取 `package` 声明 | `t.Skip(...)` / `t.SkipNow()` |
| gtest | `*.cpp / *.cc / *.cxx / *.c++` 及头文件 | 宏正则（容忍换行/宏嵌套）：`TEST(suite, name)`、`TEST_F(fixture, name)`、`TEST_P(suite, name)`；`INSTANTIATE_TEST_SUITE_P/INSTANTIATE_TEST_CASE_P` 字面量列表按名展开 | `DISABLED_` 前缀视为 skipped；`GTEST_SKIP()` |

通用补充：

- 行号取正则匹配 span（Py/Java 用更精确的节点级行号）；
- pytest 与 unittest 同一文件同时命中时，**去重规则**：同一 `file_path + class_name + case_name` 只保留一条，优先保留更具体者（显式继承 `TestCase` → `unittest`，否则 `pytest`），冲突写 `extra.detected_by`；
- 无法解析的疑似测试文件（命中命名模式但语法错误 / 解码失败）不丢弃：计入 `Metadata.suspect_file_count` 等价字段，由下游 sink 决定是否落表。

## 6. 输入 / 输出契约

### 6.1 输入行 schema（上游 SeaTunnel Source / Doris Source）

| 字段名（默认） | 类型 | 必填 | 说明 |
|----------------|------|------|------|
| `repoUrl` | STRING | ✅ | 仓库 URL（与白名单表一致） |
| `repoBranch` | STRING | ✅ | 仓库分支 |
| `scanPath` | STRING | ❌ | 扫描子路径（`""` = 整仓） |
| `projectId` | STRING | ✅ | 归属项目 |
| `platform` | STRING | ✅ | gitcode / atomgit / github / gitlab / other |

### 6.2 输出 schema（单列 JSON）

```json
{
  "testCaseMetadataList": [
    {
      "caseFileName": "test_demo.py",
      "caseFilePath": "tests",
      "className": "TestDemo",
      "caseNumber": "test_demo_case",
      "level": "",
      "type": "method",
      "frameType": "pytest",
      "repoUrl": "https://...",
      "repoBranch": "main",
      "isFlaky": "false",
      "obsPath": ""
    }
  ],
  "testCaseResultList": []
}
```

> 字段全部对齐 `ParseTestcaseTransform` 的 `model.TestCaseMetadata`，下游 Sink 可共用同一张 Doris 表。

## 7. 与 DolphinScheduler 调度平台的集成方式

本插件是**离线批处理**算子，**不**内置 HTTP 接口 / 定时调度；调度由 **DolphinScheduler 调度平台 + Java 扫描脚本**触发。

### 7.1 调用链

```
DolphinScheduler (每日触发；具体时刻与上游代码同步任务编排对齐)
   │  定时触发
   ▼
扫描脚本 (Java, 部署在调度 worker, jar 形式运行)
   │  读 Doris: community_repo_whitelist (enabled=1)
   │  按 (repo, branch, scan_path, project_id, platform) 展开成 N 个扫描单元
   │  对每个扫描单元：
   │     ├─ 构造 SeaTunnel job 配置（内存 Source / Doris 单行 Source）
   │     ├─ 通过 SeaTunnel 客户端提交 job
   │     │     ┌────────────────────────────────────┐
   │     │     │ Source → CommunityScan → Doris Sink │
   │     │     │   (单扫描单元 JSON 单列输出)         │
   │     │     └────────────────────────────────────┘
   │     ├─ 解析 job 输出中的 communityScanMeasureData JSON
   │     ├─ 按 testCaseMetadataList 拆行写 Doris: community_testcase_detail
   │     └─ 回写白名单行 last_status / last_commit / last_scan_at
   ▼
Doris (community_repo_whitelist + community_testcase_detail + community_testcase_summary)
```

### 7.2 扫描脚本职责（由 DolphinScheduler 触发，Java 实现）

| 步骤 | 脚本内操作 |
|------|-----------|
| 1 | 从 Doris 读 `community_repo_whitelist`（`enabled=1`），生成待扫描单元列表 |
| 2 | 对每个扫描单元：构造 SeaTunnel job `.conf`，提交到 SeaTunnel 集群 |
| 3 | 等待 job 完成，**解析 job 输出**中的 `communityScanMeasureData` JSON 列 |
| 4 | 遍历 `testCaseMetadataList` 元素，写入 Doris `community_testcase_detail` |
| 5 | 按 `(repo_id, project_id, branch, framework)` 聚合，写入 Doris `community_testcase_summary` |
| 6 | 回写 `community_repo_whitelist` 行的 `last_status / last_commit / last_scan_at` |
| 7 | 失败重试 ≤ 2 次；连续 3 批失败告警（脚本退出码 + DolphinScheduler 告警通道） |

### 7.3 插件与脚本的契约

- **入参**：扫描单元的 5 个字段（`repoUrl / repoBranch / scanPath / projectId / platform`），由脚本注入 SeaTunnel Source；
- **出参**：插件产出**单列 JSON 字符串** `communityScanMeasureData`；脚本负责 JSON 解析 + 拆行 + 落 Doris。

### 7.4 扫描脚本实现（Java）

- **脚本与插件同仓同包**：作为 `openlibing-seatunnel-plugins` 仓内的 Java 类（包路径 `com.openlibing.transform.communityscan.scheduler`），与 transform 插件**复用同一份 jar**；
- **入口**：`CommunityScanJobRunner`（带 `public static void main(String[])`），DolphinScheduler Java 任务通过 `java -cp <jar> com.openlibing.transform.communityscan.scheduler.CommunityScanJobRunner [args]` 触发；
- **依赖**：SeaTunnel Java Client（提交 job）+ Doris JDBC（读 `community_repo_whitelist` + 写 `community_testcase_detail` / 回写白名单）；
- **复用插件**：脚本调 SeaTunnel Client 提交的 job 配置中包含本插件 `CommunityScan` transform，**不重复实现扫描逻辑**；
- **职责**：白名单展开 → 逐扫描单元提交 SeaTunnel job → 解析 JSON 单列 → 拆行写 Doris → 回写白名单状态。

### 7.5 与 `openlibing-sync` 仓的依赖

- **无直接依赖**：本插件 (`openlibing-seatunnel-plugins`) 与 `openlibing-sync` 是独立 Maven 工程，**不**新增跨仓依赖；
- Java 扫描脚本作为独立 jar 部署在 DolphinScheduler worker，**不**依赖 `openlibing-sync` 任何 jar；
- `community_repo_whitelist` 表由 `openlibing-sync` 既有管理端写入，扫描脚本只读不写。

## 8. 代码仓访问与安全防护

### 8.1 共享存储约定

本插件**不下载、不克隆**代码仓。所有扫描的代码根目录位于上游已落盘的共享存储：

```
<sharedRoot>/<platform>/<owner>/<repo>@<branch>/
```

- 同一 `(repo, branch)` 在共享存储中**有且仅有一份**目录；
- 私有仓的鉴权 / Token 处理全部在上游完成，本插件不接触任何凭证；
- 共享存储**只读挂载**，本插件不会修改其中任何内容。

### 8.2 路径安全（`PathGuard`）

```java
public final class PathGuard {
    /** 共享存储定位：<sharedRoot>/<platform>/<owner>/<repo>@<branch> */
    public static Path resolve(Path sharedRoot, ScanItem item) {
        return sharedRoot.resolve(item.platform())
                .resolve(item.owner())
                .resolve(item.repo() + "@" + item.branch());
    }

    /** scanPath 必须在 repoRoot 之下；禁 .. / 绝对路径 / 符号链接越界 */
    public static Path resolveScanPath(Path repoRoot, String scanPath) {
        if (!Files.exists(repoRoot)) {
            throw new NotSyncedException("shared storage missing: " + repoRoot);
        }
        Path base = (scanPath == null || scanPath.isEmpty() || "/".equals(scanPath))
                ? repoRoot : repoRoot.resolve(scanPath);
        Path normalized = base.toAbsolutePath().normalize();
        if (!normalized.startsWith(repoRoot.toAbsolutePath().normalize())) {
            throw new PathInvalidException("scan_path escapes root: " + scanPath);
        }
        return normalized;
    }
}
```

### 8.3 遍历与防护（`FileWalker` / `SkipDirs`）

- 遍历根目录 = `repoRoot / scanPath`；
- 全局忽略目录：`.git、.venv、venv、site-packages、node_modules、vendor、third_party、external、build、dist、target、out、__pycache__、.pytest_cache、generated、gen、cmake-build-*`；
- 单文件 > 1 MiB 跳过并计数；二进制 / 空文件按内容嗅探跳过；UTF-8 解码失败用 `errors="ignore"` 兜底；
- 单仓文件数上限 20000、扫描时长上限 = `timeoutSeconds`，超限截断；
- 符号链接不越出 `repoRoot`（`Path.normalize()` 后校验相对路径不含 `..`）；
- 纯静态：**不**调用任何外部命令 / 不 `import` 任何仓库模块 / 不执行 conftest/Makefile。

## 9. 错误处理

与 `ParseTestcaseTransform` 对齐：

- 任一必填字段为 `null` → 返回单列 `null` 错误行（`arity=1`），日志记录缺失字段；
- 共享存储中目录不存在 → 抛 `NotSyncedException`，transform 捕获后返回 `null` 错误行；日志带 `[not_synced]` 前缀；
- 路径逃逸 → 抛 `PathInvalidException`，transform 返回 `null` 错误行；
- 单行扫描超时 / 其他异常 → 返回 `null` 错误行，日志记录异常堆栈；
- 所有错误日志均携带 `[sharedRoot=xxx]` 前缀，便于多任务混用排障。

## 10. 本期不做（后续增强）

- 平台 API 枚举自动补全白名单（GitCode / AtomGit 组织级 OpenAPI）；
- JUnit4/5、TestNG、Jest/Mocha/Vitest、Rust 等框架扫描器（仅需新增 `FrameworkScanner` 实现 + 注册）；
- 重点仓在隔离沙箱内的动态 collect 复核；
- AI 异常用例识别；与 IDE 插件采集数据、流水线执行上报的交叉分析看板。
