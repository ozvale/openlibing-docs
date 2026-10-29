# security-token-header-migration: 访问令牌从 URL 查询参数迁移到 PRIVATE-TOKEN 请求头

## 需求背景

`openlibing-cicd` 调用 GitCode/Gitee 接口时，将用户访问令牌以 `access_token` 查询参数形式拼接在 URL 上，属于 CWE-598（敏感信息通过 GET 查询串传递）。

查询参数会完整落到以下渠道，任何可读取其中任一渠道的主体都能直接获得可用的访问令牌：

- 服务端访问日志、网关与代理日志
- `Referer` 请求头、浏览器历史
- 异常堆栈、链路追踪中打印的完整 URL
- 下游 WAF、CDN 等中间设备的日志

对应安全扫描问题 openlibing-cicd#335，openlibing-cicd#361 为同一问题的重复上报。

## 功能描述

- `BranchServiceImpl#getRepoBranch` 改为通过 `PRIVATE-TOKEN` 请求头传令牌，URL 与表单参数不再带 `access_token`。
- `PipelineServiceImpl#queryPrTitle` 同样改为请求头传令牌，HTTP 超时与失败返回语义保持不变。
- `RepoServiceImpl` 的 `getRepoWebhookList`、`createRepoWebhook`、`deleteRepoWebhook` 改为构造 headerMap 携带 `PRIVATE-TOKEN` 后调用 `HttpRequestUtil.sendRequest`。
- `createRepoWebhook` 的**请求体**中 `access_token` 按 GitCode 注册 webhook 接口要求保留（不在 URL 上，不构成查询串泄露）；该字段属 form/urlencoded body 渠道，本次未做脱敏，为已知残留风险。
- 补充单元测试，断言令牌只出现在请求头、不出现在 URL 与表单参数中。
- 收敛 hutool `HttpResponse` 的资源释放方式为 try-with-resources。

## 验收标准

- [x] 本次覆盖的 5 处调用链中，令牌不再以 `access_token` 查询参数形式出现在 URL 上
- [x] `getRepoBranch` 请求头包含 `PRIVATE-TOKEN` 且值等于传入令牌，表单参数不含 `access_token`，分页等原有表单参数保持不变
- [x] `queryPrTitle` 的请求 URL 形如 `https://api.gitcode.com/api/v5/repos/openlibing/openlibing-cicd/pulls/123`，不含 `access_token`
- [x] `queryPrTitle` 仍使用 `PR_TITLE_HTTP_TIMEOUT_MS = 1500` 设置超时，超时常量未变
- [x] webhook 三个方法的 HTTP 请求均带 `PRIVATE-TOKEN` 头，URL 不含 `access_token`
- [x] 调用前仍执行 `SafeRequestUtils.isSafeProtocol(url)` 协议校验
- [x] `PipelineServiceImplTest` 全量 225 个用例通过（原 223 + 新增 2）
- [x] pre-commit 12 个钩子全部通过
- [x] 无新增配置项、无 pom 变更、无对外 HTTP 接口出入参变化
- [ ] beta 环境真实接口回归未执行：GitCode 分支查询/PR 标题、Gitee webhook 增删查需实测服务端接受 `PRIVATE-TOKEN` 头；当前仅有请求构造层单测（ArgumentCaptor 断言头部），不能证明服务端鉴权通过

## 影响范围

| 文件                                                                                   | 操作 | 说明                                                                                                                                                                      |
| -------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/cicd/business/service/impl/BranchServiceImpl.java`       | 修改 | `getRepoBranch` 由 `HttpUtil.get(url, params)` 改为 `HttpRequest.get(url).form(params).header("PRIVATE-TOKEN", accessToken)`，删除 `params.put("access_token", ...)`      |
| `src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java`     | 修改 | 私有方法 `queryPrTitle`（约 4355-4402 行）改为请求头传令牌；URL 拼接去掉 access_token；`PR_TITLE_HTTP_TIMEOUT_MS`（第 338 行）保持不变                                    |
| `src/main/java/com/openlibing/cicd/business/service/impl/RepoServiceImpl.java`         | 修改 | `getRepoWebhookList` / `createRepoWebhook` / `deleteRepoWebhook` 三处（`HttpRequestUtil.sendRequest` 调用点 416/463/511/568 行区域）URL 移除 access_token，改传 headerMap |
| `src/test/java/com/openlibing/cicd/business/service/impl/BranchServiceImplTest.java`   | 修改 | 新增 `getRepoBranch_TokenInHeaderNotInQuery`                                                                                                                              |
| `src/test/java/com/openlibing/cicd/business/service/impl/RepoServiceImplTest.java`     | 修改 | 新增 `testGetRepoWebhookList_TokenInHeaderNotInUrl`，create/delete 成功用例补 ArgumentCaptor 断言，其余用例第 4 个 header 参数由 `eq(null)` 放宽为 `any()`                |
| `src/test/java/com/openlibing/cicd/business/service/impl/PipelineServiceImplTest.java` | 修改 | 新增 `queryPrTitle_TokenInHeaderNotInUrl` 与 `queryPrTitle_RequestThrows_ReturnsNull`                                                                                     |

明确未覆盖：

- `PipelineServiceImpl` 第 7061/7091 行附近 PR 管理模块的 `access_token=` 拼接，不在本次范围。
- `createRepoWebhook` 请求体中的 `access_token` 字段按第三方接口要求保留。
- 请求体（form/urlencoded）渠道的令牌脱敏不在本次范围：本次只消除查询串渠道，与 #242 记录的消息体渠道问题同源，需后续单独处置。

## 关联 Issue

- openlibing-cicd#335 — https://gitcode.com/openlibing/openlibing-cicd/issues/335
- openlibing-cicd#361 — https://gitcode.com/openlibing/openlibing-cicd/issues/361（与 #335 为重复上报）

## 关联 PR 与提交

- PR：!634 — 《【安全】出站调用 access_token 拼接 URL 查询串整改（webhook/分支/PR标题 5 处）》，状态已合入（2026-10-29 18:11）
- 分支：`fix/security-vuln-335-361-token-header`，base `release_20261029_iter2`
- 提交：
  - `b75129d8d` `fix(cicd): pass access_token via PRIVATE-TOKEN header instead of URL query`（生产改动）
  - `acaa12f08` `refactor(cicd): close hutool HttpResponse via try-with-resources`
  - `b0082eb31` `test(cicd): assert PRIVATE-TOKEN header contract in webhook and branch tests`
  - `0b76e129c` `test(pipeline): add queryPrTitle regression tests for token header`
