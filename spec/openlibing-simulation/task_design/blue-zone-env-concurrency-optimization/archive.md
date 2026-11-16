# 蓝区环境创建并发优化 — 归档

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-simulation/issues/65
- 业务 PR：
  - [#200](https://gitcode.com/openlibing/openlibing-simulation/merge_requests/200)（已合并，merge commit `47296c1`）：Issue 65 主体交付
  - [#201](https://gitcode.com/openlibing/openlibing-simulation/merge_requests/201)（已合并，merge commit `0153270`）：nightly pre-commit 修复
- docs PR：[#1331](https://gitcode.com/openlibing/openlibing-docs/merge_requests/1331)（分支 `spec-openlibing-simulation-blue-zone-env-concurrency`）

## 交付范围

- 蓝区环境创建耗时优化：taskId 目录隔离、按物理机 IP 维度分布式锁、清理路径三重校验、`t_server_using.config_path`。

## 交付历程

| commit                       | 说明                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| `2269e5c..4bca5c6`（8 个）   | 蓝区并发优化主体：目录隔离、锁、清理校验、changeset、单测适配                         |
| `78b71fc`                    | 修复分支既有单测漂移（427 用例全绿）                                                  |
| `f149a92`                    | 安装脚本源路径 `gamma` → `prod`                                                       |
| `5ce6c82`                    | 新增 121 个单测，diff-cover 26% → 91%                                                 |
| `31163f8`                    | nightly pre-commit 修复（gitleaks allowlist + spotless 格式化，cherry-pick 到新分支） |
| docs `7fac66de` / `a84a29ec` | proposal / design / tasks 与进度更新                                                  |

## 用户自测反馈

| 反馈                                        | 处理                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `install_ub_simulate.sh` 的 flock 改造      | 由用户线下上传脚本，不纳入仓库与验收                                                             |
| 安装脚本源目录需为 prod                     | `Constans.INSTALL_SCRIPT_PATH` 改为 `/home/openlibing-manager/prod/install/script/`（`f149a92`） |
| CI 增量覆盖率门禁 26% 未达标                | 补 121 个单测至 91%（`5ce6c82`）                                                                 |
| nightly pre-commit gitleaks / spotless 失败 | allowlist 排除 `.gitleaksignore`，提交 spotless 格式化结果（`31163f8`）                          |

## 最终验证

- `mvn clean test`：548 个用例，0 失败，0 错误（已核对 `target/surefire-reports`）。
- `diff-cover`（对比 `upstream/master`）：91%，目标 ≥80%。
- `mvn compile spotless:check`：通过。
- PR #200 / #201 的 CI 均通过（`ci-pipeline-passed`）。

## 设计偏差与取舍

- 移除 43 个指向已删除私有方法的失效用例（`setSharePath`/`replaceImage`/`updateYmlContent` 等），未保留空壳测试。
- PR #200 采用「全量 `fork_1106`」方式提交，混入静态检查插件、gitleaks、优雅停机等非 Issue 65 改动，已在 PR 描述中披露。
- 仍有 78 行增量代码未覆盖：真实 SSH 握手/端口转发、`ssh-keyscan`、5 分钟/20~50 分钟超时分支，属单测不可达路径。

## 可复用经验

- **PR 与 nightly 的 pre-commit 配置不同**：`.pre-commit-config.yaml` 只含基础 hooks + gitleaks + ruff；`.pre-commit-nightly-config.yaml` 额外含 spotless / checkstyle / spotbugs / pmd，且 spotless 使用 `apply`，会因格式化改动而失败。提交前应执行 `mvn compile spotless:apply`。
- **`.gitleaksignore` 会被 gitleaks 扫描**：注释里的 `password` DDL 示例、`hmac-sha2-256-etm@openssh.com` 等会误报，需在 `.gitleaks.toml` allowlist 增加 `^\.gitleaksignore$`。
- **增量覆盖率门禁（diff-cover 80%）**：新增主代码必须配套单测；本地可用 `diff_cover.diff_cover_tool.main()` + `--compare-branch upstream/master` 复核。测试重试类方法（如 `acquireLockWithWait`）会真实 `sleep`，失败分支应通过线程中断覆盖，避免单测挂起。
- **surefire `testFailureIgnore=true`**：测试失败不影响 BUILD SUCCESS，必须查 `target/surefire-reports`。

## 归档日期

2026-11-12
