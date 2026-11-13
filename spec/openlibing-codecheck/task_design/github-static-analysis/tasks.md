# 静态代码分析 GitHub 接入方案与文档 · clang-tidy - 实现任务

## 前置资源

- [x] 华为云 IAM 注册 `GitHubActions` 身份提供商，信任委托 `github-actions`，按 `iss/aud/sub` 限定组织与仓库
- [x] OBS 创建 GitHub 专用桶 `openlibing-github-action`
- [x] 确认后端 OBS 桶白名单与平台识别支持 GitHub 桶
- [x] OIDC SDK 发布 `v0.0.7`，默认按 `GITHUB_ACTIONS` 自动选择提供商与委托

## GitHub 仓库准备

- [x] 创建 `openlibing-test/clang-tidy-full-scan-demo`（示例仓，含被扫代码与 `.github/workflows/`）
- [x] 创建 `openlibing-test/pre-commit-action`（GitHub 适配版 pre-commit 插件）
- [x] 创建 `openlibing-test/upload-sarif-action`（GitHub 适配版 SARIF 上传插件）
- [x] 三个仓设为私有：仅 `openlibing-test` 组织内可引用，跨组织复用需调整可见性或采用模板/复制策略

## upload-sarif-action 改造

- [x] 新增平台判定 `IS_GITHUB = process.env.GITHUB_ACTIONS === 'true'`
- [x] 新增来源标记 `SOURCE_CODE = IS_GITHUB ? 'GITHUB_ACTION' : 'GITCODE_ACTION'`，写入回调 `source` 并打印启动日志
- [x] GitHub 侧在 `getCredentials()` 前切换 OIDC 提供商 `GitHubActions`
- [x] OBS 桶按平台选择：GitHub `openlibing-github-action`、GitCode `openlibing-gitcode-action`
- [x] `action.yml` 移除 `obs-ak` / `obs-sk` / `obs-region` 输入，仅保留 OIDC 免密换证
- [x] 依赖升级到 `@openlibing/huaweicloud-oidc-client` v0.0.7，`package-lock.json` 同步锁定
- [x] 适配 GitHub 输出机制（`GITHUB_OUTPUT`）与运行环境检测
- [x] `npm test`（79 项）与 `pre-commit` 全绿，`ncc` 重建 `dist/index.js`
- [x] 提交并推送 `source-platform-detection` 分支（`05d5ea9e9f9a76497022ccab322f6dc22d827820`）

## pre-commit-action 改造

- [x] 平台判定与 `GITHUB_*` 上下文映射
- [x] 输出通道适配 GitHub Actions（`GITHUB_OUTPUT`）
- [x] SARIF 收集目录与 `sarif-files` 输出在 GitHub 环境下正常工作
- [x] 推送 GitHub 适配分支并供 demo 工作流引用

## demo 仓与工作流

- [x] `.github/workflows/clang-tidy-scan.yml`：workflow 全量扫描，`permissions.id-token: write`
- [x] `.github/workflows/clang-tidy-precommit.yml`：pre-commit 集成，`pre-commit-action` + `upload-sarif-action`
- [x] 预置 `clang-tidy-sarif` 二进制到 `.github/bin/`，执行机不访问外网
- [x] 工作流引用 `openlibing-test/upload-sarif-action@source-platform-detection`（验证版本 `05d5ea9e9f9a76497022ccab322f6dc22d827820`；生产接入应固定该 SHA）

## 运行验证

- [x] `clang-tidy-scan` 运行成功（run 41803721358）
- [x] `clang-tidy-precommit` 运行成功（run 41803725788）
- [x] 日志确认 `[INFO] 来源标记: GITHUB_ACTION`
- [x] 日志确认 OIDC 提供商 `GitHubActions`、委托 `github-actions`
- [x] OBS 对象写入 `openlibing-github-action`，key 含 `{owner}/{repo}/{runId}`
- [x] APIG 回调返回 `{"code":200,"msg":"success"}`
- [x] beta `static_alarm_scan_run` 落库（`category=business` / `pre-commit-report`）
- [x] `pre-commit-action` 无独立单测，通过 `clang-tidy-precommit` demo 工作流（run 41803725788）验证 `GITHUB_*` 上下文映射、`GITHUB_OUTPUT` 与 SARIF 收集

## 文档交付

- [x] `openlibing-docs` 归档 `design.md`（7 章节）与 `prototype.html`，PR #1304 已合入
- [x] `openlibing-docs` 补齐 `proposal.md` / `tasks.md` / `archive.md`
- [x] `docs` 仓 clang-tidy README 新增 `3.6` / `4.7` GitHub Actions 配置
- [x] `docs` 仓新增 `demos/github/clang-tidy-scan.yml`、`clang-tidy-precommit.yml`
- [x] `docs` 仓 full-analysis README 拆分 GitCode / GitHub 双平台样例（`4.2.2/4.2.3`、`4.3.1/4.3.2/4.3.3`），PR #59（待合入 `main`）

## 待办与关联事项

- [x] 后端 `StaticAlarmSourceEnum` 新增 `GITHUB_ACTION` / `GITEE_ACTION`、平台推断与 OBS 白名单（openlibing-codecheck#391，已合入 `release_20261116_iter1`，待随版本发布）
- [ ] 前端来源选项/标签与列表页 GitHub 平台展示适配（openlibing-web 暂无对应 PR，需补充实现并建单跟踪）
- [ ] 用户文档 PR openlibing/docs#59 合入 `main` 主干
- [ ] 按发布顺序完成前后端上线后，由测试执行转测验收
- [ ] 存量 GitCode 工作流移除 `obs-ak` / `obs-sk` / `obs-region` 参数并切换 OIDC 后，补做上传/回调回归验证（本次未执行）
- [ ] demo 工作流的 action 引用由可变分支改为固定 commit SHA（生产接入要求）
- [ ] `api.md` 不适用：本需求无新增/变更对外 HTTP 接口，结果回传复用现有回调接口
