# ut-check-action — 技术设计

## 方案概述

将「流水线 UT 检查 + 行覆盖率门禁」链路（执行机 shell/python 脚本 + 目标仓 `scripts/ut-report.sh`）迁移为**单一自包含 GitCode `node16` Action 插件**。插件在目标仓 `.gitcode/workflows/` 中以 `uses: openlibing-test/ut-check-action@master` 调用，runner 本地执行 `mvn clean test` → 解析 surefire + JaCoCo → 门禁判定 → Step Summary 输出。

## 架构决策

| 决策             | 选择                                                                                             | 原因                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 插件形态         | `node16` + `dist/index.js`（ncc 打包）                                                           | 与 oss-scan-action / sca-action / pre-commit-action 一致，GitCode 当前仅支持 node16                                                               |
| 调 mvn           | `child_process.execFileSync` 调 runner 预装 mvn（可配置 mvn 路径/args）                          | 对齐 pre-commit-action 调 CLI 范式；runner 已预装 JDK/Maven                                                                                       |
| 单插件 vs 双插件 | **单插件**（PR/版本级共用，差异用 inputs）                                                       | 两脚本核心逻辑一致（差异仅环境路径/settings），收敛为参数，避免重复维护                                                                           |
| 凭证             | **无 AK/SK、无硬编码**；私仓凭据经 workflow `env:` 注入，子进程继承透传                          | `.mvn/settings.xml` 用 `${openlibing_mvn_repo_username}/${openlibing_mvn_repo_password}` 占位，Maven Linux 直接读环境变量；对齐 pre-commit-action |
| settings 策略    | 默认尊重项目级 `.mvn/maven.config`（`-s.mvn/settings.xml`）；可选 `mvn-settings` 显式指定        | 优先级：命令行 `--settings` > 项目级 `.mvn` > 用户级 `~/.m2` > 全局；默认不注入保持项目级优先                                                     |
| 测试统计         | 解析 `target/surefire-reports/TEST-*.xml`（`@actions/glob`+`fs` 读属性）                         | 替代 bash grep 逐行解析，跨平台稳定                                                                                                               |
| 覆盖率解析       | **内聚 jacoco 解析**：解析 `target/site/jacoco/index.html`（`parse_jacoco_result.py` 逻辑改 JS） | 不再依赖执行机预置脚本，插件自包含可移植                                                                                                          |
| 语义增强         | 「失败+错误用例数>0 即阻断」作为显式门禁（`require-ut-pass`）                                    | 现有 ut-report.sh 仅 print 不阻断，需求明确要统计失败个数并阻断                                                                                   |
| 结果输出         | Step Summary（`ATOMGIT_STEP_SUMMARY`）                                                           | 平台支持，展示测试统计 + 覆盖率 + 结论                                                                                                            |
| 日志             | `debug` 输入控制 verbose；mvn 输出 captured/限制长度                                             | 避免大日志刷屏与敏感信息回显                                                                                                                      |

## 核心逻辑（index.js）

```
inputs: project-dir(.) / mvn-args(clean test)
        / line-coverage-gateway(20) / exclude-packages(config,entity,dto,vo,exception,constant)
        / require-ut-pass(true) / cobertura? (本期不做)
        / debug(false)

run():
 1. 解析 inputs（含 ATOMGIT_REPOSITORY/REFSAPP 做日志上下文）
 2. 定位项目根 project-dir（默认 .），cd 进去
 3. 校验 mvn 可用（execFileSync('mvn','--version')，失败可配置 mvn-path）
 4. 收集环境变量：继承 process.env，透传 workflow env（mvn repo 凭证无需显式读取）
 5. 执行测试:
    mvn <mvn-args>   // 默认 'clean test'；settings 由 .mvn/maven.config 或 mvn-settings 决定
    捕获 exit code + 输出（不因失败直接 setFailed，先解析报告）
 6. 解析 surefire: target/surefire-reports/TEST-*.xml
    → totalTests = Σ tests; totalFailures = Σ failures; totalErrors = Σ errors; totalSkipped = Σ skipped
    → 空目录/无报告按 0 处理
 7. 解析 jacoco: target/site/jacoco/index.html
    → 读 table#coveragetable.tfoot（total_lines / missed_lines）
    → lineCoverage = (total_lines - missed_lines) / total_lines * 100（total=0 → 0）
    → 缺失 index.html → error + setFailed（测试失败或未配置 jacoco）
 8. 门禁判定:
    blockByTests = requireUtPass && (failures + errors > 0)
    blockByCoverage = lineCoverage < lineCoverageGateway
    pass = !blockByTests && !blockByCoverage
 9. Step Summary:
    测试统计表（用例/失败/错误/跳过/类数）
    + 覆盖率表（行覆盖率/门禁）
    + ✅/❌ 结论（是否因失败用例/覆盖率阻断）
 10. !pass → core.setFailed
```

## 与现有脚本的细节对齐

| 现有脚本                                                       | 插件实现                                               |
| -------------------------------------------------------------- | ------------------------------------------------------ |
| `ut-report.sh` `mvn clean test` tee+grep                       | JS `execFileSync('mvn', args)`，捕获输出               |
| ut-report.sh surefire grep `tests=/failures=/errors=/skipped=` | `fs` 读 XML 属性 prop 累加（空保护）                   |
| `parse_jacoco_result.py` BeautifulSoup 读 index.html tfoot     | JS HTML 解析总行/未覆盖行（字符串匹配/简易 DOM）       |
| `LINE_COVERAGE_GATEWAY` env 默认 20                            | input `line-coverage-gateway` 默认 20                  |
| 排除 config/entity/dto/vo/exception/constant                   | input `exclude-packages`（解析 index.html 时按包过滤） |
| 版本级 `sed` 注入 `--settings /opt/maven/settings.xml`         | input `mvn-settings`（指定时拼进 mvn args）            |
| ut-report.sh 失败仅 print 不阻断                               | **阻断**：`failures+errors>0` → setFailed              |
| PR 级 tee 到 WORKSPACE 日志                                    | Step Summary + debug 日志                              |

## 涉及文件

| 文件                    | 操作             | 说明                                     |
| ----------------------- | ---------------- | ---------------------------------------- |
| `action.yml`            | 新增             | 插件元数据（inputs/runs）                |
| `index.js`              | 新增             | 主入口（run 流程）                       |
| `lib/parse-surefire.js` | 新增             | surefire TEST-*.xml 解析                 |
| `lib/parse-jacoco.js`   | 新增             | jacoco index.html 覆盖率解析             |
| `lib/gate.js`           | 新增             | 门禁判定 + Step Summary 组装             |
| `package.json`          | 新增             | `@actions/core` + `@vercel/ncc` + 测试   |
| `dist/index.js`         | 新增（构建产物） | ncc 打包                                 |
| `test/*.test.js`        | 新增             | 解析/判定单测（mock surefire/jacoco）    |
| `README.md`             | 新增             | 使用文档 + workflow 示例（env 注入示例） |

> 单插件、无需 shared 目录；如后续需 PR/version 双入口再抽取。结构参照 oss-scan-action 单目录交互（根 action.yml）。

## 风险 & 缓解

| 风险                                            | 缓解                                                                          |
| ----------------------------------------------- | ----------------------------------------------------------------------------- |
| jacoco HTML 结构版本差异/中文字段               | 解析 tfoot 固定 13 列；字符串兜底；单测 mock 真实结构                         |
| mvn 未预装                                      | `mvn --version` 探测，缺失报清晰错误（提示 runner 预装或配置 mvn-path）       |
| 多模块仓库（如 openlibing-sync）jacoco 在子模块 | input `project-dir` 指向子模块；或 `jacoco-report-dir` 显式指定               |
| 测试失败导致 index.html 不生成                  | 明确报错 setFailed（提示 jacoco 未生成）                                      |
| 大量测试输出刷屏                                | mvn 输出 captured + 仅 summary 可见 + debug 控制                              |
| 私仓依赖解析失败                                | mvn args 由调用方控制（可用 `-U` 等）；错误消息提示检查 workflow env/私仓可达 |

## 跨仓影响

- 生产仓（openlibing/*）**不受影响**——本插件在 `openlibing-test` 测试组织开发验证。
- 未来接入生产：在各目标仓 `.gitcode/workflows/` 增加 workflow 引用本插件，并配套 `env:` 注入私仓凭证。
