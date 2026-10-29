# gray-release-review-fixes 技术方案

## 1. 版本匹配规则（VersionLoadBalancer#filterByTrack）

由"track 精确等于 version"改为**二值判定**：`isGrayInstance(instance) == grayTrack`。

- `isGrayInstance`：`version` 元数据忽略大小写等于 `gray` 才为 true；
- metadata 为 **null**、缺 `version` key、值为任意未知值（`1.2.0`/`v2` 等）一律视为 stable；
- 效果：stable 轨道匹配"全部非明确 gray 实例"，元数据命名不统一不再导致存量实例被摘流。

## 2. 回退约束（getInstanceResponse）

- **仅 gray 轨道**在无匹配实例时回退全部实例（灰度未部署期间的正常降级）；
- stable 轨道无匹配（如全部实例均为 gray 的部署异常）返回 `EmptyResponse`，
  宁可该请求失败也不把稳定用户打到未验证实例；
- 回退日志由 WARN 降为 **DEBUG**：该分支是正常降级路径，逐请求 WARN 会刷爆告警通道。

## 3. 可信身份来源（GrayReleaseFilter#getUserId）

- 弃用请求查询参数 `userId`（AuthFilter 豁免路径/免登录接口不注入该参数，
  客户端可伪造白名单身份）；
- 改为与 AuthFilter 同源的 **JWT**：web 登录 cookie `token`，插件登录 header `plugin-token`，
  经 `JwtHelper.getClaimByName(token, UserInfoConstants.FIELD_USER_ID)` 解析；
- token 缺失或解析失败（RuntimeException）返回 null，按非白名单、参与粘性哈希处理，
  不阻断请求。

## 4. 粘性比例分流（resolveTrack）

按请求随机 `ThreadLocalRandom.nextInt(100) < ratio` 改为按用户维度粘性哈希：

```java
Math.floorMod(Objects.hashCode(userId), 100) < ratio
```

- 同一用户（含匿名 userId=null，哈希恒为 0）始终落在同一轨道，避免会话跨版本抖动；
- 行为提示：ratio>0 时匿名流量会整体进入 gray 轨道（符合粘性语义，上线前需知悉）。

## 5. 白名单脱敏与缓存（GrayReleaseConfig）

- `toString` 仅输出 `whitelistSize`，不输出白名单元素（与 `maskUserId` 脱敏约定一致）；
- `getWhitelist()` 返回 `Collections.unmodifiableSet(cachedWhitelist)`：
  - 返回包装是 SpotBugs 认可的写法（直接返回内部字段引用会触发 EI_EXPOSE_REP 门禁）；
  - 解析结果仍按配置串缓存复用（split/trim 只在配置变更时执行一次）。

## 6. 测试补强

- VersionLoadBalancerTest：缺元数据视为 stable、null metadata 不抛 NPE、
  未知版本值按 stable、全 gray 时 stable 不回退（EmptyResponse）共 4 个新用例；
- GrayReleaseFilterTest：ratio=100 匿名请求 → gray（区分比例判定与强制 stable）、
  同用户粘性、伪造 queryParam userId 不生效、坏 token 不阻断；
- GrayReleaseConfigTest：缓存复用通过反射对内部 `cachedWhitelist` 字段做
  `assertSame`（返回值是每次新建的不可变视图，不能对返回值做同一性断言）；
- 新增 VersionLoadBalancerConfigTest：ApplicationContextRunner + LoadBalancerAutoConfiguration，
  断言子上下文 `ReactorLoadBalancer<ServiceInstance>` 为 VersionLoadBalancer，
  防止默认 RoundRobinLoadBalancer 未被替换时灰度静默失效。

## 影响范围

- 改动文件：主代码 3 个（GrayReleaseFilter / GrayReleaseConfig / VersionLoadBalancer），
  测试 4 个（含新增 VersionLoadBalancerConfigTest）；
- 配置兼容性：**无破坏**；白名单/比例/开关配置项不变；
- 行为变化：匿名（无可信 JWT）请求在 ratio>0 时全部进入 gray 轨道（原为按请求随机）。
