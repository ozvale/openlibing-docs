# pipeline-bisect-operate-permission: bisect/create 补充 operate 权限校验

## 需求背景

`POST /project/pipeline/bisect/create`（触发二分定位）只标注了 `@CheckPermission`，未设置 `operate = true`。而 `AuthInterceptor` 对"已登录用户 + 非操作类端点"不进入流水线绑定权限组校验，直接走存量的登录即可访问判定，导致这条**会真实触发候选提交流水线运行**的写操作不受权限组管控。

同一控制器内的 `/run`、`/stop`、`/retry` 等操作类端点均已标注 `operate = true`，本接口属遗漏。

- 关联 Issue：https://gitcode.com/openlibing/openlibing-cicd/issues/553
- 关联 PR：https://gitcode.com/openlibing/openlibing-cicd/pulls/690

## 功能描述

- `PipelineControllerV2#bisectLocate` 的 `@CheckPermission` 改为 `@CheckPermission(operate = true)`
- 补充 Javadoc 说明该端点为何按操作类语义校验
- 不改动同一控制器内的 `/bisect/reset`

## 验收标准

- [x] `/bisect/create` 注解为 `@CheckPermission(operate = true)`，与 `/run`、`/stop` 语义一致
- [x] `/bisect/reset` 保持 `@CheckPermission`（无 pipelineId 入参，组校验路径不会触发）
- [x] 单测断言 `bisectLocate` 方法上的 `operate` 为 `true`，防止后续回退
- [x] 单测覆盖真实注解驱动的三条路径：匿名访问已绑定权限组流水线 → 401 要求登录；组内成员 → 放行；组外用户 → 403
- [x] 接口路径、入参、出参、业务逻辑无变化
- [x] 相关单测与静态检查通过

## 影响范围

| 文件                                                                              | 操作 | 说明                                               |
| --------------------------------------------------------------------------------- | ---- | -------------------------------------------------- |
| `src/main/java/com/openlibing/cicd/business/controller/PipelineControllerV2.java` | 修改 | `bisectLocate` 注解补 `operate = true`，补 Javadoc |
| `src/test/java/com/openlibing/cicd/common/auth/AuthInterceptorTest.java`          | 修改 | 新增注解守卫断言 + 三条真实注解驱动用例            |

无 HTTP 契约变化、无数据模型变化、无配置项新增、无 pom 变更。

## 配套运维动作

代码生效的前提是"流水线已绑定权限组且组内有成员"。BETA 环境核查发现：已绑定权限组的流水线共 5 条，但组成员为 0；同时 admin 缺少 `100842`（二分定位菜单权限），会在开启 operate 校验后被 403。已在 BETA 为 admin 补齐 `100842`（菜单数 490 → 493，覆盖 336 用户），代码侧不做兼容绕过。
