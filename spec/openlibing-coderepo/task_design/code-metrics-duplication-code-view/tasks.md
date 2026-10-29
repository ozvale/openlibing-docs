# 代码重复率详情 - 展示具体重复代码（实现任务）

> 配套 [proposal.md](./proposal.md) + [design.md](./design.md) + [requirement-design.md](./requirement-design.md)。
>
> 进度: 69/73 complete
>
> 核心数据模型：**"出现位置"表**（同一代码内容的所有出现位置归为同一 `group_id`，每个位置一行），前端 drawer 多页签直接映射 `occurrence_index`。文件快照存入 `code_metrics_file_detail.snapshot_data` 字段，**无 TTL 长期保留**，仅存重复块±5行上下文。`code_metrics_record` 的 **DTO/Entity 移除 `repository` 字段（DB 列保留不 drop，便于回滚）**；`identicalFileDetails` 每组**移除 `filePath`**（只保留 `duplicatedFiles` 数组）。`reportMetrics` 返回 `DataResult<String>`（recordId 用 String，避免雪花ID 在 JS Number 精度溢出）。

## 阶段 1：后端 DB Schema + Entity / Mapper（独立可验证）

- [x] 1.1 新增 liquibase changeset `src/main/resources/db/changelog/v1.0.0/code-metrics-duplication-code-view.xml`，创建 `code_metrics_duplication_block` 表（出现位置表，**无 `git_url`/`branch_name` 列**，按 `(record_id, group_id)` 定位，含 3 个索引：`idx_record_group`(record_id, group_id) / `idx_record_file`(record_id, file_path(255)) / 唯一键 `uk_record_group_file_start`(record_id, group_id, file_path(255), start_line)）
- [x] 1.2 同 changeset 内：`code_metrics_file_detail` 表新增 `snapshot_data LONGTEXT NULL` 字段（上下文片段 JSON，Base64 编码，无 TTL 长期保留）+ 新增 `idx_record_file`(record_id, file_path(255)) 索引；`code_metrics_record` 表 **repository 列保留不 drop**（仅 DTO/Entity 移除，DB 列保留便于回滚）
- [x] 1.3 在 `db.changelog.xml` 末尾 `<include>` 新 changeset
- [x] 1.4 新增 `CodeMetricsDuplicationBlockEntity.java`（@TableName, @TableField, Builder；字段含 `groupId` / `contentHash` / `occurrenceIndex` / `filePath` / `startLine` / `endLine` / `contentB64`）
- [x] 1.5 改 [CodeMetricsFileDetailEntity.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsFileDetailEntity.java)：新增 `snapshotData` 字段（`@TableField("snapshot_data")`，存上下文片段 JSON）
- [x] 1.6 改 [CodeMetricsRecordEntity.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsRecordEntity.java)：**移除 `repository` 字段**（仅 Entity 层移除，DB 列保留不 drop）
- [x] 1.7 改 [CodeMetricsRecordMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/CodeMetricsRecordMapper.xml)：resultMap 和 SELECT 语句移除 `repository` 列
- [x] 1.8 新增 `CodeMetricsDuplicationBlockMapper.java` + xml（saveBatch, selectByRecordAndFile, selectByGroupId, countByRecordAndGroupBatch, countGroupsByRecordGroupByFile, deleteByRecordId）
- [x] 1.9 **不新增 `CodeMetricsFileSnapshotEntity` / `CodeMetricsFileSnapshotMapper`**：快照数据存入 `code_metrics_file_detail.snapshot_data`，由现有 [CodeMetricsFileDetailMapper](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/mapper/CodeMetricsFileDetailMapper.java) 处理（`selectByRecordAndFile` 查询时顺带返回 `snapshot_data` 字段）
- [x] 1.10 单元测试：MapperTest 覆盖增删查，验证同 group_id 多出现位置入库 + 按组查询正确返回 N 行，Base64 字段存取正常，`snapshot_data` 字段随 file_detail 入库与读取正常
- [x] 1.11 **新增** `code_metrics_record` 幂等唯一索引 `uk_git_branch_run`(git_url, branch_name, pipeline_run_id)（changelog 内先清理已存在的重复记录再建唯一索引，保证并发上报幂等）

## 阶段 2：后端 - Base64 工具类 + 上报接口扩展

- [x] 2.1 新增 `common/utils/security/CodeContentB64Util.java`（encode/decode/isAlreadyEncoded，两阶段回检验证，对齐 codecheck [FragmentCryptoUtil.java](file:///d:/Develop/Java/openlibing-codecheck/src/main/java/com/openlibing/codecheck/common/utils/security/FragmentCryptoUtil.java)）
- [x] 2.2 单元测试 `CodeContentB64UtilTest`：覆盖中文/特殊字符/已编码数据/历史明文/"pass"等纯字母防误判/编码失败占位词
- [x] 2.3 改 [CodeMetricsReportDTO.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/metrics/CodeMetricsReportDTO.java)：**移除 `repository` 字段**；新增 `DuplicationOccurrenceDTO` 内部类（groupId/contentHash/occurrenceIndex/filePath/startLine/endLine/contentB64）+ `duplicationOccurrences` 字段；`FileDetailDTO` 新增 `snapshotData` 子字段（随文件明细上报上下文片段）；`IdenticalFileDetailDTO` **移除 `filePath`**（每组只保留 `duplicatedFiles` 数组，含组内所有文件）；**移除 `FileSnapshotDTO` 内部类和 `fileSnapshots` 字段**（快照随 fileDetails 上报）
- [x] 2.4 改 [CodeMetricsServiceImpl.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java) `reportMetrics`：**返回类型改为 `DataResult<String>`**（recordId 用 String 返回，避免雪花ID 在 JS Number 精度溢出）；幂等检查（相同 gitUrl+branchName+pipelineRunId 的旧记录先删 file_detail/duplication_block/record）；新增 `saveDuplicationBlocks` 方法（`batchInsertBlocks` 每批 `DUP_BLOCK_BATCH_SIZE`，单条失败容错，入库前**不二次编码**）
- [x] 2.5 改 `CodeMetricsServiceImpl.java` `saveCodeMetricsRecord`：移除 `.repository(request.getRepository())` 设置（字段已删除）；`buildPipelineLink` 改为从 `record.getGitUrl()` 提取 owner/repo（沿用现有 `extractOwnerRepo` 工具方法），不再依赖 `repository` 字段
- [x] 2.6 改 `CodeMetricsServiceImpl.java` `saveFileDetails`：改造 `buildFileDetailEntity` 处理 `fileDetail.snapshotData` 字段（随 file_detail 一起入库，存入 `snapshot_data` 列）
- [x] 2.7 改 `CodeMetricsServiceImpl.java` `saveIdenticalFileDetails`：适配新结构（`IdenticalFileDetailDTO` 不再含 `filePath`，先一次性查出该 record 下所有 file_detail 建立 filePath 映射，每组完全一致文件只更新组内第一个已存在文件的一条 file_detail 记录，`metrics_json` 中追加 `duplicatedFiles` 数组 + identical 标记）
- [x] 2.8 改 `CodeMetricsServiceImpl.java` `appendFileDuplicationItems`：适配新结构（不再从 `detail.getFilePath()` 取 filePath，改为从 `duplicatedFiles` 数组展示同组所有文件）
- [x] 2.9 **不再实现 `saveFileSnapshots`**：快照随 `saveFileDetails` 入库，无独立方法
- [x] 2.10 单元测试：模拟插件上报请求（含同一 group_id 的多个出现位置 + fileDetails 含 snapshotData + identicalFileDetails 不含 filePath），验证 `duplicationOccurrences` 和 `snapshotData` 正确入库，group_id 关联正确，`identicalFileDetails` 每组只生成一条 file_detail 记录，幂等删除旧记录
- [x] 2.11 **新增批量上报接口**：新增 `DuplicationBlockBatchDTO`（recordId(String) + blocks）+ `CodeMetricsService.saveDuplicationBlocksBatch`（recordId 入参 String 内部解析 Long）+ `CodeMetricsController` 新增 `POST /metrics/code/duplication-blocks`（首批随主报告 /report 上报，单批超 5000 条后续批次走此接口；saveBatch 为单条 INSERT 原子操作，**不加 @Transactional**，catch DataAccessException 返回失败避免 UnexpectedRollbackException）

## 阶段 3：插件改造（`openlibing-cicd-test-new`）

- [x] 3.1 改 [DuplicationDetector.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/detectors/DuplicationDetector.js) `detectWithTokenLevel`：扩展 `hashToLocations` 记录 `(file, startLine, endLine)`，对每个 hash 在 2+ 位置出现的，所有位置归为同一 group（`group_id = contentHash`），每个位置生成一条 `DuplicationOccurrence`
- [x] 3.2 改 `DuplicationDetector.js`：新增 `mergeConsecutiveLines(lineSet)` 工具方法（连续行号合并为区间，过滤区间长度 < minLines(10)）
- [x] 3.3 改 `DuplicationDetector.js`：新增 `extractBlockContent(filePath, startLine, endLine, sources)` 方法
- [x] 3.4 改 `DuplicationDetector.js`：新增 `buildDuplicationOccurrences(hashToLocations, sources)` 方法，同组出现位置按 (filePath, startLine) 排序，occurrenceIndex 从 0 递增
- [x] 3.5 改 `DuplicationDetector.js` `detectWithJscpd`（fallback 路径）：把同一 clone 的两端（或多端）归为同一 group，每个端点生成一条出现位置记录
- [x] 3.6 改 `DuplicationDetector.js` `detect`：新增 `buildContextSegments(fileDetails, sources, contextLines=5)`，对 `duplicationLineCount > 0` 的文件提取每个重复块±5行上下文，合并重叠/相邻区间，生成 `snapshotData`（JSON 结构：`{totalLines,contextLines,segments:[{originalStartLine,originalEndLine,contentB64}]}`，每个 segment 的 contentB64 内部再次 Base64 编码）；**不读取/上报完整文件内容**，其他部分代码由前端用 `... N lines omitted ...` 占位。生成的 `snapshotData` 直接挂到对应 `fileDetail.snapshotData` 字段上
- [x] 3.7 改 `DuplicationDetector.js` `calculateIdenticalFileDetails`：**每组完全一致文件只生成一条记录**，只含 `duplicatedFiles` 数组（含组内所有文件），**不再含 `filePath`**；前端将同组文件展示在一起
- [x] 3.8 改 `DuplicationDetector.js`：返回结果新增 `duplicationOccurrences` 字段；`fileDetails` 每项新增 `snapshotData` 子字段；`identicalFileDetails` 每项只含 `duplicatedFiles`（不含 `filePath`）；**不再返回独立的 `fileSnapshots` 字段**
- [x] 3.9 改 [CoderepoUploader.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/uploaders/CoderepoUploader.js)：新增 `encodeB64(str)` 工具，对 occurrence.content 做 Base64 编码后放入 payload（明文字段不传）；`snapshotData` 已由 `buildContextSegments` 编码，直接随 `fileDetails` 上报，不再单独处理
- [x] 3.10 改 `CoderepoUploader.js`：新增 `uploadInBatches`，单批 `duplicationOccurrences` ≤ 5000 条，**首批随主报告 /report 上报，超过部分递归调用新增 `/metrics/code/duplication-blocks` 分批接口**；`fileDetails`（含 `snapshotData`）整体上报不分批（单 record 通常 100-500 条，体量可控）
- [x] 3.11 本地跑插件扫描 openlibing-coderepo 自身代码，验证上报到测试环境后端无 413、无入库错误，同组多位置记录正确入库，`snapshot_data` 正确入库，`identicalFileDetails` 每组一条记录

## 阶段 4：后端 - 查询接口

- [x] 4.1 改 [FileMetricDetailVO.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/vo/FileMetricDetailVO.java) `DuplicationRateItem`：新增 **`totalLines`**（文件总行数，便于验证 重复率=重复行数/总行数）、`duplicationBlockCount`、`hasSnapshot` 字段
- [x] 4.2 改 `CodeMetricsServiceImpl.appendMetricItems` TOTAL_CODE_DUPLICATION_RATE 分支：`loadFileToGroupCountMap` 查 `COUNT(DISTINCT group_id)` 按组去重得块数（`countGroupsByRecordGroupByFile`）+ 查 `file_detail.snapshot_data` 是否非空（`hasSnapshot`），填入新字段
- [x] 4.3 新增 `dto/metrics/FileContentViewQueryDTO.java`（repoId, branchName, pipelineRunId, filePath；JSR-303 校验）
- [x] 4.4 新增 `vo/FileContentViewVO.java`：**segments 结构**——`CodeSegment` 内部类（originalStartLine/originalEndLine/content）、`DuplicationBlockRef` 内部类（blockId(String)/groupId/startLine/endLine/occurrenceCount）；顶层字段 `gitUrl`/`branchName`/`pipelineRunId`/`filePath`/`language`/`totalOriginalLines`/`hasSnapshot`/`segments`/`duplicationBlocks`。**不再拼接 `content` + `lineMapping`**，前端按 `originalStartLine` 渲染行号、省略行占位由前端根据相邻片段行号差计算
- [x] 4.5 新增 `dto/metrics/DuplicationBlockQueryDTO.java`：**groupId + repoId + branchName + pipelineRunId + sourceBlockId(String, 可选)**（branchName+pipelineRunId 用于定位具体扫描记录避免跨扫描混淆；repoId 用于鉴权防越权；sourceBlockId 用于交集定位）
- [x] 4.6 新增 `vo/DuplicationBlockVO.java`：顶层 `groupId`/`contentHash`/`totalCount`/`occurrences`；`Occurrence` 内部类 `blockId(String)`/`occurrenceIndex`/`filePath`/`startLine`/`endLine`/`content`/`contentStartLine`/`contentEndLine`
- [x] 4.7 改 `CodeMetricsService.java` 接口：新增 `getFileContent(query)` 和 `getDuplicationBlockDetail(query)` 方法签名
- [x] 4.8 改 `CodeMetricsServiceImpl.java`：实现 `getFileContent`（查 `code_metrics_file_detail.snapshot_data`：非空→Base64 解码→解析 segments→逐段 Base64 解码 contentB64→**组装 `segments` 列表返回（不再拼接展示串，占位由前端计算）**；为空→`hasSnapshot=false, segments=null, totalOriginalLines=null`，**不走 Git API 降级**；无论是否命中都查 `code_metrics_duplication_block` 按 group 聚合返回 `duplicationBlocks`，`occurrenceCount` 用 `countByRecordAndGroupBatch` 批量预查）
- [x] 4.9 改 `CodeMetricsServiceImpl.java`：实现 `getDuplicationBlockDetail`（按 `(recordId, groupId)` 查该组所有出现位置，按 occurrence_index 排序，逐条 Base64 解码；**`sourceBlockId` 交集定位**：以源代码块内容为基准，在其他 occurrence 的 block content 中定位匹配子区间（取交集）返回交集行号与±5行上下文，避免 occurrence 行数膨胀导致高亮范围偏大；content 优先从 snapshot_data 截取含 [startLine,endLine] 的上下文章段，snapshot 不存在时 fallback 为重复块本身；鉴权校验 groupId 归属 repoId）
- [x] 4.10 改 [CodeMetricsController.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java)：新增 `POST /metrics/code/file-content` 和 `POST /metrics/code/duplication-block/detail` 两个 endpoint，加 `@Valid`
- [x] 4.11 **不修改 [XxlJobHandler.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java)**：本需求移除 TTL 清理逻辑，不新增定时任务
- [x] 4.12 单元测试 + 集成测试：覆盖两个新接口（快照命中/未命中/空数据/同组多位置/同文件多位置）+ 鉴权（groupId 越权返回 403）

## 阶段 5：前端 - 文件代码视图 + 高亮

- [x] 5.1 改 [src/api/Repos/url.ts](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/api/Repos/url.ts)：新增 `FILE_CONTENT` 和 `DUPLICATION_BLOCK_DETAIL` 常量
- [x] 5.2 改 `src/api/Repos/api.ts`：新增 `fileContent` 和 `duplicationBlockDetail` 两个 api 函数
- [x] 5.3 新增 `src/views/Repos/dialog/DuplicationCodeView.vue` 页面：顶部信息栏（代码仓/分支/流水线/返回）+ "该记录无代码快照"占位区（仅 `hasSnapshot=false` 时显示）+ monaco-editor 容器 + 重复块列表容器（`hasSnapshot=false` 时展示）+ drawer 容器
- [x] 5.4 `DuplicationCodeView.vue` 实现 `onMounted` 调 `file-content` 接口；`hasSnapshot=true` → 按 `segments` 渲染代码（每段行号从 `originalStartLine` 起，段间省略行由前端计算并插入 `... N lines omitted ...` 占位）；`hasSnapshot=false` → 隐藏 monaco-editor，展示"该记录无代码快照"占位 + 重复块列表（`duplicationBlocks` 渲染为可点击行）
- [x] 5.5 `DuplicationCodeView.vue` 实现 `highlightAllBlocks`：遍历 `duplicationBlocks`，用 `startLine/endLine` 直接映射到对应 segment 内的展示行号（`toDisplayLine` 工具函数计算），`deltaDecorations` 高亮重复块行范围（淡黄底 `rgba(255,235,59,0.15)`，仅 `hasSnapshot=true` 时）
- [x] 5.6 `DuplicationCodeView.vue` 实现点击高亮块（`hasSnapshot=true`，`onMouseDown` 位置判断）或点击重复块列表项（`hasSnapshot=false`）→ 当前块切换深橙底高亮（`rgba(255,152,0,0.30)` + 左边框）+（`hasSnapshot=true` 时）把 block.startLine 映射为展示行号后 `revealLineInCenter` + 触发 drawer 打开（携带 `groupId` + `currentBlockId`）

## 阶段 6：前端 - Drawer 多页签 + 上下跳转 + 缩放

- [x] 6.1 新增 `src/views/Repos/dialog/DuplicationBlockDrawer.vue` 组件：props(**groupId**, visible, **currentBlockId**) + emit(close, prev, next, resize)
- [x] 6.2 `DuplicationBlockDrawer.vue` `watch(groupId)` → 调 `duplication-block/detail` 拿到该组所有 `occurrences` 列表；`activeTabIndex` 默认选中"非 currentBlockId 的第一个"出现位置
- [x] 6.3 `DuplicationBlockDrawer.vue` 顶部多页签 tabs（每个 occurrence 一个 tab，标签 `basename(filePath):startLine-endLine`）；当前点击位置（currentBlockId 匹配）标记"来源"图标；当前展示位置（activeTabIndex）标记"当前*"样式；tab 数量 > 8 时横向滚动
- [x] 6.4 `DuplicationBlockDrawer.vue` 内部 monaco-editor 只读模式渲染当前 tab 的 `occurrence.content`，行号从 `contentStartLine` 起，高亮 `[startLine, endLine]` 映射到 content 内的行范围；点击 tab 切换 `activeTabIndex` 重新渲染
- [x] 6.5 `DuplicationBlockDrawer.vue` 底部"上一个/下一个"按钮，emit 事件由父组件切换 blockIndex + 用新 `groupId` 重新调 detail
- [x] 6.6 `DuplicationBlockDrawer.vue` 实现放大缩小（三档宽度 30%/50%/70% 按钮 + 拖拽左边缘 resize）
- [x] 6.7 `DuplicationCodeView.vue` 实现 drawer 上下跳转：切换 blockIndex + monaco-editor `revealLineInCenter` + drawer 用新 groupId 重新加载

## 阶段 7：联调 + 验收

- [x] 7.1 改 [MetricsDetailDialog.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue)：metricType=3 文件路径列改为可点击 `<a>`，点击 `router.push` 到 `DuplicationCodeView`，query 携带 `repoId / branchName / pipelineRunId / filePath / runNumber / pipelineLink`
- [x] 7.2 改 `MetricsDetailDialog.vue`：metricType=3 新增"重复块数"列（prop=duplicationBlockCount），无数据时展示 '--'
- [x] 7.3 改 `MetricsDetailDialog.vue`：metricType=4（总文件重复率）列表适配新结构——`identicalFileDetails` 每项只含 `duplicatedFiles` 数组（不含 `filePath`），前端将同组所有文件展示在同一行/同一组，不再双向冗余展示
- [x] 7.4 改 `src/router`：新增 `/repos/duplication-code-view` 路由
- [x] 7.5 端到端联调：插件扫描 → 后端入库 → 前端列表 → 点击文件 → 代码视图 + 高亮 → 点击块 → drawer 多页签展示该组所有出现位置 → tab 切换 → 上下跳转 → 缩放
- [x] 7.6 同文件多位置场景验收：构造 `Foo.java:10-40` 与 `Foo.java:80-110` + `Bar.java:5-35` 同组的用例，验证 drawer 显示 3 个 tab，每个 tab 标签用行号区间区分
- [x] 7.7 旧 record 无快照场景验收：构造旧 record（无 `snapshot_data`）的用例，验证 `file-content` 接口返回 `hasSnapshot=false` + `duplicationBlocks` 仍返回；前端左侧展示"该记录无代码快照"占位 + 重复块列表；点击列表项可正常打开 drawer 查看代码片段；**确认不走 Git API 降级**
- [x] 7.8 总文件重复率验收：构造 A/B/C 三个完全一致文件 + D/E 两个完全一致文件的用例，验证 `identicalFileDetails` 只返回 2 条记录（每条含 `duplicatedFiles` 数组），前端将 A/B/C 展示为一组、D/E 展示为一组，无双向冗余
- [x] 7.9 验收对照 [proposal.md §4 验收标准](./proposal.md#4-验收标准) 逐条核对
- [x] 7.10 安全验收：DBA 直接查表确认 `content_b64` 和 `snapshot_data` 为 Base64 字符串；后端日志 grep "File content" / "Block content" 无代码内容泄露；groupId 越权访问返回 403
- [x] 7.11 性能验收：单文件代码视图 < 500ms（快照命中）；单块详情 < 200ms；drawer tab 切换 < 100ms

## 阶段 8：归档（用户触发 Phase 5 时执行）

- [x] 8.2 写 `archive.md` 沉淀交付历程、设计偏差、可复用经验
- [x] 8.3 更新 `openlibing-docs/spec/openlibing-coderepo/ai_memory.md`（仅沉淀可复用规则）
- [x] 8.4 docs PR 提交归档（分支 `spec_openlibing-coderepo_code-metrics-duplication-code-view`，加 `ai-assisted` 标签）
- [ ] 8.1 业务 Issue 关闭 / 状态更新（待业务 PR 合入后处理）
