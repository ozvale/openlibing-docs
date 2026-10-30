# 【安全】access_token 以 URL 明文拼接整改（#335/#361）— 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/335 、https://gitcode.com/openlibing/openlibing-cicd/issues/361
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pull/640
- 报告批次: 1010-002（CWE-598 敏感信息查询串传输 + CWE-532 日志泄露）
- 人工评审: liudongfang `/lgtm`、ozvale（2 条意见已闭环）

## 交付历程

- commit `d8c8c75d3`: fix(security) — 黄蓝协同与 PR 管理模块 27 处出站调用 `access_token` 从 URL query/form 统一改为 `PRIVATE-TOKEN` 认证头（与 !634 方案对齐；!634 已覆盖 5 处未触碰避免冲突）；PrServiceImplTest/PrCommentServiceImplTest mock 迁移 HttpRequest 链式
- commit `c0267205c`: fix(cross-region) — 连带修复：GitCode webhook 误用 `project.name`（项目显示名）作为仓库坐标，改为从 `project.git_http_url` 经 RepoUrlParser 解析（7 处调用点）
- commit `c8f423a43`: fix(security) — ozvale 检视修复：LabelServiceImpl/WebhookMigrationHelper/WebhookRefreshService 3 处残留收口（该 3 处此前核对结论与仓库现状不符）；PrCommentServiceImplTest 三条主路径补「URL 无令牌 + PRIVATE-TOKEN 头携带令牌」断言
- commit `bb3f79daa` / `e5fb65ba1` / `7353666d8`: CI google-java-format 格式化对齐 + release 基线合并（#332 webhook 下线的 modify/delete 冲突按删除解决）

## 关键验证

- Gitee PRIVATE-TOKEN 兼容性实测：真实令牌对 `GET /api/v5/user` 分别以 access_token 参数 / PRIVATE-TOKEN 头 / Authorization 头调用，三者均 200 且返回账号信息——统一 PRIVATE-TOKEN 方案在 Gitee 可用（响应检视 #196589491）
- 本 PR 实际收口：CrossRegionServiceImpl(2)、PrServiceImpl(19)、PrCommentServiceImpl(4)、PrLabelServiceImpl(1)、PipelineServiceImpl PR 标签方法(2)，共 28 处调用点（含 LabelServiceImpl，本次 c8f423a43 收口）
- 剩余命中（非本 PR 范围，需对应归属方跟进）：
  - !634 已覆盖 5 处：RepoServiceImpl(3)/BranchServiceImpl(1)/PipelineServiceImpl#queryPrTitle(1)
  - 随 #332 webhook 下线删除：WebhookRefreshService、WebhookMigrationHelper
- 豁免说明（#361）：`XxlJobHandler.java:806` 的 `invitation_token` 为上游 GitCode 官方接口契约要求，非本平台令牌，红线复扫（7.1.11）时引用该豁免，不重复开单
- CI 全绿：CheckStyle / SpotBugs / PMD / pre-commit 全部 Passed

## 用户自测反馈

- ozvale 检视 2 条（LabelServiceImpl 等 3 处残留与核对结论不符；测试缺 token 断言）→ commit `c8f423a43` 修复并回复 resolve
- #332 webhook 下线导致的 modify/delete 冲突 → 按删除解决（该功能已废弃，token 修改作废）

## 设计偏差与取舍

- 加密头选型统一 PRIVATE-TOKEN（而非 Gitee 文档的 Authorization: token）——实测 Gitee v5 兼容三种写法，与仓内 17 处先例对齐
- WebhookMigrationHelper / WebhookRefreshService 的 token 修复随后被 #332 下线覆盖（先修复后删除，无浪费——修复期间未合入）
- 仓库坐标解析复用既有 `RepoUrlParser`（与 coderepo/codecheck 同源逻辑），未引入新工具类

## 可复用经验

- 见 [ai_memory.md](../../ai_memory.md)：CI/本地 spotless 行为分歧处置、gitcode.cmd 传参禁忌

## 归档日期

2026-10-29
