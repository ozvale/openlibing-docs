# proposal: 升级 openlibing-common 至 1.0.21.2-SNAPSHOT（Boot4/Jackson3 适配）

> Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/450
> 分支: operation_log_architecture_v2
> 参考实现: openlibing/openlibing-codecheck#359（commit eb57e25d）、openlibing/openlibing-coderepo#170（commit b08c581c）

## 需求背景

common 仓 1.0.21.2-SNAPSHOT 已发布，技术栈从 Spring Boot 3.5 / Jackson 2 升级至 Spring Boot 4.1.1 / Spring Framework 7 / Jackson 3，用于修复 common 传递引入的开源漏洞与高危 License（jackson、spring-webmvc、logback 等）。codecheck 与 coderepo 仓已完成同分支同目标升级，cicd 需跟进对齐。

## 改造范围

1. pom.xml：common 1.0.21.1-SNAPSHOT → 1.0.21.2-SNAPSHOT；拆除 spring-framework-bom 6.2.11、spring-boot-starter-test/amqp/mail 3.4.4、junit 5.10.2、mockito 5.11.0 钉扎；surefire 2.22.2 → 3.5.5；spring-boot-maven-plugin → 4.1.1
2. Jackson 2→3 全量包名迁移（com.fasterxml.jackson.core/databind → tools.jackson.*），适配 ValueDeserializer / JacksonException（约 10 个 main 文件 + 1 个 test 文件）
3. Rabbit 重试 API 适配：RetryInterceptorBuilder.maxAttempts(3) → maxRetries(2)（Spring 7 语义换算，总尝试次数保持 3 次不变）
4. application.yaml 新增 `spring.jackson.use-jackson2-defaults: true`（feign/ribbon 配置块保留，供后续需求追加）
5. LogHandler 已是 matches/before/after 契约，编译验证兼容性
6. BETA 首次部署后修复三处 Boot3 时代依赖（启动期 NoClassDefFoundError）：redisson-spring-boot-starter 3.25.0 → redisson core（BOM 仲裁 3.45.1）、springdoc 2.8.10 拆钉扎 → BOM 3.1.1、pagehelper 2.1.0 → 4.1.1

## 已知问题核查

- codecheck 升级中发现 spring-boot 4 与 mongodb 4.0 不兼容（需升 4.2+）：cicd 无 mongodb 依赖，该问题不适用

## 验收标准

- [x] mvn compile 通过
- [x] 全量单元测试通过（基线无新增失败，1323 个测试全绿，两轮验证：首版交付 + BETA 修复后复测）
- [x] 消费者重试语义与升级前一致（总尝试 3 次、指数退避、耗尽后 republish 延迟队列）
- [x] 无接口签名变动（Controller 层零改动）
- [ ] BETA 环境重新部署后按回归清单验证通过（P0 启动 / P1 redisson 链路 / P2 分页 / P3 事件 / P4 镜像构建 / P5 操作日志）
