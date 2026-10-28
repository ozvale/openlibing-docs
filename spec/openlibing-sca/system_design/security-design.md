# 安全设计：notice-scan-status-multifilter

> 本需求为只读状态聚合查询，安全面较窄；以下按 8 维度逐项给出结论，"不适用"处均附原因。

## 1. 认证授权

- 方案：不新增。与 `ProjectNoticeScanController` 既有接口（/start /export /supplement /info）一致，认证由网关统一承担；本接口与兄弟接口同等信任级别，不引入新的鉴权绕过点。
- 凭证生命周期：不涉及（无新凭证）。
- 越权防护：状态数据按制品维度无属主模型，与既有 /info 一致；不新增横向越权面。

## 2. 输入输出

- 边界校验：`productType` 在 Service 前置非空校验（镜像 SBOM 契约，避免无效跨服务调用）；`filters`/`sortField`/`sortDir`/`pageNum`/`pageSize` 仅透传，SCA 侧不做语义解释。
- 注入面：制品名仅用于 MySQL 参数化查询（`#{}` + `<foreach>`）；filters 透传 SBOM，其服务层有 key 白名单，SCA 不拼接任何 SQL/URL。
- 输出：VO 仅 `productName`/`status`/`statusName`，最小化；不含 OBS 内部地址、errorMsg、堆栈。

## 3. 数据保护

- 分类分级：扫描状态为"内部"级，无个人敏感数据，无需加密。
- 传输/存储加密：沿用既有链路（内网 HTTP + 既有 MySQL 连接配置），本需求不变更。
- 脱敏：Feign 失败统一转 `ScaException("调用SBOM服务获取制品名称失败")`，不透出内网地址与响应原文。

## 4. 依赖供应链

- 无新增第三方依赖（复用既有 Feign / MyBatis / fastjson2）。

## 5. 部署运行时

- 配置：复用既有 `${sca.to.sbom.url}`，无新增配置项。
- 部署对齐风险：SBOM `/internal-api/queryProductNamesByMultiFilter` 需与 SCA 新版本同期可用，联调阶段验证（记录于 design.md 风险节）。
- 审计日志：沿用既有 info 级入参日志模式（与兄弟接口一致）；只读非敏感操作，不新增专项审计。

## 6. 失败模式

- Fail Secure：SBOM 不可用/超时 → 业务失败提示，不降级为无过滤查询，不返回缓存脏数据。
- 应急：接口为纯只读，异常无状态残留；SBOM 恢复即恢复。

## 7. 验证计划

- 单元测试：productType 缺失拒绝、SBOM 失败转业务异常、未扫描制品 status=null（5 场景见 tasks.md Task 7）。
- 事后审查：交由 `gitcode-security-check`（用户要求时触发）验证实现与本文档一致性，重点核对 SQL 参数化与 VO 最小化。
