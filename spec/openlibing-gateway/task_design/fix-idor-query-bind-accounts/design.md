# fix-idor-query-bind-accounts — 技术设计

## 方案概述

复用同控制器 5 个 bind 端点的既有修复模式：从 `token` cookie 解析 JWT 的 `FIELD_USER_ID` claim，与请求参数 userId 精准比对，不一致即拒绝。接口签名增加 `ServerHttpRequest request` 参数，路径与原有请求参数不变，前端无感。

## 架构决策

- **选择"参数与 token 比对"而非"忽略参数直接用 token userId"**：保持接口契约完全兼容（前端已按现有契约传参），同时落报告要求的 owner 校验；与 bind 端点"token 解析"模式同源，风格一致。
- **拒绝方式返回 `DataResult.paramError`**：本端点为同步 `DataResult` 返回（非 bind 端点的 `Mono<ResponseEntity>`），对齐 UserController 查询类端点（queryAccountBindEmailInfo）的 `DataResult.paramError("token error")` 处理惯例。
- **不重复做 JWT 验签**：该路径受 AuthFilter 保护，token 有效性已由过滤器链保证，controller 仅提取 claim 做归属比对，与既有 bind 端点实现一致。
- **saveThreePartUserInfo 直接取消 accountId/accountPlatform 入参，信任 AuthFilter 注入**：该端点处于登录中间态（token 无 userId，无认证白名单属设计使然），accountId/accountPlatform 本就由 AuthFilter 从 token claims 注入且会覆盖客户端同名传值（`getNewRequestParams` 用 `params.put` 替换，中间态分支 L217 同样经过 `getNewServerWebExchange`），故 Controller 不再声明这两个 @RequestParam，直接读取 `request.getQueryParams()` 中 token 注入的值，客户端传值彻底失效；不使用 AuthUtil.getThreePartyUser（其内部解密 access token 等 claims，对中间态 claims 缺失不健壮且超出本端点所需）。

## 涉及文件

| 文件                                                                              | 操作 | 说明                                                                                                                                      |
| --------------------------------------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| src/main/java/com/openlibing/gateway/business/controller/LoginController.java     | 修改 | queryAlreadyBoundAccounts 增加 ServerHttpRequest 参数 + token userId 比对                                                                 |
| src/main/java/com/openlibing/gateway/business/controller/UserController.java      | 修改 | saveThreePartUserInfo 取消 accountId/accountPlatform 入参、setCheckPlatform 取消 userId 入参，均改读 AuthFilter token 注入的 query params |
| src/test/java/com/openlibing/gateway/business/controller/LoginControllerTest.java | 修改 | 既有用例适配新签名；新增越权场景用例                                                                                                      |
| src/test/java/com/openlibing/gateway/business/controller/UserControllerTest.java  | 修改 | 既有用例适配新签名；新增越权场景用例                                                                                                      |

## 风险 & 缓解

- 风险：前端若未传 userId 或传了非本人 userId（历史脏调用方）将开始被拒。缓解：AuthFilter 之后正常登录会话的 userId 与 token 必然一致，该行为变化正是漏洞修复目标；既有单测与新单测共同锁定行为。
- 风险：token cookie 名与 claim 提取异常导致正常请求被误拒。缓解：完全复用 bind 端点已验证的解析代码路径（`jwtUtils.getClaimByName(token, FIELD_USER_ID).asString()`），并补单测覆盖成功路径。

## 跨仓影响

无。
