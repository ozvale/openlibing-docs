# go-purl-ssrf-hardening — 技术设计

## 方案概述

采用"单点收口 + 解析阶段结构化预检"两层防护：

- 在 `BasePackageUrlResolver#httpGet` 统一接入 `SsrfsafeUrlUtil`，并把自动重定向替换为
  "逐跳校验后手动跟随"，使所有 resolver（Maven / Npm / PyPI / Go / RPM / CGit）的
  `httpGetText` / `httpGetJson` 都受同一防护。
- 在 Go 的 go-import 兜底入口先做 module host 结构校验（首段含 `.`、非纯 IPv4 字面量），
  不满足直接返回 null，保证零出站。

## 数据流（修复后）

```
purl（用户提交 / NOTICE 合并文档条目）
  ├─ resolveFromPurl                       (GoPackageUrlResolver L146)
  └─ resolveVersionlessOrInvalidPurl       (L209)
        └─ resolveSourceRepoUrl(modulePath) (L364)
              ├─ github.com/* → 直接拼 https://github.com/<user>/<repo>
              └─ queryGoImportSourceRepo    (L390)
                    ├─ extractModuleHost → null / 不含 "." / 纯 IPv4 → WARN + null（零出站）
                    └─ httpGetText("https://" + modulePath + "?go-import=1")
                          └─ BasePackageUrlResolver#httpGet (L213)
                                ├─ validateUrl(首跳)                (L218)
                                ├─ Redirect.NEVER                   (L222)
                                ├─ sendQueryGet  (超时 queryTimeoutSeconds) (L261)
                                ├─ 3xx: URI.resolve(Location) → validateUrl → 重发（≤5 跳）(L236-L245)
                                └─ 非 200 → IllegalStateException(url, finalUrl)

toOfficialUrl → purlToSourceRepoUrl (L314) → resolveSourceRepoUrl 复用同一链路
```

## 架构决策

| 决策                                                  | 理由                                                                                                                                                                                               |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 校验下沉到基类 `httpGet`，而非在各 resolver 分别加 | `httpGet` 是 packageurl 包唯一 HTTP 出站点（`httpGetText` / `httpGetJson` 均为其封装），单点收口可避免遗漏，且一次覆盖全部生态                                                                     |
| D2 `Redirect.NEVER` + 手动逐跳校验                    | 自动跟随无法对每跳目标做校验，且允许 https→http 降级；手动模式与 `ProjectNoticeScanExecutor#doDownload`（#105）写法一致，跳数上限同为 5                                                            |
| D3 相对 `Location` 以当前跳为基准解析                 | 首跳可能换域（如 github → 镜像域名），若始终以初始 URL 解析相对路径会拼错 host，甚至绕过校验落到意外目标                                                                                           |
| D4 Go host 预检放在拼接 `metaUrl` 之前                | 结构非法的 module（IP 字面量、单标签短名）在 Go module 规范中本就不成立，提前返回可保证零出站，且日志可直接定位                                                                                    |
| D5 不做托管域白名单                                   | issue #133 建议仅放行 github.com / golang.org / gitlab.com，但会误杀合法自建 module 域名；当前用"拒绝 IP 字面量与单标签 + 通用 SSRF 校验兜底"覆盖同等攻击面                                        |
| D6 失败语义保持回退而非抛出业务异常                   | `queryGoImportSourceRepo` 已有 try/catch 返回 null 的约定，`resolveVersionlessOrInvalidPurl`（L246-L249）与 `purlToSourceRepoUrl`（L324-L327）据此保持原 purl；不改变 NOTICE 受理/合并的可预期行为 |

## 涉及文件

| 文件                                                                                | 操作 | 说明                                                                                                                                                        |
| ----------------------------------------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/dm/util/packageurl/BasePackageUrlResolver.java`   | 修改 | import `SsrfsafeUrlUtil`；`httpGet` 增加首跳校验、`Redirect.NEVER`、逐跳重定向（≤5 跳）；新增 `MAX_QUERY_REDIRECT_HOPS`、`sendQueryGet`、`isRedirectStatus` |
| `src/main/java/com/openlibing/sca/dm/util/packageurl/GoPackageUrlResolver.java`     | 修改 | 新增 `IPV4_HOST_PATTERN`（L96）、`extractModuleHost`（L426）；`queryGoImportSourceRepo` 入口结构校验与 WARN 日志（L390-L399）                               |
| `src/test/java/com/openlibing/sca/dm/util/packageurl/GoPackageUrlResolverTest.java` | 修改 | 新增 6 个 SSRF 回归用例（含出站记录与零出站断言、httpGetText 拒绝断言）                                                                                     |

## 风险 & 缓解

| 风险                                                                | 缓解                                                                                                  |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 内网自建 Go module / 内部 mirror 域名被 `validateUrl` 拒绝          | NOTICE 合并面向公网制品；如确有内网 module 解析需求，需要单独设计白名单配置（当前需求未提出，未验证） |
| 隔离网络/代理环境 DNS 解析失败，校验直接抛 `Failed to resolve host` | 失败按查询失败处理，调用方回退到原 purl 或 proxy zip 候选，不中断主流程                               |
| 3xx 不再自动跟随导致部分源站解析失败                                | 已实现手动跟随（301/302/303/307/308），超 5 跳按失败处理，与下载链路一致                              |
| 校验与建连两次独立解析，仍存在 TOCTOU / DNS rebinding 窗口          | 本提交只做校验，不 pin 地址；闭环见 #143（`ssrf-dns-rebinding-pinning`）                              |
| 新增 WARN 日志包含 modulePath / URL                                 | 内容为 purl 中的 module 地址，不含凭证；未新增敏感信息落盘                                            |
| 通用校验误伤 IP 形式 module                                         | Go module 规范不接受纯 IP 首段，实际无语义损失                                                        |

## 跨仓影响

无。业务改动仅 `openlibing-sca`，spec 文档归档 `openlibing-docs`（本目录）。
与 #133（`go-purl-versionless-ssrf`）共用同一提交，实施细节分别记录在两个目录。

## 明确不在范围

- 下载阶段 `doDownload` 的重定向/校验实现（#105 已修，目录 `ssrf-redirect-hardening`）
- DNS pinning / rebinding 闭环（#143）
- 托管域白名单与内部 module 白名单配置
- PyPI、Maven 等固定 host 查询源改造（统一 `httpGet` 已覆盖）
