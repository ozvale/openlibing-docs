# suppression-tools-extension — 技术设计

## 方案概述

扩展现有 `SuppressionStrategy` 枚举 + 少量适配 `SuppressionScanServiceImpl`，新增 10 个工具的告警抑制注释识别能力，同时简化块级注释处理逻辑。

现有架构已通过枚举 + 正则模式良好抽象，9 个工具的抑制注释为代码内注释/注解/属性，可直接复用现有行扫描逻辑。2 个工具需要特殊处理：
- **gitleaks**：`gitleaks:allow` 可出现在行内任意位置（甚至非注释中），需跳过"嵌套在字符串/注释中则无效"校验。
- **PMD**：`@SuppressWarnings` 无法可靠归属到 PMD（Java 原生也用此语法），仅识别含 `"PMD"` 前缀的注解。

## 架构决策

1. **枚举 + 正则模式复用**：10 个工具中 9 个为代码内注释/注解/属性，直接复用现有 `SuppressionPattern` + `SuppressionType` 行扫描逻辑，新增枚举值即可。
2. **块级注释简化为只识别起始标记**：对所有工具（含已有的），不再区分行级/块级/文件级，全部按告警抑制处理，只返回注释/注解所在行。原 `BLOCK_PAIRED` 起始标记统一改为 `LINE`，移除 END 标记正则和中间代码块合并逻辑。committer 只关注存在告警抑制注释，不关注注释生效范围。
3. **`skipValidation` 字段**：`SuppressionPattern` 新增 `skipValidation` 布尔字段，`MatchResult` record 携带该标志。`scanAddedLines` 中根据 `matchResult.skipValidation()` 决定是否调用 `isInvalidSuppressionComment`。gitleaks 设为 `true`。
4. **多工具匹配返回 List**：`identifyToolAndType` 改为 `identifyAllToolsAndTypes`，返回 `List<MatchResult>`。同一工具多 pattern 命中只取第一个（避免重复计数），不同工具全部返回。coderepo 在生成评论时把识别到的多个工具都写上。
5. **detect-secrets 精确匹配 6 种注释前缀**：按官方文档精确匹配 `#`、`//`、`/*...*/`、`'`、`--`、`<!-- ... -->`，不使用模糊匹配。
6. **CodeQL 按汇总表修正**：支持 `// lgtm`、`# lgtm`、`// codeql [rule]` 行级语法。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/enums/SuppressionStrategy.java` | 修改 | 新增 10 个工具枚举；`SuppressionPattern` 新增 `skipValidation`；`MatchResult` record 新增 `skipValidation`；新增 `identifyAllToolsAndTypes` |
| `business/service/impl/SuppressionScanServiceImpl.java` | 修改 | `scanAddedLines` 支持 `skipValidation` 和多工具结果；移除块级处理逻辑 |

## 各工具识别规则设计

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

### checkstyle（行级 + 块级起始，纯文本匹配）

语法：
- 行级：`// SUPPRESS CHECKSTYLE rule`、`// SUPPRESS CHECKSTYLE ALL`
- 块级起始：`// CHECKSTYLE:OFF LineLength`（按设计只识别起始标记 OFF，不识别结束标记 ON，与 CLANG_FORMAT/SPOTLESS 等工具一致；支持规则名）

checkstyle 的 `SuppressWithPlainTextCommentFilter` 为**纯文本匹配**，支持非 Java 文件（`.sh`/`.properties`/`.xml`/`.md` 等）。在这些文件中，抑制标记需写在对应注释里，例如 `.sh`/`.properties` 中写作 `# // CHECKSTYLE:OFF`。

**关键区分**：`// CHECKSTYLE:OFF` 中的 `//` 在不同文件类型中语义不同：
- **cLike 文件**（`.java`/`.c`/`.js` 等）：`//` 是行注释前缀，`// CHECKSTYLE:OFF` 整体是行注释。块注释 `/* // CHECKSTYLE:OFF */` 或行注释 `// 说明 // CHECKSTYLE:OFF` 内的 `// CHECKSTYLE:OFF` 是嵌套示例文字，不应识别。
- **非 cLike 文件**（`.sh`/`.properties`/`.md` 等）：`//` 不是注释前缀，是字面量。写在 `#` 注释里的 `// CHECKSTYLE:OFF`（如 `# // CHECKSTYLE:OFF`）是合法抑制标记，应识别。

因此 checkstyle 不用 `shouldSkipValidation`（会漏过滤 Java 字符串字面量 `"// CHECKSTYLE:OFF"` 的误报），改用 `allowInComment=true`：注释内匹配默认保留，但 `filterValidMatchResults` 中额外检查 `//` 是否是该文件注释前缀，cLike 文件注释内仍过滤。

```java
// allowInComment=true：注释内匹配默认保留（.sh/.properties 等 // 是字面量）。
// filterValidMatchResults 中进一步判断：cLike 文件（// 是注释前缀）注释内的
// // CHECKSTYLE:OFF 是嵌套示例，仍过滤；字符串字面量内一律过滤。
new SuppressionPattern("//\\s*SUPPRESS\\s+CHECKSTYLE(?:\\s+\\S+)?", false, true),
new SuppressionPattern("//\\s*CHECKSTYLE:OFF(?:\\s+\\w+)?", false, true)
```

各文件类型的识别表现（`allowInComment=true` + cLike 区分）：

| 文件类型 | lexer 规则 | `//` 是否行注释前缀 | 行首 `// CHECKSTYLE:OFF` | 注释内 `// CHECKSTYLE:OFF` | 字符串内 `// CHECKSTYLE:OFF` |
|---------|-----------|------------------|----------------------|------------------------|---------------------------|
| `.java`/`.c`/`.js` 等 | cLike | 是 | 识别 ✓ | 不识别（嵌套示例） | 不识别（误报） |
| `.sh`/`.bash`/`.yml` | hash | 否 | 识别 ✓ | 识别 ✓（`# // CHECKSTYLE:OFF`，`//` 是字面量） | 不识别（误报） |
| `.properties`/`.txt`/未知 | defaultRules（treatAllAsComment） | 否 | 识别 ✓ | 识别 ✓（`//` 是字面量） | 不识别（误报） |
| `.md`/`.xml`/`.html` | markup | 否 | 识别 ✓ | 识别 ✓（`<!-- // CHECKSTYLE:OFF -->`） | 不识别（误报） |

### PMD（行级，注释 + 注解）

语法：
- 注释：`// NOPMD - explanation`
- 注解：`@SuppressWarnings("PMD")`、`@SuppressWarnings("PMD.RuleName")`
- 多规则（阶段三增强）：`@SuppressWarnings("PMD.rule1", "PMD.rule2")`、`@SuppressWarnings({"PMD.rule1", "PMD.rule2"})`

注解型仅匹配含 `"PMD"` 前缀的 `@SuppressWarnings`，避免与 Java 原生冲突。

```java
new SuppressionPattern("//\\s*NOPMD(?:\\s.*)?"),
new SuppressionPattern(
    "@SuppressWarnings\\s*\\(\\s*\\{?\\s*\"PMD[\\w.]*\""
    + "(?:\\s*,\\s*\"PMD[\\w.]*\")*\\s*\\}?\\s*\\)")
```

### SpotBugs（行级，注解，支持跨行合并）

语法：
- 单参数：`@SuppressFBWarnings("rule")`
- 带参数（阶段三增强）：`@SuppressFBWarnings(value = "rule", justification = "explanation")`、`@SuppressFBWarnings(value = "rule", justification = "explanation", matchType = SuppressMatchType.EXACT)`
- 参数可跨行（阶段三增强）：参数换行书写时通过跨行合并匹配识别

```java
new SuppressionPattern(
    "@SuppressFBWarnings\\s*\\(\\s*(?:value\\s*=\\s*)?(?:\"[^\"]*\"|\\{[^}]*\\})"
    + "(?:\\s*,\\s*\\w+\\s*=\\s*[^)]+)*\\s*\\)")
```

正则中 `\s*` 和 `[^)]+` 均可匹配换行符，故正则本身支持跨行；但 `SuppressionScanServiceImpl.scanAddedLines` 默认按单行 `matcher.find(codeLine)`，无法匹配跨行注解。阶段三新增**跨行注解合并匹配**逻辑：

1. 单行匹配失败时，检测当前行是否为未闭合注解开始（`@SuppressFBWarnings`/`@SuppressWarnings` 后有 `(` 且括号未平衡）
2. 合并后续行直到 `(` 和 `)` 平衡，对合并字符串执行 `combinedPattern.matcher(merged).find()`
3. 匹配成功则记录结果，并标记合并的后续行为已处理避免重复匹配

适用场景：`@SuppressFBWarnings(value = "DM_DEFAULT_ENCODING",\n justification = "测试用例：演示注解抑制，实际项目应显式指定 UTF-8")` 等参数换行写法。

### spotless（块级起始）

语法：`// spotless:off`（按设计只识别起始标记）

```java
new SuppressionPattern("//\\s*spotless:off", SuppressionType.LINE)
```

### rustfmt（行级 / 块级 / 文件级，Rust 属性）

语法：
- 行级：`#[rustfmt::skip]`、`#[cfg_attr(any(), rustfmt::skip)]`（阶段三增强：支持 cfg_attr 内嵌套括号）
- 块级：`#[rustfmt::skip]`（放在函数/结构体前）、`#[rustfmt::skip::macros(name)]`
- 文件级：`#![rustfmt::skip]`、`#![rustfmt::skip::macros(name)]`

```java
new SuppressionPattern(
    "#!\\[rustfmt::skip(?:\\s*::\\s*(?:macros|attributes)\\s*\\([^)]*\\))?\\s*\\]"),
new SuppressionPattern(
    "#\\[rustfmt::skip(?:\\s*::\\s*(?:macros|attributes)\\s*\\([^)]*\\))?\\s*\\]"),
// 用 [^\]\n] 替代 [^)] 以支持 cfg_attr 内的嵌套括号（如 any()），同时限制单行
new SuppressionPattern("#\\[cfg_attr\\([^\\]\\n]*rustfmt::skip[^\\]\\n]*\\)\\]")
```

`#![` 为文件级内部属性，`#[` 为行级/块级外部属性。cfg_attr 的 `[^)]` 改为 `[^\]\n]` 是因为 `any()` 等嵌套括号会提前结束匹配，改用排除 `]` 和换行符确保整个 `#[...]` 属性被完整匹配。

### clippy（行级 / 块级 / 文件级，Rust 属性）

语法：
- 行级：`#[allow(clippy::<rule>)]`、`#[expect(clippy::<rule>)]`
- 多规则（阶段三增强）：`#[allow(clippy::rule1, clippy::rule2)]`、`#[expect(clippy::rule1, clippy::rule2)]`
- 文件级：`#![allow(clippy::<rule>)]`、`#![expect(clippy::<rule>)]`

```java
new SuppressionPattern(
    "#!\\[(?:allow|expect)\\s*\\(\\s*clippy::\\w+\\s*"
    + "(?:,\\s*clippy::\\w+\\s*)*\\)\\s*\\]"),
new SuppressionPattern(
    "#\\[(?:allow|expect)\\s*\\(\\s*clippy::\\w+\\s*"
    + "(?:,\\s*clippy::\\w+\\s*)*\\)\\s*\\]")
```

`(?:,\\s*clippy::\\w+\\s*)*` 匹配零个或多个附加规则，支持单规则和多规则两种形式。

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

### 4. `scanAddedLines` 方法调整（支持 `skipValidation` 和多工具结果）

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

## 阶段一：防误报词法分析器设计

### 问题背景

原实现仅用 `isInvalidSuppressionComment` 检查匹配位置是否在块注释内，无法处理：
- 字符串字面量内的抑制标记（如 `String s = "// NOPMD";`）会被误识别为有效
- diff 上下文行截断的字符串/行注释跨行错误传递状态，导致下一行的有效抑制标记被误判为嵌套
- Markdown 等文档类文件中的说明性文字（如 `## 标题 # noqa`）被误识别为有效告警抑制

### SuppressionLexer 状态机

8 种状态：NORMAL、LINE_COMMENT、BLOCK_COMMENT、STRING_DOUBLE、STRING_SINGLE、STRING_BACKTICK、TRIPLE_DOUBLE、TRIPLE_SINGLE。

跨行规则：
- 行注释（LINE_COMMENT）、单双引号字符串（STRING_DOUBLE/STRING_SINGLE）**不跨行**，行尾自动重置为 NORMAL —— 这是阶段一修复的关键，避免 diff 截断的字符串/行注释错误影响下一行
- 块注释（BLOCK_COMMENT）、三引号字符串（TRIPLE_DOUBLE/TRIPLE_SINGLE）、模板字符串（STRING_BACKTICK）**可跨行**，通过 `entryState`/`exitState` 在行间传递

### LexRules 扩展名分派

| 扩展名 | 规则 | 说明 |
|--------|------|------|
| `.py` | python | # 行注释，"""/''' 三引号，"/' 字符串 |
| `.java/.c/.cpp/.js/.ts/.go/.rs/...` | cLike | // 行注释，/* */ 块注释，"/'/` 字符串 |
| `.sh/.bash/.yml/.toml/...` | hash | # 行注释，"/' 字符串 |
| `.sql` | sql | -- 行注释，/* */ 块注释，'/\" 字符串 |
| `.lua` | lua | -- 行注释，--[[ ]] 块注释 |
| `.html/.xml/.vue/...` | markup | <!-- --> 块注释，"/' 字符串 |
| `.txt/.rst/.adoc` 及未知 | defaultRules | treatAllAsComment=true，所有内容视为注释 |

### 防误报判定逻辑

`isNestedInCommentOrString(start)`：
- `start == 0`：检查上一行跨行状态 `entryState`，若非 NORMAL 则整行嵌套
- `start > 0`：检查 `charStates[start - 1]`，若非 NORMAL 则匹配嵌套在注释/字符串内

抑制注释标记本身也是注释（如 `# noqa` 的 `#` 是 Python 行注释开始），故检查匹配**起始位置的前一字符**状态而非匹配区间状态。

### 三级校验机制：`shouldSkipValidation` / `allowInComment` / 默认

`SuppressionScanServiceImpl.filterValidMatchResults` 按三级机制过滤匹配结果：

1. **`shouldSkipValidation=true`**（gitleaks）：直接保留，不调用 lexer 校验。`gitleaks:allow` 可出现在行内任意位置（甚至非注释中），跳过校验与其语义一致。
2. **`allowInComment=true`**（checkstyle）：区分"注释内"与"字符串内"——
   - 字符串内：过滤（所有工具都不应在字符串字面量里识别）
   - 注释内：再按文件类型区分——cLike 文件（`//` 是注释前缀）注释内的 `// CHECKSTYLE:OFF` 是嵌套示例，过滤；非 cLike 文件（`//` 是字面量）保留
   - NORMAL 状态：保留（行首合法标记）
3. **默认**（其他工具）：注释内和字符串内都过滤，只有 NORMAL 状态保留。

checkstyle 用 `allowInComment=true` 而非 `shouldSkipValidation=true` 的原因：`shouldSkipValidation=true` 会跳过所有校验，导致 Java 字符串字面量 `"// CHECKSTYLE:OFF"` 也被误识别。`allowInComment=true` 配合 cLike 判断，既保留 `.sh`/`.properties` 中 `# // CHECKSTYLE:OFF` 的合法用法，又过滤 Java 注释内嵌套示例和字符串字面量误报。

`SuppressionLexer.getStateAt(start)` 返回匹配起始位置的具体词法状态（NORMAL/LINE_COMMENT/BLOCK_COMMENT/STRING_*），供 `filterValidMatchResults` 区分注释与字符串。`SuppressionLexer.getRules()` 暴露 `LexRules`，供查询 `//` 是否是该文件的行注释前缀。

## 阶段三：.md 文件 markup 规则与 5 个工具正则增强

### .md 文件从 defaultRules 改为 markup

**问题**：阶段一将 `.md`/`.markdown` 用 `defaultRules`（treatAllAsComment=true），导致 `.md` 中的真实告警抑制注释（如 `# // CHECKSTYLE:OFF LineLength`）被识别为嵌套误报而过滤。

**修复**：`.md`/`.markdown` 改用 `markup` 规则（HTML 块注释 + "/' 字符串）。markup 规则下 `#` 不是行注释前缀（`#` 是 Markdown 标题），故 `# // CHECKSTYLE:OFF LineLength` 中的 `// CHECKSTYLE:OFF` 位于 NORMAL 状态，被识别为有效。

**权衡**：`.md` 中的说明性文字（如示例代码 `String s = "// NOPMD"`）可能被误识别，但用户诉求是识别真实的告警抑制注释，这是合理 trade-off。`.txt`/`.rst`/`.adoc` 仍保留 `defaultRules` 避免纯文本文档误报。

### 5 个工具正则增强

| 工具 | 原正则缺陷 | 阶段三修复 |
|------|-----------|-----------|
| checkstyle | 仅 `CHECKSTYLE:OFF`，不支持规则名 | `// CHECKSTYLE:OFF(?:\s+\w+)?` 支持规则名；按设计只识别起始标记 OFF，不识别结束标记 ON；`allowInComment=true` 支持 `.sh`/`.properties` 等非 Java 文件中 `# // CHECKSTYLE:OFF` 识别，同时 cLike 文件注释内嵌套示例和字符串字面量误报被过滤 |
| PMD | `@SuppressWarnings("PMD...")` 仅单规则 | `(?:\s*,\s*"PMD[\w.]*")*` 支持多 PMD 规则和数组形式 |
| SpotBugs | `@SuppressFBWarnings\([^)]*\)` 过于宽泛且无法精确匹配参数 | 精确匹配 `value`/`justification`/`matchType` 等参数：`(?:\s*,\s*\w+\s*=\s*[^)]+)*` |
| rustfmt | `#[cfg_attr([^)]*rustfmt::skip[^)]*)]` 的 `[^)]` 遇 `any()` 嵌套括号提前结束 | 改用 `[^\]\n]` 排除 `]` 和换行符，确保整个 `#[...]` 属性完整匹配 |
| clippy | `clippy::\w+` 仅单规则 | `(?:,\s*clippy::\w+\s*)*` 支持多规则，含文件级 `#![...]` 和 `expect` 形式 |

### rustfmt cfg_attr 嵌套括号正则设计

原正则 `#[cfg_attr\([^)]*rustfmt::skip[^)]*\)\]` 对 `#[cfg_attr(any(), rustfmt::skip)]` 会匹配到 `#[cfg_attr(any()` 就停止（`)` 提前结束），无法完整匹配。

改用 `#[cfg_attr\([^\]\n]*rustfmt::skip[^\]\n]*\)\]`：`[^\]\n]` 排除 `]`（属性结束符）和换行符（限制单行），允许内部任意字符（含嵌套括号），确保 `#[cfg_attr(any(), rustfmt::skip)]` 完整匹配。
