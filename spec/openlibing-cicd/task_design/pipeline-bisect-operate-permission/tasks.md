# pipeline-bisect-operate-permission: 实现步骤

## 前置核查

- [x] 确认 `AuthInterceptor` 组校验入口均以 `operate && pipelineId 非空` 为条件
- [x] 确认 `/bisect/create` 请求体 `PipelineParamDTO` 携带 `pipelineId`，可被拦截器解析
- [x] 确认 `/bisect/reset` 入参不含 `pipelineId`，服务层已有归属 + 成员校验，加 `operate` 为空操作
- [x] 核查 BETA 存量数据：已绑定权限组流水线 5 条、组成员 0；admin 缺 `100842`

## 编码

- [x] `bisectLocate` 注解改为 `@CheckPermission(operate = true)`
- [x] 补充 Javadoc 说明按操作类语义校验的原因（不写 issue 编号）
- [x] `/bisect/reset` 保持原注解不变

## 测试

- [x] `guard_BisectOperateFlag`：断言方法注解 `operate` 为 `true`
- [x] `preHandle_BisectCreateRealAnnotation_AnonymousBoundGroup_LoginRequired`：匿名 + 已绑定组 → 401
- [x] `preHandle_BisectCreateRealAnnotation_GroupMember_Granted`：组内成员 → 放行
- [x] `preHandle_BisectCreateRealAnnotation_GroupOutsider_DeniedByGroup`：组外用户 → 403 `4030001`
- [x] 本地执行 `AuthInterceptorTest` 通过
- [x] spotless / checkstyle / spotbugs / pmd 通过

## 配套运维

- [x] BETA 为 admin 补齐 `100842`（二分定位菜单权限），菜单数 490 → 493
- [ ] 检查其他环境是否需要同样补齐（按环境绑定关系现状决定）

## 交付

- [x] 业务分支 `fix-553-bisect-operate` 提交并推送
- [x] 业务 PR #690 创建并关联 Issue #553，打 `ai-assisted` 标签
- [x] PR 合入 master（merge commit `a31cefbb0`）

## 回归（页面，待人工执行）

- [ ] 有权限用户从「流水线详情 → PR问题定位 → 查看详情」触发二分定位，正常创建任务
- [ ] 组外用户在已绑定权限组的流水线上触发二分定位，被 403 拦截且提示可读
- [ ] 未绑定权限组的流水线，二分定位行为与改造前一致
