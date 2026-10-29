# gray-release-review-fixes 任务清单

- [x] VersionLoadBalancer#filterByTrack：匹配规则改为"仅明确 gray 排除出 stable"，缺失/null/未知 version 按 stable（评审 #4、#12）
- [x] VersionLoadBalancer#getInstanceResponse：仅 gray 轨道无匹配时回退全部实例，stable 轨道返回 EmptyResponse（评审 #4）
- [x] VersionLoadBalancer：回退日志 WARN → DEBUG（评审 #7）
- [x] GrayReleaseFilter#getUserId：改为可信 JWT 身份（cookie `token` / header `plugin-token`），弃用查询参数（评审 #8）
- [x] GrayReleaseFilter#resolveTrack：按请求随机改为按用户粘性哈希（评审 #9）
- [x] GrayReleaseConfig#toString：去白名单明文，仅输出 whitelistSize，删除 Arrays 导入（评审 #5）
- [x] GrayReleaseConfigTest：缓存复用改为对内部 cachedWhitelist 字段 assertSame（评审 #3）
- [x] VersionLoadBalancerTest：补缺元数据 / null metadata / 未知版本值 / 全 gray 不回退 4 个用例（评审 #1）
- [x] GrayReleaseFilterTest：补 ratio=100 匿名请求、同用户粘性、伪造 queryParam 不生效、坏 token 不阻断用例（评审 #2）
- [x] 新增 VersionLoadBalancerConfigTest：ApplicationContextRunner 断言子上下文负载均衡器类型（评审 #6）
- [x] CI 回归修复：getWhitelist 恢复 unmodifiable 包装过 SpotBugs EI_EXPOSE_REP；测试 cookie 类型改用 HttpCookie 过编译
- [x] 本地验证：Spotless / Checkstyle / SpotBugs / PMD / test-compile 全绿
- [x] 业务 PR 更新：openlibing/openlibing-gateway!217（commit d4395ae / 89943f1 / 9b321c8）
