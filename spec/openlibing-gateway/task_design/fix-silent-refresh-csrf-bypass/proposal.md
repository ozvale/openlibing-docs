# fix-silent-refresh-csrf-bypass

## 背景

漏洞报告 openlibinggateway-20261103105553 M-0004 (1103-005)：主链路静默刷新绕过 CSRF。
AuthFilter 在静默刷新成功后（refreshedCredential=true）整体短路 `isCsrfAttack`，
连 referer host 校验也未执行（与代码注释声明不符），跨站请求可借受害者
refresh cookie 触发刷新后携带注入身份直达下游。

## 修复方案

刷新成功不再整体短路，降级为 referer host 精准匹配（`isCsrfRefererTrusted`）：

- 未刷新：走完整 `checkCsrfAttack`（trust 名单 + referer + csrf token 验签），不变
- 已刷新：referer host 精准匹配；`csrf.trust.list` 中的登录中间态路径
  （签署隐私协议、落库三方信息、账号绑定等刷新后必然无新 csrf token 的端点）豁免
- 主链路：降级校验失败 401 终止
- 公开接口分支：同型修复，降级校验失败走匿名降级（FALLBACK_ANONYMOUS）

生产配置参考值（外部部署配置，不入仓）：
`csrf.trust.list = /user/save-three-party-user-info,/user/check-account-bind,/privacy/profile/agree,/platform/account/bind,/openlibing-framework/manage/wiki/image/detail,/openlibing-framework/wiki/image/detail,/apigw-forward/,/openlibing-ai/,/openlibing-plugin-service/`

## 验收标准

1. 静默刷新成功 + 站外 referer → 主链路 401 / 公开接口匿名降级
2. 静默刷新成功 + 受信 referer → 正常续转
3. trust 名单精准匹配豁免，前缀拼接不豁免
4. 既有静默刷新链路测试适配后全量通过

## 部署注意

- 前端同站请求必须携带 referer（不得使用 no-referrer 策略），否则刷新后续请求会被 401
- `csrf.trust.list` 为外部部署配置，上线时需按上述参考值核对生产配置
