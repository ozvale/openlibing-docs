# UT 覆盖率历史扫描记录 — 实现任务（后端 + 插件）

## 进度: 12/12 complete

## 准备

- [x] T0 分支创建：openlibing-coderepo `feat-ut-coverage-history`（fetch 主仓后基于 master）；upload-ut-action `feat-ut-history-link`（基于 main）

## openlibing-coderepo（后端）

- [x] T1 db.changelog：`idx_ut_record_detection_completed_at` 索引（注：`original_report_obs_url` 列已随原始报告下载功能在 master 落地，无需再加列）
- [x] T2 实体/Mapper：selectHistoryPage / countHistory / selectMetaById（均不含明细大字段）+ selectEarliestDetectionTime / selectExpiredForCleanup / deleteExpiredByIds（清理专用）
- [x] T3 历史列表接口：UT_COVERAGE_HISTORY UrlConstant、verifyPermissionsByProduct 越权校验、retentionDays 下发、含失败记录、不返回 commitId
- [x] T4 file-detail 扩展：locateRecord 优先级 recordId > pipelineRunId > 最新一条兜底 + 归属校验（gitUrl 等价集合 + 分支一致）防跨仓枚举 + UT_COVERAGE_RECORD_NOT_FOUND 统一文案；出参含 recordId/commitId
- [x] T5 上报接口响应扩展：acceptReport 受理预处理（recordId 预生成回填请求体随 MQ 透传 + buildReportUrl 按 projectId/repoId/branchName/recordId/utCoverageDetail 拼装，域名复用 Nacos 既有 openlibing.domain）；消费侧 resolveRecordId 优先用透传 ID，存量消息降级本地生成
- [x] T6 上报入库双写 originalReportObsUrl（master 已有，失败记录保持 NULL 口径不变）
- [x] T7 XxlJobHandler utCoverageCleanupHandler → UtCoverageCleanupService：分批删 DB（单批 500）+ OBS 级联（每批删前收集 URL → NULL 跳过 → 桶/前缀白名单校验 → 逐对象二次时间校验 → 失败告警不回滚）+ 游标守卫 + 执行摘要
- [x] T8 配置：ut.coverage.retention-days=90 / cleanup-batch-size=500（application.yaml，Nacos 可覆盖）；域名复用 Nacos 既有 openlibing.domain，不新增配置项
- [x] T9 单测：locateRecord 优先级矩阵（7 例）、清理分批边界（7 例：关闭态/NULL 跳过/失败告警不回滚/多批推进/零行守卫/二次校验/create_time 兜底）、history 分页（3 例）、history DTO 校验（6 例）、Controller 适配（4 例）——共 29 例全过
- [x] T11 过程态区分（评审反馈补充）：recordId 未命中解码雪花时间戳，≤5 分钟窗口返回「处理中，请稍后刷新」（RECORD_PENDING_MESSAGE），超窗口返回「不存在/已清理」终态（isRecordPending 启发式 + 2 例单测）；design.md §3.2/§3.3/§6、design-review 风险表、原型新增视图5（⏳ 处理中态）同步

## upload-ut-action（插件）

- [x] T10 回调响应消费 recordId/reportUrl（uploadAndNotify 返回受理 data）+ run() setOutput('report_url')；旧后端无字段/回调失败仅 [WARN] 降级不影响 result；主流程测试重构 + 2 新用例；dist 重建并规范化（npm run package，版本不变）——全量 74 例通过
