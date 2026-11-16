# fix-logout-grace-key-revocation

## 背景

漏洞报告 openlibinggateway-20261103105553 M-0007 (1103-007)：登出未吊销 refresh
轮换宽限期 key。logout 仅删除 `webLoginRefresh-<accountId>-<accountName>` 主
key，未删除轮换宽限期 key `webLoginRefreshGrace-<accountId>-<accountName>`
（AuthFilter 静默刷新轮换时写入，60 秒 TTL）。登出后 60 秒内，持有轮换前旧
refresh token 的请求仍可借宽限分支换发新 access token，会话复活。

## 修复方案

LoginController.logout 在删除主 refresh key 的同时同步删除宽限期 key，
登出后旧 refresh token 轮换比对立即失配，宽限分支不再命中。

## 验收标准

1. logout 同时删除 `webLoginRefresh-*` 与 `webLoginRefreshGrace-*` 两个 key
2. 既有 logout 测试适配后全量通过

## 范围说明

- `deleteAccount`（UserServiceImpl）完全未清理 Redis 凭证（含主 refresh key）
  属另一项已记录缺口，不在本次修复范围
