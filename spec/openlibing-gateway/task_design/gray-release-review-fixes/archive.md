# gray-release-review-fixes 归档

## 变更概览

灰度发布功能（PR !217）评审意见 9 条 + CI 门禁/编译回归 2 项，共 11 项修复全部完成。

- 业务 PR：[openlibing/openlibing-gateway!217](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/217)
  （fork 分支 `codechentao:release_202601029` → upstream `release_202601029`）
- 相关 commit：
  - `d4395ae` fix(gateway): harden gray release review findings（9 条评审意见主体修复）
  - `89943f1` fix(gateway): restore unmodifiable wrapper for whitelist getter（SpotBugs EI_EXPOSE_REP 回归）
  - `9b321c8` fix(gateway): use HttpCookie in GrayReleaseFilterTest（测试源码编译错误）

## 关键决策沉淀

1. **灰度匹配语义**：版本元数据采用"黑名单式"判定——只有明确 `version=gray` 才进灰度，
   其余（缺失/null/未知值）全部按 stable，彻底避免元数据命名不统一导致存量实例被摘流。
2. **回退不对称**：仅灰度轨道允许回退全部实例；稳定轨道无匹配宁可失败，不越界进灰度。
3. **身份可信链**：网关染色过滤器消费的身份必须与 AuthFilter 同源（JWT cookie/header），
   查询参数在豁免路径上不可信。
4. **粘性分流**：比例灰度按 `floorMod(hash(userId), 100) < ratio` 分桶，会话不跨版本。
5. **防御性视图缓存**：缓存内部解析结果，对外每次返回 `Collections.unmodifiableSet`
   包装——既是防篡改约定，也是 SpotBugs EI_EXPOSE_REP 的合规写法。

## 验证记录

- 本地：Spotless / Checkstyle / SpotBugs（0 BugInstance）/ PMD / test-compile 全部通过；
- CI：安全编码扫描门禁在 `89943f1` 后需重跑确认；单测（含新增用例）由流水线执行；
- 已知行为变化：ratio>0 时匿名（无可信 JWT）流量整体进入 gray 轨道，上线前需运维知悉。

## 经验教训

- 本地校验必须用 `test-compile` 而非 `compile`，否则测试源码的 API 误用（如 cookie 类型）
  拦不住，只能靠 CI 兜底；
- 本地 SpotBugs fork JVM 在机器内存紧张时会 OOM（G1 mmap 失败），重跑即可，非代码问题；
- `gitcode pr edit --labels` 是整体替换，编辑标签时必须带上全部现有标签（含 ci/needs-issue）。
