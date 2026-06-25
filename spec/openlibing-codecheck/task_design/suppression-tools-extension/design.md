# suppression-tools-extension — 技术设计

## 方案概述

扩展现有 `SuppressionStrategy` 枚举 + 少量适配 `SuppressionScanServiceImpl`，新增 11 个工具的告警抑制注释识别能力，同时简化块级注释处理逻辑。

现有架构已通过枚举 + 正则模式良好抽象，9 个工具的抑制注释为代码内注释/注解/属性，可直接复用现有行扫描逻辑。3 个工具需要特殊处理：
- **typos**：通过 `_typos.toml` 配置文件抑制，无代码内注释，识别到配置文件即视为告警抑制。
- **gitleaks**：`gitleaks:allow` 可出现在行内任意位置（甚至非注释中），需跳过"嵌套在字符串/注释中则无效"校验。
- **PMD**：`@SuppressWarnings` 无法可靠归属到 PMD（Java 原生也用此语法），仅识别含 `"PMD"` 前缀的注解。

## 架构决策

1. **枚举 + 正则模式复用**：11 个工具中 9 个为代码内注释/注解/属性，直接复用现有 `SuppressionPattern` + `SuppressionType` 行扫描逻辑，新增枚举值即可。
2. **块级注释简化为只识别起始标记**：对所有工具（含已有的），不再区分行级/块级/文件级，全部按告警抑制处理，只返回注释/注解所在行。原 `BLOCK_PAIRED` 起始标记统一改为 `LINE`，移除 END 标记正则和中间代码块合并逻辑。committer 只关注存在告警抑制注释，不关注注释生效范围。
3. **`skipValidation` 字段**：`SuppressionPattern` 新增 `skipValidation` 布尔字段，`MatchResult` record 携带该标志。`scanAddedLines` 中根据 `matchResult.skipValidation()` 决定是否调用 `isInvalidSuppressionComment`。gitleaks 设为 `true`。
4. **多工具匹配返回 List**：`identifyToolAndType` 改为 `identifyAllToolsAndTypes`，返回 `List<MatchResult>`。同一工具多 pattern 命中只取第一个（避免重复计数），不同工具全部返回。coderepo 在生成评论时把识别到的多个工具都写上。
5. **typos 配置文件检测**：在 `processDiffFile` 和 `processCompareFile` 解析出 `filePath` 后、行扫描前，用 `TYPOS_CONFIG_PATTERN` 匹配文件路径，命中则直接生成 `FILE` 类型结果返回。
6. **detect-secrets 精确匹配 6 种注释前缀**：按官方文档精确匹配 `#`、`//`、`/*...*/`、`'`、`--`、`<!-- ... -->`，不使用模糊匹配。
7. **CodeQL 按汇总表修正**：支持 `// lgtm`、`# lgtm`、`// codeql [rule]` 行级语法。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/enums/SuppressionStrategy.java` | 修改 | 新增 11 个工具枚举；`SuppressionPattern` 新增 `skipValidation`；`MatchResult` record 新增 `skipValidation`；新增 `identifyAllToolsAndTypes` |
| `business/service/impl/SuppressionScanServiceImpl.java` | 修改 | 新增 typos 配置文件检测；`scanAddedLines` 支持 `skipValidation` 和多工具结果；移除块级处理逻辑 |

## 各工具识别规则设计

### typos（配置文件型）

不识别代码内注释，通过文件路径检测 `_typos.toml` / `typos.toml`。

### detect-secrets（行级，多注释风格）

语法：`pragma: allowlist secret` / `pragma: allowlist nextline secret`，精确匹配 6 种注释前缀：`#`、`//`、`/*...*/`、`'`、`--`、`<!-- ... -->`。

```java
new SuppressionPattern(
    "(?:#|//|--|')\\s*pragma:\\s*allowlist(?:\\s+nextline)?\\s+secret"
    + "|/\\*\\s*pragma:\\s*allowlist(?:\\s+nextline)?\\s+secret\\s*\\*/"
    + "|<!--\\s*pragma:\\s*allowlist(?:\\s+nextline)?\\s+secret\\s*-->",
    SuppressionType.LINE)
```

### gitleaks（行级，任意位置）

语法：`gitleaks:allow`，本行包含该子串即可，甚至可以不在注释中。`skipValidation=true` 跳过嵌套校验。

```java
new SuppressionPattern("gitleaks:allow", SuppressionType.LINE, true)
```

### pylint（行级 / 文件级）

语法：
- 行级：`# pylint: disable=rule1, rule2`、`# pylint: disable-next=<msg>`
- 文件级：`# pylint: skip-file`（文件顶部）

按设计只识别起始标记，不识别 `enable`。

```java
new SuppressionPattern("#\\s*pylint:\\s*disable-next\\s*=\\s*\\S+", SuppressionType.LINE),
new SuppressionPattern("#\\s*pylint:\\s*disable\\s*=\\s*[\\w,\\s\\-]+", SuppressionType.LINE),
new SuppressionPattern("#\\s*pylint:\\s*skip-file", SuppressionType.FILE_TOP)
```

### Bandit（行级）

语法：`# nosec`、`# nosec rule1, rule2`

```java
new SuppressionPattern("#\\s*nosec(?:\\s+\\S+(?:\\s*,\\s*\\S+)*)?", SuppressionType.LINE)
```

### checkstyle（行级 + 块级起始）

语法：
- 行级：`// SUPPRESS CHECKSTYLE rule`、`// SUPPRESS CHECKSTYLE ALL`
- 块级起始：`//CHECKSTYLE:OFF`（按设计只识别起始标记）

```java
new SuppressionPattern("//\\s*SUPPRESS\\s+CHECKSTYLE(?:\\s+\\S+)?", SuppressionType.LINE),
new SuppressionPattern("//\\s*CHECKSTYLE:OFF", SuppressionType.LINE)
```

### PMD（行级，注释 + 注解）

语法：
- 注释：`// NOPMD - explanation`
- 注解：`@SuppressWarnings("PMD")`、`@SuppressWarnings("PMD.RuleName")`

注解型仅匹配含 `"PMD"` 前缀的 `@SuppressWarnings`，避免与 Java 原生冲突。

```java
new SuppressionPattern("//\\s*NOPMD(?:\\s.*)?", SuppressionType.LINE),
new SuppressionPattern("@SuppressWarnings\\s*\\(\\s*\\{?\\s*\"PMD(?:\\.\\w+)?\"", SuppressionType.LINE)
```

### SpotBugs（行级，注解）

语法：`@SuppressFBWarnings("rule")`、`@SuppressFBWarnings(value = {"rule1", "rule2"}, justification = "...")`

```java
new SuppressionPattern("@SuppressFBWarnings\\s*\\([^)]*\\)", SuppressionType.LINE)
```

### spotless（块级起始）

语法：`// spotless:off`（按设计只识别起始标记）

```java
new SuppressionPattern("//\\s*spotless:off", SuppressionType.LINE)
```

### rustfmt（行级 / 块级 / 文件级，Rust 属性）

语法：
- 行级：`#[rustfmt::skip]`、`#[cfg_attr(any(), rustfmt::skip)]`
- 块级：`#[rustfmt::skip]`（放在函数/结构体前）、`#[rustfmt::skip::macros(name)]`
- 文件级：`#![rustfmt::skip]`、`#![rustfmt::skip::macros(name)]`

```java
new SuppressionPattern(
    "#!\\[rustfmt::skip(?:\\s*::\\s*(?:macros|attributes)\\s*\\([^)]*\\))?\\s*\\]",
    SuppressionType.FILE_TOP),
new SuppressionPattern(
    "#\\[rustfmt::skip(?:\\s*::\\s*(?:macros|attributes)\\s*\\([^)]*\\))?\\s*\\]",
    SuppressionType.LINE_OR_BLOCK_UNPAIRED),
new SuppressionPattern("#\\[cfg_attr\\([^)]*rustfmt::skip[^)]*\\)\\]", SuppressionType.LINE)
```

`#![` 为文件级内部属性，`#[` 为行级/块级外部属性。

### clippy（行级 / 块级 / 文件级，Rust 属性）

语法：
- 行级：`#[allow(clippy::<rule>)]`、`#[expect(clippy::<rule>)]`
- 文件级：`#![allow(clippy::<rule>)]`、`#![expect(clippy::<rule>)]`

```java
new SuppressionPattern(
    "#!\\[(?:allow|expect)\\s*\\(\\s*clippy::\\w+\\s*\\)\\s*\\]",
    SuppressionType.FILE_TOP),
new SuppressionPattern(
    "#\\[(?:allow|expect)\\s*\\(\\s*clippy::\\w+\\s*\\)\\s*\\]",
    SuppressionType.LINE_OR_BLOCK_UNPAIRED)
```

## 核心改动点

### 1. `SuppressionPattern` 内部类扩展（新增 `skipValidation` 字段）

```java
@Getter
public static class SuppressionPattern {
    private final String regex;
    private final SuppressionType type;
    private final Pattern compiledPattern;
    private final boolean skipValidation;  // 新增

    public SuppressionPattern(String regex, SuppressionType type) {
        this(regex, type, false);
    }

    public SuppressionPattern(String regex, SuppressionType type, boolean skipValidation) {
        this.regex = regex;
        this.type = type;
        this.compiledPattern = Pattern.compile(regex);
        this.skipValidation = skipValidation;
    }
}
```

### 2. `MatchResult` record 扩展

```java
public record MatchResult(String toolName, SuppressionType type, boolean skipValidation) {
    // 兼容旧调用
    public MatchResult(String toolName, SuppressionType type) {
        this(toolName, type, false);
    }
}
```

### 3. `identifyAllToolsAndTypes` 方法（返回多工具匹配结果）

```java
public static List<MatchResult> identifyAllToolsAndTypes(String matchedText) {
    List<MatchResult> results = new ArrayList<>();
    for (SuppressionStrategy strategy : values()) {
        // 同一工具只取第一个匹配的 pattern，避免同一工具因多 pattern 命中而重复返回
        for (SuppressionPattern pattern : strategy.getPatterns()) {
            if (pattern.getCompiledPattern().matcher(matchedText).find()) {
                results.add(new MatchResult(strategy.getToolName(), pattern.getType(),
                        pattern.isSkipValidation()));
                break;
            }
        }
    }
    if (results.isEmpty()) {
        results.add(new MatchResult("unknown", SuppressionType.LINE, false));
    }
    return results;
}
```

### 4. typos 配置文件检测（`SuppressionScanServiceImpl`）

```java
private static final Pattern TYPOS_CONFIG_PATTERN =
        Pattern.compile("(^|/)_?typos\\.toml$", Pattern.CASE_INSENSITIVE);

private boolean isTyposConfigFile(String filePath) {
    if (StringUtils.isBlank(filePath)) {
        return false;
    }
    return TYPOS_CONFIG_PATTERN.matcher(filePath).find();
}

private SuppressionScanResult buildTyposResult(String filePath) {
    SuppressionScanResult result = new SuppressionScanResult();
    result.setFilePath(filePath);
    result.setLineNumber(1);
    result.setToolName("typos");
    result.setSuppressionType(SuppressionStrategy.SuppressionType.FILE.getCode());
    result.setCodeSnippet("1: # typos 配置文件，可能包含拼写告警抑制配置");
    return result;
}
```

在 `processDiffFile` 和 `processCompareFile` 解析出 `filePath` 后、行扫描前插入：

```java
if (isTyposConfigFile(filePath)) {
    results.add(buildTyposResult(filePath));
    return;
}
```

### 5. `scanAddedLines` 方法调整（支持 `skipValidation` 和多工具结果）

```java
List<SuppressionStrategy.MatchResult> matchResults =
        SuppressionStrategy.identifyAllToolsAndTypes(matchedText);

// 判断是否需要跳过嵌套校验（gitleaks 等可出现在任意位置的工具）
boolean anySkipValidation = matchResults.stream()
        .anyMatch(SuppressionStrategy.MatchResult::skipValidation);
if (!anySkipValidation
        && isInvalidSuppressionComment(codeLine, suppressionMatcher.start(), suppressionMatcher.end())) {
    continue;
}

// 按设计：不再区分行级/块级/文件级，全部按告警抑制处理，只返回注释所在行（含上下文）
String codeSnippet = extractSimpleCodeSnippet(ctx.addedLines(), ctx.addedLineNumbers(),
        i, matchedText);
for (SuppressionStrategy.MatchResult matchResult : matchResults) {
    SuppressionScanResult result = new SuppressionScanResult();
    result.setFilePath(ctx.filePath());
    result.setLineNumber(lineNumber);
    result.setCodeSnippet(codeSnippet);
    result.setToolName(matchResult.toolName());
    result.setSuppressionType(matchResult.type().getCode());
    ctx.results().add(result);
}
```

## 数据模型设计

不涉及

## 性能设计

不涉及

## API 接口设计

不涉及

## 安全设计

不涉及
