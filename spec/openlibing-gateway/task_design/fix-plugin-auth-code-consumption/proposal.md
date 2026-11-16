# fix-plugin-auth-code-consumption

## 背景

漏洞报告 openlibinggateway-20261103105553 M-0005 (1103-006)：插件登录一次性 code
消费链路两个缺陷：

1. Controller 预检（`/plugin/get/access/token`）用裸 `hasKey(code)` 探测 Redis，
   与写入/消费侧的 `openlibing-gateway:plugin:auth-code:` 前缀不一致——预检恒
   false（功能缺陷），且裸 code 直接作为 Redis key 可被客户端枚举探测任意 key
   存在性（安全缺陷）
2. Service 消费侧 get→del 两步非原子，并发请求可在两步间重复消费同一 code，
   重复签发 token

## 修复方案

- LoginController 预检 key 补齐 `PLUGIN_AUTH_CODE_PREFIX` 前缀，与写入/消费侧对齐，
  裸 code 不再作为 Redis key
- RedisHelper 新增 `getAndDelete`（`opsForValue().getAndDelete`，Redis GETDEL 原子命令）
- LoginServiceImpl.generatePluginAuth 改为原子消费，移除独立 del

## 验收标准

1. 预检只命中带前缀 key，裸 code 探测不到任何 key
2. code 消费为单次原子操作，无 get→del 并发窗口
3. 既有 Controller/Service 测试适配后全量通过
