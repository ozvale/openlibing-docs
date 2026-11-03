# pre-commit-action 新增安全 issue 分析（#43、#48）

> 分析基准：`master`（HEAD: 09304b5），整改分支 `fix-issue43-report-residue`（9228f77）、`fix-issue48-log-injection`（bf7bfe1）。
> 分析日期：2026-11-03。本条为独立新批次（上一批 `security-issues-analysis-20261012.md` 覆盖 #20~#37）。
> 验证环境：`openlibing-test/openlibing-cicd-test`（私有仓，引用统一测试分支 `fix-security-remediation`）。

## 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 真问题·等价加固（已实施并验证） | #43 | 收集前清理默认报告目录的历史残留 SARIF |
| 真问题·等价加固（已实施并验证） | #48 | 日志输出清洗不可信输入的换行与控制字符 |

两条均未触及业务逻辑，属硬规则 1 白名单内的「临时文件治理」与「日志脱敏」，无契约变化、无默认值变化、无失败语义变化。

---

## 一、#43 共享 runner 历史残留 SARIF 被误收集

- **位置**：`index.js` `collectScanReports()`（调用前置钩子）
- **核实**：真实。`REPORT_DIR_DEFAULT` 固定为 `/tmp/pre-commit-reports/`，成功路径会把报告留在该目录供后续 `openlibing-upload-sarif` 消费。共享 runner 上，上一次任务残留的 `*.sarif` 会被本次收集全量纳入，导致报告被误归属到当前仓。
- **整改**：新增 `clearStaleDefaultReports()`，在 `collectScanReports()` 开始、`isPrEvent()` 判断之前，清空默认目录内的 `*.sarif`；仅作用于默认目录，用户通过 `report-dir` 显式指定的目录不做清理（业务资产）。清理失败仅告警不阻断。
- **等价性**：PR 事件本就不生成/收集报告，清醒后无行为差异；版本级事件只清理"上一次任务遗留"，本次任务自身生成的报告在清理之后才写入，不受影响。
- **验证（Run #601，绿）**：workflow 预置 `stale-from-previous-job.sarif` 后运行，日志出现
  `[INFO] 已清理历史残留 SARIF 报告 1 个: /tmp/pre-commit-reports/`，种子文件未被收集。

## 二、#48 外部可控内容注入伪造日志行

- **位置**：`index.js` 的 `exec()` / `execFile()` / `runPython` 参数打印 / `--files` 提示 / `检测到自定义参数` 共 5 处日志输出点
- **核实**：真实。`extra_args`、文件名、命令参数均含外部可控内容，若其中带 `\r\n`，可在 CI 日志中伪造独立行。
- **整改**：新增 `sanitizeLogValue()`，剔除 `\r`、`\n` 及不可见控制字符（`\u0000-\u0008`、`\u000b`、`\u000c`、`\u000e-\u001f`、`\u007f`），5 个日志点全部接入。正常单行内容清洗后保持不变。
- **等价性**：只影响日志文本渲染，不改变传入 pre-commit 的实际参数，不改变退出码与报告内容。
- **验证（Run #604，预期红）**：注入 `extra_args = "--all-files\n--injected-marker"`（原始为两行），日志实际输出
  `[INFO] 检测到自定义参数: --all-files--injected-marker`、`> python -m pre_commit run --all-files--injected-marker`，
  均为单行；随后因参数非法由 pre-commit 报 `unrecognized arguments` 并按门禁失败退出——红色由注入的畸形参数导致，属预期。
- **旁证**：非 `--` 开头的注入内容会先被既有 `extra_args` 白名单拦截（`[ERROR] Invalid extra_args: ... Only -- arguments are allowed.`），与 #48 的日志清洗构成两层防护。

---

## 三、验证与回退

| 项 | 内容 |
|---|---|
| 统一测试分支 | `fix-security-remediation`（26eeaa0，revert 掉无关的 gc_token 改造后仅含 #43+#48） |
| 端到端验证 | Run #601（绿，验证 #43）、Run #604（预期红，验证 #48） |
| 产物一致性 | `npm run package` 重建 `dist/index.js`，与源码调用点一一对应（`clearStaleDefaultReports` / `sanitizeLogValue` 各 8 处） |
| 回退方式 | 两分支均为单提交，`git revert` 即可；测试分支可直接 revert 对应 merge |
| 与 gc_token 改造的关系 | gc_token 移除属独立需求，未纳入本批整改；测试仓验证时仍传 `gc_token: secrets.GC_TOKEN` |
