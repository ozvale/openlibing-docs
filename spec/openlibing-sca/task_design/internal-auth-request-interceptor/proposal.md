# Feign 内部调用认证拦截器（InternalAuthRequestInterceptor）

## 需求背景

openlibing-sca 服务间存在内部接口调用（Feign），目前内部接口没有统一、轻量级的认证手段。为内部接口补充一层轻量认证：服务间调用时自动携带内部 token header，供被调方校验，避免内部接口暴露在无认证状态下。

本特性从 `openlibing-anti-poison` 的 `develop_202608_iter1` 分支移植而来。

## 功能描述

- 新增 Feign `RequestInterceptor` 实现 `InternalAuthRequestInterceptor`，标注 `@Component` 由 Spring 自动注册到全局 Feign 请求链。
- 通过 `${internal.auth.token}` 配置注入内部 token。
- 通过 `${internal.auth.enabled:true}` 控制开关（默认开启）。
- `apply(RequestTemplate)` 在 enabled 且 token 非空时，为所有 Feign 出站请求添加 `X-Internal-Token` header；否则仅打 debug 日志跳过。
- 不包含被调方校验逻辑（下游校验由后续 PR/需求实现）。

## 验收标准

- [ ] 编译通过（`mvn compile`）。
- [ ] 配置 `internal.auth.token` 后，Feign 调用请求 header 中包含 `X-Internal-Token`。
- [ ] `internal.auth.enabled=false` 时跳过 header 注入，行为符合预期。
- [ ] token 为空时跳过 header 注入并打 debug 日志。
- [ ] 与既有 Feign 配置兼容，不破坏现有 RequestInterceptor 链。
- [ ] 未配置任何 `internal.auth.*` 时启动不失败（enabled 默认 true、token 默认空 → 跳过注入）。

## 影响范围

- 仅 `openlibing-sca` 仓新增单文件 `src/main/java/com/openlibing/sca/common/interceptor/InternalAuthRequestInterceptor.java`。
- 需要调用方在 `application*.yaml` 中补充 `internal.auth.token`（和可选 `internal.auth.enabled`）配置。
- 无接口契约/数据模型/DB schema/部署变化。
- 行为变化：所有 Feign 出站请求可能新增 `X-Internal-Token` header（配置 token 后）。
