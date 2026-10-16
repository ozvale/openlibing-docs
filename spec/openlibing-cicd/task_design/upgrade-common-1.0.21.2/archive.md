# 升级 openlibing-common 至 1.0.21.2-SNAPSHOT（Boot4/Jackson3 适配）— 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/450
- 业务 PR: 无独立业务 PR——业务分支 operation_log_architecture_v2 由多人协作提交，最终由同事统一合入 develop_202610_iter1；业务改动以下方交付历程中的 cicd 分支提交为准
- docs PR: <创建后回填>

## 交付历程

业务改动均位于 cicd 仓 `operation_log_architecture_v2` 分支：

- commit [055b0750](https://gitcode.com/openlibing/openlibing-cicd/commit/055b07502712b47ad88ce9e83b3287de3b034433)：升级 common 1.0.21.2-SNAPSHOT 并适配 Boot4/Jackson3（pom 拆钉扎、Jackson 2→3 迁移、Rabbit maxRetries 语义换算、yaml use-jackson2-defaults、@WebMvcTest 切片迁移、mybatis-plus 3.5.17 单测适配）
- commit [a6b7cfcf](https://gitcode.com/openlibing/openlibing-cicd/commit/a6b7cfcfb9a08304d0a721ed04c6d3e50eeaecf9)：补回误删除的 feign 配置块（用户手动提交）
- commit [96136e9d](https://gitcode.com/openlibing/openlibing-cicd/commit/96136e9d36d47db0fe1224ddab4b6fa75f12fe0b)：修复 Boot4 升级遗留的三个 Boot3 时代依赖（redisson starter→core 3.45.1、springdoc→BOM 3.1.1、pagehelper→4.1.1）

## 用户自测反馈

- BETA 首次部署构建成功但启动期崩溃（NoClassDefFoundError）→ 根因：Boot 3 时代 starter 自动配置引用 Boot 4 已移包的内部类 → 修复 commit [96136e9d](https://gitcode.com/openlibing/openlibing-cicd/commit/96136e9d36d47db0fe1224ddab4b6fa75f12fe0b)，1323 个单测复测全绿
- feign 配置块曾被评估为 ribbon 死配置删除，用户要求恢复（后续需求需追加内容）→ commit [a6b7cfcf](https://gitcode.com/openlibing/openlibing-cicd/commit/a6b7cfcfb9a08304d0a721ed04c6d3e50eeaecf9)

## 最终验证

- mvn compile：通过
- 全量单测：1323 个全绿（两轮：首版交付 + BETA 修复后复测，4 个既有跳过）
- 接口签名变动：无（Controller 层零改动，前端无需适配）
- Rabbit 消费重试语义：与升级前一致（总尝试 3 次、指数退避 1s/2s/封顶 5s、耗尽后 republish 60s 延迟队列）
- BETA 回归验证：清单已产出（P0 启动 / P1 redisson 链路 / P2 分页 / P3 事件 / P4 镜像构建 / P5 操作日志），待 BETA 重新部署后执行

## 设计偏差与取舍

- redisson 从 starter 改为 core：RedisConfig 已手动 `Redisson.create()` 装配 RedissonClient、spring-data-redis 走 Jedis 连接工厂，starter 自动配置纯多余且引用 Boot 3 内部类，弃用 starter 改用 core（BOM 仲裁 3.45.1）
- pagehelper 2.1.0 → 4.1.1：官方 Boot 4 线（基于 mybatis-spring-boot-starter 4.0.1），保留原有 mybatis 排除与 mybatis-plus 共存
- BETA 阶段修复属依赖兼容性补漏，未偏离 Phase 1 确认的升级方案

## 可复用经验

已同步至 [ai_memory.md](../../ai_memory.md)「Common 升级（Boot 3→4 / Jackson 2→3）」章节，核心三条：

- Boot 3 时代 starter（redisson / springdoc 2.x / pagehelper 2.x）自动配置引用 Boot 3 内部类，Boot 4 下启动崩溃且构建期不报错，需换 Boot 4 线版本
- `@WebMvcTest` 在 Boot 4 拆到 `spring-boot-starter-webmvc-test` 独立构件
- mybatis-plus 3.5.17 的 `in()` 构建期解析 Lambda 列名，纯 Mockito 单测需 `TableInfoHelper.initTableInfo`

## 归档日期

2026-10-16
