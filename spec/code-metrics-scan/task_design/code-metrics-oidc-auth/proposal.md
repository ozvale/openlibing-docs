# Proposal：code-metrics 插件 OIDC 联邦认证改造

> FE 需求：【openlibing】GitCode插件流水线交互适配OIDC认证方案
> 业务 Issue：openlibing/code-metrics-action#8、openlibing/security-compilation-options-action#6
> 流程模式：Full
> 关联文档：本目录《sec-option-scan-需求设计.md》《code-metrics-scan-需求设计.md》

## 需求背景

code-metrics-scan 插件上报链路依赖 4 个长期静态凭证（APIG App AK/SK + OBS AK/SK），经 workflow secrets 分发。按 FE 需求，为插件新增 OIDC 联邦认证通道（OIDC ID Token → STS 临时凭证 → V11 签名 / OBS 临时凭证）。

考虑到迁移期内大量存量 workflow 尚未改造（未声明 `permissions: id-token: write`），本次改造采用**双模式自动切换**方案：保留原有 AK/SK 认证逻辑与旧网关接口不变，新增 OIDC 认证通道走新网关接口，插件按 workflow 是否声明 `permissions: id-token: write` 自动选择，存量脚本零修改继续可用。

sec-option-scan 插件已完成同构改造并通过线上验证（含网关 IAM 认证切换、信任委托配置），本次为 code-metrics 插件复制该已验证模式。

## 改造范围

| 仓库 | 位置 | 变更 |
| --- | --- | --- |
| openlibing/code-metrics-scan | `.gitcode/actions/code-metrics-scan` | 源码双模式改造（CoderepoUploader / index.js / scanner.js / package.json / action.yml / README） |
| openlibing/code-metrics-action | 仓根 | 发布包装同步（action.yml / README / dist / package.json，SDK 0.0.5）+ ncc 重新打包 |
| openlibing/security-compilation-options-action | 仓根 | 同构双模式改造（CicdUploader / index.js / scanner.js / package.json / action.yml / README / dist，SDK 0.0.5）+ ncc 重新打包，并修复 timeout 透传、_stack_flag_state 跨段聚合、stackClash 输出名规避 |
| openlibing/openlibing-cicd | `.gitcode/workflows` | build.yml / code-metrics-scan.yml 增加 `permissions: id-token: write`、移除凭证注入、插件引用固定 SHA |
| openlibing-docs | `spec/code-metrics-scan/task_design/code-metrics-oidc-auth/` | 两份需求设计文档 + proposal / tasks / archive（本目录） |

分支安排：
- code-metrics-scan：沿用 `sec-option-oidc-auth` 分支（用户确认不切分支），提交后推送 origin，不走 PR
- code-metrics-action：新建 `code-metrics-oidc-auth` 分支（基于 origin/master），创建 PR #20 关联 Issue #8
- security-compilation-options-action：新建 `sec-option-oidc-auth` 分支（基于 origin/master），创建 PR #12 关联 Issue #6

## 验收标准

- [x] 双模式自动切换：workflow 声明 `permissions: id-token: write` 时走新接口 `/action-api/...` + OIDC 认证；未声明时走旧接口（`/openlibing-cicd/...` / `/openlibing-coderepo/...`）+ AK/SK 认证，二者一一对应不混用
- [x] 存量兼容：AK/SK 模式下凭证输入（`apig-app-key` / `apig-app-secret` / `obs-ak` / `obs-sk`）恢复为可选参数，存量脚本零修改可用
- [x] OIDC 链路走通：声明 permissions 后，ID Token 申请 → STS 换证 → APIG 上报成功、OBS 临时凭证上传成功
- [x] 接口契约不变：report 接口 payload / 响应解析、OBS 桶与 objectKey 规则均保持原样
- [x] 兜底语义不变：OBS 已传但 report 失败时提示保底任务补导入
- [x] ncc 打包产物包含 SDK（callApig / getCredentials）与 AK/SK 签名器（ApigSigner），两仓 dist 一致
- [x] pre-commit 通过
