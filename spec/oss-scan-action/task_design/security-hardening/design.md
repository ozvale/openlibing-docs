# security-hardening — 技术设计

## 方案概述

在不改变门禁阻断语义的前提下，对 `shared/index.js` 做安全加固与提示增强，并修复 Pre-commit / UT 门禁，最后通过集成测试把 PR 增量行覆盖率提升到 80% 以上。

## 关键决策

| 决策            | 选择                                                                                                                | 原因                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 测试可注入性    | `checkTrivy` / `runTrivyScan` / `scan` 增加可选 `execFn`，默认仍用 `execFileSync`；`scan` 从内部 `meta.execFn` 读取 | 单测不依赖真实 trivy/mvn，跨平台可跑，生产入口不传参行为不变                |
| 临时结果文件    | `mkdtempSync` 0700 专属目录 + `open('wx')` 排他创建 + `O_NOFOLLOW`/`fstat`/属主校验 + `finally` 清理                | 防止可预测路径、符号链接写穿与结果替换；`hasResultContent` 兼容预创建空文件 |
| Summary 转义    | 统一 `escapeMarkdownCell`（`&                                                                                       | \` [ ] ( ) < > !`、换行）+ `getReportFence` 动态围栏                        | 从输出面阻断 Markdown/HTML 注入与围栏闭合 |
| 日志注入        | `sanitizeLog`：换行→空格、行首 `::`→`: :`                                                                           | 阻止 PR 可控内容被 runner 解析为工作流命令                                  |
| Python 提示     | 按目录判断：同目录有 `uv.lock`/`poetry.lock`/`Pipfile.lock` 任一则不提示；`requirements.lock` 不抑制提示            | 对齐 uv SOP：requirements 仅直接依赖，`requirements.lock` 不被 trivy 识别   |
| 前端提示        | `package.json` 声明了依赖且同目录无 4 类锁文件时提示                                                                | trivy 仅解析锁文件，仅 package.json 会静默 0 漏洞                           |
| Prettier/ESLint | 新增 `.prettierrc`、`.prettierignore`、`eslint.config.js` 与 eslint 依赖                                            | pre-commit 钩子要求；忽略 dist/package-lock 避免生成物格式化 churn          |
| UT 历史         | checkout `fetch-depth: 0`                                                                                           | diff-cover 三点 diff 需要 merge base，浅克隆会失败                          |
| UT Summary      | 测试文件与 workflow 测试步骤均把 `ATOMGIT_STEP_SUMMARY` 指向临时文件                                                | 防止 Maven 降级提示等测试副作用污染 UT job 汇总                             |

## 涉及文件

| 文件                                                                                      | 操作      | 说明                                                    |
| ----------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------- |
| `shared/index.js`                                                                         | 修改      | 安全加固、提示、转义、日志清洗、exec 注入 seam          |
| `oss-pr-scan-action/test/test-oss-pr-scan-action.test.js`                                 | 修改      | 安全/提示/覆盖率测试 + `scan()` 集成测试 + Summary 隔离 |
| `oss-version-scan-action/test/test-oss-version-scan-action.test.js`                       | 修改      | 同上（不含 scan 集成测试）                              |
| `oss-pr-scan-action/dist/index.js`、`oss-version-scan-action/dist/index.js`               | 重打包    | `ncc build` 产物                                        |
| `.gitcode/workflows/ut.yml`                                                               | 修改      | `fetch-depth: 0`、测试步骤 Summary 临时路径             |
| `.prettierrc`、`.prettierignore`、`eslint.config.js`、`package.json`、`package-lock.json` | 新增/修改 | Pre-commit 工具链对齐                                   |

## 关键取舍

1. **提示类不阻断**：Maven 预解析失败、trivy 无结果文件、官方未修复高危漏洞均只提示，不新增 `setFailed`。理由：多属执行机环境或上游无修复方案，不应由代码提交人承担；nightly 流水线对存量问题有兜底。
2. **格式化与覆盖率**：prettier 重排使 `shared/index.js` 大量行被 diff 视为“变更行”，增量覆盖率会向全文件覆盖率靠拢；通过 6 组 `scan()` 集成测试把覆盖率提升到 98%，而非降低阈值。
3. **ESLint 最小规则集**：先保证钩子可用（`rules: {}` 仅做语法校验），避免一次性引入大量历史告警；后续可逐步加规则。
4. **生成物忽略**：`dist/` 与 `package-lock.json` 加入 `.prettierignore`，避免 ncc/锁文件被反复格式化。

## 风险与缓解

- `meta.execFn` 仅供测试注入，生产入口 `index.js` 不传；默认路径仍为 `execFileSync`，不存在外部输入注入 exec 的入口。
- Windows 无 `O_NOFOLLOW` 时退化为 `fstat` 校验；CI/生产 runner 为 Linux，可完整生效。
- `fetch-depth: 0` 会增加 checkout 时间；本仓库历史较小，影响可接受。
- 新增提示会增加 Summary/log 内容，但不改变门禁判定。

## 跨仓影响

- 下游使用 `oss-pr-scan-action` / `oss-version-scan-action` 的仓库会看到新增提示，无需修改 workflow 或配置。
- `main` 分支仅同步代码与测试（无 `ut.yml` 与新版 pre-commit 配置），不同步 workflow/工具链文件。
