# proposal: merge-result-display

## 需求背景

当前 CI 流水线中，测试结果展示由独立的 `test-result-display` 插件完成：

- 输入：`json-file`（测试结果 JSON 路径）、`last-json`（上次结果，可选）
- 输出：将测试用例汇总表写入 `$ATOMGIT_STEP_SUMMARY`，并输出 `total-cases`/`passed-cases`/`not-passed-cases`

`pytest-orch` 插件在 Step 11 产出 `testcase-file`（测试结果 JSON 文件路径），该输出恰好就是 `test-result-display` 的 `json-file` 输入。当前流水线需要串接两个插件，存在以下问题：

1. **链路冗余**：pytest-orch 产出 testcase-file 后，需要在流水线 YAML 中再声明一个 test-result-display 步骤消费它，增加编排复杂度。
2. **数据二次传递**：testcase-file 路径经 `core.setOutput` → 流水线变量 → 下游 `core.getInput` 传递，路径在两步之间脱离了 pytest-orch 已建立的可信根校验上下文。
3. **安全校验重复**：test-result-display 内部对 json-file 重新做路径白名单、符号链接、realpath 校验，与 pytest-orch 已做的 `confineOutputPath` 语义重叠。

## 需求目标

将 `test-result-display` 的结果展示能力合并到 `pytest-orch` 插件内部，作为一个新的内部步骤完成，合并后：

- pytest-orch 在产出 `testcase-file` 后，直接调用结果展示逻辑，无需额外插件步骤。
- 保留 `last-json` 输入，支持重试结果对比展示。
- 展示步骤内部完成统计计算与 Markdown 汇总写入，统计量不作为插件输出暴露。
- 原有 `test-result-display` 插件暂不删除（后续可独立清理）。

## 实现约束

用户明确要求：

1. **不在 `index.js` 中直接内联展示代码**，而是新建独立文件 `test-result-display.js`，将展示相关函数与常量集中于此。
2. `index.js` 通过 `require("./test-result-display")` 引用该模块导出的**主函数 `displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, obsConfigured = true)`**（适配原 `run()` 而来，四入参显式契约），该函数负责完成解析、Markdown 生成、摘要写入，并自行将错误转为 `core.warning`。相对原 `run()` 的三处适配（getInput 改入参、setOutput 改日志、setFailed 改 warning）见 design.md §2.2；`envLogFile`/`obsConfigured` 为实现阶段新增入参，分别用于在表格前插入环境日志链接、在 OBS 未配置时省略"用例结果"下载链接列。
3. `index.js` 侧仅负责：读取 `last-json` 输入、提升 Step 11 产出的可信 `testcase-file`/`env-log-file` 路径与 `obsConfigured` 一并传入 `await displayTestResults(...)`、防御性兜底；不设置额外 outputs（统计量仅供展示步骤内部消费）。

## 验收标准

| 编号  | 验收项                                                                                                                                                                                                                    | 验证方式                        |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| AC-1  | 新建 `pytest-orch/test-result-display.js`，包含原 `test-result-display/index.js` 的全部辅助函数与常量                                                                                                                     | 文件存在，函数清单与原文件一致  |
| AC-2  | `test-result-display.js` 导出适配后的 `displayTestResults(testcaseFilePath, lastJsonInput, envLogFile, obsConfigured = true)` 函数（沿用原 run() 结构，三处适配 + 新增 envLogFile/obsConfigured 入参，四入参）            | 函数签名与适配点符合            |
| AC-3  | `index.js` 通过 `require("./test-result-display")` 引入 `displayTestResults`，在 Step 11 之后新增一步 `await displayTestResults(safeTestCaseFileForDisplay, lastJsonInput, safeEnvLogFileForDisplay, obsConfigured)` 调用 | 代码审查                        |
| AC-4  | 新步骤将 Markdown 汇总写入 `$ATOMGIT_STEP_SUMMARY`（若环境变量已设置）                                                                                                                                                    | 运行时检查 summary 文件         |
| AC-5  | `action.yml` 新增 `last-json` 输入（可选）                                                                                                                                                                                | action.yml diff                 |
| AC-6  | 结果展示步骤为非关键步骤：任何异常只告警，不影响后续上传与 finalize                                                                                                                                                       | 构造异常 JSON 验证不中断        |
| AC-7  | 原 `test-result-display` 插件文件不被修改、不被删除                                                                                                                                                                       | 文件状态无变化                  |
| AC-8  | `testcase-file` 为空（output.json 缺失或 TestCaseFile 丢失）时不报错                                                                                                                                                      | 缺失 output.json 场景验证       |
| AC-9  | `envLogFile` 非空时在表格标题前插入 `[环境日志](<path>)` 链接，写入 summary 前剔除换行符防注入；为空时不插入                                                                                                              | 传入有效/空 envLogFile 分别验证 |
| AC-10 | `obsConfigured=false`（OBS 三参未齐）时表格省略"用例结果"下载链接列且跳过 `validateResultUrl`；仍生成统计与表格                                                                                                           | 仅传 OBS 三参子集场景验证       |

## 非目标

- 不删除 `test-result-display` 插件（后续独立清理）。
- 不修改 `test-result-display` 插件的任何文件。
- 不改变 pytest-orch 现有 Step 0-11 的对外行为：Step 11 仅新增内部变量提升（`safeTestCaseFileForDisplay`/`safeEnvLogFileForDisplay`）与 source 前缀拼接供展示步骤消费，现有 outputs 语义不变。
- 不改变 `testcase-file`/`testcase-obs-url`/`env-log-file` 现有输出的语义与格式。
