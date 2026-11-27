# UT 覆盖率历史扫描记录 — 需求提案（后端 + 插件范围）

## 需求背景

分支管理 UT 覆盖率只展示最新一次扫描结果；历史数据已入库（code_ut_record）但无查看入口；流水线插件仅输出 result 无结果链接，历史流水线回看时指标对不上当次构建；扫描记录持续累积无清理机制。

评审对齐（2026-11-18）后明确实施分工：**本任务实施范围 = 后端 openlibing-coderepo + 插件 upload-ut-action；前端 openlibing-web 由看板组另行实施**。

关联业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/300

## 功能描述

- 历史扫描记录列表接口：按分支扫描时间倒序分页，含 retentionDays 下发；不返回 commitId（对齐点②）
- 详情接口扩展：recordId 定位（优先级 recordId > pipelineRunId > 最新一条兜底），查无记录返回统一文案（区分"处理中"与"已清理"两态）；仓库定位支持 repoId 与 repoUrlLike+platforms 双模式（后期演进，见 design.md §9）
- 上报接口响应扩展：recordId 受理时预生成 + reportUrl 直返（对齐点①，不再新增查询接口）；链接定位参数为 projectId + platforms + repoUrlLike（后期演进：由 repoId 改为 platforms+repoUrlLike 组合，仓库删除重建后链接长期有效）
- 定时清理：xxl-job 按 retention-days 分批删 DB，连带清理 OBS 原始报告 JSON（对齐点③，方案 A 级联删除）
- 插件：回调响应直接读取 recordId/reportUrl 并 setOutput('report_url')，无查询接口、无重试

## 不做什么

- openlibing-web 前端页面与 URL 适配（看板组负责）
- UT 原始报告下载功能（独立任务 ut-original-report-download；本次仅落其依赖的 original_report_obs_url 双写列，为 OBS 级联清理提供定位依据）
- 分支列表指标更新时间（utSyncedAt / staticAlertCountSyncedAt）透出：属独立任务 branch-metric-update-time，不在本提案范围

## 验收标准（后端 + 插件部分，已全部交付）

- [x] 历史列表接口按扫描时间倒序分页返回，含失败记录与 retentionDays
- [x] 详情接口 recordId 精确定位；已清理记录返回统一文案（区分处理中/已清理两态）
- [x] 详情接口兼容 repoUrlLike+platforms 定位（后期演进 !363），跨平台同名仓由 platforms 消除歧义
- [x] 插件每次流水线输出 report_url（上报响应直返，无额外查询），指向当次记录且仓库重建后仍有效（!363）
- [x] 超保留期记录及其 OBS JSON 被自动清理（NULL 跳过、失败告警不回滚、obsFailed>0 时 job 标记失败供运维感知）；repo_branch 最新指标快照不受影响
- [x] 旧链接（pipelineRunId）与旧版插件在过渡期行为零变化

## 影响范围

- openlibing-coderepo：db.changelog（索引 + original_report_obs_url 列）、CodeUtRecordEntity、UtCoverage Mapper/Service/Controller、XxlJobHandler、application.yml 配置
- upload-ut-action：index.js（回调响应消费 + setOutput）、单测

## 落地与演进

- 主设计随 PR !345 合入 master；后期演进三轮：!345（清理 UNION 修复 + 详情行覆盖率回显）、!355（详情接口透出 retentionDays）、!363（链接 platforms+repoUrlLike 定位改造），详见 design.md §9 演进记录。
