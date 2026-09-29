# Proposal: 将 issue-scanner lcsca 扫描能力迁移至 openlibing-sca tools 目录

- **仓库**: openlibing/openlibing-sca
- **业务 Issue**: https://gitcode.com/openlibing/openlibing-sca/issues/78
- **交付 PR**: https://gitcode.com/openlibing/openlibing-sca/pull/313（dev_scanner -> release_20260923，已合入）
- **流程模式**: Full
- **开发分支**: dev_scanner（业务仓）/ spec-openlibing-sca-migrate-issue-scanner-lcsca（docs 仓）
- **日期**: 2026-09-17（交付 2026-09-23）

## 1. 需求背景

`openlibing-sca` 的本地 copyright/license 扫描能力依赖独立仓库 `openlibing/openlibing-sca-issue-scanner`：

- 镜像构建时（Dockerfile L76-79）执行 `git clone -b scancode https://gitcode.com/openlibing/openlibing-sca-issue-scanner.git ./issue-scanner`，clone 前需写入 `GIT_USERNAME`/`GIT_PASSWORD` 构建凭证；
- 运行时由 `OpenPersonDMScanDMServiceImpl#getCopyrightAndLicense` 通过 `ProcessBuilder` 在扫描工具工作目录下执行 `python src/command.py -m lcsca <path>`，解析其 stdout JSON 得到扫描结论。

当前问题：

1. **构建链路已断裂**：远端 `scancode` 分支已被删除（仅存 master / dev_20260730），现有 Dockerfile 构建必然失败；
2. **隐性供应链依赖**：构建依赖外部仓 + 构建凭证，与本仓 `tools/OSSinfo_extraction` 已落地的"工具源码纳入本仓"模式不一致。

## 2. 目标

1. 将 lcsca 扫描所需**最小依赖闭包**源码纳入本仓 `tools/`（最终目录名 `tools/license-scanner`）；
2. Dockerfile 改为 `COPY` + pip install，彻底移除 git clone 与凭证逻辑；
3. Java 侧仅调整工作目录常量（`DMContastName.ISSUESCANNER`），扫描命令与结果解析逻辑零改动；
4. 扫描行为与迁移前一致；迁移过程中顺带完成依赖漏洞修复（42 个 High/Critical 归零）与死代码清理。

## 3. 非目标

- 不迁移 issue-scanner 的 web 服务层（main.py / tornado）、调度层（scheduleUtil.py / APScheduler）、数据统计层（queryBoard.py / queryMeasure.py / dbSyn.py 等）；
- 不修复 issue-scanner 源码自身的既有缺陷（如 `scaResult` 中 `scaResult` 变量在异常路径下未初始化、`subprocess.Popen.poll` 误用等），保持原样迁移以保证行为一致；
- 不改动 `PrCommonName.ISSUESCANNER` 的引用关系（定义未使用，但既有测试断言其值，随本次一并同步路径）。

> 范围调整（交付期新增）：迁移验证过程中发现 `repoDb`/`prSca`/`itemLicSca`/`takeRepoSca` 四个 DB 模块在 lcsca 路径为死代码（见 design.md §4），最终 PR 将其整体删除并同步裁剪 requirements，属"行为一致性"原则下的死代码清理，不改变 lcsca 扫描行为。

## 4. 验收标准（已随 PR #313 合入验证）

| #   | 标准                                                                                 | 验证方式                             | 状态                 |
| --- | ------------------------------------------------------------------------------------ | ------------------------------------ | -------------------- |
| 1   | `tools/license-scanner/` 包含 lcsca 最小闭包 15 个源文件 + requirements.txt（16 项） | 文件清单比对                         | ✅                   |
| 2   | `python src/command.py -m lcsca <path>` 在依赖安装后可运行并输出 JSON                | 容器内端到端扫描                     | ⏳ PR 测试计划遗留项 |
| 3   | Dockerfile 无 git clone / git-credentials / GIT_USERNAME / GIT_PASSWORD 残留         | 文本检查 + docker build              | ✅（构建通过）       |
| 4   | `DMContastName.ISSUESCANNER == "tools/license-scanner"`，相关单测更新后全部通过      | `python scripts/run-mvn.py` 执行单测 | ✅（4/4）            |
| 5   | Java 侧 ProcessBuilder 命令、stdout JSON 解析逻辑无改动                              | code review                          | ✅                   |
| 6   | pip 依赖解析无冲突，漏洞依赖升级后 High/Critical 归零                                | Docker 构建 + 依赖审计               | ✅                   |

## 5. 风险与约束

- **依赖冲突风险**：scancode-toolkit 31.0.1 对 click、spdx-tools 等有版本约束，裁剪 requirements 时必须保留这些 pin（已核实）；
- **依赖升级跨度**：urllib3 1.x → 2.x 等升级跨度较大，已核对代码 API 兼容性，最终以容器内端到端扫描确认（PR 测试计划遗留项）；
- **镜像内路径变更**：issue-scanner 工作目录由 `issue-scanner` 变为 `tools/license-scanner`，Java 调用侧常量已同步；若有外部脚本硬编码旧路径需注意；
- **行为一致性**：`CommSca` 不再触库（DB init 与 DB 模块已删除），lcsca/repo/local 三条实际路径行为不变；部署环境不再依赖 `MYSQL_*` 环境变量；
- **commit 体量**：19 个源文件约 5000+ 行，按"源码迁移 / Dockerfile / Java 常量与测试"拆分说明（见 design.md §6）。
