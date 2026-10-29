# Gitee Token Bearer 化 — 技术设计

## 方案概述

删除"gitee 仅支持查询参数鉴权"的分支逻辑，gitee / gitcode 统一为：URL builder 只产出业务参数（`?ref=`、`?per_page=100`、`?recursive=1` 等），token 一律由 HTTP 客户端层写入 `Authorization: Bearer <token>` 请求头。涉及 Apache HttpClient（下载链路）、JDK HttpURLConnection（分支列表链路）、自研 `HttpClientUtil` / `HttpUtil`（API 调用链路）三种客户端，均已有设置请求头的能力，无需新增封装。

## 关键决策

1. **SEC-2：token 统一走 `Authorization: Bearer` 请求头，不拼入 URL**（gitee / gitcode 一致）。消除 token 进入日志 / 监控 / 堆栈的泄露面，对应 Issue #85、#104。
2. **SEC-1：空 token 不携带鉴权头**。避免发送裸 `Bearer ` 前缀导致平台侧 401 或语义歧义。
3. **一次性清理遗留物**：删除 `PrCommonName.TOKEN`（`&access_token=`）、`ACCESS_TOKEN`（`?access_token=`）、`SCA_GITEE_RECURSIVE`（`&recursive=1`）常量与 `ApiUrlDto.urlToken` 字段，防止后续代码复用回退。
4. **URL builder 不再感知 token**：`buildRepoSizeCheckUrl` 等方法去掉 token 入参，token 获取上移到调用方（`sendToMqBasedOnRepoSize` 等），按 repoUrl 前缀（giteeUrl / gitcodeUrl）解析对应平台 token 后传给 HTTP 层。
5. **`getFromPlatformApi` 收敛为单一路径**：不再按 platform 分流单参 / 双参 `HttpClientUtil.get`，统一走 `get(url, token)` 双参重载。
6. **测试用本地 `com.sun.net.httpserver.HttpServer` 实收请求**：JDK `HttpURLConnection.getRequestProperty` 对 `Authorization` 头刻意掩码（`EXCLUDE_HEADERS`），反射读取无法验证，改为启动本地 HttpServer 捕获真实请求头断言。

## 涉及文件

| 文件                                 | 操作 | 说明                                                                                                                                      |
| ------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `pom.xml`                            | 修改 | 显式引入 `com.rabbitmq:amqp-client:5.34.0`                                                                                                |
| `OpenScanServiceImpl.java`           | 修改 | `fetchFileContent` / `buildApiUrl` 不再向 URL / `ApiUrlDto` 注入 token，gitee 也解析 headerToken                                          |
| `DownLoadFilesUtils.java`            | 修改 | `createDownloadConnection(url, token)` 增加 Bearer 头；`buildScanossUrl` / `buildDownloadUrl` 去掉 token 拼接；HttpGet 统一设置 Bearer 头 |
| `ScanCommonServiceImpl.java`         | 修改 | `getFromPlatformApi` 统一双参 get；contents / compare / commits / files 四类 URL builder 去掉 gitee token 拼接                            |
| `IntegrationApiServiceImpl.java`     | 修改 | `urlAdd`、`generatePrUrl`、分支列表、仓库信息、`buildRepoSizeCheckUrl`（4 参 → 3 参）、`sendToMqBasedOnRepoSize` 全链路改造               |
| `ApiUrlDto.java`                     | 修改 | 删除 `urlToken` 字段                                                                                                                      |
| `PrCommonName.java`                  | 修改 | 删除 `TOKEN` / `ACCESS_TOKEN` / `SCA_GITEE_RECURSIVE` 常量                                                                                |
| `DownLoadFilesUtilsTest.java`        | 修改 | 断言 Bearer 头 + URL 无 token；新增 2 个 HttpServer 实收测试                                                                              |
| `PrCommonNameTest.java`              | 修改 | 删除已移除常量的断言                                                                                                                      |
| `IntegrationApiServiceImplTest.java` | 修改 | URL 无 token 断言；`buildRepoSizeCheckUrl` 3 参调用；doGet 头传 token 验证                                                                |
| `ScanCommonServiceImplTest.java`     | 修改 | `HttpClientUtil.get` 统一 mock 双参重载并验证 token 走请求头                                                                              |

## 行为逻辑

```
出站请求统一路径:
  token = platformUtil.getPlatformToken(<平台默认token>, projectId, <平台标识>)
  url   = <urlBuilder>(业务参数, 不含 token)
  if token 非空:
      请求头 Authorization: Bearer <token>
  else:
      不携带 Authorization 头
```

改造前 gitee 分支：`url + "&access_token=" + token`（或 `?access_token=`），请求头为空；改造后 gitee 与 gitcode 完全一致。

## 测试策略

- **单测**：4 个测试类同步更新，核心断言从"URL 含 access_token"反转为"URL 不含 token + Authorization 头等于 `Bearer <token>`"。
- **新增测试**：`createDownloadConnection_withToken_sendsBearerHeader`、`createDownloadConnection_withBlankToken_noAuthHeader`，用本地 HttpServer 实收请求头。
- **CI**：PR 流水线通过（`ci-pipeline-passed`）。
- **手动**：真实 gitee 环境验证文件下载正常、URL 无 token（PR 测试计划中的勾选项）。

## 风险与缓解

| 风险                                                     | 缓解                                                                                                                                     |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| gitee 平台对 Bearer 头鉴权支持异常（假设不成立时的回归） | Gitee v5 官方支持 Authorization 头鉴权；单测 + 手动下载验证双保险；若出现 401 可快速回滚                                                 |
| 出口代理 / 网关剥离 `Authorization` 头导致鉴权失效       | 现网 gitcode 链路已用同机制运行，链路一致性可佐证                                                                                        |
| 遗漏某条 URL 拼接路径                                    | 已枚举下载、contents、compare、commits、files、branches、trees 全链路并逐条断言；`PrCommonName.TOKEN` 等常量删除后编译器兜底拦截残留引用 |
| 空 token 场景行为变化                                    | 显式定义：空 token 不带头，与原 gitee 无凭据场景兼容，已有单测覆盖                                                                       |

## 跨仓影响

- 仅 `openlibing-sca`，无其他仓改动，无外部接口契约变化。
- 对下游不可见：出站请求的鉴权凭据不变，仅传递通道从 URL 移到请求头。
