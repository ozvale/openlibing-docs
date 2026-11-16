# fix-refresh-token-key-alignment

## 背景

漏洞报告 openlibinggateway-20261103105553 L-0013 (argus-007)：PAT/密码登录
（giteePasswordLogin / gitcodePatLogin）的 buildXxxResult 将 refresh token 写入
`userIdToken-<accountId>-<accountName>-refresh` 前缀 key，而 Web 端静默刷新链路
（AuthFilter）读取 `webLoginRefresh-<accountId>-<accountName>`。写读前缀不一致，
该两类登录的 refresh token 无法被静默刷新消费（长令牌改造遗留），同时 logout
删除 `webLoginRefresh-*` 也吊销不到该类会话的 refresh 凭证。

## 修复方案

两个 build 方法中 refresh token 写入 key 改为
`webLoginRefresh-<accountId>-<accountName>`（TTL 30 天不变），与 Web 静默刷新、
logout 吊销（含宽限期 key）全部对齐。旧 `userIdToken-*-refresh` 前缀全仓无任何
读取方，不再写入；存量旧 key 依赖 30 天 TTL 自然过期，无需迁移。

## 验收标准

1. PAT/密码登录成功后 refresh token 写入 `webLoginRefresh-*` key
2. 不再写任何含 `-refresh` 后缀的旧前缀 key
3. LoginServiceImplTest 全量通过
