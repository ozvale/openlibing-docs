# Webhook 接入 APIG 并下线废弃 hooks 接口 — 归档

## 关联

- 业务 PR #143（阶段 1 迁移上线）：https://gitcode.com/openlibing/openlibing-coderepo/pull/143
- 业务 PR #153（阶段 3 移除废弃 hooks 接口）：https://gitcode.com/openlibing/openlibing-coderepo/pull/153
  - 提交 `d89bff5`：`refactor(webhook): remove deprecated legacy webhook endpoints`
- docs PR：本 PR（合并本归档文档）

## 交付历程

- #143（阶段 1）：新增 3 个 APIG 专用接口 `/apig/webhook/{platform}/repo`，抽取公共处理方法，新增
  `logWebhookSource` 流量来源日志；`RepoServiceImpl` 拆分 `autoSetCoderepoWebHook` 并新增
  `migrateLegacyCoderepoWebhooks` / `updateRepoWebhookUrl` / `buildWebhookUrlUpdateBody`；
  `RepoWebhook` 新增 `config` + `RepoWebhookConfig`；`refreshWebhookHandler` 定时迁移存量 webhook URL 到不含
  repoId 的 APIG 链接；5 个旧接口保留并增加来源日志用于观察期统计。
- #153（阶段 3）：观察期通过后删除 5 个旧直连 `/webhookEvent/hooks/*` 接口（gitcode / gitee / github，含 2 个
  `{repoId}` 兼容路径）及相关无用方法、多余引用；`WebHookEventControllerTest` 旧接口用例替换为 APIG 入口用例。

## 用户自测反馈

- 无（阶段 3 为纯删除 + 用例替换，编译与 pre-commit 通过后直接交付）。

## 最终验证

- 编译：`mvn` 编译通过。
- 单元测试：`WebHookEventControllerTest` 通过（apig 入口成功 / 权限校验失败用例）。
- pre-commit 检查通过（spotless / checkstyle / spotbugs / pmd / gitleaks）。

## 设计偏差与取舍

- 阶段 3 前，需求设计文档中 APIG 路径曾记为 `/webhookEvent/apig/hooks/{platform}`；最终实施统一为
  `/apig/webhook/{platform}/repo`（见 `proposal.md` / `design.md` 的最终验收与架构章节），以实际代码为准。

## 可复用经验

- webhook 类接口迁移到 APIG 采用「分阶段：迁移上线 → 观察 → 下线旧接口」策略，通过流量来源日志
  （apig / direct / legacy-with-repoId）100% 量化迁移进度后再删旧接口，避免事件丢失。
- 无其他需沉淀到 ai_memory 的经验。

## 归档日期

2026-08-29