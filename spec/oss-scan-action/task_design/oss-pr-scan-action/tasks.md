# oss-pr-scan-action — 实现任务

## 进度: 8/8 complete（PR 级插件已完成并由 workflow 实跑验证）

- [x] Task 1: 搭建插件目录骨架（oss-pr-scan-action/ + package.json + action.yml + .gitignore）
- [x] Task 2: 实现 index.js 核心（inputs 解析 + trivy 探测/扫描 + JSON 解析统计 + 阈值判定 + Step Summary + core.setFailed）
- [x] Task 3: 编写单测（mock trivy 输出：有高危/全部通过/空结果/部分字段缺失）
- [x] Task 4: ncc 构建 dist/index.js
- [x] Task 5: README.md（用法 + 输入参数 + 判定规则）
- [x] Task 6: `.pre-commit-config.yaml`（代码规范钩子）
- [x] Task 7: `.gitcode/workflows/oss-pr-scan.yml`（push:master + workflow_dispatch + pull_request 自测）
- [x] Task 8: 质量门禁（npm test 8/8 通过 + pre-commit 通过）+ 提交 commit

### 开发中补充/修正（已并入）

- [x] 执行机 trivy 环境确认（版本级机 a959 vs PR 级机 7dbc，见 design.md）
- [x] 移除 `--skip-db-update`，对齐原脚本，漏洞库过期由 trivy 自动更新（commit `468b4c8`）
- [x] 定位老分支漏报根因（详见对话回顾：测试跑错执行机 + 扫全量分支而非预合并）
- [ ] 版本级插件 `oss-version-scan-action`（待开发，确认分支/是否建 issue 语义）

## 验证方式

- 单测：`npm test`（覆盖解析与判定逻辑）
- 本地构建：`npm run build`（ncc 打包 dist）
- workflow 自测：push 到 master 触发 oss-pr-scan.yml，在 openlibing-test 仓跑通扫描并看 Step Summary
- 钩子：pre-commit（yaml/json/md 格式 + gitleaks）

## 生成前约束

- [ ] 只修改 openlibing-test/oss-scan-action + openlibing-docs/spec/oss-scan-action
- [ ] 遵循 pre-commit-action 的 node 调 CLI 风格（execFileSync，不用 docker）
- [ ] 无无关重构 / 格式化 churn
- [ ] 无硬编码凭据 / 敏感信息
- [ ] 行为变化有单测覆盖（解析 & 判定核心逻辑）
- [ ] Commit 规范：type(scope) + Co-authored-by + Generated-by
