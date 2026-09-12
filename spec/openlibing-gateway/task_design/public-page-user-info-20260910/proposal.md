# Proposal: 免认证页面已登录用户信息透传与 bcprov 漏洞修复

## 需求背景

openlibing-gateway 的 `AuthFilter` 原有逻辑中，无认证可访问详情页面（publicInterface）仅对**未携带 token** 的请求放行；已登录用户（Cookie 中带 token）访问这类页面时不会命中放行分支，会继续走完整认证流程，导致已登录用户访问公开详情页时被拦截或丢失用户上下文，下游接口无法获取用户信息做个性化展示。

同时，安全扫描发现 `bcprov-jdk18on` 1.84 存在已知漏洞，需要升级到 1.85。

本期（release_20260910 迭代）需要：

1. **免认证页面已登录用户信息透传**：已登录用户访问无认证详情页面时放行请求，并将用户信息（从 JWT 解析）封装进下游请求，传递给后端接口。
2. **bcprov 漏洞修复**：`bcprov-jdk18on` 1.84 → 1.85。

## 功能描述

### 做什么

- `AuthFilter.filter` 中 publicInterface 分支调整：携带 token 的请求不再落入后续认证流程，而是通过已有的 `getNewServerWebExchange` 方法封装用户信息后放行到下游
- `pom.xml` 中 `bcprov-jdk18on` 版本 1.84 → 1.85

### 不做什么

- 不修改 `getNewServerWebExchange` / `getNewRequestParams` 本身（复用已有实现，其他鉴权路径已在用）
- 不修改受保护接口的鉴权流程、CSRF 校验、机器接口鉴权等逻辑
- 不修改数据库 schema、路由配置

## 验收标准

- [x] 本地编译通过
- [x] 单元测试通过（1453 个测试，含更新后的 `testFilterWithPublicInterfaceAndToken`）
- [x] 未登录用户访问公开详情页：直接放行（行为不变）
- [x] 已登录用户访问公开详情页：放行且下游请求查询参数携带 `openLiBingUserId` / `openLiBingUserName` 等用户信息
- [x] 受保护接口鉴权行为不变
- [ ] 部署后环境验证：已登录用户访问免登录页面可获取用户信息

## 影响范围

### 业务仓文件

| 文件                                                    | 操作 | 说明                                                                |
| ------------------------------------------------------- | ---- | ------------------------------------------------------------------- |
| `src/main/java/.../business/filter/AuthFilter.java`     | 修改 | publicInterface 分支：已登录用户封装用户信息后放行（+8/-3）         |
| `pom.xml`                                               | 修改 | bcprov-jdk18on 1.84 → 1.85                                          |
| `src/test/java/.../business/filter/AuthFilterTest.java` | 修改 | 更新 `testFilterWithPublicInterfaceAndToken` 以匹配新行为（+21/-3） |

### 跨仓影响

- 无跨仓依赖变更（bcprov-jdk18on 为直接依赖，1.85 已发布到 Maven 中央仓库）

## 关联

- 业务 PR: openlibing/openlibing-gateway#190（`codechentao:chentao_release_20260910` → `release_20260910`）
- 同分支前置变更 spec: [nacos-springdoc-20260910](../nacos-springdoc-20260910/)（PR #189）
