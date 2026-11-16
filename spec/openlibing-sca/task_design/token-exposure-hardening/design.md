# token-exposure-hardening — 技术设计

## 方案概述

把 gitee 文件数检查链路的凭证从 URL 查询参数迁移到 `Authorization: Bearer` 请求头，与 gitcode 分支及 #85 的 gitee Bearer 整改保持一致；在 URL 构建处剥离配置中心存量模板中残留的 `access_token=` 片段。同时给 `ScanossFileDto.token` 加 `@ToString.Exclude`，消除 Lombok `toString()` 的凭证泄露面。HTTP 工具层与签名均不改动。

## 数据流（修复后）

```
getPrFileSize(prScanPo, repoInfo)
  ├─ buildFileCheckUrl
  │    ├─ gitee:  giteeFileUrl（剥离残留 access_token= 及其尾随 ?/&）
  │    │          .replace({owner}/{repo}/{number})   ← URL 不含 token
  │    └─ gitcode: gitcodeFileUrl.replace({owner}/{repo}/{number})
  ├─ headerToken = platformUtil.getPlatformToken(token, projectId, PLATFORM_GITCODE|PLATFORM_GITEE)
  └─ checkFileNum(url, headerToken)  →  HttpClientUtil.get(url, token)
                                          └─ addAuthorizationHeader：非空 token 加 "Authorization: Bearer <token>"
```

## 架构决策

| 编号 | 决策                                                                                            | 理由                                                                                                                 |
| ---- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| D1   | `buildFileCheckUrl` 只做资源信息模板替换，gitee 分支删除 accessToken 拼接                       | 凭证与 URL 分离，URL 可安全进入日志 / 网关 / 异常堆栈                                                                |
| D2   | `getPrFileSize` 对 gitee 也取平台 token 作为 `headerToken`，与 gitcode 分支同构                 | 复用既有 `checkFileNum(url, token)` 通路，签名与调用方不变；gitee v5 支持 Bearer（#85 结论）                         |
| D3   | 存量配置兼容：`giteeFileUrl` 中命中 `access_token=` 时截断至该位置，并去掉尾部 `?` / `&`        | Nacos 存量模板可能仍是 `...?access_token=` 形态；若不剥离，URL 会带空参数或再次把 token 拼回                         |
| D4   | `ScanossFileDto.token` 用 `@ToString.Exclude` 抑制                                              | 只影响 Lombok 生成的 `toString()`，不影响 getter/setter、序列化与下载功能，成本最低                                  |
| D5   | 测试用 `spy` + `doReturn`/`verify` 验证传参与 URL 形态，并用 `ReflectionTestUtils` 注入存量配置 | 不改方法可见性即可覆盖真实调用链；`buildFileCheckUrl` 为 public 实例方法，可直接断言                                 |
| D6   | 不改 `HttpClientUtil`                                                                           | `get(url, token)` 与 `addAuthorizationHeader` 已实现 Bearer 与"空 token 不带头"，避免重复改造（SEC-1 已在 #85 落地） |

## 涉及文件

| 文件                                                                                  | 操作               | 说明                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/dm/service/impl/IntegrationApiServiceImpl.java`     | 修改               | `getPrFileSize`（L508-531）新增 gitee 分支取 headerToken；`buildFileCheckUrl`（L540-570）gitee 分支去 token 拼接 + 存量 `access_token=` 剥离；注释修正（commit `d5d284ed`）                           |
| `src/main/java/com/openlibing/sca/common/domain/ScanossFileDto.java`                  | 修改               | `token` 字段加 `@ToString.Exclude`，新增 `lombok.ToString` import（commit `2e309ec5`，+2 / -1）                                                                                                       |
| `src/test/java/com/openlibing/sca/dm/service/impl/IntegrationApiServiceImplTest.java` | 修改               | 新增 `testGetPrFileSize_Gitee_UsesHeaderToken`（L504）、改造 `testBuildFileCheckUrl_Gitee`（L526）、新增 `testBuildFileCheckUrl_Gitee_StripsLegacyAccessTokenFromConfig`（L543）（commit `d5d284ed`） |
| `src/main/java/com/openlibing/sca/analysis/utils/HttpClientUtil.java`                 | 未修改（只读核实） | `get(url, token)` L225-231；`addAuthorizationHeader` L263-268 发送 Bearer，空 token 不带头                                                                                                            |

## 风险 & 缓解

| 风险                                                                                                                   | 缓解                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 存量 `gitee.file.url` 若形如 `...?access_token=X&other=1`，D3 截断会丢弃后续参数                                       | 代码仅兜底；运维需按新模板（不含 token）更新配置中心键值（本轮未验证真实配置）              |
| `prScanPo.getPrUrl()` 不以配置的 `gitee.url` 开头时 `headerToken` 为 null，请求不带鉴权头，gitee 可能返回 401 / 空结果 | `getPrFileSize` 异常分支返回 -1（L524-530）；需保证配置域前缀与 PR URL 一致（未加自动校验） |
| gitee 平台个别接口不认 Bearer 头，文件数检查失败                                                                       | 单测覆盖 URL 与传参；真实环境回归未执行                                                     |
| `checkFileNum` Javadoc（L606）仍写"gitee 为 null，token 已拼入 URL"，与现状不一致                                      | 属注释残留，未在本次 commit 修正，建议后续清理（不影响运行）                                |
| `@ToString.Exclude` 无单测守护，后续重构可能被移除                                                                     | 建议补充 `toString()` 不含 token 的断言（本轮未做）                                         |
| 其他 DTO / 日志点仍可能打印 token                                                                                      | 本 issue 只覆盖 `ScanossFileDto`；同类整改需在敏感日志脱敏批次统一处理                      |

## 跨仓影响

无代码跨仓影响。配置中心（Nacos）中 `gitee.file.url` 模板建议同步去掉 `access_token=`（运维动作），代码侧已做兼容，不阻塞发布。
