# argus-action 硬编码公网端点收敛

## 需求背景

issue #2（SenInfo）指出 argus-action 代码中存在硬编码 URL（apig 地址、openlibing 地址）。

现状核查：

- `codecheck-ip` / `openlibing-url` 已是 action input，代码中的硬编码只作为兜底默认值；
- 两个地址均为 OpenLibing 公开 SaaS 端点，不是凭证、内网拓扑或账号标识；
- 真正的问题是默认值重复且漂移（`apig.openlibing.com:443` vs `apig.openlibing.com`；
  `openlibing.com` vs `www.openlibing.com/apps/argus`），以及 ncc 产物/zip 会重复携带字符串；
- 组织已有同类先例：upload-sarif-action #10、pr-label-action #3、upload-ut-action #2、
  code-metrics-action #22，均按“公开功能端点不是漏洞 + 默认值保留 + 白名单/集中配置”处置。

## 功能描述

做什么：

- 将两个默认端点收敛为 `argus-scan.js` 顶部常量，删除 4 处重复字面量；
- 对齐两处默认值漂移；
- 在默认值行登记 `gitleaks:allow` 并写明理由；
- 补测试覆盖默认端点、CLI 覆盖和 Summary 链接；
- 修复构建链，确保 `npm run build` 同步更新 `argus-action/dist/index.js` 与 zip；
- 为 ncc 打包产物登记 gitleaks 路径白名单，消除第三方依赖误报；
- 同步 README 的 OIDC 认证方式与默认值说明。

不做什么：

- 不删除默认地址，不新增环境变量（action input / CLI 参数已可覆盖）；
- 不改 action 输入输出契约、门禁判定、退出码；
- 不处理 ncc 内联的第三方 URL；
- 不重构目录结构、不升版本号、不打 tag。

## 验收标准

- [ ] Action 模式下 `codecheck-ip` / `openlibing-url` 的 effective 默认值不变；
- [ ] CLI 默认链接对齐到 `https://www.openlibing.com/apps/argus`（唯一有意行为变化）；
- [ ] 源码中两个端点各只声明一次，无重复字面量；
- [ ] `npm test` 全绿，新增用例覆盖默认值 / 覆盖 / Summary 链接；
- [ ] `npm run build` 后 `argus-action/dist/index.js` 与 `argus-action.zip` 同源；
- [ ] pre-commit（含 gitleaks）全绿；
- [ ] README 不再出现 `scan-access-key` / `scan-secret-key` / `signer.js`；
- [ ] issue #2 有证据评论并关闭。

## 影响范围

单仓 `argus-action`（远端 `openlibing/vulnerability-hunting-action`）：

- `argus-action/dist/argus-scan.js`
- `argus-action/action.yml`（仅注释）
- `argus-action/README.md`
- `test/mock-sdk.js`、`test/argus.test.js`
- `zip.js`
- `.gitleaks.toml`（打包产物路径白名单）
- `argus-action/dist/index.js`、`argus-action.zip`（重建产物）
