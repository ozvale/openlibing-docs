# 安全合规评分看板接口 · design.md

> 日期：2026-09-23
> 前置阅读：proposal.md（口径拍板记录）、`docs/0912/design.md` v4.3（评分体系与 Doris 分层设计）
> 适用对象：后续执行开发的 agent / 前端

---

## 1. 数据链路与职责边界

```text
DolphinScheduler ETL（需求方维护）              Java（openlibing-ops，后续开发 agent）
────────────────────────────────────          ─────────────────────────────────────
D4: dwi 明细 → dm_rd_efc_security_scan_score    接口 1/2: 查 project_score 快照（纯查询）
    （仓库×批次 粒度，18 指标得分列 +               接口 3/4(1)/4(2): 查 scan_score
     score_rule_weighted / score_all_weighted /      "每仓 ≤ statDate 最新批次"窗口取数
     rule_weight_sum / all_weight_sum / rule_light）（简单取数 SQL，无业务计算）
D6: scan_score → dm_rd_efc_security_project_score  接口 5: 查 metric_conf.template_content
    （project×stat_date 快照；改造点见 §5-E2）       freemarker 渲染逻辑【后置】
配置表: dm_rd_efc_security_community_conf（新建，§2）
```

**核心原则：分数/亮灯/聚合的权威公式只在 ETL（D4/D6）一处实现，Java 是纯视图层，不做任何业务计算。**

口径耦合点（唯一）：接口 3/4 的"每仓 ≤ statDate 最新批次"取数 SQL 与 D6 的"每仓最新批次"聚合口径同源；将来若时间口径调整，两处需同步修改。

---

## 2. 社区配置表（新建）

```sql
CREATE TABLE IF NOT EXISTS dm_rd_efc_security_community_conf (
    project_id          INT          NOT NULL COMMENT '社区ID，主键，取 sdi_project_info.project_id（社区与project同实体）',
    community_name      VARCHAR(64)  NOT NULL COMMENT '社区展示名：openEuler/openGauss/Ascend/openUBMC/booskit（及Ascend子社区名）',
    parent_project_id   INT          NOT NULL DEFAULT 0 COMMENT '父社区ID，顶层=0；Ascend子社区(MindIE等)填Ascend的project_id',
    has_sub_community   TINYINT      NOT NULL DEFAULT 0 COMMENT '下层是否还有社区（开源项目层）：1=是(Ascend) 0=否',
    display_order       INT          NOT NULL DEFAULT 0 COMMENT '展示顺序',
    status              VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT 'active/disabled，便于后续引入新社区',
    etl_time            DATETIME              COMMENT 'ETL时间'
) ENGINE=OLAP
UNIQUE KEY(project_id)
COMMENT '安全合规评分看板·社区配置表（手动维护）'
DISTRIBUTED BY HASH(project_id) BUCKETS 1;
```

数据要求（需求方录入，O1）：

- 5 条顶层记录（parent=0）：openEuler / openGauss / Ascend / openUBMC / booskit，其中 Ascend `has_sub_community=1`
- Ascend 子社区记录（parent=Ascend.project_id）：MindCluster / MindIE / MindSpeed / MindStudio
- ⚠️ booskit 在 `sdi_project_info` 中无记录，需先明确其对应的 project_id；Ascend 顶层社区挂哪个 project_id 亦需录入时指定

`metric_conf` 新增模版字段（需求方执行，O3）：

```sql
ALTER TABLE dm_rd_efc_security_metric_conf
    ADD COLUMN template_content TEXT COMMENT 'freemarker模版内容，指标达标明细HTML渲染（手动录入）';
```

---

## 3. 接口设计（字段级）

### 3.0 统一约定

| 项            | 约定                                                                                                                                                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 列表通道      | `POST /common/detail`，DetailReq.category 多态路由（DetailCommonEnum + @JsonSubTypes + repoDetailFactory，同既有 details 模式）                                                                                            |
| 详情通道      | 独立 POST 接口，返回 `Result<T>`                                                                                                                                                                                           |
| 时间入参      | **复用 TimeReq.startDate 作为 statDate（LocalDate，`yyyy-MM-dd`）**；endDate / startTime / endTime 一律不使用。⚠️ TimeReq.setStartDate 有副作用（同步置 startTime=00:00），实现只取 `req.getStartDate()`，不得触碰其余字段 |
| statDate 语义 | 见 proposal.md §3.3：快照日。不传 = 最新                                                                                                                                                                                   |
| light         | 数值 1绿/2黄/3红；null = 未扫/全NA，前端置灰                                                                                                                                                                               |
| score         | DECIMAL；null → 前端 NA；0 是有效得分                                                                                                                                                                                      |
| 默认排序      | `light DESC, scoreRule DESC`                                                                                                                                                                                               |
| 模糊查询      | Doris LIKE 大小写敏感，社区/项目/仓库名模糊统一 `UPPER(...) LIKE UPPER('%kw%')`                                                                                                                                            |

### 3.1 接口 1 · 社区汇总

`POST /common/detail`，`category = security-community-summary`

入参（Req 继承 DetailReq）：

| 字段                                   | 类型      | 必填 | 说明                                                              |
| -------------------------------------- | --------- | ---- | ----------------------------------------------------------------- |
| startDate                              | LocalDate | 否   | statDate；不传 = project_score 最新 stat_date                     |
| communityName                          | String    | 否   | 社区名模糊查询（UPPER 归一）                                      |
| page / pageSize / sortField / sortRule | -         | 否   | 继承 DetailReq；sortField 支持 `light` / `scoreRule` / `scoreAll` |

出参（PageResult，行结构）：

| 字段          | 类型       | 说明                   | 来源                          |
| ------------- | ---------- | ---------------------- | ----------------------------- |
| communityId   | Integer    | 社区 project_id        | community_conf.project_id     |
| communityName | String     | 社区展示名             | community_conf.community_name |
| light         | Integer    | 1/2/3，null=无快照     | project_score.rule_light      |
| scoreRule     | BigDecimal | 规则项得分（0-10）     | project_score.score_rule      |
| scoreAll      | BigDecimal | 全部得分（仅展示）     | project_score.score_all       |
| repoCount     | Integer    | 应扫仓库数（含无分仓） | project_score.repo_count      |
| nullRepoCount | Integer    | 无分仓数               | project_score.null_repo_count |

数据源：`dm_rd_efc_security_project_score`（stat_date = startDate）INNER JOIN `community_conf`（parent=0, status=active, ORDER BY display_order）。
Ascend 行由 D6 落快照（§5-E2），Java 无需感知其特殊聚合。

### 3.2 接口 2 · 开源项目清单（仅 Ascend）

`POST /common/detail`，`category = security-project-list`

入参：`startDate`、`communityId`（Integer，必填，前端传 Ascend 的 project_id）、`projectName`（模糊）、分页排序同上。

出参行：

| 字段                                                     | 类型    | 说明                                          |
| -------------------------------------------------------- | ------- | --------------------------------------------- |
| projectId                                                | Integer | 子社区 project_id                             |
| projectName                                              | String  | 子社区展示名（community_conf.community_name） |
| light / scoreRule / scoreAll / repoCount / nullRepoCount | -       | 同接口 1，来自该子社区的 project_score 快照   |

数据源：`community_conf`（parent_project_id = communityId）JOIN `project_score`（stat_date=startDate）。

### 3.3 接口 3 · 代码仓清单

`POST /common/detail`，`category = security-repo-list`

入参：

| 字段            | 类型      | 必填   | 说明                                                                         |
| --------------- | --------- | ------ | ---------------------------------------------------------------------------- |
| startDate       | LocalDate | 否     | statDate                                                                     |
| communityId     | Integer   | 二选一 | 社区筛选：经 community_conf 展开为 project 集合（Ascend 顶层含其所有子社区） |
| projectId       | Integer   | 二选一 | 直接按 project 过滤                                                          |
| repoName        | String    | 否     | 仓库名/URL 模糊查询（UPPER 归一）                                            |
| light           | Integer   | 否     | 1/2/3 亮灯筛选                                                               |
| sortField       | String    | 否     | `light` / `scoreRule` / `scoreAll`                                           |
| sortRule        | String    | 否     | asc / desc                                                                   |
| page / pageSize | -         | 否     | 继承 DetailReq                                                               |

出参行：

| 字段      | 类型       | 说明                         | 来源                           |
| --------- | ---------- | ---------------------------- | ------------------------------ |
| repoId    | Long       |                              | operate_conf.repo_id           |
| repoName  | String     |                              | sdi_repo_info.repo_name        |
| repoUrl   | String     |                              | sdi_repo_info.repo_url         |
| scoreRule | BigDecimal | null=未扫/全NA               | scan_score.score_rule_weighted |
| scoreAll  | BigDecimal | 同上                         | scan_score.score_all_weighted  |
| light     | Integer    | 1/2/3，null=未扫             | scan_score.rule_light          |
| scanTime  | DateTime   | 该仓实际批次时间（各仓不同） | scan_score.scan_time           |

数据源与取数逻辑：

```sql
-- 全集 = 应扫（proposal §3.4）；批次 = 每仓 ≤ statDate 最新（proposal §3.3）
repo 全集: sdi_rd_efc_repo_operate_conf WHERE is_operated = 1
  [AND project_id IN (community_conf 展开的 project 集合)]  -- communityId 筛选
LEFT JOIN (
    SELECT * FROM (
        SELECT t.*, ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC) rn
        FROM dm_rd_efc_security_scan_score t
        WHERE scan_time <= {statDate} 23:59:59   -- 不传 statDate 则不设上界
    ) WHERE rn = 1
)
-- 不传 statDate 与传"表内最新日期"结果等价；排序默认 light DESC, scoreRule DESC
```

### 3.4 接口 4(1) · 代码仓概要（详情页头部 KPI）

独立 `POST /security/repo-summary`

入参：`repoId`（Long，必填）、`startDate`（LocalDate，否）
出参（Result<T>，单对象）：

| 字段                        | 类型       | 说明         |
| --------------------------- | ---------- | ------------ |
| repoId / repoName / repoUrl | -          | 仓库基础信息 |
| scoreRule / scoreAll        | BigDecimal | 同接口 3     |
| light                       | Integer    | 同接口 3     |
| scanTime                    | DateTime   | 该仓批次时间 |

取数 = 接口 3 的单仓版（同一"每仓 ≤ statDate 最新批次"口径）。

### 3.5 接口 4(2) · 代码仓指标明细

独立 `POST /security/repo-metric-detail`

入参：`repoId`（必填）、`startDate`（否）、`metricType`（String，否，`rule` / `advice` 指标类型筛选）

出参（Result<List<T>>，18 行，按 metric_conf.display_order）：

| 字段         | 类型       | 说明                                                                                  |
| ------------ | ---------- | ------------------------------------------------------------------------------------- |
| metricCode   | String     | 指标码（如 VULNS）                                                                    |
| metricName   | String     | 指标名（中文）                                                                        |
| metricType   | String     | rule（规则类）/ advice（建议类），来源 metric_conf                                    |
| weight       | BigDecimal | 权重，metric_conf.weight                                                              |
| score        | BigDecimal | **null = NA**（含 deferred 恒 NULL、全 NA、未扫）；来源 scan_score 行的对应指标得分列 |
| scanTime     | DateTime   | 该仓批次时间                                                                          |
| contribution | BigDecimal | 对满分贡献；**计算逻辑后置，本期可返回 null**（预留字段）                             |

取数：定位批次（同 4(1)）→ scan_score 18 个指标得分列行转列，与 metric_conf 全表（18 项，含 deferred）按 metric_code 关联展开。**不按 status 过滤**。

### 3.6 接口 5 · 指标达标明细 HTML（渲染逻辑后置）

独立 `POST /security/metric-detail-html`

入参：`metricCode`（String，必填）、`repoId`（Long，必填）、`startDate`（否）

出参实体（Result<T>，正常实体返回，html 为字段）：

| 字段       | 类型   | 说明                                           |
| ---------- | ------ | ---------------------------------------------- |
| metricCode | String |                                                |
| metricName | String |                                                |
| html       | String | freemarker 渲染后的明细 HTML 片段，前端 v-html |

本期实现边界：

- 查 `metric_conf.template_content`（O3 手动录入）；
- 渲染数据 model 约定 = 定位批次后取 dwi 明细表数据组装；**仅靠 dwi 明细表字段不全，需按指标关联 sdi 层表补全展示字段**（已校验清单见 §3.6.1）；
- **渲染逻辑整体后置**：本期接口字段定型，html 可先返回模版原文或空串，保证前端可先行开发。

#### 3.6.1 明细页数据来源（按指标，随真实数据校验逐个补充）

以指标 7 CODE_REVIEW 为例（2026-09-27 真实数据校验结论，校验页 `docs/0912/明细数据设计freemarker模版/06-code-review-real-data.html`）：

| 表                            | 层  | 提供字段                                            | 关联键                                     |
| ----------------------------- | --- | --------------------------------------------------- | ------------------------------------------ |
| dwi_rd_efc_security_pr_scan   | dwi | score、纳入统计数、已评审数、未评审 PR 及其合入时间 | repo_id + 批次（每仓 ≤ statDate 最新批次） |
| sdi_rd_efc_pr_review_reviewer | sdi | 评审人、评审命令（is_effective_review=1）           | repo_id + pr_number                        |
| sdi_repo_pull_request_info    | sdi | PR 标题、创建人、合入时间、PR 链接                  | repo_id + number                           |

关联校验中已发现的数据链路问题（明细页对应字段只能留「—」的根因，待数据链路侧排查）：

1. **PR 维表疑似停更**：raw_pull_request_gitcode / sdi_repo_pull_request_info 全表最新数据停在 2026-06-28；
2. **编号体系不一致**：msmodeling（repo_id 401661）维表 PR 最大 469，扫描表为 734~928，满分仓 30 个 PR 的标题/创建人/合入时间全部无法关联；评审明细表编号与扫描表一致且数据新鲜（最新 etl_time 2026-09-26）；
3. cann-recipes-spatial-intelligence（repo_id 401471）维表同步停在 2026-05-25，#51~#57 缺失；
4. 汇总卡「剔除机器人创建」无任何表字段支撑，暂展示「—」；
5. PR 链接兜底：维表 url 缺失时按 `repo_url + /merge_requests/<number>` 拼接（维表实际链接格式为 /merge_requests/，非 /pulls/）。

其余 17 个指标的明细表 + 关联表清单随校验进度在本节逐个补充。

---

## 4. 涉及改动点清单（Java 侧，供开发 agent 排期）

| #   | 改动                                                                                                                               | 位置（沿用既有模式） |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| J1  | DetailCommonEnum 新增 3 个枚举：SECURITY_COMMUNITY_SUMMARY / SECURITY_PROJECT_LIST / SECURITY_REPO_LIST                            | common detail 通道   |
| J2  | 3 个 Req 类（继承 DetailReq）+ @JsonSubTypes 注册                                                                                  | 请求模型             |
| J3  | 3 个 DetailService 实现类 + repoDetailFactory 注册 + 对应 Mapper/SQL                                                               | 业务与数据访问       |
| J4  | ⚠️ 排序字段白名单：`light` / `scoreRule` / `scoreAll` 必须加入 SORT_FIELD_MAPPING，否则前端排序无响应（历史踩坑记录）              | 排序映射             |
| J5  | 独立接口 3 个：/security/repo-summary、/security/repo-metric-detail、/security/metric-detail-html（Controller + Service + Mapper） | 新模块               |
| J6  | "每仓 ≤ statDate 最新批次"通用 SQL 片段（接口 3/4(1)/4(2) 共用，MyBatis sql 片段抽公共）                                           | Mapper               |

## 5. 依赖项清单（ETL/表侧，需求方）

| #   | 事项                                                                                                                                                                                                                                        | 状态       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| E1  | 建 `dm_rd_efc_security_project_score`（DDL 见 docs/0912/design.md §7.1.1）                                                                                                                                                                  | **未建表** |
| E2  | D6 脚本改造：在"按 project_id 聚合"之外，按 community_conf 额外产出**顶层社区行**——Ascend 行 = 名下所有仓库重算（AVG 有分仓 score_rule_weighted / score_all_weighted，MAX rule_light，repo_count / null_repo_count 求和）                   | 待改       |
| E3  | 建 `dm_rd_efc_security_community_conf`（§2 DDL）+ 录入 5 顶层 + 4 Ascend 子社区                                                                                                                                                             | 待建       |
| E4  | metric_conf 加 `template_content` + 模版录入                                                                                                                                                                                                | 待加       |
| E5  | D4 跑批产出 scan_score 数据                                                                                                                                                                                                                 | 0 行，待跑 |
| E6  | PR 采集链路排查（影响 CODE_REVIEW 明细页标题/创建人/合入时间）：① raw_pull_request_gitcode / sdi_repo_pull_request_info 停更（最新 2026-06-28）；② msmodeling 维表 PR 编号最大 469 与扫描表 734~928 不一致（疑数据源平台不同）。详见 §3.6.1 | 待排查     |

## 6. ETL 与接口的对账关系（验收用）

| 对账项     | 规则                                                                       |
| ---------- | -------------------------------------------------------------------------- |
| 仓库数     | 接口 1 社区行 repoCount == 接口 3 该社区（不传 light/repoName 筛选）总行数 |
| 社区分数   | 接口 1 scoreRule == 接口 3 该社区有分仓 scoreRule 的平均（无分仓剔除）     |
| 社区亮灯   | 接口 1 light == 接口 3 该社区 light 的 MAX（null 不计）                    |
| 指标行数   | 接口 4(2) 行数 == metric_conf 全表行数（18）                               |
| 最新一致性 | 不传 startDate 的结果 == 传"表内最新 stat_date"的结果                      |
