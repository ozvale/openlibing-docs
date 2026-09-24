# openlibing-upload-sarif 通用 SARIF 上传插件 — 归档

## 归档信息

| 项目     | 内容                                                                                 |
| -------- | ------------------------------------------------------------------------------------ |
| 需求名称 | openlibing-upload-sarif 通用 SARIF 上传插件（OBS 上传与 pre-commit-action 机制统一） |
| 业务仓   | `openlibing/upload-sarif-action`（本地目录 `openlibing-upload-sarif`）               |
| 开发分支 | `feat-full-check-compliance`                                                         |
| 流程模式 | Standard                                                                             |
| 归档日期 | 2026-09-17                                                                           |

## 关联

- 业务 PR: [openlibing/upload-sarif-action#7](https://gitcode.com/openlibing/upload-sarif-action/merge_requests/7)（`refactor(upload-sarif): unify OBS upload via esdk-obs-nodejs SDK`，head=`taohuoquan:feat-full-check-compliance` → base=`main`）
- docs PR: 本次提交（target=master）
- 注：本插件需求无独立业务 Issue；仓内 Issue #1 为 pre-commit workflow 缺陷模板占位，与本次归档无关

## 交付历程

| commit    | 说明                                                              |
| --------- | ----------------------------------------------------------------- |
| `2fc8317` | feat: adapt OIDC auth and generic SARIF upload                    |
| `0067d1e` | feat: self-contained OIDC via embedded SDK, drop oidc-auth plugin |
| `cfa4b64` | build: commit dist bundle so action works from remote checkout    |
| `745cb90` | feat: auto-enrich region.snippet when SARIF lacks code context    |
| `9ab67e5` | feat: comply with full-code-check design retry and metadata       |
| `08cfe96` | refactor: remove layer/mode/tool_failed params                    |
| `5f3ecdd` | feat: dynamic OBS prefix by tool name                             |
| `4717f8c` | refactor: switch OBS upload from obsutil CLI to esdk-obs-nodejs   |
| `474c2ce` | refactor: unify OBS path/server with pre-commit-action            |
| `932df0b` | Merge remote-tracking branch 'upstream/main'                      |
| `4e54c2c` | chore: apply pre-commit formatting fixes                          |

## 用户自测反馈

- 交付过程中用户提出 **OBS 上传逻辑需与 `pre-commit-action` 对齐**：统一 server 来源为动态 region、统一 SARIF 路径结构 `{前缀}/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/`、统一时间戳 `yyyyMMdd.HH`、`build-result.json` 与 SARIF 同路径、数据源支持文件/目录/逗号多值
- 用户要求移除 `layer`/`mode`/`tool_failed` 冗余参数，保留需求必需的输入项
- 用户要求上传与回调均加指数退避重试（默认 3 次），防止网络抖动数据丢失

## 最终验证

| 项                  | 结果                                                                                                                                                                         |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 本地构建            | ✅ `npm run build`（ncc 打包 dist + zip）                                                                                                                                    |
| Pre-commit 质量门禁 | ✅ trailing-whitespace / end-of-file-fixer / check-yaml / check-json / check-xml / check-merge-conflict / check-added-large-files / detect-private-key / gitleaks / prettier |
| 业务 PR             | ⏳ PR #7 open 待合并（流水线实测项在 PR 描述中标记待完成）                                                                                                                   |
| docs PR             | 本次提交（target=master）                                                                                                                                                    |

## 设计偏差与取舍

### 偏差 1：beta 环境 APIG 域名临时使用已发布 `/action-api` 的域名

**背景**：`beta.apig.openlibing.com` DNS 已指向华为云 APIG，但证书尚未绑定该域名（TLS 握手返回默认证书）。

**取舍**：当前临时使用已发布 `/action-api` 接口的 APIG 域名 `174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.myhuaweicloud.com`（代码中已注释说明），保证 beta 链路可测；平台绑定证书后应切回 beta 域名。

### 偏差 2：`build-result.json` 使用首个工具目录前缀

**背景**：多工具 SARIF 各归各自前缀后，构建产物清单只有一个文件。

**取舍**：`build-result.json` 放在首个 SARIF 的工具目录前缀下（与 SARIF 同路径），不单独使用 `code-arts-check-results` 前缀，与 pre-commit-action 一致。

### 偏差 3：回调失败不阻断

**背景**：APIG 回调偶发网络抖动。

**取舍**：回调失败仅输出 WARN，SARIF 上传成功即视为成功（`result=success`），避免 OBS 已上传成功但回调失败导致整个 Action 误判失败。

## 可复用经验

1. **两个 SARIF 上传插件机制统一**：`pre-commit-action`（固定 `pre-commit-results` 前缀）与 `openlibing-upload-sarif`（动态 `{toolName}-results` 前缀）共用同一套 OBS 上传机制（esdk-obs-nodejs + 动态 region server + `public-read`）、路径结构（`{前缀}/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/`）与数据源约定（文件/目录/逗号多值输入）。新增同类插件时应继续沿用，差异仅由业务场景决定。
2. **`esdk-obs-nodejs` 客户端构造后需让出一个微任务**：其初始化是异步的（内部 await refresh 后才设置签名上下文），立即 `putObject` 会读到 null signatureContext。构造后 `await Promise.resolve()` 即可。
3. **OBS 上传与 APIG 回调必须指数退避重试（默认 3 次）**：同步用 `withRetrySync`（`sleep 2^(n-1)` 秒）、异步用 `withRetryAsync`（`2^(n-1) * 1000ms`），防止网络抖动数据丢失。
4. **OBS 对象必须 `public-read`**：后端通过匿名 HTTP GET 下载 SARIF，对象权限不足会导致解析失败。
5. **APIG 回调 `obsUrl` 恒传数组**：后端 DTO 为 `List<String>`，旧版无 StringOrListDeserializer，恒传数组兼容新旧后端。

## 归档日期

2026-09-17
