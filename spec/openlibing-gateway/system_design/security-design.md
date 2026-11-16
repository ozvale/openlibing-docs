# 安全设计：gateway 灰度染色（gray-release）

配套威胁模型：[threat-model.md](./threat-model.md)

## 1. 认证授权

- 本需求不新增认证授权面。染色判定复用 AuthFilter（order=2）已校验的 `userId` 查询参数；未认证路径（豁免/机机接口）无 userId，仅按比例判定，不构成提权路径。
- 灰度白名单只决定"路由到哪个版本的实例"，不绕过任何下游接口的鉴权。

## 2. 输入输出

- **入站 header 不可信**：`X-Release-Track` 一律覆盖（先移除后注入），杜绝客户端伪造 `gray` 自选灰度实例或伪造 `stable` 逃逸灰度。
- **nacos 配置视为受控输入**：`gray.ratio` 越界钳位到 [0,100]；`gray.whitelist.userIds` 按逗号 split、trim、去空；解析失败回退空集合（fail-safe）。
- 输出：仅注入 header 与 debug 日志，不向响应写任何内容。

## 3. 数据保护

- 用户 ID 属敏感 PII：仅内存比对，不持久化；日志脱敏（前 4 位 + `***`），仅在 debug 级输出。
- 不记录请求体/响应体。

## 4. 依赖供应链

- 零新增依赖：spring-cloud-loadbalancer、spring-cloud-context（refresh）均由既有 openlibing-common / spring-cloud-gateway 传递依赖提供。

## 5. 部署运行时

- 配置管理：灰度配置存 nacos `gateway` dataId（group=OPENLIBING），@RefreshScope 动态生效；配置变更由 CSE 审计留痕。
- 回滚：`gray.enabled=false` 一键回滚，无需重新发布。
- 审计日志（最小集合）：灰度判定为 debug 日志，不进入审计流（灰度路由不是安全敏感操作）；nacos 配置变更审计由 CSE 承担。
- 可观测：染色命中情况 debug 可查；异常兜底路径 warn 日志。

## 6. 失败模式

- Fail Secure：GrayReleaseFilter 内任何异常 → 按 `stable` 放行（绝不因灰度逻辑阻断请求）。
- LoadBalancer：请求 header 缺失 → 默认 stable；无匹配版本实例 → 回退全部实例（可用性优先，避免灰度未部署时 503）。
- 应急响应：灰度异常由运维在 nacos 关闭开关，秒级生效。

## 7. 验证计划

- 单元测试覆盖：header 覆盖（防伪造）、ratio 钳位、白名单命中/未命中、开关关闭、无匹配实例回退、异常兜底 stable。
- 事后审查：由 `gitcode-security-check` 验证实现与本文档约束一致（用户按需触发）。
