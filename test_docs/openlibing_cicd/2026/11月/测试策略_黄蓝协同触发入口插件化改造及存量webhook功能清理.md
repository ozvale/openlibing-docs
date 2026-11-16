# 测试策略 — issue_517_黄蓝协同触发入口插件化改造及存量webhook功能清理

> **模板版本**: v3.10
> **对应规则**: AGENTS.md「规则 01 — 需求驱动的测试策略与设计」+「月度版本工作模式」

> 团队：软件实现&持续集成工具链团队 | 月度：202611 | 版本发布日期：20261116 | issue 编号：517 | issue 标题：黄蓝协同触发入口插件化改造及存量webhook功能清理
> 文档状态：已定稿 | 创建日期：2026-11-13 | 负责人：测试（AI 辅助）

---

## 1. 测试策略

> 业务输入**唯一来源**为 gitcode issue 内的开发设计文档，AI/测试人员必须实际读取链接，禁止超出文档范围发散。

### 1.1 Issue 信息

| 字段 | 内容 |
|------|------|
| Issue编号 | 517 |
| Issue标题 | 【黄蓝协同】黄蓝协同触发入口插件化改造及存量webhook功能清理 |
| 关联需求 | https://gitcode.com/openlibing/openlibing-cicd/issues/517 |
| 所属团队 | 软件实现&持续集成工具链团队 |
| 所属微服务 | openlibing-cicd（cross-region）+ pr-sync-action |
| 所属模块 | CrossRegionController / CrossRegionServiceImpl / 插件触发与轮询链路 |
| 负责人 | 崔世英（开发） |
| 创建日期 | 2026-11-13 |

### 1.2 需求摘要

> 详见 `测试过程数据/需求分析文档.md` 1.2 / 1.6 `FP-01~FP-11` / 1.7 `BR-01~BR-11` / 1.8 `EX-01~EX-12`。

统一触发模型 v2：workflow `on` 为唯一事件入口开关；触发接口只做 triggerEvent（open/reopen/update/merge/comment，缺省 comment）白名单校验并原样透传 req_type；全事件统一插流水线记录（START/WAIT_START）+ msgId 绑定；10 分钟幂等窗口先于 60 秒限流；Redis 异常 fail-open；存量 webhook 自动触发链路（创建 PR / 推提交）下线，push 直发链路保留；插件统一触发 + 轮询，评论命令 `sync` 的 demo 需可跑通。MQS 不带 access_token，account 为真实触发人。

### 1.3 测试目标

1. 验证 workflow `on` 是唯一事件开关：配置内事件触发、未配置事件无动作（FP-01）。
2. 验证 triggerEvent 白名单、缺省 comment、req_type 透传及非法值零副作用（FP-02/FP-03，BR-01/BR-02，EX-01）。
3. 验证流水线记录插入与 msgId 绑定（FP-04）；MQS 发送失败恢复（BR-06/EX-08）按用户确认从本次测试设计剔除。
4. 验证幂等窗口优先于限流、窗口命中返回既有 msgId、窗口过期打断重建（FP-05，BR-03/BR-05，EX-04/EX-05）。
5. 验证 60 秒限流拒绝文案与 Redis 异常 fail-open（FP-06，BR-04，EX-06/EX-07）。
6. 验证存量 webhook 自动触发链路下线、push 直发保留且幂等共存（FP-07/FP-08，EX-12）。
7. 验证插件统一触发 + 轮询、demo 评论 `sync` 触发与状态回显（FP-09/FP-11，BR-09~BR-11，EX-09/EX-10）。
8. 验证 OIDC 鉴权、MQS 不含 access_token、account 真实触发人（FP-10，BR-07）。

### 1.4 测试范围

| 测试类型 | 是否覆盖 | 说明 |
|----------|----------|------|
| UI功能测试 | 是 | GitCode demo 仓库 PR 页：创建/更新 PR、评论 `sync`、PR 标签（SC-RUNNING-2/SC-SUCC-2/SC-FAIL-2）、插件任务结果页（结果/MR 链接/详情链接）。黄区平台页面涉及加密区，由测试人工观测，不做 UI 自动化。对应 FP-01/FP-04/FP-07/FP-08/FP-09/FP-11 |
| API接口测试 | 是（条件执行） | `POST /cross-region/pr-sync/trigger` 的 triggerEvent 白名单、缺省、必填缺失、platform 非法、幂等命中、限流拒绝。因接口经 APIG OIDC 认证，优先复用 demo workflow 的 OIDC 免密链路；如具备合法 OIDC 凭证则用 API 脚本补充，否则以插件触发+人工观测替代。对应 FP-02/FP-03/FP-05/FP-06/FP-10 |
| DFX测试 | 是（可靠性子集） | 覆盖幂等（重复触发防重）、限流（防滥用）、Redis 异常 fail-open（可用性优先）。MQS 发送失败恢复按用户确认剔除。不做性能压测（触发链路由插件低频调用，无性能需求）。对应 FP-05/FP-06，EX-04~EX-07 |
| 安全测试 | 是（部分维度） | 认证：未认证/无效 OIDC 请求被拒（EX 级人工验证）；授权：非法 triggerEvent 参数校验拒绝；传输：APIG HTTPS；敏感信息：MQS 消息不带 access_token、account 为真实人（BR-07）；CSRF：接口为 OIDC 机机调用，不涉及浏览器会话 CSRF；注入：org/repo/prNumber 参数校验（缺失/非法 platform）。不构造高权限越权与加密区内部注入测试（Q-05 人工观测约束） |

**维度组合定稿说明（v3.23 自动定稿）**

- 方案 A「仅手工端到端」：与 Q-05 人工观测最贴合，但幂等/限流/非法值难以精确复现，覆盖不足。
- 方案 B「手工端到端为主 + 条件 API 契约」：以 demo 仓库评论 `sync` 为主链路，接口负向在具备 OIDC 凭证时用脚本补充；推荐采用。
- 方案 C「手工 + UI 自动化」：GitCode PR 评论动作可自动化，但黄区结果页在加密区、轮询最长 1h，自动化收益低且不稳定，不采用。
- **定稿：方案 B**。推荐理由：与用户「加密区人工观测」约束一致，同时保留幂等/限流/非法值的精确验证能力；备选方案 A 作为 API 不可用时的降级路径。

### 1.5 测试策略

- 手工测试（P0/P1 主路径）：
  - P0：demo 仓库 PR 创建/更新 → 插件触发 → 流水线记录 START/WAIT_START → 黄区同步 → 标签与结果页回显（FP-01/04/09）。
  - P0：PR 评论 `sync` → 插件评论事件触发 → triggerEvent=comment → 同步重跑 → 结果回显（FP-09，BR-11）。
  - P0：同一 PR 10 分钟内重复触发 → 返回既有 msgId、不重复同步（FP-05）。
  - P0：同一 PR 60 秒内二次触发（无幂等命中场景）→ 明确限流文案（FP-06）。
  - P1：非法 triggerEvent → 参数错误且无 MQS/无新记录（FP-02/03）。
  - P1：triggerEvent 缺省 → 按 comment 处理（BR-02）。
  - P1：创建 PR 不再由服务端直发触发（仅插件触发一次），push 直发仍可触发（FP-07/08）。
  - P1：CLOSED 事件 skipped、comment 无 sha 反查失败不失败（FP-11）。
  - P2：Redis fail-open（MQS 发送失败恢复场景按用户确认剔除）。
- 自动化测试（条件执行，P1/P2）：脚本位置 `src/automation/software-cicd/api/build_management/pipeline/beta/`（API 契约）与 `src/automation/software-cicd/ui/development_management/code_repository_management/beta/`（GitCode PR 评论动作，如具备稳定登录态）；脚本仅在具备 OIDC/登录凭证时执行，否则登记为手工执行。
- 优先级：P0 覆盖触发主链路与幂等/限流核心规则；P1 覆盖白名单、缺省、旧链路下线与插件归一；P2 覆盖故障恢复类。

### 1.6 复用检查（强制）

| 检索范围 | 可复用用例 | 复用结论 |
|----------|-----------|----------|
| 特性树（本团队 01~04） | TC-ISSUE259-001/002（PR 同步事件触发）、TC-ISSUE259-003/004（push 同步事件触发）、TC-ISSUE259-009（黄区主动触发 PR 同步） | TC-ISSUE259-003/004 直接 reuse（push 直发保留回归）；TC-ISSUE259-001/002/009 需按插件触发路径改造后复用（旧 webhook 自动触发已下线，原断言不再成立），标注 reuse-with-modification |
| 易用性通用库 | 无 | 黄蓝协同触发链路属跨端功能，易用性通用库无对应用例，需新建 |

### 1.7 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 链路涉及加密区，MQS req_type、旧 webhook 是否仍发消息无法直接观测 | 无法直接证明 FP-03/FP-07/FP-08 的内部行为 | 以人工观测外部现象（流水线记录数、同步次数、标签变化）为主；必要时请开发提供日志/查询佐证（P-01/P-02） |
| Redis 异常 fail-open 无故障注入手段 | EX-07 可能无法实测 | 优先请开发协助重启/断连 Redis 或提供异常日志；不可行时以代码走查 + 标记"未实测"记录 |
| APIG OIDC 凭证不可自主获取 | API 负向用例无法脚本化 | 复用 demo workflow 触发链路；接口负向改为人工构造不可行时，由开发提供合法调用方式后补测 |
| 黄区同步流水线耗时不可控（轮询默认 60s/超时 1h） | 端到端用例执行时间长、易超时 | 用例设置人工等待上限，记录实际耗时；超时按 TIMEOUT 结果判定并登记 |
| 存量用例 TC-ISSUE259-001/002 基于旧 webhook 链路 | 517 后断言失效导致误判 | 标记 reuse-with-modification，执行时按插件触发路径复核，不沿用旧断言 |
| 并发双触发（同一 PR 同时评论+更新） | 幂等/限流边界竞争 | 设计并发场景 1 条，P1；预期最多一次 MQS、其余命中幂等或限流 |

### 1.8 依赖与前置条件

- demo 仓库：`https://gitcode.com/openlibing-test/repesync`（main 分支 workflow：`comments: ['sync']`、`uses: openlibing/pr-sync-action@feat-pr-sync-trigger-events`、指定 APIG 地址）。
- 平台前置：GitCode 仓库录入、黄区 CodeHub 映射、双方仓库成员角色（`openLibingCI` / `p_LibingCI`）已配置。
- 环境：issue 517 已部署（用户确认）；APIG 网关 OIDC 可用。
- 账号/权限：可操作 demo 仓库 PR 与评论的 GitCode 账号；加密区黄区页面的只读观测账号（P-04）。
- 观测能力：GitCode PR 标签与插件任务结果页；黄区流水线记录/同步结果由人工观测；开发协助提供 MQS/日志佐证（P-01/P-02）。
