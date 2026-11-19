# 设计：UT 覆盖率详情页补齐来源流水线信息

关联 Issue：[#249](https://gitcode.com/openlibing/openlibing-coderepo/issues/249)（同类先例：#219 代码度量下钻页，已修）

## 1. 链路现状（已核实，基于 release_20261116_iter1）

### 1.1 数据流与根因（已核实，2026-11-12）

```text
upload-ut-action 插件
  ├─ index.js:139  pipelineRunId = env.ATOMGIT_RUN_ID
  ├─ index.js:140  commitId = env.ATOMGIT_SHA
  ├─ index.js:190  CoverageNormalizer.normalize(parsedList, { gitUrl, branchName, pipelineRunId, commitId })
  └─ CoverageNormalizer.js:76-82  标准 JSON 元数据区仅 5 字段：
      gitUrl / branchName / pipelineRunId / commitId / lineCoverage
      ★ 无 runNumber、无 pipelineName、无 detectionCompletedAt（src 全文 grep 零命中）
        ↓ obsUrl 指向该标准 JSON
openlibing-coderepo UtCoverageServiceImpl#reportUtCoverage
  ├─ 流式解析元数据 readUtMetaField：runNumber(L283)/detectionCompletedAt(L292) 两个 case
  │   永不命中（JSON 无对应字段）→ payload 值恒为 null；parseDateTime(null) 返回 null（L666-669）
  ├─ saveUtRecord(L444-448) 入库：run_number=NULL、detection_completed_at=NULL
  └─ upsertBranchLatest(L485) 分支快照：ut_detection_time=parseDateTime(null)=NULL（同源同命运）
        ↓
getFileDetail 明细接口：runNumber/checkTime 字段链路存在但值恒为空
```

**数据库实证**（2026-11-12 生产库截图）：

- `code_ut_record.run_number` 全量 NULL，`pipeline_run_id`/`commit_id`/`line_coverage` 均有值——与「插件上报了 commitId（取 ATOMGIT_SHA）但从未上报 runNumber」完全吻合；
- `detection_completed_at` **分界线现象**：最早期约 5 行（2026-09-21 ~ 09-24）有值且**与 create_time 秒级完全相同**，此后全部 NULL——见下方时间线。

**根因结论**（git 考古修正版）：

| 时间点 | 提交 | 行为 |
| --- | --- | --- |
| 2026-09-20 | `90e02d2f`（UT 覆盖率功能引入） | `parseDateTime` 对空值**兜底返回 `new Date()`**（服务器当前时间）。插件 JSON 从未携带 `detectionCompletedAt`，故每条记录的检测时间 = 上报处理时刻 ≈ create_time（假时间） |
| 2026-09-23 17:09 | `379bed9e`（Refs #189 修复） | **兜底被刻意移除**：`return new Date()` → `return null` + 告警。提交注释明确：「避免用服务器当前时间冒充检测时间（会失真展示并打乱『取最近一次成功记录』排序）」。发版后新记录 detection_completed_at 恒为 NULL |
| 2026-10-14 | `62fc4c90`（OBS 流式解析重构） | `parseDateTime` 行为未变（仅调用点格式化），非分界点 |

即：**早期记录的「有值」是后端兜底产生的假时间**（≈create_time，无真实语义），兜底移除后暴露出插件侧 `detectionCompletedAt` 元数据从未上报的事实，形成「分界线之后全 NULL」。`run_number` 与 `pipeline_name` 则是纯粹的同模式插件侧元数据缺失（从未有值）。issue 中「检查时间后端已返回」的定位需要修正——后端返回链路存在但依赖插件数据，数据源头即为 NULL，「缺少检查时间」的根因同样在插件侧数据缺失，而非前端未渲染。

### 1.2 同类先例（对齐目标，code-metrics-action 仓已核实）

| 项 | code metrics（已修，#219） | UT 覆盖率（本设计） |
| --- | --- | --- |
| pipelineName 来源 | `index.js:199`：`ciEnv('workflow')`——GitCode 取 `ATOMGIT_WORKFLOW`，GitHub 取 `GITHUB_WORKFLOW`（`src/utils/ciContext.js` 双平台适配） | `ATOMGIT_WORKFLOW`（UT 插件当前仅适配 GitCode 平台） |
| runNumber 来源 | `ciEnv('runNumber')`——GitCode 取 `ATOMGIT_RUN_NUMBER`（ciContext.js:27） | `ATOMGIT_RUN_NUMBER`（UT 插件从未上报，本次补齐） |
| JSON 元数据 | `CodeMetricsPayload.pipelineName`（L52）；OBS 全量 JSON 写入（`CoderepoUploader.js:306`） | 元数据区缺 pipelineName/runNumber/detectionCompletedAt，补齐 |
| 上报请求体 | `/metrics/code/report` body **不含** pipelineName（`CoderepoUploader.js:327-337`），仅 JSON 元数据单一来源 | 同款：请求 DTO 不动 |
| 流式解析 | `CodeMetricsServiceImpl:388 case "pipelineName"` | runNumber/detectionCompletedAt case 已存在（L283/L292），仅新增 pipelineName case |
| 入库 | `code_metrics_record.pipeline_name`（changeSet `20261016_add_pipeline_name_to_code_metrics_record`） | `code_ut_record` 加列 pipeline_name；run_number/detection_completed_at 列已存在（数据源补齐后即有值） |
| 下钻返回 | `FileMetricDetailVO.pipelineName`（`CodeMetricsServiceImpl:992`） | `UtCoverageFileDetailVO` 新增 pipelineName；checkTime/runNumber 字段已存在 |
| 下钻页展示 | `流水线: {pipelineName} #{runNumber}` 整体为跳转链接（组合样式） | UT 详情页对齐同款 |

### 1.3 前端现状（含对齐目标口径）

- **code metrics 下钻页（MetricsDetailDialog.vue，对齐目标）**信息条结构：`代码仓 | 分支 | 扫描时间：{{ checkTime }} | 流水线：{{ pipelineDisplayName }}`；其中「扫描时间」数据源就是 `checkTime`（detection_completed_at 格式化，**无独立的 started_at 字段**），`pipelineDisplayName` 为 computed（L83-87）：`pipelineName ? \`${pipelineName} #${runNumber}\` : \`#${runNumber}\``，整体走 `pipeline-link` 跳转链接；
- **UT 详情页（MR 879 版本）现状**：信息条为 `代码仓 | 分支 | 检测时间：{{ utCoverage.detectionTime }} | 检查时间：{{ checkTime }} | 流水线：#{{ runNumber }}`——渲染代码已在 feature 分支实现但生产未发版；且因数据源头缺失（§1.1），**即便发版，存量记录的检查时间与流水线编号仍为空**；
- 差异：UT 页「检查时间」label 与 metrics 页「扫描时间」不一致；「检测时间」与「检查时间」同源重复展示；流水线段无名称且编号值为空。三要素（扫描时间/编号/名称）的修复必须从插件数据源开始（§2.3），仅前端发版无法解决。

## 2. 详细设计

### 2.1 数据模型（openlibing-coderepo）

`db.changelog.xml` 新增 changeSet（完全对齐 metrics 先例结构）：

```xml
<!-- 新增 pipeline_name 字段，记录 UT 覆盖率数据来源流水线名称（由插件端写入报告 JSON 元数据，用于详情页展示来源流水线） -->
<changeSet id="20261112_add_pipeline_name_to_code_ut_record" author="ai-assisted">
    <preConditions onFail="MARK_RAN">
        <tableExists tableName="code_ut_record"/>
        <not>
            <columnExists tableName="code_ut_record" columnName="pipeline_name"/>
        </not>
    </preConditions>
    <addColumn tableName="code_ut_record">
        <column name="pipeline_name" type="VARCHAR(255)" remarks="流水线名称（插件写入报告 JSON 元数据，解析入库）">
            <constraints nullable="true"/>
        </column>
    </addColumn>
    <rollback>
        <dropColumn tableName="code_ut_record" columnName="pipeline_name"/>
    </rollback>
</changeSet>
```

要点：

- `VARCHAR(255)` + 可空：与 `code_metrics_record.pipeline_name` 完全同规格；历史记录与旧版插件上报均为 NULL，语义即「未知来源」，前端兜底 `--`；
- `preConditions` 防重跑（columnExists MARK_RAN），幂等安全；
- 位置紧跟 `run_number`（语义分组，建表 changeSet 内列序不调整——历史 changeSet 不可修改，新列走 addColumn）。

### 2.2 后端解析与入库（openlibing-coderepo）

| # | 文件 | 改动 |
| --- | --- | --- |
| 1 | `UtCoveragePayload` | 新增 `private String pipelineName;`（与 runNumber/commitId 同组） |
| 2 | `UtCoverageServiceImpl#readUtMetaField` | switch **仅新增** `case "pipelineName": payload.setPipelineName(parser.getValueAsString()); break;`——runNumber（L283）/detectionCompletedAt（L292）case 已存在，数据源补齐后自动生效，零改动 |
| 3 | `CodeUtRecordEntity` | 新增 `private String pipelineName;`（@Builder 链式，紧跟 runNumber） |
| 4 | `UtCoverageServiceImpl#saveUtRecord`（L444 附近 builder） | `.pipelineName(payload.getPipelineName())`；runNumber/detectionCompletedAt 入库链路已存在（L444/L448），零改动 |
| 5 | `UtCoverageFileDetailVO` | 新增 `private String pipelineName;` |
| 6 | `UtCoverageServiceImpl#getFileDetail`（L586-600 builder） | `.pipelineName(record.getPipelineName())`；checkTime/runNumber 返回链路已存在（L592-594） |

设计约束：

- **单一数据来源**：pipelineName 只从报告 JSON 元数据解析，不加入 `UtCoverageReportDTO` 请求参数——与 runNumber/commitId 同口径，避免「请求参数 vs JSON 内容」双源不一致（与 metrics 先例一致：`CodeMetricsPayload.pipelineName` 同为 JSON 元数据）；
- **向后兼容**：旧版插件报告 JSON 无 `pipelineName` 字段 → 流式解析走 `default: parser.skipChildren()` 分支跳过（既有机制，L295-298）→ payload 为 null → 入库 NULL → VO 返回 null，零破坏；
- **失败记录不带**：`saveFailureRecord`（L504-536）不设置 pipelineName——失败记录无报告 JSON 可解析（下载/解析失败时 payload 未产生），与 runNumber/commitId 同口径；失败原因已在 `errorMessage` 透出；
- **无契约变更**：请求 DTO、幂等清理（按 gitUrl+branch 删旧记录）、记录定位逻辑均不变。

### 2.3 插件侧（upload-ut-action）——本设计核心改动

标准 JSON 元数据区从 5 字段补齐至 8 字段（新增 **runNumber / pipelineName / detectionCompletedAt**）：

| # | 文件 | 改动 |
| --- | --- | --- |
| 1 | `index.js`（L139-140 附近） | 新增两行上下文读取：`const runNumber = (process.env.ATOMGIT_RUN_NUMBER \|\| '').trim();`（对齐 code-metrics-action `ciContext.js:27`）、`const pipelineName = (process.env.ATOMGIT_WORKFLOW \|\| '').trim();`（对齐 `ciContext.js:29`） |
| 2 | `index.js:190` | `CoverageNormalizer.normalize(parsedList, { gitUrl, branchName, pipelineRunId, commitId, runNumber, pipelineName }, repoRoot)` |
| 3 | `CoverageNormalizer.js`（L76-82 元数据区） | 新增三个字段：`runNumber: meta.runNumber \|\| ''`、`pipelineName: meta.pipelineName \|\| ''`、`detectionCompletedAt: <组装完成时刻，格式 yyyy-MM-dd HH:mm:ss>`——完成时间由插件在组装标准 JSON 时打点（与 metrics 的 scanner 写入 detectionStartedAt/CompletedAt 同款语义），格式走后端 `parseDetectionTime` 已兼容的空格分隔形式 |
| 4 | `test/` | normalize 用例扩展：meta 带/不带 runNumber、pipelineName 的断言 + 元数据区字段完整性快照 |
| 5 | `dist/` | `npm run build` 重新生成并随版本发布；`package.json` 版本号升级 |

要点：

- **一次补齐三个缺失元数据**：runNumber（编号展示）、pipelineName（名称展示）、detectionCompletedAt（扫描时间展示）同源同模式——均为「流水线上下文 → JSON 元数据 → 后端既有解析 case → 入库」，其中 runNumber/detectionCompletedAt 的后端解析与入库链路已存在（`readUtMetaField` L283/L292、`saveUtRecord` L444/L448），插件补数据后立即生效、后端零改动；
- **环境变量名已确定**：`ATOMGIT_RUN_NUMBER`（编号）、`ATOMGIT_WORKFLOW`（名称）——均与 code-metrics-action `ciContext.js` GitCode 分支同源；手动触发无变量时兜底空串；
- **detectionCompletedAt 打点语义**：取标准 JSON 组装完成时刻（此时扫描已完成），无名称/时间上下文时不兜底假值——空串入库由后端 parseDateTime 归一为 NULL，前端按未知时间兜底；
- 上报契约（POST /ut/coverage/report 请求体）**零变更**——与 metrics 先例一致：pipelineName/runNumber/detectionCompletedAt 只进 OBS 全量 JSON 元数据（`CoderepoUploader.js:327-337` 请求体不含此类字段），后端从 JSON 解析，单一数据来源。

### 2.4 前端（openlibing-web）

**整体对齐 code metrics 下钻页信息条口径**（截图确认 + MetricsDetailDialog.vue 实测）：

```text
代码仓：xxx  分支：xxx  扫描时间：{checkTime}  流水线：{pipelineName} #{runNumber}
```

`UtCoverageDetailDialog.vue` 信息条改造：

| 项 | 现状（MR 879 版本） | 目标（对齐 metrics 页） |
| --- | --- | --- |
| 扫描时间 | label 为「检查时间」（checkTime）；**存量记录值为空**（数据源缺失，§1.1） | label 统一为「**扫描时间**：{{ checkTime }}」——与 metrics 页同字段同 label；**空值兜底 `--`**（存量记录/旧插件数据 checkTime 为 null） |
| 检测时间 | 额外展示「检测时间：{{ utCoverage.detectionTime }}」 | **移除**——与扫描时间同源重复（分支行快照 detectionTime 与记录 detection_completed_at 取自同一最新记录，值恒等），metrics 页无此双重展示 |
| 流水线 | `#{{ runNumber }}`（**存量记录 runNumber 为空 → 仅显示 `#`**） | `pipelineDisplayName` computed 同款复刻：`pipelineName ? \`${pipelineName} #${runNumber}\` : \`#${runNumber}\``，整体走既有 `pipeline-link` 链接样式（点击 `goToNotice(pipelineLink)`；pipelineLink 缺失时保持纯文本） |

要点：

- pipelineName 数据来自明细接口新增字段（§2.2）；**流水线段双重空值兜底**：runNumber 与 pipelineName 均缺失（存量记录）时整段展示 `--`；仅缺名称（旧插件新数据）退化为仅编号；齐全时展示组合链接——与 metrics 页 L84-86 逻辑一致并加强；
- 扫描时间空值兜底 `--`：存量记录/旧插件数据 checkTime 为 null（数据源修复前），插件修复上线后新数据有值；「检测时间」移除为 UI 口径统一决策：若评审认为分支快照检测时间有独立价值（如未来分支行与最新记录解耦），可保留，不阻塞本设计；
- 无新增后端字段、无新增接口调用。

### 2.5 发版与灰度顺序

1. 后端先行（加列 + 解析 + VO 返回，向后兼容旧 JSON）——老插件数据 pipelineName/runNumber/checkTime 为 NULL，无影响；
2. 插件发版（JSON 元数据补齐 runNumber/pipelineName/detectionCompletedAt 三字段，后端解析链路已就绪）——新数据三要素齐全，`run_number`/`detection_completed_at` 开始有值；
3. 前端发版（扫描时间 label 统一 + 空值兜底 + 流水线组合展示）——新记录展示完整信息，存量记录兜底 `--`。

任一环节单独上线均不产生破坏：后端兼容旧 JSON、旧后端对新 JSON 未知字段跳过（`default: skipChildren`）、旧前端不读新字段。

**存量数据说明**：`run_number`/`detection_completed_at` 历史值为 NULL 属数据源缺失（列一直存在，非 schema 问题），不做刷数回填——历史记录详情页按空值兜底展示；分界线前（2026-09-23 兜底移除发版前）少数记录的 detection_completed_at 为后端 `new Date()` 兜底产生的**假时间（≈create_time）**，同样不具备真实语义，不做清洗也不参与展示口径讨论；如需回填可后续评估基于 `pipeline_run_id` 反查流水线系统的离线刷数任务（不在本次范围）。

## 3. 测试策略

### 3.1 后端单测（openlibing-coderepo）

| 用例 | 断言 |
| --- | --- |
| 报告 JSON 含 pipelineName/runNumber/detectionCompletedAt 元数据（新版插件形态） | 三字段解析入库一致，VO 返回 pipelineName + checkTime + runNumber 同值 |
| 报告 JSON 无三字段（旧插件/历史形态，当前线上真实形态） | pipelineName/runNumber 为 null、detection_completed_at 为 null（parseDateTime(null)→null），VO 返回空，不抛错、不落失败记录 |
| pipelineName 为空串 | 按原样入库（空串），VO 返回空串——前端兜底展示，与 metrics 侧一致 |
| 失败记录路径 | saveFailureRecord 不写 pipelineName（保持 null） |
| changeSet | preConditions 幂等（重复执行 MARK_RAN 不报错）——跟随既有 changelog 测试惯例 |

### 3.2 插件单测（upload-ut-action）

- normalize：meta 带 runNumber/pipelineName → JSON 元数据含两字段且 detectionCompletedAt 为合法时间格式（后端 parseDetectionTime 可解析）；meta 不带 → 字段为空串；
- 既有用例回归（元数据区新增字段不破坏既有断言结构）。

### 3.3 联调验收

按 proposal.md 验收标准执行：新版插件上报 → 详情页三要素（扫描时间/名称+编号组合链接）齐全；存量旧记录打开 → 扫描时间与流水线段兜底 `--`。

## 4. 风险与开放问题

| 项 | 评估 |
| --- | --- |
| Liquibase 加列（可空，单行 DDL） | 锁表时间短，风险低；preConditions 防重跑 |
| 存量数据 run_number/detection_completed_at 全 NULL | 数据源缺失所致（列一直存在），不做刷数回填——详情页空值兜底 `--`；分界线前少数记录 detection_completed_at 为后端兜底假时间（≈create_time，详见 §1.1 时间线），无真实语义不清洗；如需回填可另行评估基于 pipeline_run_id 的离线刷数任务（不在本次范围） |
| 旧版插件共存期 | 新插件上线前数据三要素为 NULL，前端空值兜底展示，无功能破坏 |
| 「检测时间」展示移除 | 与扫描时间同源同值（同一最新记录），对齐 metrics 页口径去重；如评审有异议可保留，不阻塞 |
| pipelineName 环境变量 | **已闭环**：`ATOMGIT_WORKFLOW`，与 code-metrics-action `ciContext.js` GitCode 分支同源（该仓已核实）；手动触发无该变量时兜底空串，前端组合展示自动退化为仅编号 |
| UT 插件双平台适配 | UT 插件存量仅 GitCode（`ATOMGIT_*`）；GitHub 平台（`GITHUB_WORKFLOW`）适配为可选增强，随插件上 GitHub 需求另行评估，不在本次范围 |
| 跨仓发版顺序 | 见 §2.5，三环节任意顺序上线均向后兼容 |
| 明细接口响应体膨胀 | 新增 1 个可空字符串字段，影响可忽略 |
