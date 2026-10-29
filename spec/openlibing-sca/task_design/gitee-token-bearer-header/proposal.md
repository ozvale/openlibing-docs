# Gitee Token 鉴权方式整改：URL 查询参数改为 Bearer 请求头

## 需求背景

openlibing-sca 调用 Gitee v5 API（文件下载、contents、compare、commits、PR files、branches、git trees 等链路）时，访问令牌原以 `access_token=<token>` 形式拼接在 URL 查询参数中。URL 会进入访问日志、网关日志、监控埋点与异常堆栈，造成平台凭据泄露风险。此前 GitCode 平台链路已改为 `Authorization: Bearer` 请求头，但 Gitee 链路基于"gitee 仅支持查询参数鉴权"的假设保留了 URL 拼接。

该假设不成立：Gitee v5 API 同样支持 `Authorization: Bearer` 请求头鉴权。本需求统一两条平台链路的鉴权方式，消除 URL 中的 token 明文。

对应安全 Issue：

- openlibing/openlibing-sca#85 【安全】【墨菲】Gitee API 拼接 access_token 存在敏感信息泄露风险
- openlibing/openlibing-sca#104 【安全】【Argus】queryRepoSizeKb gitee 分支将平台 token 拼入 URL 查询串导致凭据泄露风险

## 功能描述

- 下载与 API 调用全链路（gitee / gitcode 统一）：token 不再拼入 URL，改由 `Authorization: Bearer <token>` 请求头传递。
- 空 token（null 或空串）时不携带鉴权头，避免发送 `Bearer ` 空前缀。
- 清理 URL token 拼接的遗留物：`PrCommonName.TOKEN` / `ACCESS_TOKEN` / `SCA_GITEE_RECURSIVE` 常量、`ApiUrlDto.urlToken` 字段。
- `buildRepoSizeCheckUrl` 方法签名收敛（去掉 token 参数，token 改由请求头传递）。
- 同步更新相关单元测试，并用本地 `HttpServer` 实收请求验证 Bearer 头真实发送（绕开 JDK 对 `Authorization` 头的读取掩码）。

## 验收标准

- [x] 编译与单元测试通过（DownLoadFilesUtilsTest、IntegrationApiServiceImplTest、ScanCommonServiceImplTest、PrCommonNameTest）。
- [x] 所有出站 API URL（gitee / gitcode）不再包含 `access_token=` 或明文 token。
- [x] 非 空 token 请求携带 `Authorization: Bearer <token>` 头（本地 HttpServer 实收验证）。
- [x] 空 token 请求不携带鉴权头。
- [x] gitee 文件下载、PR diff 获取、分支列表、仓库体积检查等链路功能不回退。
- [x] CI 流水线通过（PR 已打 `ci-pipeline-passed` 标签）。
- [ ] 手动验证 gitee 真实环境下载与扫描结果一致。

## 影响范围

- 仅 `openlibing-sca` 单仓，11 个文件（+204 / -154），无接口契约 / DB schema / 部署配置变化。
- 行为变化：所有对 gitee / gitcode 平台的出站请求改为请求头鉴权；若平台侧凭据权限配置不当，原 URL 鉴权隐性行为不再存在。
- 顺带变更：`pom.xml` 显式引入 `com.rabbitmq:amqp-client:5.34.0` 依赖。
