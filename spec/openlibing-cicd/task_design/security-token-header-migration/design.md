# security-token-header-migration — 技术设计

## 1. 方案设计

**漏洞类型**：CWE-598，访问令牌作为 URL 查询参数传递。

**Sink（3 个类、5 处调用链）**：

- `BranchServiceImpl#getRepoBranch`：`HttpUtil.get(url, params)`，令牌由 `params.put("access_token", ...)` 进入查询串。
- `PipelineServiceImpl#queryPrTitle`（约 4355-4402 行）：`HttpUtil.get(url, params, timeout)`，URL 由 `urlPrefix + owner + "/" + repo + "/pulls/" + mergeId` 拼成并附带 access_token。
- `RepoServiceImpl#getRepoWebhookList` / `#createRepoWebhook` / `#deleteRepoWebhook`：`HttpRequestUtil.sendRequest` 调用点（416/463/511/568 行区域），令牌拼在 URL 上。

**Source**：访问令牌由业务侧持有。以 `PipelineServiceImpl` 为例，令牌链路为 `resolveAccessToken`（4404-4415 行，带 tokenCache）→ `decryptAccessToken`（1206-1213 行，`SecurityUtil.decrypt(token, part1)`，解密异常时回退原文）。

**攻击链**：

```
业务触发（分支查询 / PR 标题查询 / webhook 管理）
  → 拼装 URL：...&access_token=<明文令牌>
  → hutool 发起 HTTP GET
  → URL 写入访问日志 / 代理日志 / Referer / 异常堆栈 / 浏览器历史
  → 日志或链路数据的读取者获得可用令牌，可直接调用 GitCode/Gitee 接口
```

**修复策略**：等价加固，把令牌从查询串迁移到 `PRIVATE-TOKEN` 请求头，URL 与表单参数保持原有业务含义，超时、协议校验、异常处理语义全部保持不变。

**兼容性依据**：仓内已有同类先例，`GiteeIssueClient`、`RepoServiceImpl#getGiteeOrgMembers` 均以 `PRIVATE-TOKEN` 头访问 Gitee 接口，本次沿用同一约定。

**已知取舍**：

- `createRepoWebhook` 请求体保留 `access_token`：GitCode 注册 webhook 接口要求该字段，且请求体不进入访问日志 / Referer，不构成查询串泄露。
- `PipelineServiceImpl` 第 7061/7091 行附近 PR 管理模块的 `access_token=` 拼接不在本次范围，后续单独整改。

## 2. 实现逻辑设计

### 2.1 BranchServiceImpl#getRepoBranch

改前：

```java
params.put("access_token", accessToken);
HttpResponse response = HttpUtil.get(url, params);
```

改后：

```java
HttpResponse response = HttpRequest.get(url)
        .form(params)
        .header("PRIVATE-TOKEN", accessToken)
        .execute();
```

- 删除 `params.put("access_token", ...)`。
- 分页等原有表单参数继续通过 `.form(params)` 传递，参数集合内容除 access_token 外不变。

### 2.2 PipelineServiceImpl#queryPrTitle（约 4355-4402 行）

改前：`HttpUtil.get(url, params, timeout)`，URL 中带 access_token。

改后：

```java
HttpRequest request = HttpRequest.get(url)
        .header("PRIVATE-TOKEN", accessToken)
        .timeout(PR_TITLE_HTTP_TIMEOUT_MS);
```

- URL 拼接改为 `urlPrefix + owner + "/" + repo + "/pulls/" + mergeId`，不再附带查询参数。
- HTTP 超时常量 `PR_TITLE_HTTP_TIMEOUT_MS = 1500`（第 338 行）保持不变。
- 令牌来源链路未改动：`resolveAccessToken`（4404-4415 行，带 tokenCache）→ `decryptAccessToken`（1206-1213 行）。
- 调用前仍执行 `SafeRequestUtils.isSafeProtocol(url)` 校验。
- 异常处理保持原状：`catch (Exception)` 后 `return null`（4398-4401 行），即查询失败只表现为"PR 标题为空"，不向上抛出。

### 2.3 RepoServiceImpl 的 webhook 三处

改前：URL 中拼接 access_token 后调用 `HttpRequestUtil.sendRequest(...)`。

改后：URL 移除 access_token，构造 `Map<String, String> headerMap`，放入 `PRIVATE-TOKEN`，随请求传入。

- 影响方法：`getRepoWebhookList`、`createRepoWebhook`、`deleteRepoWebhook`。
- `createRepoWebhook` 的请求体字段不变，仍包含接口要求的 `access_token`。
- `HttpRequestUtil.sendRequest` 的调用签名未改动，仅第 4 个 header 参数由 `null` 变为携带令牌的 headerMap。

### 2.4 HttpResponse 资源释放

hutool `HttpResponse` 改为 try-with-resources 关闭（`acaa12f08`），与令牌迁移无功能耦合，属同批次的资源泄漏收敛。

## 3. 类设计

无新增类，无对外方法签名变化。

| 类                    | 方法                                                             | 变化                                                                                                             |
| --------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `BranchServiceImpl`   | `getRepoBranch`                                                  | 签名不变；内部由 `HttpUtil.get` 改为 `HttpRequest` 链式构造 + `PRIVATE-TOKEN` 头                                 |
| `PipelineServiceImpl` | `queryPrTitle`（private）                                        | 签名不变；内部改为 `HttpRequest.get(...).header(...).timeout(PR_TITLE_HTTP_TIMEOUT_MS)`；URL 不再带 access_token |
| `PipelineServiceImpl` | `resolveAccessToken` / `decryptAccessToken`                      | 未改动，继续为 `queryPrTitle` 提供令牌                                                                           |
| `RepoServiceImpl`     | `getRepoWebhookList` / `createRepoWebhook` / `deleteRepoWebhook` | 签名不变；内部新增 `Map<String, String> headerMap` 携带 `PRIVATE-TOKEN`                                          |
| `HttpRequestUtil`     | `sendRequest`                                                    | 未改动签名，第 4 个参数（headerMap）由调用方填充                                                                 |

## 4. 数据模型设计

无变更。本次不涉及库表结构、实体字段、缓存键或序列化格式。

## 5. 性能设计

- 无新增网络请求，请求次数与原来一致。
- `queryPrTitle` 超时仍为 `PR_TITLE_HTTP_TIMEOUT_MS = 1500` ms，未放宽或收紧。
- `tokenCache` 与解密逻辑未改动，令牌获取开销不变。
- 请求头相较查询参数无额外开销，URL 变短不影响分页等批量调用。

## 6. API接口设计

无变更。本次只改变服务端调用第三方（GitCode/Gitee）接口的方式，`openlibing-cicd` 自身对外暴露的 HTTP 接口出入参、路径与返回结构均未变化。

## 7. 安全设计

**防护边界**：

- 令牌通过请求头传输，不再进入 URL，因此不会落入访问日志、代理日志、Referer、浏览器历史与异常堆栈中的 URL。
- 调用前仍保留 `SafeRequestUtils.isSafeProtocol(url)`，SSRF 协议校验边界不变。
- 请求体中的 `access_token` 属第三方接口契约要求，不进入 URL 与日志。

**失败语义**：

- `queryPrTitle` 请求失败（含认证失败）仍被 `catch (Exception)` 捕获后 `return null`，业务表现为 PR 标题为空，不阻断主流程。
- webhook 三处调用的返回处理逻辑未改动。

**残留风险与已知取舍**：

- `PipelineServiceImpl` 第 7061/7091 行附近 PR 管理模块仍存在 `access_token=` 的 URL 拼接，本次未处理，需后续整改。
- 若第三方接口对某些路径不识别 `PRIVATE-TOKEN` 头，需回归验证；仓内 `GiteeIssueClient`、`RepoServiceImpl#getGiteeOrgMembers` 已证明该头部可用。
- 令牌仍存在于进程内存与请求头，属不可避免的最小暴露面。

**验证覆盖**：

- `BranchServiceImplTest#getRepoBranch_TokenInHeaderNotInQuery`：ArgumentCaptor 捕获 form 与 header，断言 form 不含 access_token、header 键为 `PRIVATE-TOKEN` 且值等于传入 token。
- `RepoServiceImplTest#testGetRepoWebhookList_TokenInHeaderNotInUrl`：断言 URL 不含 access_token、headerMap 中 `PRIVATE-TOKEN` 值正确；create/delete 成功用例补同等断言。
- `PipelineServiceImplTest#queryPrTitle_TokenInHeaderNotInUrl`：静态 mock `SafeRequestUtils.isSafeProtocol`、`cn.hutool.http.HttpRequest.get`、`SecurityUtil.decrypt`，断言请求 URL 精确为 `https://api.gitcode.com/api/v5/repos/openlibing/openlibing-cicd/pulls/123` 且不含 access_token，并 verify `header("PRIVATE-TOKEN","plain-token")` 与 `timeout(1500)`。
- `PipelineServiceImplTest#queryPrTitle_RequestThrows_ReturnsNull`：execute 抛异常时返回 null，不向上抛。
