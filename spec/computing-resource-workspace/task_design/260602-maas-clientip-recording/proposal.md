# MaaS 调用记录 clientIp - Proposal

## 一、需求背景

MaaS 代理接口（chat/completions）的鉴权体系独立于项目空间的统一鉴权，使用 API Key + `MaasAuthContext`（ThreadLocal）管理请求上下文。后续需要基于调用方 IP 实现 IP 黑名单封禁能力，MaaS 接口鉴权独立于项目空间，无法复用项目空间的黑白名单管理，需自建基于 IP 的风控能力。

为此，需要在 `workspace_maas_tracing_log` 表中记录每次 MaaS 模型调用的客户端真实 IP，作为 IP 黑名单的前置数据基础。

## 二、前置工作

### 2.1 APIG 环境 IP 获取路径验证

当前部署架构为 `用户 → 华为云 APIG → MaaS 服务`，需确认 APIG 环境下哪个 IP Header 可信。经测试验证（0d3f261b）：

| Header | APIG 处理方式 | 可信度 |
|--------|--------------|--------|
| `X-Forwarded-For` | 原样透传（客户端可伪造） | 不可信 |
| `X-Real-IP` | APIG 覆盖为真实来源 IP | 可信 |
| `RemoteAddr` | TCP 连接来源（与 X-Real-IP 一致） | 可信 |

确定 IP 提取优先级：`X-Real-IP → RemoteAddr → 0.0.0.0`。安全场景必须使用可信 IP，`X-Forwarded-For` 仅用于审计排查。

## 三、改造范围

- `MaasAuthInterceptor`：实现 `resolveClientIp()`，按优先级提取 IP 并存入 `MaasAuthContext`
- `MaasAuthContext`：新增 `clientIp` 字段
- `TracingLogEntity` / `MaasTracingLog`：新增 `clientIp` 字段
- `MaasTracingLogMapper.xml`：INSERT 语句包含 `client_ip`
- 数据库：`maas-tables.xml` 新增 `client_ip` 列
- 所有 `TracingLogEntity.builder()` 调用处添加 `.clientIp(MaasAuthContext.getClientIp().orElse(null))`

## 四、验收标准

- [x] APIG 环境下 IP 提取优先级正确（X-Real-IP → RemoteAddr → 0.0.0.0）
- [x] `workspace_maas_tracing_log` 记录中 `client_ip` 字段有值
- [x] 非流式请求和流式请求均能正确记录 IP
- [x] 降级/限流/重试等错误路径的 `client_ip` 也能正确记录
- [x] 全量测试通过

## 五、约束

- 不修改 `MaasAuthContext` 本身的 ThreadLocal 机制
- 不修改 `workspace_maas_tracing_log` 表结构（`client_ip` 字段已存在）
- 安全场景必须使用可信 IP（X-Real-IP / RemoteAddr），不依赖 `X-Forwarded-For`

## 六、后续展望

本次改动为 IP 黑名单功能的前置基础。后续可实现：
- 基于 `client_ip` 的黑名单封禁（MaaS 专属，不走项目空间黑白名单）
- IP 维度的调用频率监控和异常检测
- 可疑 IP 自动告警
