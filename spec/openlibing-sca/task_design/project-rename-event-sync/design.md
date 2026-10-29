# 消费 framework 项目重命名事件同步 community 数据 — 技术设计

## 方案概述

新增 RabbitMQ 消费者 `ProjectChangeListener`，监听 framework 投递的项目重命名事件（`PROJECT_RENAME`），在单事务内将 SCA 侧 7 张表的 community 维度数据从旧项目名更新为新项目名，随后失效相关 Redis 缓存，解决项目重命名后 SCA 数据与 framework 不一致的问题。

## 消费链路

```
framework（项目重命名事务提交后）
  → 默认交换机直投队列 project_change_event_sca_queue_<环境后缀>
    → ProjectChangeListener.receivedProjectChangeMessage(message, channel)
        → eventType != PROJECT_RENAME        → 记 warn 日志，basicAck 跳过
        → old/newProjectName 为空            → 记 ERROR，basicReject(false) 丢弃
        → old == new                          → 记 info 日志，basicAck 跳过
        → ProjectChangeEventService.applyProjectRename(old, new)   # 单事务更新 7 张表
        → evictProjectRenameCache(old, new)                        # 失效 community 缓存
        → basicAck
        → 任一步骤异常                        → 记 ERROR，basicReject(false) 丢弃
```

## 关键决策

1. **`queuesToDeclare` 自动声明队列**：`@Queue(durable = "true")` 声明参数（持久化、非 exclusive、非 autoDelete）与 framework 生产端保持一致，队列名走 `spring.rabbitmq.project-change.queue` 配置，环境间按后缀隔离（beta/gamma/prod）。
2. **毒消息 reject 丢弃而非重投**：非法消息（非 JSON、字段为空）与同步失败均 `basicReject(false)` 丢弃并记 ERROR，避免毒消息无限重投阻塞队列；失败场景依赖日志告警 + 人工按需重同步（同步逻辑幂等，可直接重放事件）。
3. **同步逻辑天然幂等**：更新条件为 `WHERE community(_name) = 旧项目名`，消息重放时旧项目名数据已不存在，更新 0 行无副作用，支撑"reject 丢弃 + 需要时重放"的容错策略。
4. **单事务保证一致性**：`applyProjectRename` 使用 `@Transactional(rollbackFor = Exception.class)`，7 张表任一更新失败全部回滚，避免出现部分表新名、部分表旧名的中间态。
5. **缓存清理放在事务提交后、失败不抛异常**：数据库重命名事务已提交后才清缓存；任一 key 删除失败仅记 ERROR，不抛异常——否则消息被 reject 丢弃后，缓存将与数据库长期不一致。清理范围：`CACHE_PERSON_SCAN_BY_COMMUNITY_PREFIX + 旧名/新名`（TTL 1 天）与 `CACHE_PERSON_COMMUNITY_LIST`（TTL 10 分钟）。
6. **缓存 key 常量化**：`ProjectConstant` 新增 `CACHE_PERSON_SCAN_BY_COMMUNITY_PREFIX`、`CACHE_PERSON_COMMUNITY_LIST`，`PRScanSchedule`、`OpenPersonScanServiceImpl` 与 listener 统一引用，消除三处魔法字符串漂移风险（key 漂移会导致缓存清理失效）。顺带修复 `PRScanSchedule` 的 LOGGER 声明类错误。
7. **SQL 移入 MyBatis mapper XML**：`ProjectChangeEventMapper` 接口 + `mapper/dm/ProjectChangeEventMapper.xml`，表名/列名固定、新旧项目名经 `#{}` 参数绑定，无注入风险。
8. **复用既有 `projectNoticeScanContainerFactory`**：沿用现有 RabbitListenerContainerFactory，不新增连接工厂配置。

## 数据同步范围

| 表                    | 列               | 说明         |
| --------------------- | ---------------- | ------------ |
| `tbl_export_data`     | `community`      | 导出数据     |
| `tbl_measure`         | `community`      | 度量数据     |
| `tbl_person_scan`     | `community`      | PR 扫描记录  |
| `tbl_repo`            | `community`      | 社区仓库     |
| `tbl_scan_result_log` | `community_name` | 扫描结果日志 |
| `tbl_scanoss_shield`  | `community_name` | 扫描屏蔽配置 |
| `tbl_shield_role`     | `community_name` | 屏蔽角色配置 |

## 配置项

| 配置键                                                           | 值                                     | 说明                                                 |
| ---------------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------- |
| `spring.rabbitmq.project-change.queue`（application-local/beta） | `project_change_event_sca_queue_beta`  | 本地与 beta 环境队列                                 |
| 同上（application-gama）                                         | `project_change_event_sca_queue_gamma` | gama 环境队列，与 framework 生产端 queue-suffix 一致 |
| 同上（application-prod）                                         | `project_change_event_sca_queue_prod`  | prod 环境队列                                        |

## 涉及文件

| 文件                                                 | 操作 | 说明                             |
| ---------------------------------------------------- | ---- | -------------------------------- |
| `common/config/rabbitmq/ProjectChangeListener.java`  | 新增 | 队列消费者 + 缓存清理            |
| `dm/service/ProjectChangeEventService.java`          | 新增 | 同步服务接口                     |
| `dm/service/impl/ProjectChangeEventServiceImpl.java` | 新增 | 单事务同步 7 张表                |
| `dm/dao/ProjectChangeEventMapper.java`（+XML）       | 新增 | 7 条 UPDATE 语句                 |
| `common/constants/ProjectConstant.java`              | 修改 | 新增 2 个缓存 key 常量           |
| `common/schedule/PRScanSchedule.java`                | 修改 | 改用常量引用；修复 LOGGER 类声明 |
| `OpenPersonScanServiceImpl.java`                     | 修改 | 改用常量引用                     |
| `application*.yaml`（local/beta/gama/prod）          | 修改 | 新增队列配置                     |
| `test/.../ProjectChangeListenerTest.java`            | 新增 | 6 个消费分支用例                 |
| `test/.../ProjectChangeEventServiceImplTest.java`    | 新增 | service 层用例                   |

## 风险与缓解

| 风险                                              | 缓解                                                                                                                       |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 消息消费失败被 reject 丢弃，数据不同步            | 同步逻辑幂等，可按 ERROR 日志中的 eventId/old/new 手工重放事件；关键路径有结构化日志（各表 updatedRows、totalUpdatedRows） |
| 队列声明参数与 framework 生产端不一致导致投递失败 | durable 非 exclusive 非 autoDelete，与生产端默认提交参数一致；环境队列名经配置对齐                                         |
| 缓存删除失败导致 TTL 内返回旧数据                 | 删除失败记 ERROR；扫描列表缓存 TTL 1 天、社区列表 TTL 10 分钟，最终一致                                                    |
| 重命名前消费方未部署/队列未声明                   | `queuesToDeclare` 消费端启动即声明队列，framework 投递不丢（队列先于消费存在）                                             |

## 跨仓影响

- 依赖 framework 侧：项目重命名事务提交后经默认交换机直投 `project_change_event_sca_queue_<环境后缀>`，消息体 JSON 字段（eventType/eventId/projectId/oldProjectName/newProjectName/publishedAt）由双方约定。
- SCA 侧仅消费，不改动 framework。
