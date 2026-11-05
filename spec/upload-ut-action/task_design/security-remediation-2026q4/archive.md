# 【upload-ut-action】安全整改 2026Q4 — 归档

## 关联

- 业务仓：openlibing/upload-ut-action
- 安全 Issue 总量：24
- 业务 PR：#1（OBS ACL 可配置、OIDC 接口地址外置）、#3（消除 resolveRepoRoot 命令注入）、#4（ObsUploader 临时文件、runId key 与 TLS 校验加固）、#5（resolveRepoRoot 去除 shell 管道）
- 统一测试分支：`fix-security-remediation`
- docs PR：本归档 PR

## 整改范围

### 1. 命令注入（PR #3 / #5）

- `resolveRepoRoot` 改为纯 Node 实现，去除 shell 管道与字符串拼接，消除命令注入面。

### 2. 上传链路加固（PR #4）

- 临时文件权限收紧并按生命周期清理。
- OBS 对象 key 与 runId 的拼接做校验。
- TLS 校验强制开启。

### 3. 配置化（PR #1）

- OBS ACL 改为可配置参数，默认值保持 `public-read`（等价变换）。
- OIDC / API 接口地址从硬编码改为配置注入，保留环境变量覆盖，默认值与原文一致。

## 存量核对

| 指标 | 数量 |
|---|---:|
| 总体 | 24 |
| 已修复（closed） | 22 |
| 剩余（open） | 2 |

## 剩余项

| Issue | 内容 | 状态 |
|---|---|---|
| #21 | public-read 覆盖率数据明文可读且无大小上限 | 无 PR，需定性 |
| #4 | OBS 对象硬编码 public-read ACL，覆盖率数据公网可读可枚举 | 无 PR，需定性 |

这两条同源：覆盖率数据对象默认 `public-read` 是后端匿名下载链路的依赖，改成 `private` 会导致消费方无法读取。整改路径需平台侧先支持凭证化下载，插件侧再切换默认 ACL；在此之前维持现状并在 issue 中记录裁决结论。

## 可复用经验

- ACL 默认值类改动属于「默认行为变化」，必须先确认下游消费方，禁止只改插件侧。
- 同类问题（public-read）在多仓重复出现时，应统一裁决口径，避免各仓结论不一致。

## 归档日期

2026-11-05
