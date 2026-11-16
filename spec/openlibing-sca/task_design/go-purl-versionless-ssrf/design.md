# go-purl-versionless-ssrf — 技术设计

## 方案概述

针对无版本 Go purl 的兜底解析链，采用"解析阶段结构预检（零出站）+ 出站层统一 SSRF 校验">
双层防护。结构预检在 `queryGoImportSourceRepo` 拼接 go-import URL 之前拦截纯 IPv4 / 单标签 host；
其余域名交由 `BasePackageUrlResolver#httpGet` 的 `SsrfsafeUrlUtil` 校验（含 DNS 解析结果判定）
兜底，并用逐跳校验的手动重定向替代 `Redirect.ALWAYS`。

## 数据流（修复后）

```
POST /project/notice/scan/supplement（ProjectNoticeScanController L134）
  └─ resolveVersionlessOrInvalidPurl (GoPackageUrlResolver L209)
        ├─ queryLatestVersion → https://proxy.golang.org/<module>/@latest（固定官方 host）
        └─ @latest 失败 → resolveSourceRepoUrl (L364)
              ├─ github.com/* → 直接构造 https://github.com/<user>/<repo>
              └─ queryGoImportSourceRepo (L390)
                    ├─ extractModuleHost (L426)
                    ├─ host == null || !host.contains(".") || IPv4 字面量
                    │     → WARN "go-import fallback rejected..." → return null（零出站）
                    └─ httpGetText("https://" + modulePath + "?go-import=1")
                          → BasePackageUrlResolver#httpGet (L213)
                              ├─ validateUrl 首跳（协议白名单 / localhost / 内网与特殊网段）
                              ├─ Redirect.NEVER + 逐跳 validateUrl（≤5 跳）
                              └─ 200 → 解析 <meta name="go-import">；异常 → null

null 结果回退：
  ├─ resolveVersionlessOrInvalidPurl → 保留原 purl 候选（L246-L249）
  └─ toOfficialUrl / purlToSourceRepoUrl → 保留原 purl（L323-L327）
```

## 架构决策

| 决策                                    | 理由                                                                                                                            |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| D1 先做解析阶段结构预检，再进入 httpGet | 对最典型利用形态（`pkg:golang/169.254.169.254/x`）实现零出站，攻击者无法借 DNS 解析时序做探测；日志可直接定位被拒 module        |
| D2 拒绝纯 IPv4 字面量与单标签 host      | Go module path 首段按规范应是含 `.` 的域名；纯 IP 与内网短名都不可能是合法公共 module。该判定不依赖 DNS，确定性强、无网络副作用 |
| D3 不维护托管域白名单                   | 白名单会阻断自建 module 域（如企业内部域名、镜像生态），且需持续维护；通用 SSRF 校验已能拦截解析到内网的域名                    |
| D4 拒绝时返回 null 并保持原 purl        | 沿用既有兜底约定（无法解析则保持 purl，由下游抛出明确错误），避免 supplement 受理行为突变、也避免静默丢弃用户输入               |
| D5 出站层与 #97 共用同一改造            | 合并链路（toOfficialUrl）与解析链路（resolve/兜底）都经过 `httpGet`，一次修复覆盖两个入口，避免重复实现                         |
| D6 `@latest` 查询不做 host 校验         | `proxy.golang.org` 为代码内固定常量 `OFFICIAL_HOST`，用户不可控，不属于 SSRF 向量                                               |

## 涉及文件

| 文件                                                                                | 操作 | 说明                                                                                                                                        |
| ----------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/dm/util/packageurl/GoPackageUrlResolver.java`     | 修改 | 新增 `IPV4_HOST_PATTERN`（L96）；`queryGoImportSourceRepo` 入口结构校验（L390-L399）；新增 `extractModuleHost`（L426）                      |
| `src/main/java/com/openlibing/sca/dm/util/packageurl/BasePackageUrlResolver.java`   | 修改 | `httpGet` 首跳 + 逐跳 `SsrfsafeUrlUtil.validateUrl`，`Redirect.NEVER`，新增 `sendQueryGet` / `isRedirectStatus` / `MAX_QUERY_REDIRECT_HOPS` |
| `src/test/java/com/openlibing/sca/dm/util/packageurl/GoPackageUrlResolverTest.java` | 修改 | 新增 6 个用例：两个零出站（resolve）、一个 toOfficialUrl 零出站、三个 httpGetText 出站前拒绝                                                |

## 风险 & 缓解

| 风险                                                         | 缓解                                                                                    |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| 合法但单标签的 module 名被拒                                 | Go module 规范要求首段含点；命中时回退原 purl，不产生错误写库，影响仅为该 purl 无法解析 |
| 企业内网自建 Go module 域名被 `validateUrl` 判定为内网而拒绝 | 属于预期收敛；如需支持需引入显式白名单配置（当前无此需求，未验证）                      |
| 代理环境下校验侧 DNS 解析失败                                | 抛 `Failed to resolve host`，调用方回退原 purl，主流程不中断                            |
| 重定向被限制为 5 跳                                          | 与 `ProjectNoticeScanExecutor` 下载链路一致；超限视为解析失败并回退                     |
| 仍存在 DNS rebinding（校验与建连两次解析）                   | 本提交不闭环，由 #143 统一处理                                                          |
| 拒绝日志打印 modulePath                                      | 仅包含用户 purl 的 module 段，无凭证；不新增敏感数据落盘                                |

## 跨仓影响

无。业务改动仅 `openlibing-sca`，spec 归档 `openlibing-docs`（本目录）。
与 #97（`go-purl-ssrf-hardening`）为同一提交 `c3f88357` 的两个 issue 视角：
#97 关注 `httpGet` sink 本身，#133 关注无版本 purl 兜底链路。

## 明确不在范围

- 托管域白名单与内部 module 白名单配置（issue 修复建议 2 未按原样实现）
- DNS pinning / rebinding 闭环（#143）
- 下载阶段 `doDownload` 校验与重定向策略（#105）
- supplement 接口鉴权、限流与请求体校验（另行整改）
