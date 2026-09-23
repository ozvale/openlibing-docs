# ut-check-action — 流水线 UT 检查门禁插件

## 需求背景

openlibing PR/版本级流水线中的「UT 检查 + 行覆盖率门禁」环节，当前由执行机预置 shell/python 脚本串联实现：

- PR 级：runner 预置 `ut-report.sh`（目标仓 `scripts/` 随仓提供）+ 执行机预置 `parse_jacoco_result.py` + 大量环境/权限修复胶水
- 版本级：同上，另通过 `sed` 注入 `--settings`、处理 `openlibing-sync-service` 多模块聚合

现状痛点：

- **重复胶水**：每个 Java 仓都要放一份 `scripts/ut-report.sh`（已发现 339 行/237 行/30 行等多版本），维护成本高、行为易漂移
- **门槛藏在执行机**：覆盖率门禁值 `LINE_COVERAGE_GATEWAY`、解析脚本 `parse_jacoco_result.py` 都在执行机（`/home/ut/scripts/`、`/opt/ut/`），换机即失联，不可移植
- **语义不统一**：UT 失败仅 print 不阻断（ut-report.sh 无 set -e）；只有覆盖率不达标或 jacoco 缺失才阻断

本次需求：将 UT 检查链路插件化为**单一 GitCode Action 插件**（`openlibing-test/ut-check-action`），自包含 `ut-report + jacoco 解析 + 门禁判定`，PR/版本级共用一份核心逻辑，差异收敛为 inputs。

> 本需求在 `openlibing-test` 测试组织开发验证，暂不关联业务 Issue。

## 功能描述

### 做什么

1. 在 `pull_request`（预合并分支）/ `push: master` / `workflow_dispatch` 事件下触发。
2. 检出代码后在**目标仓库根目录**执行 `mvn clean test`（依赖 `.mvn/settings.xml` + 项目级 maven.config 生效），生成 surefire 报告 + JaCoCo 覆盖率（index.html）。
3. 解析 `target/surefire-reports/TEST-*.xml`，统计**用例总数 / 失败数 / 错误数 / 跳过数 / 测试类数**。
4. 解析 `target/site/jacoco/index.html`，计算**行覆盖率**（排除 entity/dto/vo/exception/constant/config 类后），并对齐现有 `parse_jacoco_result.py` 语义。
5. **门禁判定（两个维度，任一不通过即阻断）**：
   - **用例失败数 > 0 → 不通过**（本需求语义增强：现有脚本仅 print 不阻断，本次将「总失败个数>0 视为不通过」作为明确门禁）
   - **行覆盖率 < 门禁值 `LINE_COVERAGE_GATEWAY`（默认 20）→ 不通过**
   - `index.html` 缺失（测试失败/报告未生成）→ 阻断
6. 结论写入 Step Summary：测试统计表 + 覆盖率表 + 通过/未通过结论。
7. 私仓凭证不落插件：由 workflow `env:` 注入 `openlibing_mvn_repo_username` / `openlibing_mvn_repo_password`，透传给 `mvn` 子进程，让 `.mvn/settings.xml` 占位符生效。

### 不做什么

- 不做覆盖率上传 OBS（`upload-ut-action` 职责，不重复）。
- 不调用平台后端 API，不使用 OIDC / AK/SK（本地 mvn + 本地解析，无需凭据认证）。
- 不打包代码、不做 docker 构建（仅 UT 检查）。
- 不创建 Issue、不写仓库、不修代码。
- 不依赖执行机预置脚本（`parse_jacoco_result.py` 内聚进插件；`ut-report.sh` 逻辑由插件 JS 重写，不再要求目标仓带 scripts 脚本）。

## 输入参数（action.yml 草案）

| 参数                    | 必填 | 默认值                                    | 说明                                                 |
| ----------------------- | ---- | ----------------------------------------- | ---------------------------------------------------- |
| `project-dir`           | 否   | `.`                                       | mvn 项目根目录                                       |
| `mvn-args`              | 否   | `clean test`                              | mvn 目标（默认仅测试；如需打包则传 `clean package`） |
| `line-coverage-gateway` | 否   | `20`                                      | 行覆盖率门禁（%），未达标阻断                        |
| `exclude-packages`      | 否   | `config,entity,dto,vo,exception,constant` | 覆盖率计算排除的包名                                 |
| `require-ut-pass`       | 否   | `true`                                    | 【语义增强】失败+错误用例数 >0 即不通过              |
| `jacoco-report-num`     | 否   | `1`                                       | 多模块聚合场景下 jacoco/index.html 数量预期          |
| `debug`                 | 否   | `false`                                   | 调试日志                                             |

> 精确参数名以 design.md 为准，此处为需求级草案。

## 验收标准

- [ ] 插件在预合并分支代码上正确执行 `mvn clean test` 并生成 surefire + JaCoCo 报告
- [ ] 正确统计用例总数/失败/错误/跳过（解析 surefire TEST-*.xml）
- [ ] 正确解析 jacoco index.html 行覆盖率（空报告/缺字段兜底为 0）
- [ ] 【语义增强】失败+错误用例数>0 时 setFailed 阻断
- [ ] 行覆盖率 < 门禁值时 setFailed 阻断
- [ ] index.html 缺失时明确报错并退出
- [ ] 门禁通过时 Step Summary 展示测试统计 + 覆盖率 + 通过结论
- [ ] 私仓凭证仅经 workflow env 注入，插件内无硬编码密钥、不在日志泄漏
- [ ] 目标仓无 `scripts/ut-report.sh` 也能完成 UT 检查（自包含）
- [ ] 单测覆盖解析与判定核心逻辑（mock surefire/jacoco 输出）

## 影响范围

- 新仓：`openlibing-test/ut-check-action`（master 分支直接开发）
- 插件目录：根目录（单插件：action.yml + index.js + dist + package.json + test + shared）
- 本需求仅在 `openlibing-test` 测试组织开发验证，不涉及生产仓 workflow 改动

## 关联

- 迁移基准：PR 级脚本（JDK/Maven 环境修复脱敏为 inputs）+ 版本级脚本（settings 注入收敛为参数）+ 目标仓 `scripts/ut-report.sh`（339 行标准版）+ 执行机 `parse_jacoco_result.py`
- 插件范式：`oss-scan-action`（node16 + ncc + Step Summary）、`pre-commit-action`（node action 调 CLI + env 注入私仓凭证）
