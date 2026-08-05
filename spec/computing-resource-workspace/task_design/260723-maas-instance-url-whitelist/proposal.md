# 260723-maas-instance-url-whitelist - Proposal

## 一、需求背景

生产集群对外部域名做了白名单管控，非白名单域名/IP 访问会被 `connect reset` 拦截。当前 MaaS 实例的 `url`、`healthCheckUrl`、`metricsUrl` 三个地址无任何域名限制，导致：

1. 健康检查（默认 60s）/指标采集（默认 3s）频率高，用户配了非白名单地址会被高频拦截，产生大量失败日志。
2. 健康检查 failed 难以区分是「模型失效」还是「被集群白名单拦截」，排障成本高。

需要在创建/更新实例时校验这三个地址的主机是否在允许白名单内，不在则直接拒绝配置。

## 二、功能描述

1. **校验时机**：`createInstance` / `updateInstance` 的现有 `validateUrlFields` 中增加主机白名单校验，不新增接口、不改 controller。
2. **校验对象**：`url`、`healthCheckUrl`、`metricsUrl` 三个地址。
3. **匹配规则**：仅精确域名/精确 IP 匹配（`URI.getHost()` 小写后做 Set 包含判断），不引入 CIDR/通配/正则。
4. **配置方式**：Apollo `application` namespace 新增 `maas.instance.url-whitelist`（逗号分隔），`@Value` 注入；Apollo 热发布自动刷新字段，**无需重启**（与 `@Scheduled(fixedRateString)` 启动时一次性解析不同，本校验在请求时读字段）。
5. **空白名单**：空/未配置 = 不校验（功能关闭，向后兼容）。
6. **存量数据**：新增 Liquibase changeSet 清空 `workspace_model_instance` 和 `workspace_model_instance_health_history`，由用户按白名单重新配置。

## 三、验收标准

- [ ] 创建实例时，三个地址 host 不在白名单则返回 400，错误消息指明地址与 host
- [ ] 更新实例时同样校验（含只更新部分字段、地址沿用旧值的场景）
- [ ] 白名单仅精确域名/IP 匹配，大小写不敏感
- [ ] 白名单为空时不校验（放行）
- [ ] Apollo 修改 `maas.instance.url-whitelist` 后，下一次创建/更新请求即生效，无需重启
- [ ] 存量数据被 changeSet 清空（两表），表结构不变
- [ ] 无接口变化、无表结构变化、无 controller 改动
- [ ] 编译通过、相关单元测试通过

## 四、影响范围

- **新增**：`InstanceUrlWhitelistValidator`（@Component，@Value + 精确匹配）
- **修改**：`ModelInstanceServiceImpl`（注入 validator，`validateUrlFields` 增加调用）
- **修改**：`maas-tables.xml`（新增 `20260723-017` 清理 changeSet）
- **配置**：Apollo 新增 `maas.instance.url-whitelist`
- **测试**：新增 `InstanceUrlWhitelistValidatorTest`

## 五、约束

- 不过度设计，做最小实现
- 白名单只收精确域名/IP（找集群管理员申请白名单本身就是给精确数据）
- 不引入 CIDR/后缀通配/正则/端口/scheme 维度
- 存量数据直接清空，不做「按白名单筛选保留」
- 业务仓 PR 不带 spec 文件

## 六、后续展望

- 如需 IPv6 网段或 CIDR 批量匹配，后续可扩展匹配规则
- 如需「保留白名单内容但临时关闭」，可加 `maas.instance.url-whitelist-enabled` 开关
- 如需排查存量不合规实例，可加管理接口列出疑似实例（本次不做）
