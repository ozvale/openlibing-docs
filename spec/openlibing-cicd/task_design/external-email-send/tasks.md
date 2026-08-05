# external-email-send — 实现任务

## 进度: 0/5 complete

- [ ] Task 1: 新增 `dto/email/EmailSendReqDTO.java`：title（`@NotBlank`）、content（`@NotBlank @Size(max=100000)`）、contentType（默认 "html"）、recipients（`@NotEmpty @Size(max=50) List<@Email>`）
- [ ] Task 2: 新增 `controller/EmailSendController.java`：`@PostMapping` 接收 `@RequestBody @Valid EmailSendReqDTO`，调用 EmailSendService.send，返回 `DataResult<String>`
- [ ] Task 3: 新增 `service/EmailSendService.java` 接口 + `service/impl/EmailSendServiceImpl.java` 实现：内容标准化（text→`<pre>`+HTML转义）→ 委托 `EmailSender.send`（传入限流 key）→ 返回结果
- [ ] Task 4: 修改 `listener/PipelineFailEmailConsumer.java`：`@RabbitListener` 新增 `concurrency = "5"`
- [ ] Task 5: 编译验证 + 全量测试通过

## 验证方式
- Phase 1：编译通过（`mvn compile -pl . -am`）
- Phase 2：发送测试请求确认邮件送达
- Phase 3：全量测试通过

## 生成前约束检查
- [x] 只修改 `openlibing-cicd` 业务仓
- [x] 遵循既有代码风格（华为版权头、Javadoc、SLF4J 日志）
- [x] 避免无关重构、无关格式化
- [x] 无硬编码凭证、敏感信息
