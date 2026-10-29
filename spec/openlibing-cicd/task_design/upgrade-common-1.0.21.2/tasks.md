# tasks: 升级 openlibing-common 至 1.0.21.2-SNAPSHOT（Boot4/Jackson3 适配）

> Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/450

- [x] T1 pom.xml：common 升 1.0.21.2-SNAPSHOT，拆 spring-framework-bom / Boot starter / junit / mockito 钉扎
- [x] T2 pom.xml：surefire 2.22.2 → 3.5.5，spring-boot-maven-plugin → 4.1.1
- [x] T3 Jackson 2→3 迁移：10 个 main 文件 + 1 个 test 文件（包名、异常类型、ValueDeserializer）
- [x] T4 RabbitConnectionFactoryConfig：maxAttempts(3) → maxRetries(2)，注释修正
- [x] T5 application.yaml 新增 `spring.jackson.use-jackson2-defaults: true`（feign/ribbon 配置块曾评估为死配置删除，后按用户要求恢复保留）
- [x] T6 mvn compile 验证（含 LogHandler 契约兼容性确认）
- [x] T6a 测试切片迁移：pom 新增 spring-boot-starter-webmvc-test（test scope，Boot 4 将 @WebMvcTest 拆到独立构件），PipelineControllerTest 的 import 迁至 org.springframework.boot.webmvc.test.autoconfigure
- [x] T6b mybatis-plus 3.5.10.1→3.5.17 传递升级适配：ImageServiceImplTest.deleteImage 补 TableInfoHelper.initTableInfo（3.5.17 中 in() 构建期即解析 Lambda 列名）
- [x] T7 全量单测执行，确认基线无新增失败（1323 个测试全绿，4 个既有跳过；ImageServiceImplTest 经 stash 验证为升级引入，已修复）
- [x] T8 自检报告：接口变动检测（无变动）、mongodb 兼容性结论（不适用）
- [x] T9 BETA 首次部署启动异常修复（commit 96136e9d3）：redisson-spring-boot-starter 3.25.0 → redisson core（BOM 仲裁 3.45.1，RedisConfig 手动装配 starter 纯多余且引用 Boot 3 内部类崩溃）、springdoc 2.8.10 拆钉扎 → BOM 3.1.1、pagehelper 2.1.0 → 4.1.1；修复后 1323 个单测复测全绿
- [ ] T10 BETA 重新部署后按回归清单验证（P0 启动 / P1 redisson 链路 / P2 分页 / P3 事件 / P4 镜像构建 / P5 操作日志），异常反馈至 Issue #450
