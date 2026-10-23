# tasks: merge-result-display

## 实现步骤

### Task 1: 新建 test-result-display.js

- [ ] 1.1 在 `pytest-orch/` 下新建 `test-result-display.js`
- [ ] 1.2 从 `test-result-display/index.js` 迁移以下常量（原样复制，不修改值与注释）
  - `LINE_BREAK_RE`
  - `SENSITIVE_PATTERNS`
  - `KNOWN_TEST_STATES`
  - `OBS_HOST_PATTERN`
  - `MASKED_URL_DISPLAY`
  - `SENSITIVE_QUERY_KEYS`
  - `MAX_INPUT_BYTES`
  - `MAX_SUMMARY_BYTES`
- [ ] 1.3 迁移以下辅助函数（原样复制，保留 JSDoc）
  - `escapeMarkdownTable`
  - `stripCellLineBreaks`
  - `redactSensitive`
  - `validateJsonFilePath`
  - `validateSummaryFilePath`
  - `sanitizeState`
  - `sanitizeSourceTask`
  - `parseTestResults`
  - `stripSensitiveQueryParams`
  - `validateResultUrl`
  - `generateMarkdownTable`（新增第 3 入参 `showDownloadLink = true`，`false` 时省略"用例结果"列并跳过 `validateResultUrl`）
  - `countStatistics`
  - `parseJsonFileInput`
  - `capSummarySize`
- [ ] 1.4 适配 `displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, obsConfigured = true)` 函数（复制原 `run()` 第 553-666 行，做 3 处改动 + 2 处新增分支）
  - 适配点 1：`async function run()` → `async function displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, obsConfigured = true)`；删除两行 `core.getInput("json-file", { required: true })` 与 `core.getInput("last-json", { required: false })`，改为 `const jsonFileInput = testcaseFilePath || "";`（last-json 直接用入参 `lastJsonInput`）
  - 适配点 2：try 块末尾 3 行 `core.setOutput("total-cases"/"passed-cases"/"not-passed-cases", ...)` 替换为 1 行 `core.info(\`Summary stats: total=${stats.total}, passed=${stats.passed}, notPassed=${stats.notPassed}\`);`
  - 适配点 3：catch 块 3 行 `core.setOutput(..., "0")` + `core.setFailed(error.message)` 替换为 1 行 `core.warning(\`Test result summary error (skipped): ${error.message}\`);`
  - 新增分支 A：`generateMarkdownTable(combinedResults, showRetryColumn, obsConfigured)` 第 3 入参透传 `obsConfigured` 作为 `showDownloadLink`
  - 新增分支 B：`envLogFile` 非空时在表格 title 前插入 `[环境日志](<path>)` 链接，写入前 `replace(/[\n\r]/g, "")` + `replace(/>/g, "&gt;")` 防注入；拼到 `markdownTable` 前
  - 其余逻辑原样保留（parseJsonFileInput / parseTestResults / isRetry 标记 / passedOnly / countStatistics / 写 $ATOMGIT_STEP_SUMMARY；last-json 解析用入参 `lastJsonInput`，原 `if (lastJsonInput && lastJsonInput.trim())` 判断不变）
- [ ] 1.5 在文件末尾添加 `module.exports`，导出 `displayTestResults` + 全部辅助函数 + 全部常量（供单元测试）
- [ ] 1.6 文件顶部 `require("@actions/core")`、`require("fs")`、`require("path")`

### Task 2: 修改 index.js

- [ ] 2.1 顶部新增 `const { displayTestResults } = require("./test-result-display");`
- [ ] 2.2 Step 11 中提升 `testCaseFile`/`envLogFile` 到 `if (fs.existsSync(...))` 之前
  - 新增 `let safeTestCaseFileForDisplay = "";` 与 `let safeEnvLogFileForDisplay = "";`
  - 在 `confineOutputPath(TestCaseFile)` 赋值后拼入 source 前缀：`const stepNameForSource = (ciEnv.step_name || "").replace(/[:\n\r]/g, "");` → `safeTestCaseFileForDisplay = testCaseFile && stepNameForSource ? \`${stepNameForSource}:${testCaseFile}\` : testCaseFile;`
  - 在 `confineOutputPath(EnvLogFile)` 赋值后同步赋值 `safeEnvLogFileForDisplay = envLogFile;`
- [ ] 2.3 在原 Step 12（APIG upload）之前插入新 Step 12（Generate test result summary）
  - `core.startGroup("Step 12: Generate test result summary")`
  - `try` 块内：`const lastJsonInput = core.getInput("last-json", { required: false });` + `await displayTestResults(safeTestCaseFileForDisplay, lastJsonInput, safeEnvLogFileForDisplay, obsConfigured);`
  - `catch` 块：`core.warning`（防御性兜底，displayTestResults 内部已 catch）+ `if (error && error.stack) core.warning(\`Step 12 stack:\n${error.stack}\`);`
  - `finally`：`core.endGroup()`
- [ ] 2.4 原 Step 12 → Step 13（APIG upload）
  - 修改 `core.startGroup` 文本与注释中的步骤号
- [ ] 2.5 原 Step 13 → Step 14（OBS upload）
  - 修改 `core.startGroup` 文本与注释中的步骤号
- [ ] 2.6 原 Step 14 → Step 15（Set outputs and finalize）
  - 修改 `core.startGroup` 文本与注释中的步骤号

### Task 3: 修改 action.yml

- [ ] 3.1 在 `skip-venv` 之后新增 `last-json` 输入（`required: false`）
- [ ] 3.2 补充 `obs-bucket-name` 的 description：OBS 三参任一未设置时结果展示与 OBS 上传整体跳过（仅改描述文本）

### Task 4: 构建与验证

- [ ] 4.1 执行 `npm run build`（或 `ncc build`）重新生成 `dist/index.js`
- [ ] 4.2 静态检查：确认 `test-result-display.js` 无语法错误、`require` 路径正确
- [ ] 4.3 逻辑自检：
  - `displayTestResults("", "", "", false)` 不抛异常（parseJsonFileInput 返回空数组，stats 为 {0,0,0}，无 env 日志链接，省略"用例结果"列）
  - `displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, true)` 在 testcase-file/envLogFile 有效时正确写 summary、插入环境日志链接并保留"用例结果"列
  - 新 Step 12 异常不影响后续 Step 13/14/15

## 验证方式

| 验证项                | 方式                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 文件存在              | `ls pytest-orch/test-result-display.js`                                                                                      |
| 语法正确              | `node -e "require('./pytest-orch/test-result-display')"`                                                                     |
| 主函数可调用          | `node -e "const m=require('./pytest-orch/test-result-display'); console.log(typeof m.displayTestResults)"` 应输出 `function` |
| index.js require 正确 | `node -c pytest-orch/index.js`（语法检查）                                                                                   |
| action.yml 格式       | YAML 解析通过                                                                                                                |
| dist 产物更新         | `dist/index.js` 包含 `displayTestResults` 调用                                                                               |

## 不在本次范围

- 不编写单元测试文件（pytest-orch 目录当前无测试框架配置）
- 不删除 `test-result-display` 插件
- 不修改 `pytest-orch/validators.js`
- 不修改流水线 YAML 消费方
