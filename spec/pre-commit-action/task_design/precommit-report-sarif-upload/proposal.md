# precommit-report-sarif-upload

## 需求背景

openlibing 平台使用 pre-commit 对代码仓做静态检查（trailing-whitespace / gitleaks 等钩子）。当前 `pre-commit-action` 插件只执行检查并输出日志，检查结果无法沉淀到平台，缺少可追溯的扫描报告。

用户需要：pre-commit 各工具把扫描报告输出到 CI 机器的临时目录，`pre-commit-action` 插件读取这些报告，统一转成 SARIF 格式上传到 OBS，并通过 APIG 回调 openlibing 后端（codecheck 接口）完成结果归档。

## 功能描述

**做什么**
- `openlibing-cicd-test/.pre-commit-config.yaml` 中为 gitleaks 配置报告输出：`--report-path /tmp/pre-commit-reports/gitleaks.json --report-format json`
- `pre-commit-action` 插件改造：
  - 新增 npm 依赖 `@openlibing/huaweicloud-oidc-client@0.0.5` + `esdk-obs-nodejs@3.26.2`
  - pre-commit 运行后读取报告目录（默认 `/tmp/pre-commit-reports/`，input `report-dir` 可覆盖）
  - 将 gitleaks JSON 报告转成 SARIF 2.1.0
  - OIDC 换临时凭证，上传到 OBS 桶 `openlibing-gitcode-action`，路径 `pre-commit-reports/<仓库名>/<日期>/<runId>/gitleaks.sarif`
  - APIG 回调 codecheck 接口（复用 upload-sarif 的 payload 结构），用 OIDC callApig 方式
  - PR 类型触发（mr/pull_request/note）只做检查，不进行报告上传回调
  - 检查失败仍上传已生成的报告；上传失败仅 warning 不阻断检查结果
  - action.yml 新增输入（report-dir / debug 等）+ 重新 ncc build + README 同步
- `openlibing-cicd-test` 新建 `.gitcode/workflows/pre-commit-report.yml`（push/schedule/workflow_dispatch 触发，声明 `id-token: write`）做端到端验证

**不做什么**
- 不处理不支持报告输出的 pre-commit-hooks 钩子（trailing-whitespace 等）
- 不改动 openlibing-cicd-test 内已有的 pre-commit-action 副本（单独新建 workflow yaml）
- 不做 OBS 桶的新建/权限变更（沿用现有桶）

## 验收标准

- [ ] gitleaks 检查生成 `/tmp/pre-commit-reports/gitleaks.json`
- [ ] 插件读取报告并转成 SARIF 2.1.0（含 rules + results + 文件定位）
- [ ] SARIF 上传到 `pre-commit-reports/<仓库名>/<日期>/<runId>/gitleaks.sarif`，公网可匿名读取
- [ ] 上传成功后 APIG 回调 codecheck 接口，obsUrl 传 SARIF 下载地址
- [ ] PR 类型触发不执行报告上传回调
- [ ] pre-commit 检查失败时报告仍会上传；上传失败不阻断检查结果
- [ ] `.pre-commit-config.yaml` 与新建 workflow 在 openlibing-cicd-test 验证通过

## 影响范围

- `pre-commit-action` 仓：index.js / action.yml / package.json / dist/index.js / README.md / zip.js
- `openlibing-cicd-test` 仓：`.pre-commit-config.yaml` / `.gitcode/workflows/pre-commit-report.yml`
- 参考仓（只读）：`huaweicloud-oidc-sdk-nodejs` 的 OBS 与 APIG 用法
