# fix-open-redirect-bind-authoriz

## 背景

漏洞报告 openlibinggateway-20261103105553 M-0001 (1103-003)：OAuth 绑定回调开放重定向。
uniportal/openubmc/gitee/gitcode/github 共 5 个 bind 端点将客户端传入的 `redirect`
参数经 SPLIT_STR 还原后原样写入 Redis（`<userId>:<platform>:redirect`，30 分钟 TTL），
绑定回调处理时该值直接写入 `Location` 响应头发起 302，攻击者可构造恶意
redirect 地址将受害者绑定流程重定向到任意站点（钓鱼/凭证收集）。

## 修复方案

写入侧统一校验（5 个端点共用同一模式，单点收敛）：

- LoginController 新增 `isRedirectUrlTrusted`：
  - 相对路径：必须以单个 `/` 开头（拒绝 `//evil.com`、`/\evil.com` 等 protocol-relative 变体）
  - 绝对地址：仅允许 http/https，host 与 `jwtConfig.getDomainName()` 精准一致（忽略大小写）
  - 语法非法/其他协议（javascript: 等）一律拒绝
- 5 个 bind 端点在写 Redis 前校验，不受信地址返回 400，不落 Redis

## 验收标准

1. 同站绝对地址 / 同站相对路径 → 正常授权重定向并写 Redis
2. 站外绝对地址、protocol-relative、非 http 协议、非法语法 → 400 且不写 Redis
3. 既有 bind 端点用例适配后全量通过

## 部署注意

- 受信 host 取自 `jwtConfig.getDomainName()`（与 cookie 域一致），生产配置的
  domain-name 必须与前端 PR 管理页面实际域名一致，否则合法 redirect 会被 400
