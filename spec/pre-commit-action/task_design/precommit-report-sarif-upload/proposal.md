# precommit-report-sarif-upload

## 需求背景

openlibing 平台使用 pre-commit 对代码仓做静态检查（detect-secrets / gitleaks / spotbugs 等钩子）。当前 `pre-commit-action` 插件只执行检查并输出日志，检查结果无法沉淀到平台，缺少可追溯的扫描报告。

用户需要：pre-commit 各工具的扫描报告经过**通用链路**（业务仓负责把原始报告转成 SARIF，插件负责上传 OBS + 回调 openlibing 后端）沉淀到平台，形成可追溯的扫描结果。

## 功能描述

**通用契约（不绑定具体工具）**
- 各工具钩子把原始报告（JSON 等）输出到约定目录（默认 `/tmp/pre-commit-reports/`，插件 input `report-dir` 可覆盖）
- **SARIF 转换由业务仓负责**：业务仓把原始报告转为 SARIF 2.1.0，文件名 `<tool>.sarif` 写入同一约定目录。转换脚本按工具各自实现（detect-secrets 用 `scripts/convert-detect-secrets-to-sarif.py`，gitleaks / 其他工具同理）
- `pre-commit-action` 插件**不感知具体工具、不内置任何转换器**，只读取约定目录下所有 `*.sarif` 上传 OBS（public-read）并 APIG 回调后端
- 后端解析 SARIF：优先取 `partialFingerprints.primaryLocationLineHash` 构建指纹，缺失时**后端兜底计算**（sha256(uri|startLine|ruleId)），保证任何工具都不因缺指纹而静默丢 issue

**做什么**
- `pre-commit-action` 插件改造：
  - 新增 npm 依赖 `@openlibing/huaweicloud-oidc-client@0.0.5` + `esdk-obs-nodejs@3.26.2` + `undici@^5.28.4`（Node16 兜底）
  - pre-commit 运行后读取报告目录（input `report-dir`，默认 `/tmp/pre-commit-reports/`）下所有 `*.sarif`，逐个上传 OBS 并回调
  - OIDC 换临时凭证，上传到 OBS 桶 `openlibing-gitcode-action`，路径 `pre-commit-reports/<仓库名>/<runId>/<file>.sarif`，对象 `ACL: public-read`
  - APIG 回调 codecheck 接口（`/action-api/codescan/v1/result/receive`，IAM 认证分组），OIDC callApig（V11 签名 + X-Security-Token），并校验响应体业务码（HTTP 200 不等于成功）
  - 环境切换：`env-type`（prod → `apig.openlibing.com`，beta → 华为云 APIG 实例域名）
  - `branch` 字段兼容 `workflow_dispatch` 等非 MR 事件（`resolveBranch`：MR 用 `ATOMGIT_HEAD_REF`，其余用 `ATOMGIT_REF_NAME`）
  - PR 类型触发（mr/pull_request/note）只做检查，不进行报告上传回调
  - 检查失败仍上传已生成的报告；上传失败仅 warning 不阻断检查结果
  - action.yml 新增输入（report-dir / env-type / debug）+ 重新 ncc build + README 同步
- `openlibing-cicd-test` 示例实现（detect-secrets）：
  - `.pre-commit-config.yaml` local 钩子 `scripts/detect-secrets-report.sh`：扫描生成 `detect-secrets.json` → 同一钩子内调用 `scripts/convert-detect-secrets-to-sarif.py` 转出 `detect-secrets.sarif` → 临时 baseline 做拦截检查
  - 新建 `.gitcode/workflows/pre-commit-report.yml`（workflow_dispatch 触发，声明 `id-token: write`）做端到端验证
- `openlibing-codecheck` 后端：`StandardSarifParser.extractLocationHash` 增加指纹兜底（`primaryLocationLineHash` 缺失时按 uri+startLine+ruleId 计算）

**不做什么**
- 插件不提供 JSON→SARIF 转换能力（转换归属业务仓）
- 不处理不支持报告输出的 pre-commit-hooks 钩子（trailing-whitespace 等）
- 不做 OBS 桶的新建/权限变更（沿用现有桶）

## 验收标准

- [ ] detect-secrets 钩子执行时生成 `/tmp/pre-commit-reports/detect-secrets.json` 并转出 `detect-secrets.sarif`（SARIF 2.1.0，含 rules + results + 文件定位 + 稳定指纹）
- [ ] 插件读取报告目录下所有 `*.sarif`，上传到 `pre-commit-reports/<仓库名>/<runId>/<file>.sarif`，对象公网可匿名读取（public-read）
- [ ] 上传成功后 APIG 回调 codecheck 接口，obsUrl 传 SARIF 下载地址；beta 环境回调 beta 域名
- [ ] 回调响应体业务码非成功时插件打 WARN 并输出业务码（不误报成功）
- [ ] PR 类型触发不执行报告上传回调
- [ ] pre-commit 检查失败时报告仍会上传；上传失败不阻断检查结果
- [ ] 后端对缺失 `primaryLocationLineHash` 的 SARIF 兜底计算指纹，issue 正常入库（可在 codeCheck 应用查看）
- [ ] `.pre-commit-config.yaml` 与新建 workflow 在 openlibing-cicd-test 验证通过

## 影响范围

- `pre-commit-action` 仓：index.js / action.yml / package.json / dist/index.js / README.md
- `openlibing-cicd-test` 仓：`.pre-commit-config.yaml` / `scripts/detect-secrets-report.sh` / `scripts/convert-detect-secrets-to-sarif.py` / `.gitcode/workflows/pre-commit-report.yml`
- `openlibing-codecheck` 仓：`StandardSarifParser.java`（指纹兜底）+ 单测
- 参考仓（只读）：`huaweicloud-oidc-sdk-nodejs` 的 OBS 与 APIG 用法
