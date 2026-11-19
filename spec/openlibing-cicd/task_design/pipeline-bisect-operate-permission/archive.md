# bisect/create 补充 operate 权限校验（#553）— 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/553 （安全问题，已关闭）
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pulls/690
- 分支: `fix-553-bisect-operate` → `master`
- 合并: merge commit `a31cefbb0`，合并时间 2026-11-19
- 本 PR 标签: `ai-assisted` / `approved` / `lgtm`

## 交付历程

- commit `0c13ada3c`: fix(auth) — `bisectLocate` 注解改为 `@CheckPermission(operate = true)`，补 Javadoc；`AuthInterceptorTest` 新增 4 条用例（注解守卫 + 匿名 401 / 组内放行 / 组外 403）

## 关键判定

- `AuthInterceptor` 的权限组校验入口全部以 `operate && StringUtils.hasText(pipelineId)` 为前提；`/bisect/create` 请求体 `PipelineParamDTO` 带 `pipelineId`，可被从 body 解析，因此加 `operate = true` 真实生效
- `/bisect/reset` 入参只有 `projectId` / `userId` / `id`，无 `pipelineId`，组校验分支恒不触发；且 `resetBisect` 已有 `requireOwnershipOrThrow` + `requireProjectMemberOrThrow`，故不跟随改动
- `/bisect/create` 服务层无归属/成员校验，此前仅要求登录；本改动把"已绑定权限组"的流水线纳入组管控

## 检视闭环

- 检视建议"`/bisect/reset` 也应加 `operate = true`"：技术上为空操作（无 pipelineId 不进入组校验），且服务层已有归属 + 成员校验，"任意已登录用户可重置他人任务"不成立，**选 A 不改**，已按证据回复并标记 resolved

## 配套运维与数据核查（BETA）

- 已绑定权限组的流水线 5 条，组成员为 0 → 组校验在 BETA 暂无实际拦截样本，需运维补齐组成员
- admin 角色缺 `100842`（二分定位菜单权限），开启 operate 后会误 403 → 已补齐，菜单数 490 → 493，覆盖 336 用户
- 代码侧不做默认放行兜底

## 设计偏差与取舍

- 未在服务层新增归属校验：该端点需要的是"操作类权限组管控"，在服务层重复实现拦截器逻辑会与拦截器口径漂移
- 未在拦截器内为 admin 做特判：权限问题通过配置修正，不在代码里开白名单

## 可复用经验

- 给接口加 `operate = true` 前必须先确认请求链路中 `pipelineId` 可被 `AuthInterceptor` 解析（路径变量 / body / 列表参数），否则注解加了个寂寞
- 权限类整改要同时核查"代码 + 配置"两侧：代码收紧后，管理角色的菜单权限缺失会立刻表现为误 403

## 回归状态

页面回归（流水线详情 → PR问题定位 → 查看详情）已在 Issue #553 评论区给出步骤，待人工执行。

## 归档日期

2026-11-19
