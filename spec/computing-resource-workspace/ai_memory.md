# computing-resource-workspace AI Memory

本文档保存 `computing-resource-workspace` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`computing-resource-workspace` 是 OpenLiBing 平台的**计算资源工作区服务**，基于 Spring Boot（Java 21）构建，承载两大业务板块：

1. **一站式作业** — IDE插件，主要功能为环境申请 → 软件安装 → 任务执行 → 资源释放，对接 HiDevLab
2. **AI 作业平台（灵枢）** — 项目空间管理 + MaaS 模型推理代理，网页端

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及鉴权、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 鉴权体系

- 系统存在三套独立鉴权拦截器，修改鉴权逻辑时必须确认影响的是哪套拦截器。
- `AuthInterceptor`（一站式作业）：Cookie + HiDevLab 权限校验，计划迁移为 JWT。
- `OpenlibingAuthInterceptor`（AI 作业平台管理接口）：JWT Token 鉴权。
- `MaasAuthInterceptor`（MaaS 模型调用）：API Key 鉴权，Key 以 SHA-256 哈希存储。
- `UserContext.resolveUserId()` 有优先级链，修改时需注意各场景下的用户 ID 来源。

## MaaS 模块约束

- 格式转换使用 Universal Model 中间层，新增格式只需实现 `ModelAdapter`，不要在代理主流程中硬编码格式逻辑。
- 源格式与目标格式相同时会短路跳过转换，不要假设每次请求都经过完整转换。
- 限流使用 Redis + Lua 固定窗口，修改限流逻辑时需保证 Lua 脚本的原子性。
- 调用日志是双写架构（文件 + DB），修改日志字段时需同步两处。
- 参数过滤规则从 Apollo 配置热加载，不要在代码中硬编码白名单。

## 环境管理约束

- 环境状态流转由 `EnvStatusTransitionService` 统一管理，不要在业务代码中直接修改环境状态。
- `deploy_failed` / `install_failed` 会自动触发释放，不要遗漏这些自动流转路径。
- 定时轮询使用 Redis 分布式锁，多实例部署时需确保锁的正确性。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| 修改鉴权逻辑时遗漏拦截器注册顺序 | 修改拦截器后必须检查 `WebConfig.addInterceptors()` 中的注册顺序和路径匹配 | — |
| 新增模型格式时在代理主流程硬编码 | 新增格式必须实现 `ModelAdapter` 接口并注册到 `AdapterRegistry` | — |
| 修改环境状态时绕过状态机 | 环境状态变更必须通过 `EnvStatusTransitionService` | — |
