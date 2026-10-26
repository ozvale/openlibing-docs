# 安全合规评分看板接口 · tasks.md

> 日期：2026-09-23
> 前置阅读：proposal.md（口径）、design.md（字段级设计）
> 说明：本期为接口设计交接稿，编码由后续 agent 执行。开发前请先确认 E1~E5 依赖项状态。

---

## Java 侧（openlibing-ops，后续开发 agent）

- [ ] T1 新建分支（基于主仓 master 最新，Windows 分支名禁止斜杠，如 `feat-security-score-dashboard-api`）
- [ ] T2 detail 通道接入：DetailCommonEnum 加 3 枚举 + 3 个 Req（继承 DetailReq）@JsonSubTypes 注册 + 3 个 DetailService 实现 + repoDetailFactory 注册
  - [ ] security-community-summary（社区汇总）
  - [ ] security-project-list（开源项目清单）
  - [ ] security-repo-list（代码仓清单，含窗口函数"每仓 ≤ statDate 最新批次"）
- [ ] T3 排序白名单：light / scoreRule / scoreAll 加入 SORT_FIELD_MAPPING（漏配=排序无响应）
- [ ] T4 独立接口 ×3：POST /security/repo-summary、/security/repo-metric-detail、/security/metric-detail-html
  - [ ] 4(2) 指标明细：scan_score 18 得分列行转列，JOIN metric_conf 全表（不过滤 status），score null 原样返回
  - [ ] 5：查 metric_conf.template_content，渲染逻辑后置，html 可先返回空/模版原文
- [ ] T5 抽公共 MyBatis SQL 片段："每仓 ≤ statDate 最新批次"（T2 接口 3 / T4 的 4(1) / 4(2) 共用，口径不得各自实现）
- [ ] T6 时间入参：只取 req.getStartDate() 作为 statDate；严禁使用 endDate/startTime/endTime（TimeReq.setStartDate 有 setter 副作用）
- [ ] T7 模糊查询统一 UPPER 归一（Doris LIKE 大小写敏感）
- [ ] T8 单测：至少覆盖 ①statDate 当天/历史/不传 ②light 排序默认红黄绿 ③score null 透传 ④community_conf 层级展开（Ascend 顶层含子社区仓库）
- [ ] T9 服务级验证：启动服务跑改动接口，响应结构 + 字段值 + 与 Doris 表交叉对账（design.md §6 对账表），结果发布 Issue 评论
- [ ] T10 提交 commit 前经用户确认改动清单与 commit 信息

## ETL/表侧（需求方，编码启动的前置依赖）

- [ ] E1 建 dm_rd_efc_security_project_score（DDL 已在 docs/0912/design.md §7.1.1）— **未建**
- [ ] E2 D6 改造：按 community_conf 额外产出顶层社区快照行（Ascend = 跨子社区仓库重算）
- [ ] E3 建 dm_rd_efc_security_community_conf + 录数据（5 顶层 + 4 Ascend 子社区；booskit / Ascend 顶层 project_id 待定）
- [ ] E4 metric_conf 加 template_content 字段 + 模版手动录入
- [ ] E5 D4 跑批产出 scan_score 数据（当前 0 行；前端联调依赖）

## 前端（并行）

- [ ] F1 按 design.md §3 字段定义开发 4 个页面，可先行 mock 联调
- [ ] F2 空值语义：score null → NA；light null → 置灰；0 分是有效得分不转 NA

## 交付闸门（沿用工作流）

- 编码完成 → 用户自测确认 → 业务 PR（ai-assisted 标签 + 关联 Issue）→ 用户触发归档
- 业务仓 PR 不带 spec 文件；本目录文档通过 openlibing-docs PR 归档
