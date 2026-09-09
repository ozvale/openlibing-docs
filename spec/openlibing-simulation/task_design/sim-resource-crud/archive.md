# 仿真资源增删改管理接口（sim-resource-crud）— 归档

## 归档信息

| 项目        | 内容                                        |
| ----------- | ------------------------------------------- |
| FE 需求名称 | 仿真机器/引擎/qcow/附件资源增删改管理接口   |
| 业务 Issue  | openlibing/openlibing-simulation#27         |
| 业务 PR     | openlibing/openlibing-simulation#155        |
| 开发分支    | feat/sim-resource-crud（已合入，可删除）    |
| 归档日期    | 2026-09-08                                  |

## 关联（permalink）

- 业务 Issue: <https://gitcode.com/openlibing/openlibing-simulation/issues/27>
- 业务 PR: <https://gitcode.com/openlibing/openlibing-simulation/merge_requests/155>
- 业务合入 merge commit: <https://gitcode.com/openlibing/openlibing-simulation/commit/7d9123d>

## 交付历程

- commit [`8695b8f`](https://gitcode.com/openlibing/openlibing-simulation/commit/8695b8f): 提供 server(basic/extend)/engine/qcow/attachment 四类资源管理 Controller/Service/Mapper/XML + 4 个 Service 单测
- commit [`02d6e9b`](https://gitcode.com/openlibing/openlibing-simulation/commit/02d6e9b): 删除端点由 DELETE 改为 POST（管理端点统一 POST 约定）
- commit [`cb72bc6`](https://gitcode.com/openlibing/openlibing-simulation/commit/cb72bc6): openlibing-common 升级 1.0.20.4 → 1.0.20.6
- docs: proposal.md/tasks.md（[`1fe34bcd`](https://gitcode.com/openlibing/openlibing-docs/commit/1fe34bcd) 对齐 Issue #27、[`4fa65932`](https://gitcode.com/openlibing/openlibing-docs/commit/4fa65932) 对齐 POST-only 约定）

## 用户自测反馈

- 范围变更（编码期）：t_server_using 不需要增删改 → 从接口与 Mapper 中移除 using 相关 CUD；删除接口统一为 POST
- 空 SET 报错：update 请求只传 `id` 时，动态 `<set>` 生成空内容 → 非法 SQL `UPDATE ... WHERE id = ?`，被 MyBatis-Plus BlockAttack(jsqlparser) 拦截抛 MybatisPlusException → **用户决策不改代码**，约定测试/调用方至少携带一个可更新字段

## 最终验证

- CI 流水线通过（ci-pipeline-passed / approved / lgtm）
- 业务 PR #155 已合入 master
- IDE 静态诊断 0 error；新增单测 4 类（ServerResource / EngineResource / QcowResource / AttachmentResource）
- 说明：本地沙箱无法访问私有 Maven 仓库，`mvn test` 未在本地执行，依赖 CI 门禁

## 设计偏差与取舍

- 6 张候选表中 t_server_using 不开放管理增删改（沿用既有分配/释放流程，避免绕过业务约束）
- HTTP 方法约定：add/update/delete 全部使用 POST（与库内既有管理端点一致，规避内部鉴权过滤对标准方法/查询参数的额外约束）
- 删除策略：server_basic_info/server_using 逻辑删（业务无软删字段约束前保留记录），engine/qcow/server_extend/attachment 物理删
- creator 一律取自 `X-Openlibing-User` 请求头，不信任请求体

## 可复用经验

- 动态 `UPDATE` 用 `<set>+<if>` 时，若所有可更新字段为空会生成无 SET 子句的非法 SQL，并被 MyBatis-Plus BlockAttackInnerInterceptor(jsqlparser) 解析拦截报 `MybatisPlusException: Failed to process`；Service 层更新接口应校验"至少一个可更新字段非空"
- 实体 primitive boolean/double 字段不能写 `<if test="xxx != null">`（永远不会为 null），会导致该列被跳过/语义错误，应无条件赋值
- gitcode `pr view` 的 Commits/Files 计数存在平台展示延迟（显示 0），实际 diff 以 `gitcode pr diff <n>` 或合入后 commit 为准
- openlibing-common 升级 1.0.20.6 后 enforcer/构建可通过，新代码依赖该版本

## 关联文档

- 需求分析: `proposal.md`
- 实现核对: `tasks.md`
