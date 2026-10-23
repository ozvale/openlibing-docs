# design: merge-result-display

## 1. 总体方案

### 1.1 模块划分

```
pytest-orch/
├── index.js            # 主入口，新增 require("./test-result-display") 与一步调用
├── test-result-display.js # 新建：展示逻辑（适配后的 displayTestResults() + 常量 + 辅助函数）
├── validators.js       # 不变
└── action.yml          # 新增 last-json 输入
```

### 1.2 数据流

```
Step 11 (Read output.json)
  ├─ confineOutputPath(TestCaseFile) → testCaseFile（可信路径）
  ├─ confineOutputPath(EnvLogFile) → envLogFile（可信路径）
  ├─ safeTestCaseFileForDisplay = `${ciEnv.step_name}:${testCaseFile}`（source 前缀，供展示）
  ├─ safeEnvLogFileForDisplay = envLogFile（供展示）
  ├─ sanitizeOutputValue(testCaseFile/envLogFile) → safe*（用于 setOutput）
  └─ core.setOutput("testcase-file"/"env-log-file", safe*)

Step 12 (Generate test result summary) ← 新增
  ├─ const lastJsonInput = core.getInput("last-json", { required: false });
  └─ await displayTestResults(safeTestCaseFileForDisplay, lastJsonInput,
                             safeEnvLogFileForDisplay, obsConfigured)
       ├─ parseJsonFileInput / parseTestResults（复用原逻辑）
       ├─ envLogFile 非空时在表格前插入 [环境日志](<path>) 链接
       ├─ generateMarkdownTable(combined, showRetryColumn, obsConfigured)
       │   + countStatistics
       ├─ 写入 $ATOMGIT_STEP_SUMMARY（若已设置）
       └─ 内部 try/catch：错误转 core.warning，不 setFailed、不 setOutput

Step 13 (Upload XmlFiles via APIG)   ← 原 Step 12
Step 14 (Upload ArchiveLogDir via OBS) ← 原 Step 13
Step 15 (Set outputs and finalize)    ← 原 Step 14
```

### 1.3 主函数签名

```javascript
// test-result-display.js

/**
 * 读取测试结果 JSON 并生成 Markdown 汇总，写入 step summary。
 * 由原 test-result-display/index.js 的 run() 适配而来，保留原结构与逻辑，
 * 仅做三处适配（见 §2.2）；envLogFile / obsConfigured 为实现阶段新增入参。
 * @param {string} testcaseFilePath - Step 11 产出的可信路径（confineOutputPath 结果，未 sanitize）；
 *   index.js 会拼成 `${ciEnv.step_name}:${testCaseFile}` 的 source:path 格式；
 *   为空时 parseJsonFileInput 返回空数组，流程自然走空，统计为 {0,0,0}
 * @param {string} lastJsonInput - 可选的上次结果输入（原 last-json，支持多行 source:path 格式）；
 *   为空字符串或纯空白时跳过 last-json 解析
 * @param {string} envLogFile - 可选的环境日志文件路径（confineOutputPath 结果，未 sanitize）；
 *   非空时在 Markdown 表格 title 之前插入 [环境日志](<path>) 链接；
 *   写入 summary 前剔除换行符防注入；为空时不插入链接
 * @param {boolean} obsConfigured - OBS 三参是否齐备。为 false 时表格不展示
 *   "用例结果"下载链接列（仍生成统计与表格，仅省略该列及 [下载](url) 渲染）
 */
async function displayTestResults(
  testcaseFilePath,
  lastJsonInput,
  envLogFile,
  obsConfigured = true,
) {
  // ... 适配后的原 run() 逻辑 + envLogFile/obsConfigured 新增分支 ...
}

module.exports = { displayTestResults /* + 辅助函数供测试 */ };
```

**设计要点**：

- 主函数沿用原 `run()` 结构，内部包含完整的 try/catch，错误转 `core.warning`，**不调用 `core.setFailed`**（避免失败整个 pytest-orch 步骤）。
- 主函数**不设置 outputs**（无 `core.setOutput`），统计仅供 `core.info` 日志，不暴露为插件输出。
- 主函数内部对单个 source 文件解析失败只 `core.warning` 并跳过（与原 `run()` 一致）。
- **四入参显式契约**：`testcaseFilePath`、`lastJsonInput`、`envLogFile`、`obsConfigured` 均由 index.js 传入，函数内不再调用 `core.getInput`，依赖在签名中可见，便于测试与复用。
- index.js 侧读一次 `last-json` 输入并连同 Step 11 提升的可信路径、`obsConfigured` 一并传入，调用 `await displayTestResults(...)`，无需自建 try/catch 包裹（函数内部已兜底）。
- **新增 envLogFile 分支**：非空时在表格标题前插入 `[环境日志](<path>)` 链接，写入前剔除 `\n`/`\r` 并转义 `>`，使用 GFM 角括号链接语法允许含空格/`)`/`]` 的路径合法渲染。
- **新增 obsConfigured 列开关**：传给 `generateMarkdownTable` 作为 `showDownloadLink`；为 `false` 时省略"用例结果"列并跳过 `validateResultUrl`，避免 OBS 未配置时打印无谓告警。

## 2. test-result-display.js 内容

### 2.1 从 test-result-display/index.js 迁移的内容

**常量**（原样迁移）：

| 常量                   | 值                                                | 用途             |
| ---------------------- | ------------------------------------------------- | ---------------- |
| `LINE_BREAK_RE`        | `/[\r\n\u2028\u2029\u0085\f\u0000]+/g`            | 换行归一化       |
| `SENSITIVE_PATTERNS`   | 5 条正则                                          | 路径/IP/凭证脱敏 |
| `KNOWN_TEST_STATES`    | `["passed","failed","skipped","error","unknown"]` | 状态枚举         |
| `OBS_HOST_PATTERN`     | OBS 主机正则                                      | URL 白名单       |
| `MASKED_URL_DISPLAY`   | `"[下载链接已脱敏]"`                              | 非 OBS URL 显示  |
| `SENSITIVE_QUERY_KEYS` | 12 个签名参数名                                   | URL 查询参数剥离 |
| `MAX_INPUT_BYTES`      | `3*1024*1024`                                     | 输入大小上限     |
| `MAX_SUMMARY_BYTES`    | `256*1024`                                        | 摘要大小上限     |

**函数**（原样迁移）：

| 函数                                                          | 职责                                                                                   |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `escapeMarkdownTable(text)`                                   | Markdown 单元格特殊字符转义                                                            |
| `stripCellLineBreaks(row)`                                    | 行级换行剥离（防御性）                                                                 |
| `redactSensitive(text)`                                       | 路径/IP/凭证片段脱敏                                                                   |
| `validateJsonFilePath(p)`                                     | JSON 路径安全校验（白名单+符号链接+realpath）                                          |
| `validateSummaryFilePath(p)`                                  | 摘要文件路径安全校验                                                                   |
| `sanitizeState(raw)`                                          | 测试状态归一化到枚举                                                                   |
| `sanitizeSourceTask(raw)`                                     | sourceTask 字符白名单（`[A-Za-z0-9-]`）                                                |
| `parseTestResults(file, source, passedOnly)`                  | 解析 JSON 文件为结果数组（fd 绑定读取）                                                |
| `stripSensitiveQueryParams(url)`                              | URL 签名参数剥离                                                                       |
| `validateResultUrl(rawUrl)`                                   | OBS URL 白名单校验                                                                     |
| `generateMarkdownTable(results, showRetry, showDownloadLink)` | 生成 Markdown 表格（`showDownloadLink=false` 省略"用例结果"列，实现阶段新增第 3 入参） |
| `countStatistics(results)`                                    | 统计 total/passed/notPassed                                                            |
| `parseJsonFileInput(input)`                                   | 解析 `source:path` 多行输入（单路径走 fallback 分支）                                  |
| `capSummarySize(content)`                                     | 摘要字节上限截断                                                                       |

**适配**：

| 函数                                                                             | 职责                                                                   |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, obsConfigured)` | 适配后的主入口，沿用原 run() 结构 + 新增 envLogFile/obsConfigured 分支 |

### 2.2 run() 适配点（共 3 处）

原 `run()` 见 `test-result-display/index.js` 第 553-666 行。适配后保留全部解析/合并/Markdown/summary 逻辑，仅改以下 3 处；此外实现阶段新增 `envLogFile`/`obsConfigured` 入参与对应分支（不属于原 `run()` 的"适配"，而是新增能力）：

| #   | 原代码                                                                                                                             | 适配后                                                                                                                                                                                             | 原因                                                                                                                                                                             |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `async function run()` + 两行 `core.getInput("json-file", { required: true })` / `core.getInput("last-json", { required: false })` | `async function displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, obsConfigured = true)` + `const jsonFileInput = testcaseFilePath \|\| "";`（last-json 直接用入参 `lastJsonInput`） | 四入参显式契约；前两入参替代原 `core.getInput`，`envLogFile`/`obsConfigured` 为实现阶段新增能力（见下方新增分支）；路径来自 Step 11 内部可信变量，函数内不再调用 `core.getInput` |
| 2   | try 块末尾 3 行 `core.setOutput("total-cases"/"passed-cases"/"not-passed-cases", ...)`                                             | 替换为 1 行 `core.info(\`Summary stats: total=${stats.total}, passed=${stats.passed}, notPassed=${stats.notPassed}\`);`                                                                            | 不暴露为插件输出                                                                                                                                                                 |
| 3   | catch 块 3 行 `core.setOutput(..., "0")` + `core.setFailed(error.message)`                                                         | 替换为 1 行 `core.warning(\`Test result summary error (skipped): ${error.message}\`);`                                                                                                             | 非关键步骤，失败只告警，不影响后续上传                                                                                                                                           |

**适配后的 displayTestResults() 关键片段**（仅展示改动点，其余原样保留）：

```javascript
async function displayTestResults(
  testcaseFilePath,
  lastJsonInput,
  envLogFile,
  obsConfigured = true,
) {
  try {
    // 适配点 1：json-file / last-json 均不再从 core.getInput 读取，改为接收参数
    const jsonFileInput = testcaseFilePath || "";

    const jsonFiles = parseJsonFileInput(jsonFileInput);
    core.info(`Parsing test results from ${jsonFiles.length} source(s)`);

    // ... parseJsonFileInput / parseTestResults / 合并 / isRetry 标记 / passedOnly
    //     全部原样保留；last-json 解析用入参 lastJsonInput，
    //     原 `if (lastJsonInput && lastJsonInput.trim())` 判断不变 ...

    const stats = countStatistics(combinedResults);

    // 新增分支：obsConfigured 作为 showDownloadLink 传入，控制"用例结果"列
    const markdownTable = generateMarkdownTable(
      combinedResults,
      showRetryColumn,
      obsConfigured,
    );

    // 新增分支：envLogFile 非空时在表格 title 之前插入 [环境日志](<path>) 链接；
    // 写入前剔除 \n/\r 并转义 > 防 Markdown 注入；为空时不插入
    const safeEnvLogPath = (envLogFile || "")
      .replace(/[\n\r]/g, "")
      .replace(/>/g, "&gt;");
    const summaryMarkdown = safeEnvLogPath
      ? `[环境日志](<${safeEnvLogPath}>)\n\n${markdownTable}`
      : markdownTable;

    // 写 $ATOMGIT_STEP_SUMMARY（capSummarySize 截断 + fd 绑定 append）原样保留 ...

    // 适配点 2：原 3 行 core.setOutput 替换为日志
    core.info(
      `Summary stats: total=${stats.total}, passed=${stats.passed}, notPassed=${stats.notPassed}`,
    );

    core.info("Test results summary generated successfully");
  } catch (error) {
    // 适配点 3：原 3 行 setOutput + setFailed 替换为 warning
    core.warning(`Test result summary error (skipped): ${error.message}`);
  }
}
```

> **空路径行为**：`testcaseFilePath` 为空时，`parseJsonFileInput("")` 返回 `[]`（`"".split("\n")` 经 `.filter(line => line.trim())` 后为空），后续 `allTestResults`/`combinedResults` 均为空，`stats` 为 `{0,0,0}`，Markdown 表为空表头，summary 写入空内容——整体不报错，与原 `run()` 传入空 json-file 的行为一致。

### 2.3 导出清单

```javascript
module.exports = {
  displayTestResults, // 适配后的主函数（index.js 调用）
  // 以下供单元测试复用
  escapeMarkdownTable,
  redactSensitive,
  sanitizeState,
  sanitizeSourceTask,
  validateResultUrl,
  validateJsonFilePath,
  validateSummaryFilePath,
  capSummarySize,
  generateMarkdownTable,
  parseJsonFileInput,
  parseTestResults,
  countStatistics,
  stripSensitiveQueryParams,
  MASKED_URL_DISPLAY,
  MAX_SUMMARY_BYTES,
  MAX_INPUT_BYTES,
  OBS_HOST_PATTERN,
  SENSITIVE_PATTERNS,
  SENSITIVE_QUERY_KEYS,
  KNOWN_TEST_STATES,
  LINE_BREAK_RE,
};
```

## 3. index.js 改动

### 3.1 顶部新增 require

```javascript
const { displayTestResults } = require("./test-result-display");
```

### 3.2 Step 11 变量提升

当前 `testCaseFile` 声明在 Step 11 的 `try` 块内部（第 566 行），新步骤无法访问。需将其提升到 Step 11 的 `if (fs.existsSync(...))` 之前，初始化为 `""`：

```javascript
// Step 11: Read output.json
let safeTestCaseFileForDisplay = "";  // 新增：供 Step 12 使用
let safeEnvLogFileForDisplay = "";    // 新增：供 Step 12 传入 envLogFile
// ... 原有 safeXmlSnapshots / archiveLogSnapshots / safeObsPrefix 声明 ...
if (fs.existsSync(outputJsonPath)) {
  try {
    // ...
    const testCaseFile = confineOutputPath(...);
    // 拼入当前 CI step 名作为 source 前缀（source:path 格式），供展示表格"来源任务"列
    const stepNameForSource = (ciEnv.step_name || "").replace(/[:\n\r]/g, "");
    safeTestCaseFileForDisplay =
      testCaseFile && stepNameForSource ? `${stepNameForSource}:${testCaseFile}` : testCaseFile;
    const envLogFile = confineOutputPath(outputJson.EnvLogFile, ...);
    safeEnvLogFileForDisplay = envLogFile;  // 新增：保存未 sanitize 的可信路径
    // ...
  } catch (error) { ... }
}
```

> **注意**：传给 `displayTestResults` 的 `testcaseFilePath`/`envLogFile` 均为 `confineOutputPath` 返回的原始可信路径（未 `sanitizeOutputValue`），因为 `sanitizeOutputValue` 会转义 `\`/`=` 等字符，破坏路径语义。`testcaseFilePath` 还拼了 `${ciEnv.step_name}:` 前缀（`parseJsonFileInput` 的 source:path 分支会解析该前缀），`envLogFile` 直接传原始路径。`validateJsonFilePath` 内部会重新做 realpath 校验，防御深度足够。

### 3.3 新增 Step 12（display）

在原 Step 12（APIG upload）之前插入。index.js 读取 `last-json` 输入并连同可信路径、`obsConfigured` 一并传入，`displayTestResults` 内部已含 try/catch，外层仅做防御性兜底：

```javascript
// Step 12: Generate test result summary
// Non-critical: displayTestResults 内部 try/catch 将错误转为 core.warning，不影响后续步骤
// obsConfigured=false 时仍生成汇总表，仅省略"用例结果"下载链接列
core.startGroup("Step 12: Generate test result summary");
try {
  const lastJsonInput = core.getInput("last-json", { required: false });
  await displayTestResults(
    safeTestCaseFileForDisplay,
    lastJsonInput,
    safeEnvLogFileForDisplay,
    obsConfigured,
  );
} catch (error) {
  // 防御性兜底：displayTestResults 内部已 catch，此处仅在适配函数本身异常时触发
  core.warning(`Step 12 unexpected error (skipped): ${formatStepError(error)}`);
  if (error && error.stack) {
    core.warning(`Step 12 stack:\n${error.stack}`);
  }
} finally {
  core.endGroup();
}
```

### 3.4 步骤重编号

| 原步骤  | 新步骤  | 说明                     |
| ------- | ------- | ------------------------ |
| Step 11 | Step 11 | 不变，仅提升变量         |
| —       | Step 12 | 新增：结果展示           |
| Step 12 | Step 13 | APIG 上传 XmlFiles       |
| Step 13 | Step 14 | OBS 上传 ArchiveLogDir   |
| Step 14 | Step 15 | Set outputs and finalize |

仅需修改 `core.startGroup` / `core.endGroup` 内的步骤编号文本与注释，逻辑不变。

## 4. action.yml 改动

### 4.1 新增输入

```yaml
last-json:
  description: >-
    Optional previous test results JSON (multi-line 'source:/path/to/file.json' or plain path);
    passed results are rendered with retry column
  required: false
```

插入位置：`skip-venv` 之后（inputs 段末尾）。

### 4.2 OBS 输入描述补充

`obs-bucket-name` 的 description 补充说明：OBS 三参（`obs-bucket-name`/`obs-server`/`obs-base-url`）任一未设置时，结果展示与 OBS 上传整体跳过（对应 `obsConfigured=false` 时省略"用例结果"下载链接列的行为）。仅修改描述文本，无新增输入。

## 5. 安全分析

### 5.1 路径可信链

```
output.json (不受信)
  → confineOutputPath (白名单+realpath+存在性)  [Step 11]
  → testCaseFile (可信路径)
  → displayTestResults(testCaseFile, lastJsonInput)
    → validateJsonFilePath (白名单+符号链接+realpath+扩展名+fd 绑定读取)  [test-result-display.js]
```

两层校验叠加，无 TOCTOU 窗口（test-result-display.js 使用 fd 绑定读取）。

### 5.2 保持的安全机制

| 机制                              | 来源                                           | 保留情况 |
| --------------------------------- | ---------------------------------------------- | -------- |
| 路径白名单（cwd realpath + /tmp） | validateJsonFilePath                           | 完整保留 |
| 符号链接拒绝                      | validateJsonFilePath / validateSummaryFilePath | 完整保留 |
| realpath 二次校验                 | validateJsonFilePath                           | 完整保留 |
| fd 绑定读取（TOCTOU 关闭）        | parseTestResults                               | 完整保留 |
| 输入大小上限 3MB                  | MAX_INPUT_BYTES                                | 完整保留 |
| 摘要大小上限 256KB                | MAX_SUMMARY_BYTES + capSummarySize             | 完整保留 |
| OBS URL 白名单                    | validateResultUrl                              | 完整保留 |
| 签名参数剥离                      | stripSensitiveQueryParams                      | 完整保留 |
| 敏感片段脱敏                      | redactSensitive                                | 完整保留 |
| Markdown 注入防御                 | escapeMarkdownTable + stripCellLineBreaks      | 完整保留 |
| 状态枚举归一化                    | sanitizeState                                  | 完整保留 |
| sourceTask 字符白名单             | sanitizeSourceTask                             | 完整保留 |

### 5.3 新增风险点

| 风险                                     | 评估   | 缓解                                                  |
| ---------------------------------------- | ------ | ----------------------------------------------------- |
| last-json 输入来自外部，可能指向任意路径 | 低     | validateJsonFilePath 白名单限定 cwd/tmp，与原插件一致 |
| testcase-file 为空时主函数行为           | 无风险 | 空值直接返回 {0,0,0}，不进入解析                      |
| 新步骤异常影响后续上传                   | 无风险 | try/catch 包裹，异常只 warning                        |

## 6. 影响范围

### 6.1 文件变更清单

| 文件                                 | 变更类型 | 说明                                              |
| ------------------------------------ | -------- | ------------------------------------------------- |
| `pytest-orch/test-result-display.js` | 新建     | 展示逻辑模块                                      |
| `pytest-orch/index.js`               | 修改     | 新增 require + 变量提升 + 新 Step 12 + 步骤重编号 |
| `pytest-orch/action.yml`             | 修改     | 新增 1 输入（last-json）                          |

### 6.2 不受影响

- `pytest-orch/validators.js`：不变
- `pytest-orch/dist/index.js`：构建产物，由 ncc 重新打包生成（实现阶段需 `npm run build` 或等价命令）
- `test-result-display/`：整个插件不变
- 流水线 YAML：消费方可以选择移除 test-result-display 步骤（非本次强制范围）

### 6.3 向后兼容

- pytest-orch 原有 5 个输出（pipeline-id/job-run-id/testcase-obs-url/testcase-file/env-log-file）不变，不新增任何输出。
- 新增 1 个输入（last-json）为可选，不设置时行为与原 test-result-display 仅传 json-file 一致。
