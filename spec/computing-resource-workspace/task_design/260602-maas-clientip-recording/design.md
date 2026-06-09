# MaaS 调用记录 clientIp - Design

## 一、功能目标

在 `workspace_maas_tracing_log` 表中记录每次 MaaS 模型调用的客户端真实 IP，为后续 IP 黑名单封禁提供数据基础。

## 二、IP 提取方案

### 2.1 部署架构

```
用户 → 华为云 APIG → MaaS 服务
```

经测试验证（0d3f261b），APIG 环境下各 IP Header 可信度：

| Header | APIG 处理方式 | 可信度 |
|--------|--------------|--------|
| `X-Forwarded-For` | 原样透传（客户端可伪造） | 不可信 |
| `X-Real-IP` | APIG 覆盖为真实来源 IP | 可信 |
| `RemoteAddr` | TCP 连接来源（与 X-Real-IP 一致） | 可信 |

### 2.2 IP 提取优先级

```
X-Real-IP → RemoteAddr → 0.0.0.0（兜底值）
```

安全原则：黑名单、限流、风控等安全场景**必须**使用可信 IP（X-Real-IP 或 RemoteAddr），`X-Forwarded-For` 仅用于审计排查，不参与安全决策。

### 2.3 实现位置

在 `MaasAuthInterceptor.preHandle()` 中，API Key 验证通过后调用 `resolveClientIp(request)` 提取 IP，存入 `MaasAuthContext`。

## 三、数据流

```
MaasAuthInterceptor.resolveClientIp(request)
       │ (X-Real-IP → RemoteAddr → 0.0.0.0)
       ▼
  MaasAuthContext.clientIp
       │
       ▼ (各 TracingLogEntity.builder() 调用处)
  TracingLogEntity.clientIp
       │
       ▼
  workspace_maas_tracing_log.client_ip
```

所有 `TracingLogEntity.builder()` 调用处通过 `MaasAuthContext.getClientIp().orElse(null)` 获取 IP 值，包括：
- `ModelProxyServiceImpl`：阻塞请求成功/失败
- `StreamingRequestHandler`：流式请求成功/失败
- `ProxyErrorResponseWriter`：限流拒绝、降级耗尽等错误路径

## 四、涉及文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| MaasAuthInterceptor.java | 修改 | 新增 `resolveClientIp()`，IP 提取优先级：X-Real-IP → RemoteAddr → 0.0.0.0 |
| MaasAuthContext.java | 修改 | 新增 `clientIp` 字段 |
| TracingLogEntity.java | 修改 | 新增 `clientIp` 字段 |
| MaasTracingLog.java | 修改 | 新增 `clientIp` 字段 |
| maas-tables.xml | 修改 | 新增 `client_ip` 列定义 |
| MaasTracingLogMapper.xml | 修改 | INSERT 语句包含 `client_ip` |
| ModelProxyServiceImpl.java | 修改 | `TracingLogEntity.builder()` 添加 `.clientIp()` |
| StreamingRequestHandler.java | 修改 | `TracingLogEntity.builder()` 添加 `.clientIp()` |
| ProxyErrorResponseWriter.java | 修改 | `TracingLogEntity.builder()` 添加 `.clientIp()` |

## 五、风险评估

- **风险低**：改动为纯增量，在现有数据链路上增加字段，不改变业务逻辑
- **兼容性**：`clientIp` 为 nullable 字段，取不到也不影响原有流程
- **安全**：IP 提取使用可信 Header，不依赖客户端可控的 `X-Forwarded-For`
