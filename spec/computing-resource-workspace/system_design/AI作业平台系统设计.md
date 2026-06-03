# AI 作业平台（灵枢） — 系统设计

> 更新时间：2026-06-01

## 模块定位

灵枢作业平台当前阶段提供**项目空间管理**和 **MaaS 模型推理代理**两大能力，后续将扩展推理、训练等功能。前端以网页端为主。

## 架构概览

```
客户端 (IDE / Web)
    │
    ├── JWT 鉴权 ──→ OpenlibingAuthInterceptor
    │                 /api/project/**, /api/maas/**(管理), /api/monitor/**
    │
    └── API Key 鉴权 ──→ MaasAuthInterceptor
                         /api/maas/v1/**
    │
    ▼
Workspace 后端 (Spring Boot)
    ├── 项目空间管理
    │   ├── ProjectSpaceService    项目 CRUD
    │   ├── ApiKeyService          API Key 管理（SHA-256 存储）
    │   ├── 成员管理               owner/admin/member 角色体系
    │   └── UserInfoSyncService    用户信息异步同步
    │
    ├── MaaS 模型推理代理
    │   ├── ModelProxyService      请求代理主流程
    │   ├── FormatConversionService Universal Model 格式转换
    │   ├── LoadBalancer           加权随机负载均衡
    │   ├── DegradationService     Tier 层级降级
    │   ├── CircuitBreakerManager  熔断器
    │   ├── RateLimitService       Redis + Lua 限流
    │   ├── ModelHealthScheduler   健康检查 + 指标采集
    │   ├── ParamTransformer       参数过滤与转换
    │   └── MaasTracingLogService  调用日志（文件 + DB 双写）
    │
    └── 用户监控
        └── UserMonitorService     Dashboard / 趋势 / 分布
    │
    ▼
模型推理实例 (vLLM / MindIE / ...)
```

## 核心模块

### 项目空间管理

项目空间是 MaaS 模型调用的隔离单元，每个项目拥有独立的 API Key 和成员权限体系。

| 功能 | 接口路径 | 说明 |
|------|---------|------|
| 项目 CRUD | `/api/project/*` | 创建/查询/更新/删除项目，owner 全权 |
| 成员管理 | `/api/project/{id}/members*` | owner/admin/member 三级角色 |
| API Key 管理 | `/api/project/{id}/apikeys*` | `sk-` 前缀，SHA-256 存储，Redis 缓存验证 |

**角色权限**：

| 角色 | 权限 |
|------|------|
| owner | 全部权限：更新/删除项目、管理成员、管理 API Key |
| admin | 管理成员、管理 API Key |
| member | 查看项目信息、使用 API Key 调用模型 |

**用户信息同步**：`UserInfoSyncService` 在每次接口请求时异步同步用户信息到 `workspace_user_info`，检测 userName 变更则更新业务表冗余字段。添加成员时通过 `FrameworkUserQueryService` 查询三方账号表完成 accountLogin → userId 转换。

### MaaS 模型推理代理

MaaS（Model as a Service）是 AI 作业平台的核心模块，提供模型推理代理服务。

**请求处理主流程**：

```
API Key 鉴权 → 限流检查 → 查找可用实例 → 格式转换 → 负载均衡 → 熔断检查 → HTTP 转发 → 响应转换 → 记录日志 → TPM 校正
```

**接口**：

| 接口 | 路径 | 说明 |
|------|------|------|
| OpenAI Chat | POST `/api/maas/v1/chat/completions` | OpenAI 格式对话 |
| Anthropic Chat | POST `/api/maas/v1/messages` | Anthropic 格式对话 |
| 实例管理 | `/api/maas/{projectId}/instances/*` | CRUD 模型实例 |

**格式转换 (FormatConversionService)**：

采用 Universal Model 中间层模式：源格式 → `ModelAdapter.toUniversal()` → UniversalChatRequest → `ModelAdapter.fromUniversal()` → 目标格式。源格式与目标格式相同时短路跳过转换。

**负载均衡 (LoadBalancer)**：

加权随机策略，权重基于 `InstanceMetricsCache` 中的实时指标（等待队列、运行数、Cache 使用率）动态计算。

**降级 (DegradationService)**：

Tier 层级降级：同 Tier 不同模型 → 下一 Tier 任意模型 → 无可用实例返回错误。

**熔断 (CircuitBreakerManager)**：

状态机：CLOSED → OPEN（连续失败 ≥ 阈值）→ HALF_OPEN（冷却后探测）→ CLOSED/OPEN。基于 ConcurrentHashMap 的内存实现。

**限流 (RateLimitService)**：

Redis + Lua 固定窗口计数器，支持用户级 RPM、实例级 RPM/TPM 三个维度。

**健康检查与指标采集**：

`ModelHealthScheduler` 定时检查所有实例健康状态并采集指标。连续失败 ≥ 3 次标记为 unhealthy。支持 vLLM 和 MindIE 两种后端的 Prometheus 格式指标解析，统一为 `UnifiedMetrics` 模型。

**参数过滤与转换 (ParamTransformer)**：

- 白名单过滤：按后端类型维护参数白名单，从 Apollo 配置热加载
- 参数转换：thinking 处理、reasoning_effort 转换、reasoning_content 补全、cache_control/metadata 移除

**调用日志**：

双写架构：文件通道（`tracing.log`，由 LTS 采集入湖）+ DB 通道（ConcurrentLinkedQueue + Scheduled Flush 批量插入）。

### 用户监控

| 接口 | 路径 | 说明 |
|------|------|------|
| Dashboard | `/api/monitor/project/{id}/user/dashboard` | 用户级概览 |
| 调用趋势 | `/api/monitor/project/{id}/user/call-trend` | 调用量趋势 |
| Token 趋势 | `/api/monitor/project/{id}/user/token-trend` | Token 用量趋势 |
| 模型分布 | `/api/monitor/project/{id}/user/model-distribution` | 模型使用分布 |

第一阶段已实现，第二阶段（更丰富的统计维度）待开发。

## 关键数据模型

| 表 | 说明 |
|------|------|
| `workspace_project_space` | 项目空间 |
| `workspace_project_member` | 项目成员（含角色） |
| `workspace_project_api_key` | API Key（SHA-256 存储） |
| `workspace_user_info` | 用户信息映射（openLiBing ↔ 三方平台） |
| `workspace_model_instance` | 模型实例（含限流配置、健康状态、Tier 层级） |
| `workspace_model_instance_health_history` | 健康检查历史 |

## 关键设计决策

| 决策 | 说明 |
|------|------|
| Universal Model 中间层 | 格式转换通过 Universal Model 解耦，新增格式只需实现 ModelAdapter |
| 源=目标时短路 | 避免不必要的序列化/反序列化，多数国产模型使用 OpenAI 格式 |
| 加权随机负载均衡 | 基于 Metrics 实时权重计算，优先选择负载低的实例 |
| 内存熔断器 | ConcurrentHashMap 实现，轻量高效 |
| Redis + Lua 限流 | 原子操作保证计数准确性 |
| 异步日志双写 | 文件通道入湖 + DB 通道查询，互不阻塞 |
| Tier 层级降级 | 同层优先、逐层降级，保证服务可用性 |
| SHA-256 存储 API Key | 不存明文，验证时对比哈希 |
| 冗余存储 userName | 业务表冗余用户名，避免 JOIN 查询 |

## 鉴权方式

| 拦截器 | 路径 | 鉴权方式 |
|--------|------|---------|
| OpenlibingAuthInterceptor | `/api/project/**`, `/api/maas/**`(管理), `/api/monitor/**` | JWT Token |
| MaasAuthInterceptor | `/api/maas/v1/**` | API Key (Bearer Token) |

`UserContext.resolveUserId()` 统一获取用户 ID，优先级：JWT 已解析 → Header 传入 → Openlibing 上下文 → 一站式作业上下文。

## 后续规划

- 鉴权统一：一站式作业鉴权变更
- 添加用户模块变更，从查表改为openLiBing接口调用，避免依赖数据库
- 用户监控第二阶段：更丰富的统计维度
- 推理服务：模型推理任务的提交与管理
- 训练服务：模型训练任务的提交与管理
