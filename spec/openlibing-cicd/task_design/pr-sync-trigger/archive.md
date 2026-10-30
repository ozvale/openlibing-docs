# PR 同步触发接口与失败信息展示 — 归档

## 关联

- FE 需求：【黄蓝协同】黄蓝协同新增映射实时校验及失败信息展示功能
- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/234
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pull/584

## 交付历程

- commit `86f0bf27e`: feat(cross-region): PR 同步触发接口主体（Controller/Service/DTO/VO/单测 +7）
- commit `682e1d793`: refactor(cross-region): gpi upsert 查询键对齐 compileTrigger（全局 id+平台）
- commit `24debec55`: 修改字段名称
- commit `4c9cb08f6`: chore: spotless google-java-format（补跑 pre-commit 欠下的格式化）
- commit `e8e0fba67` / `6f12de211`: pipeline-status 新增扩展字段（错误码/构建链接回写）
- commit `04b9c9cbe`: chore: merge release_20260923_iter2（解决 PR #584 的 db.changelog.xml 冲突）

## 用户自测反馈

- PR 创建后发现与 release_20260923_iter2 存在 db.changelog.xml 冲突 → merge 目标分支解决：保留目标分支 secoption 变更集（20260904/20260907/20260915），追加本需求变更集（20260908），merge commit `04b9c9cbe`

## 最终验证

- 单元测试：CrossRegionServiceImplTest 73 用例全部通过（Failures 0 / Errors 0）
- CI pre-commit（增量模式）：通用钩子 / gitleaks / spotless / checkstyle / spotbugs / pmd 全部 Passed
- spotless:check 本地复验通过；PR mergeable=True

## 设计偏差与取舍

- MQS 消息简化：不传 title、description 固定空串、账号只用统一 account 字段（不建 gitcode_/gitee_/github_ 平台账号组）——参考 coderepo buildMessage 对齐后按评审收敛
- 触发接口 req_type 取 compile（对齐评论触发编译流程）而非 open
- spec 文档未在 Phase 1 落盘（压缩流程执行，本 archive 为补录归档）

## 可复用经验

- 见 [ai_memory.md](../../ai_memory.md)：Liquibase 已执行变更集禁改规则、GitCode CLI 本机路径、pre-commit Windows 环境要点

## 归档日期

2026-09-22

---

# 演进归档（2026-10-29）— 幂等加固 / compile 降级 / 检视闭环（PR !641）

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pull/641
- 关联 Issue: #312（0929-003 维度限流）、#314（0929-016 msgId 绑定）、#315（0929-017 幂等保护）、#316（0929-018 令牌收紧）——四项安全整改已全部实现
- 分支: `feat/pr-sync-yellow-blue`（基于 release_20261029_iter2 对 pr-sync 全量提交重建，并同步 develop）

## 本轮交付

- pr-sync 全量提交（10 个）在 release 基线重建并合入 `develop_202610_iter2`
- commit `55bd4784b`: compile 降级——首次同步（无历史记录或 MR 状态未回写 WAIT_START）发 compile 全量同步，重触发（已回写）发 update
- commit `a874769c5`: 检视修复——幂等判定先于限流（窗口内重复触发走幂等 graceful 而非硬拒）、MQS 发送失败释放限流占位、`WAIT_START` 落库与判据同源（枚举 getCode）、DTO 死字段 gitUrl 清理
- commit `95969cc5d`: 幂等命中增加 msgId 前置条件（ozvale 检视）——无 msgId 记录（/compile、Gitee 标签链路写入）不再被误命中返回假 SEND_OK，改走打断重建并降级 compile
- commit `e4ce211b5`: CI google-java-format 格式化对齐

## 安全整改关联（安全 issue 闭环）

- #315（0929-017）：幂等键——窗口内重复触发返回已有实例（msgId），不重复打断/建记录/发 MQS
- #314（0929-016）：msgId 落库 + 回调强校验（不一致拒绝），`yellow_region_pipeline` 新增 `msg_id` 列（liquibase）；extension/mrLink 格式校验
- #312（0929-003）：触发接口维度限流（Redis SET NX EX）+ 限流器故障 fail-open + 发送失败释放占位
- #316（0929-018）：`PrSyncTriggerReqDTO` 移除 `accessToken`/`gitUrl` 字段，MQS 消息不携带调用方令牌

## 用户自测反馈

- 黄区回调 `extension` 为 JSON primitive 时被蓝区校验拒绝（`Invalid callback payload`）→ 定性为黄区侧报文格式待对齐（合并前置项）

## 最终验证

- `CrossRegionServiceImplTest` 90 用例全绿（触发/msgId 落库/compile 降级/幂等命中/死记录重建/限流拒绝/fail-open/回调 msgId 校验/复合状态计算全场景）
- AI 检视 8 条全部修复并 resolve；人工评审 liudongfang `/lgtm`；CI 全绿

## 设计偏差与取舍

- 幂等语义保持 0929-017 设计：窗口内重复触发返回已有实例不发新消息（评审提出的新提交漏同步风险已确认为设计取舍，新提交由 MR 更新事件在窗口过期后触发）
- 幂等命中增加 msgId 前置条件：无 msgId 记录（compile/Gitee 标签链路写入）视为不可复用，降级 compile 全量同步

## 可复用经验

- 见 [ai_memory.md](../../ai_memory.md)：长生命周期分支并行合并静默回退、CI/本地 spotless 行为分歧处置

## 归档日期

2026-10-29
