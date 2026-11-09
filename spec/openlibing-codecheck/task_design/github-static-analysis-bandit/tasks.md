# Tasks：静态代码分析工具 bandit 接入 GitHub Actions

## 1. 前置核对

- [x] 华为云 IAM `GitHubActions` 身份提供商、`github-actions` 信任委托可用
- [x] OBS 桶 `openlibing-github-action` 与后端桶白名单确认
- [x] `upload-sarif-action@source-platform-detection`、`pre-commit-action@main` 分支可用
- [x] GitCode 侧 `test-bandit-scan` 参照实现与 bandit 1.9.4 SARIF 链路确认

## 2. 演示仓搭建（bandit-full-scan-demo）

- [x] 被扫样例：`demo/insecure_demo.py`（9 类常规风险）、`demo/safe_demo.py`（安全对照，零检出）、`demo/high_risk_demo.py`（3 条 HIGH/HIGH：B605/B701/B501）
- [x] 规则单一事实源 `.bandit.yml`（YAML，bandit 1.9.x `-c` 仅认 YAML/TOML）
- [x] `.pre-commit-config.yaml`：默认 stage 拦截 hook + manual stage `bandit-sarif` 直出 hook（`additional_dependencies` 补 `sarif-om`/`jschema-to-python`）
- [x] `.github/workflows/bandit-scan.yml`：全量扫描（手动 / push main / schedule）
- [x] `.github/workflows/bandit-precommit.yml`：pre-commit 集成（手动 / push main / PR 门禁）
- [x] README 风险声明与检出说明

## 3. 迭代修复（实测驱动）

- [x] GitHub 版 pre-commit-action `extra_args` 校验：改等号形式 `--hook-stage=manual`
- [x] GitHub 版 pre-commit-action 不预创建 report 目录：workflow 补 `mkdir -p`，消除日志解析兜底退化
- [x] 退出码语义细化：rc>=2（运行错误）直接失败防静默假绿，rc=1（有检出）继续上传
- [x] pre-commit 版本固定 4.6.0（与 4.x stages 语义前提一致）
- [x] safe_demo 移除触发 B603/B404 的 subprocess 示例，检出口径修正为 12 条 / 12 类（9+3）

## 4. 全链路验证

- [x] 两条工作流 success（最终 commit `10bf370`）
- [x] 日志核对：来源标记 `GITHUB_ACTION`、OIDC 换证 `GitHubActions`/`github-actions`
- [x] OBS 上传：桶 `openlibing-github-action`，key 含 owner/repo/runId
- [x] 回调 `/codescan/v1/result/receive` 返回 `{"code":200,"msg":"success"}`
- [x] 原生 SARIF 链路：无日志解析兜底
- [ ] beta 库 `static_alarm_scan_run` 入库核对（阻塞：本机到 beta 库网络不通，查询脚本已备好）
- [ ] beta 前端 GitHub 平台筛选与高危严重度展示目检（待人工）

## 5. 文档归档

- [x] spec 三件套（proposal.md / design.md / tasks.md）落盘 openlibing-docs 并提 PR
- [ ] docs PR 评审合入（PR #1316，评审人 ozvale）
- [ ] docs 用户文档（bandit README GitHub 差异小节 + demos 示例，后续 US）
