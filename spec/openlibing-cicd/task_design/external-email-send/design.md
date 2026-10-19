# external-email-send — 技术设计

## 方案概述
在 openlibing-cicd 中新增外部邮件发送 REST 接口。Controller 接收请求后委托 Service 层对内容进行标准化（纯文本转 HTML），再通过现有 `EmailSender` 组件发送，借助 RabbitMQ 实现异步投递。

## 架构决策

### 决策 1：接口路径
- 选择：`POST /project/email/send`
- 原因：与现有 `/project/` 前缀保持一致，便于网关路由统一配置

### 决策 2：内容类型处理
- 选择：纯文本内容自动包装 `<pre>` 标签并做 HTML 转义，HTML 内容原样发送
- 原因：`EmailSender` 底层使用 HTML 格式发送，纯文本需转换为 HTML 以保证显示格式

### 决策 3：限流策略
- 选择：使用固定 key `external_email_send` 复用 `EmailSender` 内置限流
- 原因：避免新增限流组件，与现有邮件发送共享限流水位

### 决策 4：消费者并发
- 选择：`PipelineFailEmailConsumer` 新增 `concurrency = "5"`
- 原因：流水线失败邮件场景存在突发高峰，提高消费能力减少消息堆积

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `controller/EmailSendController.java` | 新增 | `POST /project/email/send` 端点 |
| `dto/email/EmailSendReqDTO.java` | 新增 | 请求体 DTO，含 Bean Validation |
| `service/EmailSendService.java` | 新增 | 邮件发送服务接口 |
| `service/impl/EmailSendServiceImpl.java` | 新增 | 服务实现：内容标准化 + 限流 + 委托发送 |
| `listener/PipelineFailEmailConsumer.java` | 修改 | `@RabbitListener` 新增 `concurrency = "5"` |

## 风险 & 缓解
- **风险 1**：邮件发送失败（EmailSender 异常）
  - 缓解：Service 层 catch 异常后记录错误日志，返回友好提示，不抛到 Controller
- **风险 2**：限流导致部分请求被丢弃
  - 缓解：限流为 `EmailSender` 内置能力，超出水位时返回错误而非静默丢弃

## 跨仓影响
无。改动仅限 `openlibing-cicd` 仓。
