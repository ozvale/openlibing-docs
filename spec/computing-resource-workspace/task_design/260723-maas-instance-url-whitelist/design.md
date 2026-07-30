# 260723-maas-instance-url-whitelist - 设计文档

## 1. 需求背景

生产集群对外部域名做了白名单管控：只有在白名单内的域名/IP 才能被访问，其他地址访问时会被 `connect reset` 拦截。

当前 MaaS 实例的三个地址（`url`、`healthCheckUrl`、`metricsUrl`）没有任何域名限制，带来两个问题：

1. **健康检查/指标采集频率高**（`ModelHealthScheduler` 默认健康检查 60s、metrics 3s），一旦用户配了非白名单地址，会被高频拦截，产生大量失败日志。
2. **失败原因难以区分**：健康检查 failed 到底是「模型失效」还是「被集群白名单拦截」无法从错误码区分，排障成本高。

因此在**创建/更新实例**时，需要校验用户传入的三个地址的主机是否在允许白名单内，不在则直接拒绝配置。

约束：

- 白名单可配置在 Apollo，支持热发布，**无需重启实例即可生效**。
- 不过度设计，做最小实现。
- 后续实例大概率是服务器地址（自建模型，IP 为主），少量可能用内网域名。
- 白名单只收**精确域名/精确 IP**：找集群管理员申请白名单本身就是给精确数据，Apollo 白名单与之一致，匹配逻辑最简。

## 2. 现状分析

### 2.1 入口与现有校验

- 接口入口：`GatewayController` 的 `createInstance` / `updateInstance`。
- 业务实现：`ModelInstanceServiceImpl` 已有 `validateUrlFields(url, healthCheckUrl, metricsUrl)`，目前**只校验 `http://`/`https://` 前缀**，是天然的扩展点。
- 三个地址都在 `CreateInstanceRequest` / `UpdateInstanceRequest` 中，字段一致。

### 2.2 为什么「schedule 类需要重新部署」

`ModelHealthScheduler` 用的是：

```java
@Scheduled(fixedRateString = "${maas.gateway.health-check.interval-ms:60000}")
```

`@Scheduled` 的 `fixedRateString` 在 **Spring 的 `ScheduledAnnotationBeanPostProcessor` 处理 Bean 时解析一次**，随后调度周期固定。Apollo 热发布属性后，**不会重新调度任务**，所以调度间隔类配置需要重启才能生效。

这是 Spring `@Scheduled` 的机制限制，**不是 Apollo 热发布的问题**。

### 2.3 Apollo @Value 是否热生效

本项目 `@EnableApolloConfig` 已开启，且 Apollo 的 `AutoUpdateConfigChangeListener`（`apollo.autoUpdateInjectedSpringProperties` 默认 true）处于运行状态（`logback-spring.xml` 第 98-99 行压制了它的日志，说明它在跑）。

因此**普通 `@Value` 字段在 Apollo 配置变更时会被自动刷新**。`ModelHealthScheduler` 里的 `healthCheckTimeoutMs`、`maxFailures` 也是靠这个机制热生效的（它们在方法调用时读取字段，所以能拿到新值）。

结论：本次校验在 HTTP 请求处理时读取 `@Value` 字段，属于「调用时读取」而非「启动时一次性解析进调度器」，**Apollo 热发布后下一次创建/更新请求即生效，无需重启**。

### 2.4 匹配工具

精确匹配无需特殊工具：`java.net.URI.getHost()` 取主机后，与白名单条目做字符串相等判断即可（统一小写）。不引入 `IpPatternMatcher`（其 CIDR/通配能力本方案不用）。

## 3. 方案设计

### 3.1 校验时机与位置

- 在 `createInstance` / `updateInstance` 已有的 `validateUrlFields` 中增加主机白名单校验，**不新增接口、不改 controller**。
- 三个地址都校验：`url`、`healthCheckUrl`、`metricsUrl`。
- 仅校验**创建/更新时刻**；存量数据通过一次性 changeSet 清空（见 3.8），由用户按白名单重新配置。

### 3.2 白名单配置

| 项 | 值 |
|---|---|
| 配置键 | `maas.instance.url-whitelist` |
| 位置 | Apollo `application` namespace（与 `maas.gateway.*`、`maas.apig.*` 一致） |
| 格式 | 逗号分隔的允许主机列表（仅精确域名/精确 IP） |
| 默认值 | 空 |
| 空/未配置 | 不校验（功能关闭，向后兼容） |

配置示例：

```
maas.instance.url-whitelist=10.0.0.1,10.0.0.2,model.internal.com,api.internal.com
```

空 = 功能关闭（opt-in）。这样既向后兼容，也允许 ops 通过清空配置快速关闭限制进行排查。

### 3.3 匹配规则

1. 用 `java.net.URI(url).getHost()` 提取主机，转小写。
2. 白名单条目只支持**精确主机名/IP**，host 与条目完全相等即放行：

   | 条目形态 | 示例 | 匹配逻辑 |
   |---|---|---|
   | 精确域名 | `model.internal.com` | host 完全相等 |
   | 精确 IP | `10.0.0.1` | host 完全相等 |

3. host 为空（URL 解析不出主机，如格式异常）-> 拒绝。
4. 匹配大小写不敏感（host 与条目统一小写比较）。
5. 命中任一条目即放行。

> 取舍：不引入 CIDR/后缀通配/正则/端口/scheme 维度。理由：找集群管理员申请白名单本身就是给精确的域名/IP，Apollo 白名单与之一致即可；匹配逻辑因此最简（Set 包含判断），最不易出错。

### 3.4 热发布机制（重点）

采用最简方案：**`@Value` 注入原始字符串 + 调用时即时解析**。

```java
@Value("${maas.instance.url-whitelist:}")
private volatile String urlWhitelist;  // Apollo 自动刷新
```

- Apollo 配置变更 -> `AutoUpdateConfigChangeListener` 自动写入字段 -> 下一次创建/更新请求读取到新值。
- 字段标记 `volatile` 保证多线程可见性。
- 解析（split + 小写 + Set 包含）在每次校验时进行：创建/更新是低频操作，几十条目的解析开销可忽略，**省掉缓存与失效逻辑**，最简且必然热生效。

与 `@ApolloConfigChangeListener` 方案（参考 `DashboardMatrixConfig`）的取舍：

- `@ApolloConfigChangeListener` 适合「高频读取 + 需缓存解析结果」的场景（如每个请求都查的看板配置）。
- 本场景低频，`@Value` 自动刷新已足够，**不引入额外监听器**，更最小。

> 与 `@Scheduled` 的区别再强调：`@Scheduled(fixedRateString)` 启动时解析一次进调度器，Apollo 刷新属性不会重新调度，所以调度间隔需重启；本校验是「请求时读字段」，不存在该问题。

### 3.5 白名单为空时的行为

空 = 不校验（功能关闭）。理由：

1. 向后兼容，存量环境不配置即不受影响。
2. 功能 opt-in，ops 在 Apollo 配置后才开启。
3. 与 `260610-access-control-blacklist-whitelist` 中「白名单空 = 放行」的语义一致。

### 3.6 错误处理

- 校验失败返回 400，复用现有 `DataResult.fail(400, msg)`，与 `validateUrlFields` 现有错误风格一致。
- 错误消息指明是哪个地址、哪个主机不在白名单，便于用户排查：

  ```
  健康检查地址的域名 example.com 不在允许访问的白名单内，请联系管理员
  ```

- 前缀校验（http/https）保留不动，白名单校验在前缀校验通过后执行。

### 3.7 新增组件

新增一个小组件 `InstanceUrlWhitelistValidator`（`@Component`），职责单一、可单测：

- `@Value` 注入 `maas.instance.url-whitelist`。
- 提供 `validate(String url, String healthCheckUrl, String metricsUrl)` 返回 `DataResult<Void>`。
- 内部：把白名单字符串 split + trim + 小写 为 `Set<String>`；解析每个非空 URL 的 host（小写）-> 判断是否在 Set 内 -> 任一不在即返回失败。

`ModelInstanceServiceImpl` 改动：

- 注入 `InstanceUrlWhitelistValidator`。
- 在 `validateUrlFields` 末尾（前缀校验通过后）调用 `validator.validate(...)`，失败直接返回。

> 备选：也可不新增类，把 `@Value` 与匹配逻辑直接内联到 `ModelInstanceServiceImpl`。本设计选择独立组件以便单测且保持 service 聚焦，代码量很小（约 40 行）。若倾向更少文件可内联，二选一即可。

### 3.8 存量数据清理 changeSet

引入白名单校验前，存量 instance 可能携带非白名单地址。为保证存量数据合规，新增一个 Liquibase changeSet 清空存量数据，由用户后续按白名单重新配置：

- 文件：`src/main/resources/db/changelog/v1.0.0/maas-tables.xml`
- id：`20260723-017-purge-model-instance-data`
- 操作：`<delete>` 清空 `workspace_model_instance` 和 `workspace_model_instance_health_history`（后者依赖 instance，一并清避免孤儿历史）。
- 一次性数据迁移，下次启动由 Liquibase 自动执行。

changeSet 内容：

```xml
<changeSet id="20260723-017-purge-model-instance-data" author="l00957468">
    <comment>引入实例地址主机白名单校验前，清空存量实例数据（仅清数据不删表），由用户按白名单重新配置</comment>
    <preConditions onFail="MARK_RAN">
        <tableExists tableName="workspace_model_instance"/>
        <tableExists tableName="workspace_model_instance_health_history"/>
    </preConditions>
    <delete tableName="workspace_model_instance"/>
    <delete tableName="workspace_model_instance_health_history"/>
</changeSet>
```

> 取舍：
> - `<delete>` 是 DML，**只清数据、不删表**（删表是 `<dropTable>`）；表结构由 `20260423-005` / `20260519-012` 建，保持不变。
> - 清空而非「按白名单筛选保留」：存量多为测试/历史数据、且无法判断哪些地址在集群白名单内，直接清空最简。
> - `preConditions` 加 `tableExists`（`onFail=MARK_RAN`）：与该文件其他 changeSet 风格一致，表不存在时跳过而非报错，保证环境兼容/幂等。
> - 用 `delete`（而非 truncate）：不重置自增 ID，行为更稳；两表无外键约束，删除顺序无要求。

## 4. 涉及文件

| 类型 | 文件 | 改动 |
|---|---|---|
| 新增 | `business/service/maas/InstanceUrlWhitelistValidator.java` | 白名单校验组件（@Value + 解析 + 精确匹配） |
| 修改 | `business/service/maas/impl/ModelInstanceServiceImpl.java` | 注入 validator；`validateUrlFields` 增加白名单校验调用 |
| 修改 | `src/main/resources/db/changelog/v1.0.0/maas-tables.xml` | 新增 `20260723-017` changeSet，清空存量 instance + health_history 数据（见 3.8） |
| 配置 | Apollo `application` namespace | 新增 `maas.instance.url-whitelist`（空默认值） |
| 测试 | `InstanceUrlWhitelistValidatorTest`（新增） | 覆盖精确域名/精确IP/空配置/host 异常等场景 |

无接口变化、无表结构变化、无 controller 改动；含一个一次性数据清理 changeSet。

## 5. 配置示例

```
# 允许的实例地址主机白名单（逗号分隔；仅精确域名/精确IP）
maas.instance.url-whitelist=10.0.0.1,10.0.0.2,model.internal.com,api.internal.com
```

匹配示例（该配置下）：

| 用户配置的地址 | host | 结果 |
|---|---|---|
| `http://10.0.0.1:8080/v1` | `10.0.0.1` | 通过（精确命中） |
| `http://model.internal.com/health` | `model.internal.com` | 通过（精确命中） |
| `http://10.0.0.3:8080/v1` | `10.0.0.3` | 拒绝（未在白名单） |
| `http://evil.com/health` | `evil.com` | 拒绝 |

## 6. 风险与待确认

| # | 项 | 说明 / 取舍 |
|---|---|---|
| 1 | IPv6 字面量的方括号 | `URI.getHost()` 对 `http://[::1]:8080/` 返回的 host 字符串需与白名单条目精确一致；内部模型服务器以 IPv4 为主，IPv6 极少，若出现由 ops 按实际 host 字符串配置即可。 |
| 2 | 存量数据清理是破坏性操作 | `20260723-017` changeSet 会在下次启动时清空 `workspace_model_instance` 和 `workspace_model_instance_health_history`。上线前需确认存量数据可弃；若需保留某些实例，先导出再上线。 |
| 3 | Apollo 白名单与集群实际白名单需人工保持一致 | 由 ops 维护，本系统只保证「配置的 Apollo 白名单」即允许集合。 |
| 4 | 是否需要独立 enabled 开关 | 当前「空 = 关闭」已满足开关需求。若希望「保留白名单内容但临时关闭」，可再加 `maas.instance.url-whitelist-enabled`（可选，非必要）。 |
