# 【openlibing-cicd】外部邮件发送接口

## 需求背景
openlibing-cicd 现有邮件发送能力仅服务于流水线失败通知等内部场景。外部服务（经网关认证）需要独立的邮件发送入口，提供标题、内容、收件人列表的通用邮件发送能力。

关联 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/51

## 功能描述
1. `EmailSendController` 新增 `POST /project/email/send` 接口，接收外部邮件发送请求
2. `EmailSendReqDTO` 请求体包含：title（标题）、content（内容）、contentType（html/text，默认 html）、recipients（收件人列表，最大 50 个）
3. `EmailSendService` / `EmailSendServiceImpl` 处理邮件发送逻辑，支持 HTML 内容与纯文本内容自动转换
4. 纯文本内容自动包装为 `<pre>` 标签并做 HTML 转义后发送
5. 使用 `EmailSender` 现有能力发送，通过固定 key 做限流
6. `PipelineFailEmailConsumer` 邮件消费者新增 `concurrency = "5"` 并发消费配置

## 不做
- 不新增邮件发送引擎，复用现有 `EmailSender`
- 不修改邮件模板逻辑
- 不处理附件发送
- 不新增鉴权（由 API 网关统一认证）

## 验收标准
- [ ] `POST /project/email/send` 返回成功响应，邮件送达收件人
- [ ] `contentType=text` 时内容自动包装为 `<pre>` 并转义 HTML 特殊字符
- [ ] `contentType=html` 时内容原样发送
- [ ] 收件人列表超过 50 个时返回校验错误
- [ ] 收件人邮箱格式不合法时返回校验错误
- [ ] 标题为空时返回校验错误
- [ ] 内容为空时返回校验错误
- [ ] `EmailSender` 发送异常时返回友好的错误信息
- [ ] `PipelineFailEmailConsumer` 使用 concurrency=5 并发消费

## 影响范围
- 后端：`openlibing-cicd` 仓
  - `controller/EmailSendController.java`：新增外部邮件发送端点
  - `dto/email/EmailSendReqDTO.java`：新增请求体 DTO（含 Bean Validation）
  - `service/EmailSendService.java`：新增服务接口
  - `service/impl/EmailSendServiceImpl.java`：新增服务实现（HTML 标准化、限流、委托 EmailSender）
  - `listener/PipelineFailEmailConsumer.java`：新增 concurrency=5 配置
