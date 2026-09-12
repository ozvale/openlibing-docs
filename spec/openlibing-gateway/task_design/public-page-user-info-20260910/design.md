# Design: 免认证页面已登录用户信息透传与 bcprov 漏洞修复

## 技术方案

### 1. AuthFilter publicInterface 分支调整

**变更前**：

```java
// 无认证可访问详情页面(token信息需为空)
if (publicInterface(path) && !tokenFromCookie.isPresent()) {
  return chain.filter(exchange);
}
```

携带 token 的请求不命中放行分支，继续走认证流程（CSRF / referer 校验等），已登录用户访问公开详情页可能被拦截。

**变更后**：

```java
// 无认证可访问详情页面
if (publicInterface(path)) {
  // 未登录用户访问无认证详情页面
  if (!tokenFromCookie.isPresent()) {
    return chain.filter(exchange);
  }
  // 已登录用户访问无认证详情页面，需要单独封装用户信息给接口
  return chain.filter(getNewServerWebExchange(chain, exchange, tokenFromCookie.get()));
}
```

两种路径：

- **未登录**（无 token）：行为与原来完全一致，直接放行原始 exchange。
- **已登录**（有 token）：复用已有的 `getNewServerWebExchange` 方法封装用户信息后放行。

### 2. getNewServerWebExchange 复用说明

`getNewServerWebExchange` / `getNewRequestParams` 为 AuthFilter 中**已有**的私有方法（web 登录插件等其他鉴权路径已在用），本次变更未修改这两个方法本身：

- `getNewRequestParams`：从 JWT token 解析 `openLiBingUserId` / `openLiBingUserName` 等用户信息字段，添加到请求查询参数中；解析失败（CustomSecurityException / JWTDecodeException）时仅记录错误日志并返回原始参数，不阻断请求。
- `getNewServerWebExchange`：基于原始请求构建新的 ServerWebExchange（mutate），携带新查询参数。

用户信息字段常量定义在 `UserInfoConstants`（FIELD_USER_ID、FIELD_USER_NAME 等）。

### 3. bcprov-jdk18on 升级

`pom.xml` 直接依赖版本 1.84 → 1.85，修复安全扫描发现的已知漏洞。BouncyCastle 1.85 与 1.84 API 兼容，无代码适配需要。

## 影响范围分析

- **鉴权行为变化**：仅 publicInterface 命中且携带 token 的请求路径发生变化（原：走完整认证流程；新：封装用户信息后放行）。未登录访问、受保护接口、机器接口等路径行为不变。
- **风险点**：
  - 已登录用户带 token 访问公开页面时，JWT 解析失败会静默降级为不带用户信息的原始参数放行（沿用既有 getNewRequestParams 行为）。
  - 需确认下游公开详情接口对新增的查询参数（openLiBingUserId 等）兼容（多余参数通常被忽略，已有路径验证过）。

## 测试策略

更新 `AuthFilterTest.testFilterWithPublicInterfaceAndToken`：

- 根因：原测试断言旧行为（期望 401），且未 stub `webFilterChain.filter`，生产代码变更后返回 null 导致 `.block()` 抛 NPE。
- 新测试：stub `webFilterChain.filter` 返回 `Mono.empty()`、stub `jwtUtils.getClaimValue`，通过 ArgumentCaptor 捕获传递给过滤器链的 exchange，断言：
  - 过滤器链被调用 1 次
  - 转发的 exchange 是封装后的新 exchange（非原对象）
  - 新 exchange 查询参数携带 userId / userName 用户信息

## 备选方案

- **在下游接口单独做 token 解析**：需要每个公开接口重复实现，侵入性大，不采用。
- **新增独立 Filter 处理**：增加过滤器链复杂度，且用户信息封装逻辑与已有方法重复，不采用。
