# gray-release-review-fixes

## 需求背景

灰度发布功能（[gray-release](../gray-release/proposal.md)，业务 PR
[openlibing/openlibing-gateway!217](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/217)）
在评审中收到 9 条问题意见，覆盖正确性、安全、可观测性与测试有效性四个维度；随后 CI
安全编码扫描（SpotBugs）与测试编译又暴露 2 个回归。本轮集中修复全部 11 项问题。

## 问题清单

| #   | 位置                                                   | 问题                                                                                   | 风险                               |
| --- | ------------------------------------------------------ | -------------------------------------------------------------------------------------- | ---------------------------------- |
| 1   | VersionLoadBalancerTest                                | stable 轨道用例未守住"缺元数据视为 stable"契约                                         | 存量实例被摘流无法被测试发现       |
| 2   | GrayReleaseFilterTest                                  | 匿名请求用例 ratio=0 断言无法区分"走比例判定"与"强制 stable"                           | 测试覆盖盲区                       |
| 3   | GrayReleaseConfigTest                                  | 缓存用例用 assertEquals 而非同一性断言                                                 | 缓存失效不被发现，每请求重复解析   |
| 4   | VersionLoadBalancer#filterByTrack                      | 精确匹配 gray/stable，元数据命名不统一（如 1.2.0）时 stable 轨道匹配不到实例并回退全部 | 灰度隔离失效，稳定用户打到灰度实例 |
| 5   | GrayReleaseConfig#toString                             | 明文输出白名单用户ID                                                                   | 敏感信息入日志，违反脱敏约定       |
| 6   | VersionLoadBalancerConfig                              | 无配置注册测试                                                                         | 默认负载均衡器未替换时灰度静默失效 |
| 7   | VersionLoadBalancer 回退日志                           | 每请求 WARN 日志放大                                                                   | 污染告警通道、IO/GC 开销           |
| 8   | GrayReleaseFilter#getUserId                            | 白名单身份取自请求查询参数，可被未登录调用方伪造                                       | 任意调用方自行钉进 gray 轨道       |
| 9   | GrayReleaseFilter#resolveTrack                         | 按请求随机比例分流，无用户粘性                                                         | 同一会话跨版本，状态丢失/校验失败  |
| 12  | VersionLoadBalancer#getMetadata                        | metadata 为 null 时 NPE → 请求 5xx                                                     | 与可用性优先目标相反               |
| CI  | GrayReleaseConfig#getWhitelist / GrayReleaseFilterTest | EI_EXPOSE_REP 门禁回归；cookie 类型编译错误                                            | 流水线失败                         |

## 验收标准

- stable 轨道绝不路由到明确 gray 实例；缺失/null/未知 version 元数据一律按 stable。
- 仅 gray 轨道允许无匹配回退；回退日志为 DEBUG 级别。
- 白名单身份仅来自可信 JWT（cookie `token` / header `plugin-token`）。
- 比例分流按用户维度粘性，同一用户轨道恒定。
- toString 不输出白名单明文；SpotBugs/PMD/Checkstyle/Spotless 门禁全绿；测试源码编译通过。
