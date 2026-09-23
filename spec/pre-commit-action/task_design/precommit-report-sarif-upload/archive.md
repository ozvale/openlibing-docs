# precommit-report-sarif-upload — 归档

## 关联

- 业务 Issue: [openlibing/openlibing-codecheck#190](https://gitcode.com/openlibing/openlibing-codecheck/issues/190)（社区全量代码检查方案落地）
- 业务 PR: [openlibing/pre-commit-action#7](https://gitcode.com/openlibing/pre-commit-action/merge_requests/7)
- docs PR: [openlibing/openlibing-docs#1016](https://gitcode.com/openlibing/openlibing-docs/merge_requests/1016)

## 交付历程

### 报告上传与回调链路（OIDC + OBS + APIG）

- commit `1947312`: feat(pre-commit-action): upload gitleaks scan reports as SARIF to OBS
- commit `1faebb7`: feat(pre-commit-action): support beta env APIG callback endpoint
- commit `f6d2a7b`: feat(sarif): support detect-secrets report conversion
- commit `3ee925c`: fix(pre-commit-action): upload scan reports even when pre-commit fails
- commit `7f4c2ae`: fix(pre-commit-action): bundle undici for Node 16 runner
- commit `ff0a3d2`: fix(pre-commit-action): await ObsClient initFactory before putObject
- commit `09afb27`: fix(pre-commit-action): use /action-api prefix for APIG V11 callback
- commit `0aef8b1`: fix(pre-commit-action): upload SARIF to OBS with public-read ACL
- commit `0574abd`: fix(pre-commit-action): resolve callback branch for non-MR events
- commit `9446ce8`: fix(pre-commit-action): check DataResult code in APIG callback response
- commit `4633296`: fix(pre-commit-action): emit partialFingerprints for SARIF location hash

### SARIF 转换归属调整（业务仓负责）

- commit `8df36ee`: refactor(pre-commit-action): move SARIF conversion to business repo
- commit `5f2e33e`: docs(pre-commit-action): add report upload/callback usage guide

### 日志兜底 SARIF 生成（8 个工具）

- commit `cfdcf2d` / `0c02078`: feat(pre-commit-action): add fallback SARIF from pre-commit logs
- commit `9a52791`: fix(pre-commit-action): generate fallback SARIF when report dir missing
- commit `16c5ee8`: refactor(pre-commit-action): drop generic fallback sarif, warn on unsupported tools
- commit `6a122a3`: feat(pre-commit-action): per-tool report resolution for fallback sarif
- commit `1b6e05c`: feat(pre-commit-action): support detect-secrets log parsing
- commit `3ca4e38`: feat(pre-commit-action): enrich fallback sarif with region snippets
- commit `3aed16a`: fix(pre-commit-action): parser fixes so all tools get region snippets

### 数据源与路径统一（与 openlibing-upload-sarif 对齐）

- commit `9d918eb`: refactor(pre-commit-action): align OBS prefix and add upload retry
- commit `97ab27a`: feat(pre-commit-action): add sarif-file input and unify OBS path structure
- commit `7bf10ae`: merge: integrate master updates into feat-precommit-report-upload
- commit `89eda57`: feat(pre-commit-action): non-fail on release-level check findings

## 用户自测反馈

- 未进行业务 PR 合入前自测循环，业务 PR #7 保持 open，按用户要求直接归档。

## 最终验证

- `npm run package`（ncc build）构建通过
- pre-commit 全量/增量检查逻辑回归通过
- 8 个工具（clang-tidy / bandit / gosec / spotbugs / rust-clippy / eslint / gitleaks / detect-secrets）日志解析生成 SARIF 验证通过
- 流水线实测（报告上传 + 回调归档）：待业务 PR #7 合入后由流水线验证
- 关联后端（openlibing-codecheck）指纹兜底：单测覆盖（StandardSarifParserTest），待发版部署后线上确认

## 设计偏差与取舍

- **SARIF 转换从插件内置改为业务仓负责**（commit `8df36ee`）：插件保持工具无关，只做"读取 `*.sarif` → 上传 OBS → 回调"，转换脚本随业务仓演进。
- **OBS 路径前缀从 `pre-commit-reports` 统一为 `pre-commit-results`**（commit `9d918eb` / `97ab27a`）：与 openlibing-upload-sarif 共用同一路径结构 `{前缀}/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/{文件名}`，仅前缀不同，降低接入方心智负担。
- **兜底能力按工具白名单收敛**（commit `16c5ee8`）：只对支持列表内的失败钩子解析日志生成 SARIF，不支持的提示"暂不支持日志自动解析"。
- **版本级触发不按失败退出**（commit `89eda57`）：push / workflow_dispatch / schedule 触发检查发现告警仅提示，PR 门禁（mr/pull_request/note）仍按失败退出阻塞合并。

## 可复用经验

- 见 [ai_memory.md](../ai_memory.md)（OBS 路径结构、APIG 回调前缀、数据源优先级、工具支持列表）。

## 归档日期

2026-09-17
