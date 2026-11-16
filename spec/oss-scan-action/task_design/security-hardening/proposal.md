# OSS Scan Action 安全加固（security-hardening）

## 需求背景

漏洞挖掘系统（argus-security-audit / oss-scan-action 两批导出，共 15 份报告）发现并经源码核验确认 6 项代码级缺陷。维护者评审后确认纳入修复范围（对应的 runner 环境/workflow 配置类 2 项已拒绝关闭，见 #6、#12）。

关联业务 Issue：

- https://gitcode.com/openlibing/trivy-action/issues/7 （部分接受：仅提示，不阻断）
- https://gitcode.com/openlibing/trivy-action/issues/8 （部分接受：仅提示，不阻断）
- https://gitcode.com/openlibing/trivy-action/issues/9 （接受）
- https://gitcode.com/openlibing/trivy-action/issues/10 （接受）
- https://gitcode.com/openlibing/trivy-action/issues/11 （接受）
- https://gitcode.com/openlibing/trivy-action/issues/13 （部分接受：仅提示与口径说明，不强制拦截）

业务仓：`openlibing/trivy-action`（本地目录 `oss-scan-action`）
变更分支：`fix-oss-scan-security`

## 功能描述

### 做

1. **#7 Maven 预解析失败提示**：`runMavenResolve` 失败（mvn 缺失 / 离线+在线双失败 / 超时）时，在日志与 Step Summary 明确提示“本次仅覆盖直接依赖，传递依赖漏洞可能漏检”。不新增门禁阻断。
2. **#8 无结果文件提示**：`runTrivyScan` 未产出结果文件时，日志与 Summary 醒目提示“本次扫描无有效结果，不可视为无风险”。不新增门禁阻断。
3. **#9 临时文件安全**：结果文件改入 `mkdtempSync` 创建的 0700 专属目录；排他创建（`open 'wx'`）或 lstat 校验；读取前校验 `isFile()` 与属主；清理放入 `finally` 同步执行；重试路径重建目录。重打包两个 dist。
4. **#10 Step Summary Markdown 转义**：新增统一 `escapeMarkdownCell` / 围栏转义；`itemsToMarkdown`、`packageListToTable`、`licenseListToTable`、`softwareListToTable`、`dependencyTreeToText` 输出与 `pyNote` 等动态字段统一转义；依赖树围栏防闭合。重打包两个 dist。
5. **#11 日志注入防护**：新增 `sanitizeLog`（`\r`/`\n`→空格，行首 `::`→`: :`），覆盖 pyNote、依赖树、SBOM 清单等全部外部可控日志输出。
6. **#13 无修复版本漏洞提示**：对官方暂无修复版本的 CRITICAL/HIGH 漏洞，在日志与 Summary 提示；概览注明门禁仅统计有修复版本，避免“HIGH=N + 通过”误导。不强制 `--ignore-unfixed`、不阻断。
7. **Python 依赖提示（用户补充）**：依据《Python 全量依赖锁定文件生成踩坑与 SOP（uv 方案）》更新提示：按目录判断，同目录存在 `uv.lock` / `poetry.lock` / `Pipfile.lock` 任一全量锁文件则不提示；仅有 `requirements*.txt` / `Pipfile` / `pyproject.toml` / `setup.py` / `requirements.lock` 等声明文件时提示。提示给出两条路径：全量覆盖 `requirements.txt`（`uv pip compile` / `pip freeze`）或使用 `uv.lock`；明确 `requirements.lock` 不被 trivy 识别、不能抑制提示，避免 `requirements.txt` 与 `uv.lock` 并存导致重复统计；多个 requirements 目录需各自生成。
8. **前端锁文件提示（用户补充）**：依据《前端仓全量漏洞扫描经验与 SOP》，检测到 `package.json` 但同目录缺少 trivy 支持的锁文件（`package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` / `bun.lock`）时，在日志与概览提示生成并提交锁文件，避免仅有 `package.json` 时 trivy 不扫描依赖导致“0 漏洞”静默漏检；无依赖声明的脚本型 `package.json` 与 `node_modules` 不提示。
9. **CI 门禁修复（用户补充）**：
   - Pre-commit：新增 `.prettierrc` / `.prettierignore` 与 eslint 依赖、`eslint.config.js`，按 prettier 3.9.5 统一格式，修复 Prettier 自动改写与 `pnpm exec eslint: Command "eslint" not found`。
   - UT：checkout 增加 `fetch-depth: 0`，修复浅克隆导致 diff-cover 计算 `origin/master...HEAD` 报 `no merge base`；为 `checkTrivy` / `runTrivyScan` / `scan` 增加可注入 exec（生产默认不变），补充 6 组 `scan()` 主流程集成测试，将增量覆盖率从 59% 提升至 98%。
   - UT Step Summary 隔离：两个单测文件启动时将 `ATOMGIT_STEP_SUMMARY` 指向临时文件并在退出时清理；UT workflow 测试步骤同样设置临时 summary，避免 Maven 降级提示等测试副作用污染 UT job 汇总。

### 不做

- 不修改 runner 部署、Action 引用方式（#6、#12 已拒绝关闭）；仅为 UT 门禁修复 checkout 深度与测试 summary 隔离，不改变 runner 环境。
- 不改变现有门禁阈值语义与阻断逻辑（#7/#8/#13 仅增加可见性，不新增 setFailed）。
- 不做与本次加固无关的重构或格式化。

## 验收标准

- [ ] #7：预解析失败三类路径（mvn 缺失 / 双失败 / 超时）在 Summary 与日志均出现“仅直接依赖”提示；门禁判定不变；单测覆盖。
- [ ] #8：无结果文件时出现“无有效结果”提示；正常写结果路径行为不变；单测覆盖。
- [ ] #9：预置 symlink/同名文件时写入返回 EEXIST 或写入隔离目录；成功/失败/解析失败三路径无残留；单测覆盖；dist 同步。
- [ ] #10：注入载荷（`|`、换行、`[x](url)`、`<img>`、连续反引号、CRLF）进入 Summary 后无可渲染语法存活；普通输出不变；单测矩阵；dist 同步。
- [ ] #11：恶意目录名/组件名（含换行 + `::`）不再产生 `::` 起始物理行；普通输入不变；边界用例通过。
- [ ] #13：无修复版本 CRITICAL/HIGH 在日志与 Summary 有提示与口径说明；门禁仍仅统计有修复版本；单测覆盖。
- [ ] Python 提示：同目录无 `uv.lock`/`poetry.lock`/`Pipfile.lock` 且有依赖声明文件时，概览与日志提示全量锁定方式；有全量锁文件则不提示；`requirements.lock` 不抑制提示；单测覆盖。
- [ ] 前端提示：`package.json` 无支持锁文件时概览与日志提示生成锁文件；有任一锁文件、无依赖声明或缺 `package.json` 时不提示；单测覆盖。
- [ ] Pre-commit：Prettier / ESLint 均通过；`.prettierrc` / `.prettierignore` / `eslint.config.js` 生效；dist 满足 trailing-whitespace/end-of-file 钩子。
- [ ] UT：checkout 使用完整历史，`no merge base` 消失；增量行覆盖率 ≥ 80%（实际 98%）；单测 63/63、52/52 通过。
- [ ] UT Summary：单测与 workflow 测试步骤均隔离 `ATOMGIT_STEP_SUMMARY`，UT job 不再出现 Maven 降级提示等测试副作用。
- [ ] 两个 action 的现有测试全部通过；`ncc build` 成功且 dist 含新逻辑。

## 影响范围

- 代码：`shared/index.js`（两 action 共享引擎）
- 产物：`oss-pr-scan-action/dist/index.js`、`oss-version-scan-action/dist/index.js`（重打包）
- 测试：`oss-pr-scan-action/test/test-oss-pr-scan-action.test.js`、`oss-version-scan-action/test/test-oss-version-scan-action.test.js`
- CI/工具链：`.gitcode/workflows/ut.yml`、`.prettierrc`、`.prettierignore`、`eslint.config.js`、`package.json` / `package-lock.json`
- 文档：本 proposal / design / tasks（docs 仓）
