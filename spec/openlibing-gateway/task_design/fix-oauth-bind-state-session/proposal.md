# proposal: fix-oauth-bind-state-session

- 仓库: openlibing-gateway
- 分支: develop_202611_iter1
- 模式: Standard
- 来源: WEB 漏洞判定引擎 case-20261022-184729（漏洞 ID 80782，CVSS 5.3）

## 需求背景

OAuth 账号绑定流程的 state 在 Redis 中仅保存发起者 userId（`redisHelper.set(state, userId, 30min)`），
回调阶段只校验 state 存在性并一次性删除，从不校验"发起绑定的人"与"完成第三方授权的人"是否同一
浏览器会话。攻击者以自身账号发起绑定获得有效 state 后，将 OAuth 授权 URL 发送给受害者；受害者
在第三方平台授权后，回调以 Redis 中的攻击者 userId 作为绑定目标，将受害者的三方账号绑定到攻击者
的 OpenLiBing 账号（INSERT 新记录或 UPDATE 覆盖既有绑定）。gitee/gitcode/github/uniportal/openubmc
五处绑定回调接口同构，全部受影响。

## 验收标准

1. 绑定发起时，Redis 中 state 对应值由 `userId` 变为 `userId|SHA256(token)`（token 为发起者浏览器 cookie）。
2. 绑定回调时，比对回调请求 token cookie 摘要与 Redis 存储摘要；不一致/缺失/格式不合法一律 403，绑定不执行。
3. 5 个平台（gitee/gitcode/github/uniportal/openubmc）的发起与回调全部覆盖，prManages redirect 分支同样受保护。
4. 单元测试：每平台验证"会话匹配通过绑定"与"会话不匹配拒绝绑定（403）"两条路径，全部通过。
5. 摘要比较采用常量时间比较（`MessageDigest.isEqual`），摘要实现使用 JDK 自带 MessageDigest + HexFormat。

## 范围与约束

- 仅修改 `openlibing-gateway`（LoginController.java + LoginControllerTest.java）。
- OAuth 回调本身免认证（第三方 302 触发），state 会话绑定是该链路的唯一发起者身份校验点，必须 fail-closed。
- 部署后 Redis 中旧格式 state（TTL 30 分钟）自然失效，属预期，无需迁移。
