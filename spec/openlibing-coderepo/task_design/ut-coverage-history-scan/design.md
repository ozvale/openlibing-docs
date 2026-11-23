# UT 覆盖率历史扫描记录 — 后端详细设计方案

| 项目     | 内容                                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 需求名称 | UT 覆盖率历史扫描记录查看与定期清理                                                                                                       |
| 涉及仓   | openlibing-coderepo（后端）、openlibing-web（前端）、upload-ut-action（插件）                                                             |
| 关联现状 | `code_ut_record` 表已入库每次扫描记录（含文件明细 LONGTEXT）；上报走 MQ 异步；无历史列表接口、无清理机制；插件仅输出 `result`，无结果链接 |
| 设计基线 | 分支列表 UT 指标仍取 `repo_branch` 快照；历史能力全部基于 `code_ut_record` 存量数据，无需新建业务表                                       |

---

## 1. 方案总览

```
插件 upload-ut-action
  └─ 回调 /ut/coverage/report（MQ 异步入库）
  └─ 响应直接返回 {recordId, reportUrl}（recordId 受理时预生成，对齐点①：不再新增查询接口）
       └─ 插件 setOutput("report_url", ...) 输出结果链接

前端
  ├─ 分支列表 UT 指标列点击 → 详情页（最新扫描，行为不变）
  ├─ 详情页新增「查看历史扫描记录」入口 → 历史扫描记录页（新）
  │    列表：扫描时间 | 来源(流水线) | 行覆盖率 | 状态 | 操作（commitId 挪详情页，对齐点②）
  │    顶部提示"仅保留最近 N 天的扫描记录"（N 由后端配置返回）
  └─ 点击记录 → 详情页（复用现有弹窗）URL 携带 recordId（记录唯一定位）

定时清理
  └─ xxl-job utCoverageCleanupHandler 按 retention-days 分批删除 code_ut_record，连带清理 OBS 原始报告 JSON（对齐点③，见 4.1）
```

## 2. 数据模型设计

不新建业务表，复用 `code_ut_record`。两处变更（db.changelog.xml）：

### 2.1 新增清理索引

现有索引 `idx_git_branch(git_url(255), branch_name, detection_completed_at)` 服务于业务查询；定时清理按时间范围删除走不了该索引，新增：

```xml
<changeSet id="20261118_add_index_ut_record_detection_time">
  <createIndex indexName="idx_ut_record_detection_completed_at"
               tableName="code_ut_record">
    <column name="detection_completed_at"/>
  </createIndex>
</changeSet>
```

清理批次查询（评审对齐）拆为 UNION ALL 双分支以稳定走该索引——OR 两侧引用不同列（`detection_completed_at` 与 `create_time`）时 MySQL 无法稳定用单列索引完成整个谓词，大表（含明细 LONGTEXT）易退化为 index merge / 全表扫描：分支一按 `detection_completed_at < cutoff` 区间扫描；分支二覆盖 `detection_completed_at IS NULL` 的失败记录兜底（按 `create_time < cutoff` 过滤），NULL 记录聚簇于同一索引头部、数量少，回表过滤无需额外索引。外层按原口径排序 + LIMIT 收敛，清理批次语义不变（落地实现见 openlibing-coderepo !334 commit `9407647e`）。

### 2.2 保留周期配置

```yaml
ut:
  coverage:
    retention-days: 90 # 扫描记录保留天数，>0 生效；<=0 关闭自动清理
    cleanup-batch-size: 500 # 单批删除条数，防长事务锁表
```

读取方式：`@Value` 注入 UtCoverageProperties（支持配置中心覆盖）。保留天数随历史列表接口下发，前端据此渲染提示。

## 3. API 接口设计

统一约束：越权校验复用 `verifyPermissionsByProduct`，新增一条 `UrlConstant`（`UT_COVERAGE_HISTORY`）；雪花 ID 全链路以 String 传递（前端 JS Number 精度安全）；列表/详情 SELECT 均不回 `coverage_file_detail_json` 大字段（明细仅详情接口经 JSON_TABLE 分页展开）。

### 3.1 历史扫描记录列表（新增）

```
POST /ut/coverage/history
入参 UtCoverageHistoryQueryDTO：{ repoId: Integer, branchName: String, pageNum=1, pageSize=10 }
出参 UtCoverageHistoryVO：{
  total: long,
  retentionDays: int,             // 保留天数（<=0 表示未开启清理，前端不渲染过期提示）
  earliestTime: String,           // 最早可查记录时间，yyyy-MM-dd HH:mm:ss
  records: [ {
    recordId: String,
    detectionCompletedAt: String, // 扫描时间
    pipelineName: String, runNumber: String, pipelineLink: String,  // 来源（流水线）
    lineCoverage: BigDecimal,     // 行覆盖率
    status: Integer               // 0 成功 / 1 失败
  } ]
}
```

- 排序固定 `detection_completed_at DESC, id DESC`；分页物理查询。
- Mapper 新增 `selectHistoryPage(gitUrls, branchName, offset, limit)` / `countHistory(gitUrls, branchName)`：SELECT 列不含明细大字段；gitUrl 复用 `normalizeGitUrl` 等价集合匹配（跨域名/.git 变体，与现有 `selectByPipelineRunId` 同口径）。
- 失败记录（status=1）同样出现在历史列表（标注状态，供用户感知失败扫描），行覆盖率允许为 null。
- 历史列表**不返回 commitId**（对齐点②：提交信息挪至详情页展示）。

### 3.2 详情接口扩展（存量接口加参数，向后兼容）

```
POST /ut/coverage/file-detail（存量）
入参 UtCoverageFileDetailQueryDTO 增加字段：recordId: String
```

- `locateRecord` 定位优先级调整为：**recordId 精确匹配 > pipelineRunId 精确匹配 > 最近一条成功记录（兜底，现状不变）**。
- Mapper 新增 `selectMetaById(recordId)`（不含明细大字段；越权校验通过后再查明细）。
- 查无记录（含已被清理）时返回统一文案「该扫描记录不存在或已超出保留期」（HTTP 200 + 失败文案，前端据此渲染过期提示页并引导返回历史列表）。
- **过程态区分（评审反馈补充）**：插件结果链接在受理响应直返后可能被立即打开，此时 MQ 消费尚未入库——recordId 未命中时解码雪花 ID 时间戳（纪元 1288834974657，与生成口径一致），距当前 ≤ 5 分钟（覆盖消费侧 3 次退避重试 + OBS 下载解析耗时）判定为"受理后处理中"，返回文案「该扫描记录正在处理中，请稍后刷新查看结果」；超窗口仍未入库或已清理返回终态文案。前端按文案区分渲染：处理中态引导刷新重试，终态引导返回历史列表。非法格式/归属不符等确定性未命中固定归终态，不放行处理中提示。
- **兼容性**：看板组适配新链接格式前，旧链接（pipelineRunId/无参兜底）行为不变；`pipelineRunId` 与 `recordId` 同时存在时 `recordId` 优先（记录唯一定位优先于流水线定位）。
- 详情出参包含 `commitId`（对齐点②：历史列表「提交」列取消，提交信息在详情页顶部信息区展示）。

### 3.3 上报接口响应扩展（对齐点①：不再新增查询接口）

`POST /ut/coverage/report` 保持 MQ 异步受理语义，同步响应 `data` 扩展为 `{ recordId: String, reportUrl: String }`：

- **recordId 预生成**：Controller 受理时即生成雪花 ID（实体 `@TableId(type = IdType.INPUT)` 已支持指定写入），随 MQ 消息透传，消费者入库沿用同一 ID。响应返回时记录可能尚未入库（MQ 异步），但 recordId 与链接已确定，插件无需二次查询。
- `reportUrl = {webBaseUrl}/apps/repos?projectId={projectId}&repoId={repoId}&branchName={urlencode(branch)}&recordId={recordId}&utCoverageDetail=1`
- `webBaseUrl` 复用 Nacos 既有配置 `openlibing.domain`（如 beta `https://10.0.15.101:8076`），不新增配置项。
- MQ 消费延迟/失败窗口内 URL 短暂指向未入库记录：消费侧 MQ 重试自愈（最终一致），插件不做重试；前端访问窗口内未入库的 recordId 返回「处理中」过程态提示（见 3.2 过程态区分），不误报「记录不存在」。
- **兼容性**：响应字段为新增，旧版插件不读取新字段行为不变；旧版后端响应无新字段时插件降级告警（见 §5）。

## 4. 定时清理设计

`XxlJobHandler` 新增（与既有 5 个 handler 同款注册方式）：

```java
@XxlJob("utCoverageCleanupHandler")
```

- 触发：每日凌晨低峰（运维在 xxl-job 控制台配置 cron）。
- 执行逻辑：
  1. `retentionDays <= 0` 直接返回（关闭态）；
  2. 计算 cutoff = now - retentionDays；
  3. 循环 `DELETE FROM code_ut_record WHERE detection_completed_at < cutoff LIMIT {batchSize}`，直至影响行数 0；每批之间记录删除量汇总；
  4. 输出执行摘要（删除总数、耗时），失败记录（status=1）与成功记录统一按 `detection_completed_at` 清理；
  5. `repo_branch` 的 UT 快照列（ut_line_coverage/ut_pipeline_run_id/ut_detection_time）**不清理**——分支列表"最新指标"始终有值。
- 与业务的一致性：清理只删历史记录，`selectLatestByGitAndBranch`（分支最新一条）永远能命中保留期内数据；若整个分支数据全部过期，兜底查询自然返回空，前端展示为无扫描记录，无异常路径。

### 4.1 OBS 原始报告 JSON 文件级联清理（已对齐：方案 A，任务级联删除）

**对齐结论**：扫描记录保留 90 天，由 xxl-job 定时清理，**连带清理 OBS 上的 JSON 报告**（评审拍板方案 A；曾倾向的方案 B「OBS 生命周期规则」不再采用）。

**背景事实**：

1. 原始报告 JSON 存于源桶 `openlibing-gitcode-action`（GitHub 平台独立桶），前缀 `ut-coverage-action/`，key 结构 `ut-coverage-action/{repoName}/{yyyyMMdd}.{HH}/{runId|manual}/ut-coverage.json`，对象上传后不再修改；
2. 《UT 原始报告下载》方案落地后，成功记录将持有 `original_report_obs_url`（历史上报与失败记录恒为 NULL）；
3. 页面文件明细存在 DB 大字段（`coverage_file_detail_json`），不依赖 OBS；OBS 文件唯一消费方是"下载原始报告"，该方案的失败路径已覆盖"对象不存在"场景。

**执行设计（在 §4 分批删除基础上扩展）**：

1. 每批 DB 删除**前**收集该批记录的 `original_report_obs_url`；
2. 按 URL 批删源桶对象：NULL 跳过（历史上报/失败记录无产物）；桶名 + 前缀白名单校验复用 `ObsBucketServiceImpl` 既有约束，防止脏数据 URL 越权删除；
3. 删除失败仅 `[WARN]` 记录并计入执行摘要，**不回滚 DB 删除、不中断任务**——DB 已清，残留孤儿对象不阻塞主流程（"下载原始报告"本就按对象不存在失败）；
4. **误删防护**：① 删除凭证仅授予清理专用最小权限（限 ut-coverage-action 前缀删除）；② 逐对象删除前二次校验对应记录 `detection_completed_at < cutoff`；
5. 执行摘要输出：删除记录数 / OBS 删除成功数 / 失败数，便于运维核对。

## 5. 插件适配设计（upload-ut-action）

`index.js run()` 在 `ObsUploader.uploadAndNotify(...)` 成功后：

1. 从回调响应 `data` 直接读取 `recordId` / `reportUrl`（`sendCallbackOidc` 已解析响应体，本步骤新增消费；无 SDK 变化、无新依赖）；
2. 成功：`setOutput('report_url', reportUrl)`；响应无该字段（旧后端版本）：仅 `[WARN]` 告警，不影响 `result=success`——链接缺失不构成流水线失败；
3. 无额外查询请求、无重试逻辑（对齐点①：URL 由上报响应直接返回）。

输出示例（GitCode step 输出文件，机制不变）：

```
result=success
report_url=https://www.openlibing.com/apps/repos?projectId=403256&repoId=823&branchName=develop&recordId=1926534...&utCoverageDetail=1
```

## 6. 前端适配要点（openlibing-web）

1. 分支列表 UT 指标列点击**保持直进最新详情（行为不变，高频路径不变长）**；详情页新增「查看历史扫描记录」入口打开历史列表页（记录按扫描时间倒序）；历史页来源列展示 `pipelineName #runNumber`（对齐 PR #885 展示口径，存量记录降级「查看流水线」链接）。
2. 历史页点击记录 → 详情弹窗（复用 `UtCoverageDetailDialog` 结构与明细接口），URL query 由 `pipelineRunId` 迁移为 `recordId`（`syncUtCoverageQuery` / `autoGoBranch` 同步改造）；**临时保留 pipelineRunId query 解析适配**，待看板组切换新链接格式后移除。
3. 顶部信息区调整：`流水线` 更名为 `来源`；新增 **提交** 展示（`commitId` 由历史列表挪入，对齐点②），调整后顺序为 **代码仓、分支、扫描时间、来源、提交**。
4. 保留范围提示：历史页顶部横幅"仅保留最近 N 天的扫描记录"（N 取接口返回 `retentionDays`，`<=0` 不渲染）；详情页查无记录（`UT_COVERAGE_RECORD_NOT_FOUND`）时展示过期提示 + "返回历史记录"按钮。
5. **返回交互统一**：历史页与详情页均采用左上角「←」+ 层级面包屑（`分支管理 / UT行覆盖率扫描记录 [/ 扫描详情]`）——「←」恒回面包屑上一级，与现有详情页返回模式一致，不随来源变化。
6. 新增 API：`queryUtCoverageHistory`（/ut/coverage/history）；`queryUtCoverageFileDetail` 入参增加 `recordId`。
7. **过程态提示（评审反馈补充）**：详情页访问的失败响应按后端文案区分两态——「该扫描记录正在处理中，请稍后刷新查看结果」渲染 ⏳ 处理中态（引导刷新重试，不做自动轮询死循环）；「该扫描记录不存在或已超出保留期」渲染过期提示页并引导返回历史列表。文案由后端区分（雪花时间戳 ≤5 分钟窗口启发式），前端只按文案路由。

## 7. 性能与安全设计

- **性能**：历史列表不回大字段；明细查询沿用 JSON_TABLE SQL 侧分页（现状已验证）；清理走新索引 + 分批删除，单批 500，避免 LONGTEXT 大事务；OBS 级联删除随批执行并限流，失败不阻塞；上报响应直返链接，零额外查询开销。
- **安全**：新增接口全部走产品级越权校验；recordId 为雪花 ID 不可枚举，详情访问仍走登录态 + 越权校验；OBS 删除凭证最小化（限 ut-coverage-action 前缀）+ 删除前二次时间校验；雪花 ID 全链路 String 防 JS 精度截断；插件结果链接不含 token/凭证。
- **幂等/一致性**：清理不影响上报幂等（deleteExistingRecord 逻辑独立）；OBS 级联删除幂等（对象不存在视为成功）；recordId 预生成保证响应链接与入库记录严格一致。

## 8. 任务分解（checkbox）

- [ ] db.changelog：新增 detection_completed_at 单列索引
- [ ] Mapper：selectHistoryPage / countHistory / selectById（不含大字段）
- [ ] Service/Controller：history 列表接口（含越权校验、retentionDays 下发）
- [ ] Service/Controller：file-detail 增 recordId 定位 + UT_COVERAGE_RECORD_NOT_FOUND 错误码
- [ ] Service/Controller：/ut/coverage/report 响应扩展（recordId 预生成 + reportUrl 拼装，复用 Nacos 既有 openlibing.domain）
- [ ] XxlJobHandler：utCoverageCleanupHandler（分批删除 + OBS 原始报告级联清理 + 摘要日志）
- [ ] 配置：ut.coverage.retention-days / cleanup-batch-size（application.yml + 配置中心）；reportUrl 域名复用既有 openlibing.domain
- [ ] 单测：locateRecord 优先级矩阵（recordId/pipelineRunId/兜底）、清理分批边界（含 OBS 级联 NULL 跳过/失败告警）、history 分页
- [ ] 插件：回调响应消费 recordId/reportUrl + setOutput report_url（含单测）
- [ ] 前端：历史记录页 + 详情 URL recordId 迁移 + 信息区换位改名 + 过期提示
