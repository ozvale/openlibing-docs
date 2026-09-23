# nacos_config_to_mysql — 技术设计

## 方案概述

白名单数据由数据库统一管理（framework 管理端维护），网关通过 `WhitelistProvider` 按「内存快照 → Redis → DB」三层降级读取；写方增/改/删成功后主动 `DEL` Redis key（cache-aside），修改后秒级生效，任一中间层故障不影响请求处理。

## 架构决策

1. **DB 是唯一数据源**：内存兜底数据同样来自 DB（最近一次成功加载副本），无常量类、零额外维护。
2. **内存双快照**（volatile）：`current`（实际用途，每次成功加载后更新）+ `backup`（仅 DB 成功加载时更新，最终兜底）。
3. **加载链**：
   ```
   ① current 未过期（5s TTL）→ 用 current，0 网络开销
   ② 过期 → 读 Redis 命中 → 更新 current → 用
   ③ Redis miss → 查 DB 成功 → 更新 current + backup → 写回 Redis（60s TTL）→ 用
   ④ Redis 失败 + DB 失败 → 用 current（陈旧但可用）→ 无 current → 用 backup → 皆无 → 空列表 + error
   ```
4. **Redis key 约定**（网关所有，framework 只删不写）：`whitelist:exempt_paths`、`whitelist:no_users_info_paths`、`whitelist:no_auth_paths`，值均为 JSON 数组；60s 服务端 TTL 仅作漏删兜底。
5. **匹配逻辑不变**：沿用 `path.contains(whitelist)`（含 cicd `{projectId}` 插值）；`http_method` 维度本期忽略。
6. **无 Nacos 依赖**：`WhitelistProvider` 无任何 `@Value`，Nacos 下线不影响。
7. **并发**：double-check + `synchronized` 防重复加载；快照为 volatile 不可变对象；Redis 读写全部 try-catch，故障自动滑落 DB 层。

## 涉及文件

| 文件                                                              | 操作 | 说明                                          |
| ----------------------------------------------------------------- | ---- | --------------------------------------------- |
| `gateway .../entity/permission/WhitelistInterfaceInfoEntity.java` | 新增 | Lombok `@Data`，字段同表结构                  |
| `gateway .../mapper/WhitelistInterfaceInfoMapper.java`            | 新增 | `queryAllWhitelist()`                         |
| `gateway resources/mapper/WhitelistInterfaceInfoMapper.xml`       | 新增 | SQL：三 flag 任一为 '1' 全量查询              |
| `gateway .../common/utils/WhitelistProvider.java`                 | 新增 | 加载链 + 双快照 + 三个 getter                 |
| `gateway .../business/filter/AuthFilter.java`                     | 修改 | 删 3 个 `@Value`，三处校验改调 provider       |
| `gateway .../filter/AuthFilterTest.java`                          | 修改 | 反射注入改为 mock `WhitelistProvider`         |
| `gateway .../utils/WhitelistProviderTest.java`                    | 新增 | 加载链/兜底/TTL/异常场景                      |
| `gateway AGENTS.md / README.md`                                   | 修改 | 白名单来源说明（原 Nacos key 废弃）           |
| `framework ServiceInterfaceInfoServiceImpl.java`                  | 修改 | add/update/delete 成功后 `DEL` 3 个 Redis key |

## 风险 & 缓解

| 风险                             | 缓解                                               |
| -------------------------------- | -------------------------------------------------- |
| 冷启动且 DB 全程不可用 → 空列表  | 实际不可达（应用本身无法完成启动）；error 日志标记 |
| Redis 故障                       | 自动滑落 DB 层，请求不受影响                       |
| 多实例生效时间差                 | ≤5s，最终一致；DB 回源压力 = 每实例每分钟 ≤3 次    |
| 迁移脚本绕过 `url_flag` 台账联动 | §9.1 补偿 SQL（可选，仅影响台账数据质量）          |
| Nacos 配置项删除后需回滚         | 回滚前先恢复三个配置项（删除时留历史快照）         |

## 跨仓影响

- **openlibing-framework**：`ServiceInterfaceInfoServiceImpl` 三个写方法成功后新增 `DEL` Redis key 调用；`whitelist_interface_info` 表由 framework 侧管理（网关只读）。
- **共享平台 PostgreSQL**：网关与 framework 共库（已有 `machine_interface`、`user_info` 等共享表先例）。
