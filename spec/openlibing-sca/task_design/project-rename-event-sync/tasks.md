# 消费 framework 项目重命名事件同步 community 数据 — 实现任务

## 进度: 5/5 complete

- [x] 新增 `ProjectChangeListener`：监听 `spring.rabbitmq.project-change.queue`，校验 `eventType=PROJECT_RENAME` 与新旧项目名，按分支 ack/reject（含毒消息丢弃策略）
- [x] 新增 `ProjectChangeEventService`/`Impl`/`ProjectChangeEventMapper`（+XML）：单事务同步 7 张表（4 张 `community` 列 + 3 张 `community_name` 列），幂等 UPDATE
- [x] 事务提交后失效 community 缓存（扫描列表缓存新旧 key + 全量社区仓库列表缓存）；缓存 key 提取为 `ProjectConstant` 常量，`PRScanSchedule`/`OpenPersonScanServiceImpl` 改用常量引用并修复 LOGGER 类声明
- [x] `application*.yaml` 新增 `spring.rabbitmq.project-change.queue`（local/beta=`_beta`，gama=`_gamma`，prod=`_prod`）
- [x] 补充 `ProjectChangeListenerTest`（6 用例）、`ProjectChangeEventServiceImplTest`；PR #351（`ms_project` → `release_20261029`）CI 通过（`ci-pipeline-passed`）、lgtm/approved 后已合入

## 后续（可选）

- [ ] beta 环境实测：framework 侧执行项目重命名，确认 SCA 侧 7 张表同步、缓存失效、接口返回新项目名数据
- [ ] 评估消费失败告警：对 reject 丢弃路径的 ERROR 日志接入告警，避免同步缺失只能靠人工发现

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/351
- 分支: `ms_project` → `release_20261029`（已合入）
