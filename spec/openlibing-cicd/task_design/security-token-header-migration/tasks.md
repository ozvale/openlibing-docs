# security-token-header-migration — 实现任务

## 进度: 8/8 complete

- [x] Task 1: `BranchServiceImpl#getRepoBranch` 令牌迁移到 `PRIVATE-TOKEN` 头
- [x] Task 2: `PipelineServiceImpl#queryPrTitle` 令牌迁移到 `PRIVATE-TOKEN` 头
- [x] Task 3: `RepoServiceImpl` webhook 三处调用改传 headerMap
- [x] Task 4: hutool `HttpResponse` 改为 try-with-resources
- [x] Task 5: `BranchServiceImplTest` 新增令牌位置断言
- [x] Task 6: `RepoServiceImplTest` 新增 / 补充令牌位置断言
- [x] Task 7: `PipelineServiceImplTest` 新增 queryPrTitle 回归用例
- [x] Task 8: 全量测试与 pre-commit 验证

## 详细任务

### Task 1: BranchServiceImpl#getRepoBranch

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/BranchServiceImpl.java`
- 改动：删除 `params.put("access_token", ...)`；`HttpUtil.get(url, params)` 改为 `HttpRequest.get(url).form(params).header("PRIVATE-TOKEN", accessToken)`；分页等表单参数保持不变。
- 验证方式：`BranchServiceImplTest#getRepoBranch_TokenInHeaderNotInQuery`，断言 form 不含 access_token、header 键值正确。

### Task 2: PipelineServiceImpl#queryPrTitle

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java`
- 改动：`HttpUtil.get(url, params, timeout)` 改为 `HttpRequest.get(url).header("PRIVATE-TOKEN", accessToken).timeout(PR_TITLE_HTTP_TIMEOUT_MS)`；URL 拼接去掉 access_token；`PR_TITLE_HTTP_TIMEOUT_MS = 1500`（第 338 行）不变；`resolveAccessToken` / `decryptAccessToken` / `SafeRequestUtils.isSafeProtocol` 校验与 `catch (Exception) → return null` 语义保持不变。
- 验证方式：`PipelineServiceImplTest` 新增的两个用例。

### Task 3: RepoServiceImpl webhook 三处

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/RepoServiceImpl.java`
- 改动：`getRepoWebhookList`、`createRepoWebhook`、`deleteRepoWebhook`（调用点 416/463/511/568 行区域）移除 URL 中的 access_token，构造 `Map<String, String> headerMap` 携带 `PRIVATE-TOKEN` 传给 `HttpRequestUtil.sendRequest`；`createRepoWebhook` 请求体中的 `access_token` 保留。
- 验证方式：`RepoServiceImplTest` 中 URL 不含 access_token、headerMap 中 `PRIVATE-TOKEN` 值正确的断言。

### Task 4: HttpResponse 资源释放

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/` 下涉及 hutool `HttpResponse` 的调用点
- 改动：改为 try-with-resources 关闭响应对象。
- 验证方式：编译通过，全量测试通过。

### Task 5: BranchServiceImplTest

- 文件：`src/test/java/com/openlibing/cicd/business/service/impl/BranchServiceImplTest.java`
- 改动：新增 `getRepoBranch_TokenInHeaderNotInQuery`，用 ArgumentCaptor 捕获 form 与 header。
- 验证方式：mvn 执行该测试类。

### Task 6: RepoServiceImplTest

- 文件：`src/test/java/com/openlibing/cicd/business/service/impl/RepoServiceImplTest.java`
- 改动：新增 `testGetRepoWebhookList_TokenInHeaderNotInUrl`；create/delete 成功用例补 ArgumentCaptor 断言；其余用例第 4 个 header 参数由 `eq(null)` 放宽为 `any()`。
- 验证方式：mvn 执行该测试类。

### Task 7: PipelineServiceImplTest

- 文件：`src/test/java/com/openlibing/cicd/business/service/impl/PipelineServiceImplTest.java`
- 改动：
  - `queryPrTitle_TokenInHeaderNotInUrl`：静态 mock `SafeRequestUtils.isSafeProtocol`、`cn.hutool.http.HttpRequest.get`、`SecurityUtil.decrypt`；断言 URL 精确为 `https://api.gitcode.com/api/v5/repos/openlibing/openlibing-cicd/pulls/123` 且不含 access_token；verify `header("PRIVATE-TOKEN","plain-token")` 与 `timeout(1500)`。
  - `queryPrTitle_RequestThrows_ReturnsNull`：execute 抛异常时返回 null，不向上抛。
- 验证方式：mvn 执行该测试类。

### Task 8: 全量验证

- 改动：无。
- 验证方式：
  - `PipelineServiceImplTest` 全量 225 个用例通过（原 223 + 新增 2）。
  - pre-commit 12 个钩子全部通过。
  - 无新增配置项、无 pom 变更、无对外接口出入参变化。
