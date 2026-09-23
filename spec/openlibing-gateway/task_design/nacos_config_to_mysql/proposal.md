# nacos_config_to_mysql — 需求

> 源 spec：`whitelist-db-migration-spec.md` v1.2（2026-09-20）

## 需求背景

`openlibing-gateway` 的 `AuthFilter` 中三份白名单目前通过 `@Value` 从配置中心（Nacos）注入：

| 原配置 key | 用途 | 匹配位置（AuthFilter） |
|---|---|---|
| `exempt.paths` | 豁免登录认证 | `shouldExemptAuth` |
| `no.openlibing.user.info.list` | 无 openlibing 用户信息放行 | `isNoOpenLiBingUserInfoRequired` |
| `no.authentication.accessible.paths` | 无认证可访问详情页面 | `publicInterface` |

现状问题：

- 修改白名单必须走 Nacos 发布 + **服务重启**才生效（网关全库无 `@RefreshScope`，`@Value` 不会运行时重绑定）。
- 配置散落在配置中心，无管理入口、无操作留痕。
- **Nacos 后续将下线**，白名单必须有脱离配置中心的承载方式。

目标：白名单数据改由数据库统一管理（framework 提供管理端增删改），网关通过「本地缓存 → Redis → DB」三层降级读取，修改后**秒级生效**，任何一层故障都不影响请求处理；交付后三份白名单不再依赖 Nacos。

## 功能描述

做什么：

- 网关新增 `WhitelistInterfaceInfoEntity` / `WhitelistInterfaceInfoMapper`（+XML）/ `WhitelistProvider`，白名单改从数据库读取。
- `AuthFilter` 删除三个 `@Value` 字段，白名单校验改调 `WhitelistProvider`。
- framework 管理端增/改/删白名单成功后 `DEL` 三个 Redis key（cache-aside）。
- 迁移脚本将现网 64 条白名单从 Nacos 迁入 `whitelist_interface_info` 表。

不做什么：

- 不加网关 Liquibase changelog（表由 framework 侧管理）。
- 不实现 `http_method` 维度匹配（与现状一致）。
- framework 不写 Redis（回填由网关 read-through 完成）。
- 不处理 AuthFilter 其余 Nacos 配置（csrf / forward / token.header.paths），随 Nacos 整体下线另行立项。

## 验收标准

- [ ] `mvn compile` + `mvn test` 全绿。
- [ ] 冷启动（表为空）：三份白名单为空列表、全部走正常认证。
- [ ] 管理端新增一条 `exemp_flag='1'` 白名单（用当前会被拦截的路径）→ **秒级**后该路径免认证；`redis-cli` 确认 key 被删后网关回写新值（60s TTL）。
- [ ] 删除该白名单 → 秒级恢复拦截。
- [ ] DB 故障（改错 datasource 密码）→ 应用不崩：先沿用 current 旧快照，日志 error。
- [ ] Redis 故障（改错 Redis 地址）→ 白名单仍能从 DB 加载，请求正常。
- [ ] 删除 Nacos 三个配置项 → 应用照常启动运行（三个 `@Value` 已不存在，无残留依赖）。

## 影响范围

| 仓 | 模块 | 说明 |
|---|---|---|
| openlibing-gateway | `AuthFilter`、`WhitelistProvider`、`WhitelistInterfaceInfo*` | 白名单读取链路改造 |
| openlibing-framework | `ServiceInterfaceInfoServiceImpl` | 写方增/改/删成功后 DEL Redis key |
| 共享数据 | 平台 PostgreSQL `whitelist_interface_info` 表 | 白名单唯一数据源 |
