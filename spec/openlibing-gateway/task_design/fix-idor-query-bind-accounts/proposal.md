# fix-idor-query-bind-accounts

## 需求背景

漏洞报告 openlibinggateway-20261103105553-001（H-0002，高危，IDOR/CWE-639）：`GET /platform/query/already/bind/accounts`（LoginController.queryAlreadyBoundAccounts）将请求参数 userId 直接透传给 Service，全程无"请求参数 userId 与认证 token 中 FIELD_USER_ID 是否一致"的所有者校验。任意已登录用户可传入任意 userId，读取该用户在 gitee/gitcode/github/openubmc/uniportal 5 个三方平台的账号绑定关系（accountId、accountLogin、accountName 等 PII），导致全站用户三方账号关联信息泄露。

同控制器 5 个 bind 端点（uniportal/openubmc/gitee/gitcode/github BindAuthoriz）与 UserController.queryAccountBindEmailInfo 均已按"userId 从 token 解析，防止越权"模式修复，本端点属该次修复边界内的遗漏残留缺口。

## 功能描述

- 做什么：
  1. LoginController.queryAlreadyBoundAccounts：从 token cookie 解析当前登录用户 userId，并与请求参数 userId 做一致性比对；不一致或 token 缺失/无法解析时拒绝请求。接口路径、参数契约保持不变，前端无感。
  2. UserController.saveThreePartUserInfo（横向排查补充项）：该端点处于隐私协议签署前的登录中间态（token 无 userId，配置在无认证白名单内属设计使然）， accountId/accountPlatform 本就由 AuthFilter 从 token claims 注入并覆盖客户端传值，故直接取消这两个请求参数、改读注入值，防止已知他人 accountId 时替他人触发信息落库或探测签署状态。
  3. UserController.setCheckPlatform（漏洞报告 1103-004 / M-0003，横向排查确认的高危同型 IDOR）：userId 本就由 AuthFilter 从 token claims 注入并覆盖客户端传值，直接取消该请求参数、改读注入值，防止越权篡改他人门禁检测平台设置。
- 不做什么：不修改 Service 业务逻辑（userId 锁定后 accountId 仅用于从本人绑定列表中筛选当前账号；saveThreePartUserInfo 落库数据来自服务端 Redis，不可伪造）。

## 验收标准

- [ ] 携带本人有效 token 且 userId 参数与 token 一致 → 正常返回本人绑定账号列表（行为不变）
- [ ] userId 参数与他人 userId 不一致 → 拒绝，不返回任何他人绑定数据
- [ ] 无 token cookie / token 中无 userId claim → 拒绝
- [ ] 单元测试覆盖上述三个场景，全部通过
- [ ] 既有 queryAlreadyBoundAccounts_success 测试适配新签名后通过

## 影响范围

- 业务仓 openlibing-gateway：LoginController.java（单端点）、LoginControllerTest.java（适配 + 新增用例）
- 无接口契约变化、无数据模型变化、无跨仓影响
