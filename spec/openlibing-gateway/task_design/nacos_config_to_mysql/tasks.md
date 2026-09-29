# nacos_config_to_mysql — 实现任务

## 进度: 7/12 complete

> 备注：网关侧任务（1-7）已随业务 PR `openlibing/openlibing-gateway#202` 合入；framework 侧与 Nacos 下线步骤（8-12）按 spec 约定在本需求交付后执行。

### 网关（读方）

- [x] Task 1: 新增 `WhitelistInterfaceInfoEntity`（字段同 `whitelist_interface_info` 表）
- [x] Task 2: 新增 `WhitelistInterfaceInfoMapper` + XML（`queryAllWhitelist`）
- [x] Task 3: 新增 `WhitelistProvider`（三层加载链 + current/backup 双快照）
- [x] Task 4: 修改 `AuthFilter`（删 3 个 `@Value`，`shouldExemptAuth` / `publicInterface` / `isNoOpenLiBingUserInfoRequired` 改调 provider）
- [x] Task 5: 修改 `AuthFilterTest`（mock `WhitelistProvider`）
- [x] Task 6: 新增 `WhitelistProviderTest`（Redis 命中 / Redis miss 走 DB 回写 / 双快照兜底顺序 / TTL 内不重复查库 / Redis 异常不影响 DB 层 / 仅 DB 成功更新 backup）
- [x] Task 7: 更新 `AGENTS.md`、`README.md` 白名单来源说明

### 写方（framework）

- [ ] Task 8: `ServiceInterfaceInfoServiceImpl` 的 add/update/delete 成功后 `DEL` 三个 Redis key

### Nacos 下线迁移（本需求交付后执行）

- [ ] Task 9: 执行 `docs/sql/migrate-whitelist-from-nacos.sql`（64 条，`http_method` 记 `ANY`），执行后校验数量（exempt 16 / noauth 43 / nouser 5）
- [ ] Task 10: 线上验证每类白名单路径的放行/拦截行为与迁移前一致
- [ ] Task 11: 确认稳定后删除 Nacos 三个配置项（删除前留配置历史快照）
- [ ] Task 12: 回滚方案已文档化（回退网关版本；Nacos 项删除后回滚需先恢复配置项）
