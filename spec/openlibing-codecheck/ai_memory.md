# openlibing-codecheck — AI 记忆（可复用规则）

本文件沉淀经过验证且会复用的规则，供后续 AI 任务直接引用，避免重复踩坑。

## 横向鉴权（checkPermission）模式

- 接口补 `@RequestParam(value = "userId", required = true) String userId`（网关注入可信身份，客户端不可伪造）。
- `projectId <= 0` → 403「projectId is invalid」，防止 projectId=0 绕过权限校验。
- `!authUtils.checkPermission("/openlibing-codecheck" + 真实HTTP路径, projectId, userId)` → 403「no permission」；URL 约定 `/openlibing-codecheck` 前缀，`menu_url_info` 表精确匹配。
- MultiResponse 返回型 `.code(403).message(...)`；DataResult 返回型 `DataResult.build(403, msg, null)`。
- Controller 测试：`@Mock AuthUtils` + `@BeforeEach lenient().when(authUtils.checkPermission(anyString(), any(), anyString())).thenReturn(true)`；model 测试数据 `setProjectId(>0)`。
- 资源归属校验（撤销/审核）：操作人须为申请人（revision.userId）或审核人（reviewerId/reviewers.userId 命中），否则 403；空列表 50001。

## apigateway SDK（java-sdk-core）URL 行为

- `Request.setUrl()` 解析 query 后重建时**对已编码序列原样保留**（不把 `%26` 二次编码为 `%2526`），仅把 `+` 规范化为 `%20`。
- 结论：参数注入修复可在 URL 构建层对 key/value 直接 `URLEncoder.encode(value, UTF_8)`，合法值（含空格/特殊字符）语义不变，无双重编码回归（实测验证，勿凭记忆改回裸拼接）。
- 跨仓引用：`uses: owner/repo@ref`；GitCode 平台内置动作（checkout/setup-jdk/setup-go）无仓库路径，无法/无需 SHA 固定。

## Nacos / CSE

- `spring-cloud-alibaba`（2025.1.0.0）`NacosConfigProperties` **没有** `secure` 字段，`spring.cloud.nacos.config.secure` 无效；`secure` 仅存在于 `NacosDiscoveryProperties`（服务实例注册为 HTTPS，与配置拉取传输加密无关）。
- 客户端→Nacos 传输加密需 nacos-client TLS（`tls.enable` 系统属性 + 证书信任）+ 服务端开通 TLS，属部署级变更。

## GitCode CLI / Windows

- Issue `state_event` 仅接受 open/closed/reopen/close，**无法设置自定义状态**（如"修复中"）→ 告知用户在网页手动切换。
- 中文远端写操作必须 `--body-file` + `[System.IO.File]::WriteAllText(..., UTF8)` 写盘；PowerShell 5 不支持 `&&`。
- 跨仓 PR 必须 `--head fork-owner:branch`；PR 标签只追加不删（含 `ci` 的标签禁止修改、`needs-issue` 禁止删除）。
- 分支命名语义化（禁 batchX）；业务仓分支禁 `/`；docs 仓分支 `spec/<repo>/<change>`。

## 报告建议技术可行性核实

- 报告给出的属性/参数是否存在 → `javap` 反编译依赖 jar 验证（实例：NacosConfigProperties 无 secure 字段）。
- SDK/框架行为 → 写最小 Java 探针程序实测（实例：apigateway setUrl 不二次编码）。
- 外部平台能力（CSE Nacos TLS 等）无法在代码仓验证 → 标注部署级变更，不盲改，报告建议无效时向用户确认豁免并留痕。
