# 代码度量指标插件支持 GitHub — 实现任务

## 进度: 32/34 complete

## 1. 平台上下文适配

- [x] 新增 `GITHUB_ACTIONS` 平台判定，判定后只读取对应平台变量，不跨平台混用
- [x] 移除 `PIPELINE_RUN_ID` / `PIPELINE_RUN_NUMBER` 旧兼容，运行信息统一取平台标准变量
- [x] PR 事件按目标分支归属（`GITHUB_BASE_REF` / `ATOMGIT_BASE_REF`，不混用 `HEAD_REF`）
- [x] 仓库地址优先取本地 git，失败时用 `GITHUB_SERVER_URL + GITHUB_REPOSITORY` 兜底
- [x] 运行 ID / 编号 / 提交 SHA / 工作流名称按平台取值
- [x] 修复 GitHub PR 事件检出游离 HEAD 时 `branchName` 上报为 `HEAD` 的问题（`resolveBranchName` 回落目标分支）

## 2. 认证适配

- [x] GitHub 环境切换 OIDC 身份提供商为 `GitHubActions`、信任委托为 `github-actions`（SDK 0.0.7 平台感知默认值）
- [x] 保持 OIDC / AK-SK 双链路选择逻辑不变
- [x] AK/SK 降级为内部兼容能力，README 不再对外说明

## 3. 结果展示

- [x] 摘要构建抽离为 `src/utils/summary.js`，便于单测覆盖
- [x] GitHub 写 `GITHUB_STEP_SUMMARY`，GitCode 写 `ATOMGIT_STEP_SUMMARY`
- [x] 保留 GitCode `ATOMGIT_OUTPUT` 输出面板
- [x] 表格单元格转义 `|` 并压平换行，避免用户可控字段破坏 Markdown 表格
- [x] 保留 `core.setOutput` 的 5 项指标输出
- [x] 详情链接与流水线链接仅放行 http(s)，特殊字符做百分号编码

## 4. 依赖与配置清理

- [x] 移除 `config-file` 输入与文件加载逻辑
- [x] 移除 `js-yaml` 依赖与死配置（`threshold` / `parallel` / `verbose`）
- [x] `winston` 替换为 `@actions/core`
- [x] 更新 `package.json` / `package-lock.json`
- [x] 重建 `dist`，体积由约 2784KB 降至 2271KB

## 5. 接入示例与文档

- [x] 新增 `.github/workflows/code-metrics-scan.yml`：OIDC、push 仅 `master`、可选并发控制
- [x] README 增加 GitHub OIDC 接入章节（含 IAM 前置说明）
- [x] README 的 GitHub 示例与 GitCode 示例结构对齐
- [x] 注释说明 `concurrency` 的作用与可选性

## 6. 测试与质量

- [x] 抽取可测纯函数，补充 12 个测试文件、64 个用例
- [x] 新增 `.c8rc.json` 统一覆盖率口径（`src` 全量，排除入口与二进制资产）
- [x] UT 流水线改用 `c8 --all --src=src`，保留 diff-cover 增量门禁
- [x] pre-commit gitleaks 误报治理（allowlist + 行内放行）
- [x] `npm test` 通过
- [x] `pre-commit` 全量通过（prettier / eslint / gitleaks）

## 7. 端到端验证

- [x] GitHub 验证仓 `openlibing-test/code-metrics-action` 工作流运行通过（run 42987841974）
- [x] GitHub 生产镜像仓扫描与摘要输出成功（run 42990956297）
- [ ] GitHub 生产镜像仓 OIDC 换证与上报成功（IAM 信任策略已修正新格式 `sub`，待复验）
- [ ] GitCode master 使用 `v1.0.4` 的 `code-metrics-scan` 回归运行（最近一次 #105 在初始化步骤失败，未进入插件步骤，待平台侧排查）
