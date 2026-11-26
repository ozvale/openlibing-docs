# argus-action 端点配置与出站 URL 安全加固 — 技术设计

> 覆盖 Issue：#2（硬编码公网端点）、#14（codecheck-ip/prefix SSRF 与签名请求外发）。

## 方案概述

- #2：沿用组织先例（code-metrics-action #22 / upload-ut-action #2）的“部分成立·小整改 + 白名单”模式：
  保留公开 SaaS 默认值，在同文件收敛常量，补 `gitleaks:allow`、测试和产物重建。
- #14：在发起请求前对 `codecheck-ip`、`codecheck-prefix` 和拼接后的完整 URL 做校验，
  失败即退出；`repositoryName` 编码。SDK 根因不在本仓修复。

## 关键决策

1. **同文件常量，不新建 config 文件**
   - 仅 2 个端点、1 个实现文件（`argus-action/dist/argus-scan.js`）；
   - argus 没有 `src/` 层，源码本身位于 `dist/`，新增 `config/endpoints.js` 会引入
     require 路径、ncc 解析和 zip/CLI 分发约束，收益不足；
   - 先例中拆 `src/config/endpoints.js` 的场景均为 5~8 个端点、跨多个模块。

2. **不新增环境变量**
   - `codecheck-ip` / `openlibing-url` 已是 action input，CLI 也支持同名 `--` 参数；
   - 新增 env 只会扩大行为面，不增加实际覆盖能力。

3. **默认值对齐**
   - `codecheck-ip` 统一为 `https://apig.openlibing.com`（原代码 `:443` 与之等价，去冗余）；
   - `openlibing-url` 统一为 `https://www.openlibing.com/apps/argus`（与 action.yml 一致）；
     仅 CLI / 空 input 场景的链接从站点根变为 Argus 页面，属有意修正，写入交付说明。

4. **构建链修复**
   - 现状：`npm run package` 输出到 `build/argus-action/dist/index.js`，`zip.js` 从该目录打包，
     但 action 的 `main` 是 `argus-action/dist/index.js`，该文件不会被更新；
   - 方案：`zip.js` 打包前把 `build/argus-action/dist/index.js` 复制到
     `argus-action/dist/index.js`，保证 Action 实际入口与 zip 同源；
   - 不改变 ncc 输出目录，避免 ncc 清理源码目录的风险。

5. **gitleaks 白名单**
   - ncc 产物 `argus-action/dist/index.js` 内含第三方依赖的作者邮箱与变量名
     （如 SDK 中的 `secretAccessKey` 变量名、第三方依赖作者邮箱），属打包固有误报，非本次引入；
   - 在 `.gitleaks.toml` 全局 allowlist 增加 `^argus-action/dist/index\.js$`，
     与 `node_modules` / `vendor` / `.min.js` 同为“不重复扫描的产物路径”；
   - 源码 `argus-scan.js` 与 `action.yml` 仍正常扫描，默认端点行用 `gitleaks:allow` 说明。

6. **出站 URL 安全校验（#14）**
   - `assertSafeCodecheckIp(ip)`：
     - `new URL(ip)` 必须成功解析；
     - 仅允许 `https:`；
     - 拒绝 username/password；
     - 拒绝 IP 直连、`localhost`、`.localhost`、`.local`、`.internal`；
     - 拒绝 query / fragment；
   - `assertSafeCodecheckPrefix(prefix)`：
     - 必须以 `/` 开头；
     - 仅允许 URL 路径字符；
     - 拒绝 `@`、`#`、`?`、`\`、空白与控制字符；
     - 拒绝以 `//` 开头和包含 `..` 路径段；
   - `allowed-hosts`：逗号分隔的受信主机列表，默认 `apig.openlibing.com`；
     最终 host 必须精确匹配列表项；私有化/自建平台显式追加；
   - `buildSummaryUrl(ip, prefix, repositoryName)`：
     - 拼接后 `new URL()` 解析；
     - 要求最终 `origin` 与 `codecheck-ip` 的 `origin` 完全一致，阻断
       `https://apig.openlibing.com` 后跟 `@<恶意主机>` 的 userinfo/前缀绕路；
     - `repositoryName` 使用 `encodeURIComponent`；
   - 校验在 `getVulnSummary()` 调用 `callApig()` 之前执行；失败写入明确中文错误并
     `process.exit(-1)`，不换取 STS 凭证、不发送任何请求；
   - 受信边界：`codecheck-ip` 仍视为管理员受信配置，`allowed-hosts` 默认只含公有云 APIG。
     本加固不试图防御“同时控制 codecheck-ip 与 allowed-hosts 的恶意配置者”（其本就能在
     workflow 执行任意命令），只阻断协议、userinfo、IP/内网、前缀覆盖与参数注入等可被
     误配置/低权限输入放大的路径；SDK 固定 host 白名单由 SDK 维护人员处理。

## 涉及文件

| 文件                              | 操作 | 说明                                                                                        |
| --------------------------------- | ---- | ------------------------------------------------------------------------------------------- |
| `argus-action/dist/argus-scan.js` | 修改 | 默认端点常量；`gitleaks:allow`；Summary 超链接；URL/前缀校验；`repositoryName` 编码         |
| `argus-action/action.yml`         | 注释 | 默认值说明；`codecheck-ip` / `codecheck-prefix` 标注为管理员受信配置；新增 `allowed-hosts`  |
| `argus-action/README.md`          | 修改 | 移除 AK/SK、`signer.js`；补 OIDC `id-token: write`；默认值、受信配置与 `allowed-hosts` 说明 |
| `test/mock-sdk.js`                | 修改 | 记录 `callApig` 收到的 URL                                                                  |
| `test/argus.test.js`              | 修改 | 默认端点、CLI/Action 覆盖、Summary 链接、URL 安全校验、编码用例                             |
| `zip.js`                          | 修改 | 打包前同步 bundle 到 `argus-action/dist/index.js`                                           |
| `.gitleaks.toml`                  | 修改 | 打包产物路径白名单，消除第三方依赖误报                                                      |
| `argus-action/dist/index.js`      | 重建 | ncc 产物                                                                                    |
| `argus-action.zip`                | 重建 | 发布包                                                                                      |

## 风险 & 缓解

| 风险                                 | 缓解                                                                   |
| ------------------------------------ | ---------------------------------------------------------------------- |
| ncc 重建导致 `dist/index.js` 大 diff | review 以源码 / action.yml / README 为准；用 grep + unzip 校验产物     |
| CLI 默认链接变化                     | 仅影响 CLI / 空 input；Action 行为不变；新增用例覆盖                   |
| HTTP/IP 等自定义配置被拒绝           | 属安全加固的有意行为变化；README 标注改用 HTTPS 域名；默认配置不受影响 |
| 扫描器下一轮仍命中 dist              | 在 issue 评论中预置“ncc 固有行为”说明，按 upload-sarif #10 先例归档    |
| gitleaks 命中打包产物第三方误报      | 产物路径加入 `.gitleaks.toml` allowlist；源码仍正常扫描                |
| 构建链改动影响 CI                    | `build.yml` 只执行 `npm run build`，不依赖 `build/` 路径；改后命令不变 |

## 跨仓影响

- argus-action：本目录文档 + 动作代码。
- SDK：仅登记根因 issue，本仓不改 SDK；由 `huaweicloud-oidc-sdk-nodejs` 维护人员处理。
