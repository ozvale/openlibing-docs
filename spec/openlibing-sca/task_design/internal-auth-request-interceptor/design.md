# Feign 内部调用认证拦截器 — 技术设计

## 方案概述

实现 `feign.RequestInterceptor` 接口，通过 `@Component` 让 Spring 自动注册为全局 Feign 请求拦截器；每次 Feign 出站请求构建时自动注入 `X-Internal-Token` header，实现服务间内部调用的轻量级认证。

## 关键决策

1. **基于 Feign 原生 `RequestInterceptor` 而非 Spring MVC 拦截器**：Feign 请求模板阶段拦截，覆盖所有 Feign 客户端（不限 Controller 入口），统一且侵入最小。
2. **`@Component` 自动注册**：无需手动将拦截器挂到每个 FeignClient 配置，Spring 扫描到 `RequestInterceptor` Bean 即自动加入全局 Feign 链路。
3. **配置驱动 + 安全默认值**：`enabled` 默认 true，但 `token` 默认空 → 空 token 时跳过注入，保证未配置时启动不失败、不发带空值的 header。
4. **空值判断用 `StringUtils.isEmpty`**：覆盖 null 与空字符串两种情况。
5. **跳过场景只打 debug 日志**：避免无 token 部署时刷 error 日志。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/sca/common/interceptor/InternalAuthRequestInterceptor.java` | 新增 | 拦截器实现，~49 行 |

## 配置项

| 配置键 | 默认 | 说明 |
|--------|------|------|
| `internal.auth.token` | 空 | 内部调用 token，注入到 `X-Internal-Token` header |
| `internal.auth.enabled` | true | 总开关；false 时跳过注入 |

## 行为逻辑

```
apply(template):
  authEnabled == false        → debug "Internal auth is disabled"    return
  token 为空                  → debug "Internal auth token is empty" return
  否则                        → template.header("X-Internal-Token", token)
```

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 新增配置项未在 `application*.yaml` 中配置 | token 默认空 → 跳过注入，不导致启动失败；文档/Issue 提示补充配置 |
| 下游服务未校验 `X-Internal-Token` | 拦截器等同于无操作；下游校验逻辑由后续需求实现（本 PR 不含） |
| 全局拦截器影响所有 Feign 出站请求 | 仅新增一个 header，不修改请求体/路径；enabled=false 可整体关闭 |

## 跨仓影响

- 移植来源：`openlibing-anti-poison`（`develop_202608_iter1` 分支）已有同款实现，两仓实现保持一致。
- 本 PR 不含下游校验改动，不改变任何外部接口契约。
