# argus-action 端点配置与出站 URL 安全加固 — 归档

## 关联

- 业务 Issue #2：https://gitcode.com/openlibing/vulnerability-hunting-action/issues/2
- 业务 Issue #14：https://gitcode.com/openlibing/vulnerability-hunting-action/issues/14
- 业务 PR #23：https://gitcode.com/openlibing/vulnerability-hunting-action/merge_requests/23
- SDK 根因 Issue #45：https://gitcode.com/openlibing/huaweicloud-oidc-sdk-nodejs/issues/45
- docs PR：https://gitcode.com/openlibing/openlibing-docs/merge_requests/1440

## 交付历程

业务分支 `fix-argus-hardcoded-endpoints`：

- `0e81c94` `fix(argus): centralize public endpoint defaults and sync bundles`
  - #2 默认端点收敛、构建链同步、gitleaks 产物白名单。
- `c8a18f4` `fix(argus): render summary link as 漏洞详情 hyperlink`
  - 用户反馈：Summary 不再输出裸 URL，改为「漏洞详情」超链接。
- `8cb0269` `fix(argus): validate outbound endpoint configuration`
  - #14 URL/前缀校验、`allowed-hosts`、`repositoryName` 编码、fail-fast。

docs 分支 `spec-argus-action-fix-hardcoded-endpoints`：

- `0f647c5a` `docs(spec/argus-action): add hardcoded endpoint remediation artifacts`
- `f039cfde` `docs(spec/argus-action): record summary hyperlink feedback`
- `b3b03adf` `docs(spec/argus-action): cover issue #14 endpoint hardening`
- `1c179244` `docs(spec/argus-action): add allowed-hosts to issue #14 design`

## 用户自测反馈

- 概览直接暴露 URL → 改为 `[漏洞详情](url)` 超链接（`c8a18f4`）。
- #14 修复范围限定为插件内部加固；SDK 根因交由 SDK 维护人员处理（issue #45）。
- 审查反馈（PR #23，ozvale）：
  - 确认 `openlibing-url` 默认值变更：Action 模式 effective 值不变，CLI/空 input 对齐到 `/apps/argus`；
  - 确认 `dist/index.js` 由 ncc 重新生成，非手改；
  - 明示 `.gitleaks.toml` 排除 ncc 产物的取舍；
  - 写明 zip 生成方式与 MD5 复核；
  - 确认已知消费方未使用 IP 直连；如后续私有化需要 IP，单独评审放宽策略。

## 最终验证

- `npm test`：14/14 通过，覆盖率 79.15%；
- `npm run build`：ncc + zip 成功；
- `dist/index.js` 与 zip 内 bundle MD5 一致：`87952be3c9af93becdcdd99a9589da50`；
- `pre-commit`：trailing-whitespace / EOF / YAML / gitleaks / prettier / eslint 全通过；
- `node --check argus-action/dist/argus-scan.js` 通过；
- 用例覆盖默认流程、非法配置 fail-fast、自定义 host + `allowed-hosts`。

## 设计偏差与取舍

- #2 与 #14 合并为一个业务 PR #23：两者改同一批文件，避免分支冲突；PR 同时关联两个 issue。
- 未修改 SDK；SDK 受信 host 白名单 / HTTPS-only / 重定向修复由 issue #45 跟踪。
- `net.isIP` 拒绝一切 IP 字面量（含内网 IP）；已知消费方未使用 IP。如私有化部署确有 IP 直连需求，需单独评审放宽策略。
- `.gitleaks.toml` 排除 ncc 产物 `argus-action/dist/index.js`：源码、`action.yml` 与依赖仍分别扫描；代价是“打包过程引入的凭据”不被 gitleaks 发现，已在 PR 描述明示。
- 新增 `allowed-hosts` 属 action 契约变更，消费方引用 `@v1.0.3` 需等新版本/tag。

## 可复用经验

- ncc 产物入库时，构建脚本必须同时更新 Action 的 `main` 入口和 zip，避免“源码已改、运行入口未更新”。
- 出站 URL 安全校验应“先校验、后换证”：在 `callApig` 获取 STS 凭证前完成 URL/前缀/allowlist 校验，失败即 fail-closed。
- 对 ncc 产物做 gitleaks 路径白名单时，需明示“打包产物不被扫描”的取舍，避免被误认为已覆盖全部凭据扫描。
- 新增白名单类 input（如 `allowed-hosts`）要同时提供默认值、私有化扩展说明和破坏性变更提示。

## 归档日期

2026-11-26
