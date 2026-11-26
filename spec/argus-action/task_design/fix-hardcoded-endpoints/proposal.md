# argus-action 端点配置与出站 URL 安全加固

> 覆盖 Issue：#2（硬编码公网端点）、#14（codecheck-ip/prefix SSRF 与签名请求外发）。

## 需求背景

### #2 硬编码公网端点

issue #2（SenInfo）指出 argus-action 代码中存在硬编码 URL（apig 地址、openlibing 地址）。

现状核查：

- `codecheck-ip` / `openlibing-url` 已是 action input，代码中的硬编码只作为兜底默认值；
- 两个地址均为 OpenLibing 公开 SaaS 端点，不是凭证、内网拓扑或账号标识；
- 真正的问题是默认值重复且漂移（`apig.openlibing.com:443` vs `apig.openlibing.com`；
  `openlibing.com` vs `www.openlibing.com/apps/argus`），以及 ncc 产物/zip 会重复携带字符串；
- 组织已有同类先例：upload-sarif-action #10、pr-label-action #3、upload-ut-action #2、
  code-metrics-action #22，均按“公开功能端点不是漏洞 + 默认值保留 + 白名单/集中配置”处置。

### #14 出站 URL 安全加固

issue #14 记录了一个条件性 SSRF / 签名请求外发风险：

- `codecheck-ip` / `codecheck-prefix` 无校验地拼接为出站 URL；
- SDK `callApig` 对任意 URL 附加 `X-Security-Token` 与 V11 签名；
- SDK 0.0.5 允许 `http://`，默认跟随重定向；
- 默认配置和已知消费方不可利用，但消费方若把配置接自不可信来源则会触发。

本 issue 只做 argus-action 内部加固；SDK 层根因（受信 host 白名单、HTTPS-only、重定向）
由 `huaweicloud-oidc-sdk-nodejs` 维护人员另行处理。

## 功能描述

做什么：

### #2

- 将两个默认端点收敛为 `argus-scan.js` 顶部常量，删除 4 处重复字面量；
- 门禁失败 Summary 以「漏洞详情」超链接展示，不再输出裸 URL；
- 对齐两处默认值漂移；
- 在默认值行登记 `gitleaks:allow` 并写明理由；
- 补测试覆盖默认端点、CLI 覆盖和 Summary 链接；
- 修复构建链，确保 `npm run build` 同步更新 `argus-action/dist/index.js` 与 zip；
- 为 ncc 打包产物登记 gitleaks 路径白名单，消除第三方依赖误报；
- 同步 README 的 OIDC 认证方式与默认值说明。

### #14

- 校验 `codecheck-ip`：仅允许 HTTPS；拒绝 userinfo、IP 直连、localhost、内网地址、query/fragment；
- 校验 `codecheck-prefix`：必须以 `/` 开头，仅允许路径字符，拒绝 `@`、`#`、`?`、反斜杠、空白；
- 新增 `allowed-hosts` 输入（逗号分隔，默认 `apig.openlibing.com`），最终请求 host 必须在列表内；
  私有化/自建平台可显式追加；
- 拼接后再次解析完整 URL，要求 origin 与 `codecheck-ip` 一致（阻断 `@host` 绕过）；
- `repositoryName` 使用 `encodeURIComponent` 编码；
- 校验失败在发起任何请求前报错退出，不换取凭证、不发送请求；
- README/action.yml 标注两个配置为管理员受信配置，禁止接不可信来源；
- 补测试覆盖 http、IP、localhost、userinfo、`@` 前缀、query/fragment、编码等场景。

不做什么：

- 不删除默认地址，不新增环境变量；
- 不修改 SDK；SDK 根因由 SDK 维护人员处理；
- 不引入不可配置的固定单域白名单；通过 `allowed-hosts` 默认值 + 显式配置兼顾私有化/自建平台；
- 不改门禁判定、退出码语义以外的业务逻辑；
- 不处理 ncc 内联的第三方 URL；
- 不重构目录结构、不升版本号、不打 tag。

## 验收标准

### #2

- [ ] Action 模式下 `codecheck-ip` / `openlibing-url` 的 effective 默认值不变；
- [ ] CLI 默认链接对齐到 `https://www.openlibing.com/apps/argus`（唯一有意行为变化）；
- [ ] 源码中两个端点各只声明一次，无重复字面量；
- [ ] 门禁失败 Summary 在「漏洞详情」处渲染超链接，不出现裸 URL；
- [ ] `npm test` 全绿，新增用例覆盖默认值 / 覆盖 / Summary 链接；
- [ ] `npm run build` 后 `argus-action/dist/index.js` 与 `argus-action.zip` 同源；
- [ ] pre-commit（含 gitleaks）全绿；
- [ ] README 不再出现 `scan-access-key` / `scan-secret-key` / `signer.js`；
- [ ] issue #2 有证据评论并关闭。

### #14

- [ ] `codecheck-ip` 为 `http://`、IP、localhost、userinfo 或含 query/fragment 时，启动即报错，不发起请求；
- [ ] `codecheck-prefix` 含 `@`、`#`、`?`、反斜杠或非 `/` 开头时，启动即报错；
- [ ] 拼接后的 URL origin 与 `codecheck-ip` 不一致时被拒绝；
- [ ] `codecheck-ip` 主机不在 `allowed-hosts` 列表内时被拒绝；
- [ ] `allowed-hosts` 支持逗号分隔的多个受信主机；
- [ ] `repositoryName` 含 `&`、`?`、`#`、`%` 时正确编码；
- [ ] 默认配置功能回归通过（正常获取摘要、门禁判定不变）；
- [ ] pre-commit / 测试 / 构建全绿。

## 影响范围

单仓 `argus-action`（远端 `openlibing/vulnerability-hunting-action`）：

- `argus-action/dist/argus-scan.js`（默认端点、URL 校验、编码、Summary）
- `argus-action/action.yml`（默认值注释、受信配置说明）
- `argus-action/README.md`（OIDC、默认值、受信配置）
- `test/mock-sdk.js`、`test/argus.test.js`
- `zip.js`
- `.gitleaks.toml`（打包产物路径白名单）
- `argus-action/dist/index.js`、`argus-action.zip`（重建产物）
