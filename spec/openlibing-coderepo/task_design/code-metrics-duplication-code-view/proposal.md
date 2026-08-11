# 代码重复率详情 - 展示具体重复代码

> 跨仓 Full 模式需求。涉及 `openlibing-cicd-test-new`（插件）、`openlibing-coderepo-fork`（后端+DB）、`openlibing-web`（前端）三个仓。
>
> 关联业务 Issue：待创建（Phase 1 时通过 `gitcode issue create` 在 `openlibing/openlibing-coderepo` 仓创建，标题：`【openLiBing】代码重复率详情展示具体重复代码`）。
>
> 前序相关 spec：`openlibing-docs/spec/openlibing-coderepo/task_design/code-metrics-drill-down/`（已有"指标下钻"基础能力，本次在此基础上扩展重复代码块维度）。

## 1. 需求背景

`openlibing-coderepo` 当前已支持代码度量指标的下钻展示（5 类指标：代码规模、平均函数代码行、平均圈复杂度、总代码重复率、总文件重复率），其中"总代码重复率"指标当前只能下钻到「文件粒度」—— 用户能看到某文件重复率是多少、重复了多少行，但**看不到具体哪几行重复、与哪个文件的哪几行重复、重复的代码内容是什么**。

用户解决重复代码问题时，必须知道：
- 重复代码在源文件中的具体位置（哪几行）
- 与之重复的配对文件路径 + 配对位置
- 重复代码的具体内容（便于直接定位修改）

当前用户拿到"某文件重复率 35%、重复 120 行"后，仍需自行 clone 仓库、人工查重，体验割裂。本次需求把"具体重复代码"直接展示在平台上，让用户在网页上即可完成"查看 → 定位 → 修改"闭环。

## 2. 用户故事

**作为**仓库维护者，**我希望**在代码重复率详情页点击某个文件后，能看到该文件中重复代码块及其上下文（重复块±5行，其他部分以 `...` 占位）并将重复代码块重点标注，**并能**在侧边栏看到与之重复的配对文件代码片段，**以便**我直接定位并消除重复代码。

**子故事**：
1. 点击文件路径 → 弹出代码查看视图，左侧展示该文件重复块上下文片段拼接代码（非完整文件，远离重复块的部分以 `... N lines omitted ...` 占位），重复代码块用底色高亮
2. 点击某个高亮重复块 → 右侧 drawer 展示该重复块组的所有出现位置（多页签）
3. drawer 顶部每个页签对应一个出现位置（文件名:行号区间），包括源文件自身的其他位置和其他文件的位置；点击页签切换查看不同出现位置的代码片段
4. drawer 内"上一个 / 下一个"按钮 → 跳转到当前文件的相邻重复块（同步高亮 + 同步切换 drawer 内容）
5. drawer 支持放大缩小（拖拽边缘或按钮切换宽度档位）

## 3. 功能描述

### 3.1 做什么

| 模块 | 改造内容 |
|------|---------|
| 插件 `code-metrics-action` | `DuplicationDetector` 在现有 `fileDetails` 基础上，新增上报 `duplicationOccurrences`：同一代码内容的所有出现位置归为同一 group（group_id），每个出现位置含文件路径、起止行、代码内容、内容 hash。`CoderepoUploader` 上报前对代码内容做 Base64 编码。`identicalFileDetails` 每组只保留 `duplicatedFiles` 数组（含组内所有文件），不再含 `filePath` |
| 后端 `openlibing-coderepo` | 新增表 `code_metrics_duplication_block`（出现位置表，长期保留，按 group_id 关联）；**不再单独建 `code_metrics_file_snapshot` 表**，上下文片段快照直接存入 `code_metrics_file_detail.snapshot_data` 字段（**无 TTL 长期保留**，仅存重复块±5行上下文，其他部分以 `...` 占位）；**DTO/Entity 移除 `code_metrics_record.repository` 字段（DB 层 `repository` 列保留不 drop，不再使用，便于回滚）**；扩展上报接口接收新字段并入库；扩展详情查询接口返回 group 列表；新增"文件代码视图"和"重复块详情"两个查询接口，另新增"重复块分批上报"接口（`/metrics/code/duplication-blocks`，超过单批 5000 时后续批次走此接口） |
| 前端 `openlibing-web` | 在 `MetricsDetailDialog`（metricType=3）的文件列表行内，点击文件路径跳转到新页面 `DuplicationCodeView`：monaco-editor 展示上下文片段拼接代码（重复块±5行 + `...` 占位）+ 重复块高亮（用 lineMapping 转换行号）；点击高亮块弹出右侧 drawer，drawer 顶部多页签展示该组的所有出现位置（每个 tab 一个文件位置），点击 tab 切换查看对应代码片段；上一个/下一个切换 + drawer 缩放 |

### 3.2 不做什么（Non-Goals）

- ❌ **不**改造 `metricType=4`（总文件重复率，完全一致文件）的代码展示：完全一致文件的"重复内容"就是整个文件，展示价值低，且 duplicatedFiles 列表已能满足
- ❌ **不**支持跨 record 的重复块对比（即不对比同文件不同扫描时点的重复变化）
- ❌ **不**做重复块的"忽略 / 抑制"功能（类似 codecheck 的 suppression），后续单独需求
- ❌ **不**做代码 diff 视图（配对块展示原始内容即可，不做逐行 diff）
- ❌ **不**做服务端实时重算重复率（沿用扫描时点结果）
- ❌ **不**做代码 AI 修复建议

### 3.3 核心问题决策：代码缓存策略

> 这是本需求最关键的架构决策，单独成节。

#### 3.3.1 候选方案对比

| 方案 | 完整文件来源 | 重复块存储 | 优点 | 缺点 |
|------|------|------|------|------|
| **A. 实时拉取 + 不存代码** | Git 平台 API 实时拉取 | 只存行号区间 | DB 零增长、永远最新代码 | 慢、依赖 Git 平台可用性、API 限流、历史扫描时点的代码无法复现、行号会因代码变更而错位 |
| **B. 全量缓存** | 编码入库（全文件） | 编码入库 | 完整可追溯、行号严格对齐 | DB 膨胀严重（10 万行仓 ≈ 数十 MB）、隐私风险大、上报体量大、同一文件未变更时多次冗余存储 |
| **C. 只存重复块 + 完整文件实时拉取** | Git 平台 API 拉取（带短缓存） | 编码入库 | DB 体积可控、隐私风险低 | 完整文件查看仍依赖 Git 平台、历史代码可能错位（用户看的是 N 天前扫描结果，但代码已变更） |
| **D. 只存重复块 + 上下文片段快照（无 TTL，长期保留）** ✅ | 编码入库（仅重复块±5行上下文，长期保留），其他部分以 `...` 占位 | 编码入库 | 可追溯、行号严格对齐（通过 lineMapping 映射）、DB 体积大幅压缩（大文件省 90%+）、隐私风险低、历史记录完整可查 | 实现复杂度增加（需拼接展示代码 + 行号映射）、DB 有一定膨胀（用上下文 ±5 行 + 片段合并控制） |

#### 3.3.2 推荐方案：D

**理由**：
1. **重复块必须入库**：详情展示的核心数据，必须可追溯（用户看的是历史 pipelineRunId 的扫描结果，无法重新计算）
2. **上下文片段快照（非完整文件）**：保证用户看到的代码与扫描时点一致，行号严格对齐。若用方案 C（实时拉取），用户看历史扫描结果时，代码已变更，重复块行号会指向错误位置，体验崩塌。但**不必缓存完整文件**——用户关注的是重复块本身及其紧邻上下文，完整文件中远离重复块的代码对定位重复问题价值很低。因此快照仅存"重复块 ±5 行上下文片段"（合并重叠/相邻区间），其他部分前端用 `... N lines omitted ...` 占位。后端解析片段 JSON 拼接展示代码时同步构建 `lineMapping`（展示行号 ↔ 原始行号），前端高亮和跳转用 lineMapping 转换行号，保证行号严格对齐。相比全量缓存：大文件存储节省 90%+，DBA 解码后只能看片段无法还原完整文件，隐私风险更低
3. **无 TTL，长期保留（优先保证历史记录完整）**：上下文片段仅存重复块 ±5 行（合并后体积已大幅压缩，大文件省 90%+），DB 膨胀可控，无需 TTL 清理。**优先保证用户能看到完整的历史记录**——用户回溯任意一次扫描结果时，上下文片段代码都应可见，不因过期而降级。**快照未命中（旧 record 无 `snapshot_data`）不走 Git API 降级拉取完整文件**——因为重复块行号是扫描时点的，拉最新代码会导致行号错位、高亮指错位置，"看似能看实则错位"的误导比"提示无快照"更差；改为直接提示"该记录无代码快照"。但重复块代码片段（`code_metrics_duplication_block` 表，长期保留）仍可查看，drawer 内片段行号从 1 重新编号，不存在错位问题
4. **编码**：Base64（参考 codecheck 的 [FragmentCryptoUtil.java](file:///d:/Develop/Java/openlibing-codecheck/src/main/java/com/openlibing/codecheck/common/utils/security/FragmentCryptoUtil.java)），主要防止"明文出现在日志和 DBA 一眼可见"。若后续合规要求升级（如等保三级要求加密存储），可平滑升级为 AES-256（密钥从配置中心读取，不硬编码）
5. **hash 算法选用 SHA-256**：重复块内容 hash 用于"同一代码内容的出现位置归为同一组"的分组键。虽本场景 hash 非安全用途（不做完整性校验/签名），但 MD5 已被标记为不安全算法，review 中易引发争议；SHA-256（hex 编码，64 字符）消除该争议，`content_hash VARCHAR(64)` 字段长度刚好适配，无额外存储成本

#### 3.3.3 数据量预估

假设一个 10 万行代码仓（5000 文件，平均 200 行/文件）：
- 重复块：假设 5% 文件有重复，每文件平均 2 个块，每块平均 30 行 → 500 块 × 30 行 ≈ 1.5 万行代码 ≈ 600 KB 原文 / ≈ 800 KB Base64
- 文件快照（上下文片段，存于 file_detail.snapshot_data）：仅缓存有重复文件中重复块±5行上下文，合并重叠区间后 ≈ 500 块 × (30 行块 + 10 行上下文) ≈ 2 万行 ≈ 0.8 MB 原文 / ≈ 1 MB Base64（含 JSON 结构开销）；相比全量缓存（≈ 2 MB）节省约 50%，对大文件稀疏重复场景节省可达 90%+
- 单仓单次扫描：≈ 1.8 MB 入库
- 100 个仓 × 每周 1 次扫描 × 长期保留（无 TTL）≈ 100 MB/周 ≈ 5 GB/年（可接受；如需清理可按 record.create_time 统一清理过期 record）

可接受。

## 4. 验收标准

### 4.1 功能验收

- [ ] 插件扫描后，后端 `code_metrics_duplication_block` 表有对应 record 的出现位置记录，同一 group_id 的所有出现位置归为同一组
- [ ] 插件扫描后，**同文件内重复代码块也被检测到**（如文件内部多个相同 catch 块），对应的出现位置记录在 `code_metrics_duplication_block` 表中，且同组出现位置（含同文件其他位置）归为同一 group_id
- [ ] 插件扫描后，后端 `code_metrics_file_detail.snapshot_data` 字段有"含重复块文件"的上下文片段快照（仅重复块±5行上下文，非完整文件）；无重复的文件该字段为 NULL
- [ ] 插件扫描后，`identicalFileDetails` 每组完全一致文件只生成一条记录，只含 `duplicatedFiles` 数组（含组内所有文件），不再含 `filePath`；前端总文件重复率列表将同组文件展示在一起
- [ ] 后端 `reportMetrics` 接口具备幂等性：相同 `gitUrl + branchName + pipelineRunId` 重复上报时，先删除旧记录及其 file_detail，再插入新记录，不产生重复的 file_detail 数据
- [ ] 后端 `CodeMetricsReportDTO` / `CodeMetricsRecordEntity` **不再有 `repository` 字段**（写死 source-dir 后冗余，工作流所在仓 git_url 即扫描仓）；DB 层 `code_metrics_record.repository` 列**保留不 drop**（不再使用，便于回滚）
- [ ] `reportMetrics` 返回 `recordId`（String 类型），避免雪花 ID 在 JS 侧 Number 精度溢出 2^53
- [ ] 前端"总代码重复率"详情列表（metricType=3）点击文件路径，跳转到 `DuplicationCodeView` 页面
- [ ] `DuplicationCodeView` 页面用 monaco-editor 展示拼接后的展示代码（重复块±5行上下文片段 + `... N lines omitted ...` 占位行），重复块用底色高亮（通过 lineMapping 把原始行号转换为展示行号后高亮）
- [ ] 旧 record 无 `snapshot_data`（本需求上线前已扫描的数据）时，`DuplicationCodeView` 左侧代码区显示"该记录无代码快照"占位，**不走 Git API 降级拉取**；但仍展示该文件的重复块列表（来自 `code_metrics_duplication_block` 表，长期保留），用户可点击列表项打开 drawer 查看重复块代码片段
- [ ] 点击高亮块，右侧 drawer 弹出，drawer 顶部多页签展示该组的所有出现位置（每个 tab 标签为"文件名:起始行-结束行"）
- [ ] 一个块在包括源文件自身的多个位置重复时（含同文件多位置，如 `Foo.java:10-40` 和 `Foo.java:80-110`），每个位置都是独立 tab，可切换查看；同文件其他位置的 tab 标签也包含行号区间便于区分
- [ ] 点击 drawer 内任意 tab，切换展示对应出现位置的代码片段
- [ ] drawer 内"上一个 / 下一个"按钮可切换当前文件的相邻重复块（高亮同步滚动 + drawer 内容同步切换）
- [ ] drawer 支持放大缩小（至少 3 档宽度，或拖拽边缘）
- [ ] DBA 直接查询数据库表，`content_b64` 和 `snapshot_data` 字段为 Base64 字符串，非明文代码
- [ ] 后端日志不打印任何代码内容（含 Base64 编码后的字符串），只打印 `filePath + lineRange + blockId + groupId`

### 4.2 性能验收

- [ ] 单文件代码视图接口（含上下文片段拼接代码 + lineMapping + 重复块列表）响应 < 500ms（快照命中场景）
- [ ] 单重复块详情接口响应 < 200ms
- [ ] 插件单次上报体量 < 10MB（超过则分批，分批不影响数据完整性）
- [ ] **无 TTL 清理任务**：上下文片段快照随 file_detail 长期保留，不因过期而降级；如需清理历史数据可按 `code_metrics_record.create_time` 统一清理过期 record 及其关联表（不在本期范围内）

### 4.3 安全验收

- [ ] 上报接口沿用 APIG 签名 + HTTPS（已有，不退化）
- [ ] 查询接口（文件代码视图、重复块详情）校验用户对该仓库的访问权限
- [ ] Base64 编解码工具类在 coderepo 仓内独立实现一份（不跨仓依赖 codecheck），实现包含两阶段回检验证（防误判历史明文）
- [ ] 单元测试覆盖：编码 → 入库 → 查询 → 解码 全链路

### 4.4 兼容性验收

- [ ] 旧版插件（未上报 `duplicationOccurrences` / `snapshotData`）扫描的 record，前端详情列表照常展示（无"查看代码"入口，或入口点击后给出"该记录无代码快照"提示）
- [ ] 旧 record（无 `snapshot_data`）查看代码视图时，**不走 Git API 降级拉取完整文件**，左侧显示"该记录无代码快照"占位 + 重复块列表；重复块代码片段（`code_metrics_duplication_block` 表，长期保留）仍可在 drawer 中正常查看
- [ ] 现有 metricType=0/1/2/4 的详情接口行为不变（metricType=4 总文件重复率列表适配新结构：`identicalFileDetails` 不再含 `filePath`，前端将同组文件展示在一起）

## 5. 影响范围

### 5.1 跨仓影响矩阵

| 仓 | 改动类型 | 关键改动 |
|----|---------|---------|
| `openlibing-cicd-test-new` | 插件改造 | `code-metrics-action/dist/detectors/DuplicationDetector.js`（提取重复块内容、`identicalFileDetails` 每组只保留 `duplicatedFiles` 不含 `filePath`）、`dist/uploaders/CoderepoUploader.js`（Base64 编码 + 上报新字段，快照随 `fileDetails` 上报） |
| `openlibing-coderepo-fork` | 后端 + DB | 新增 1 张表（`code_metrics_duplication_block`）+ `code_metrics_file_detail` 新增 `snapshot_data` 字段 + `code_metrics_record` DTO/Entity 移除 `repository` 字段（**DB 列保留不 drop，便于回滚**）+ Entity/Mapper；扩展 `CodeMetricsReportDTO` / `FileMetricDetailVO`；新增 2 个查询接口（file-content、duplication-block/detail）+ 1 个分批上报接口（duplication-blocks）；Base64 工具类；**不新增 TTL 清理 job** |
| `openlibing-web` | 前端 | 新增 `DuplicationCodeView.vue` 页面 + `DuplicationBlockDrawer.vue` 组件；`MetricsDetailDialog.vue` 文件路径列改为可点击跳转；新增路由 + API |

### 5.2 接口契约变化

- `POST /metrics/code/report`：**返回类型由 `DataResult<Long>` 改为 `DataResult<String>`**（recordId 用 String 返回，避免雪花 ID 在 JS 侧 Number 精度溢出 2^53）；请求体 **DTO 移除 `repository` 字段**（DB 层 `code_metrics_record.repository` 列保留不 drop，便于回滚）；**移除 `fileSnapshots` 字段**（快照随 `fileDetails` 上报）；新增 `duplicationOccurrences` 可选字段；`fileDetails` 每项新增 `snapshotData` 子字段；`identicalFileDetails` 每项**移除 `filePath`**（只保留 `duplicatedFiles` 数组，含组内所有文件）。旧插件不传新字段则不存相关数据，向后兼容
- 新增 `POST /metrics/code/duplication-blocks`：插件端 `duplicationOccurrences` 超过单批 5000 时，首批随主报告 `/report` 上报，**后续批次走此接口**分批入库。请求体 `DuplicationBlockBatchDTO` 含 `recordId`（String）+ `blocks`（List\<DuplicationOccurrenceDTO\>），返回 `DataResult<Integer>`（本批保存条数）
- `POST /metrics/code/file-detail`：metricType=3 时 `DuplicationRateItem` 新增 `totalLines`、`duplicationBlockCount`、`hasSnapshot` 字段（前端据此判断是否展示"查看代码"入口）；`duplicatedFiles` 属 metricType=4 的 `FileDuplicationItem`（已有结构）
- 新增 `POST /metrics/code/file-content`：**不再返回 `content` + `lineMapping`**，改为返回 `segments`（List\<CodeSegment\>，每段含 `originalStartLine` / `originalEndLine` / `content` 明文）+ 该文件所有重复块元信息（含 groupId，按 group 去重）。前端按片段渲染，行号直接用 `originalStartLine` 递增；片段间省略行数由前端按相邻片段行号差计算并插入 `... N lines omitted ...` 占位
- 新增 `POST /metrics/code/duplication-block/detail`：按 groupId 查询该组所有出现位置（含每个位置的代码内容），前端渲染为多页签。请求 `DuplicationBlockQueryDTO` 新增 `branchName`、`pipelineRunId`（定位具体某次扫描，避免同 group_id 跨多次扫描混淆）与可选 `sourceBlockId`。`sourceBlockId` 用途：同组各 occurrence 行数可能不同（union-find 分组导致，如文件 B 的 20 行块和文件 A 的 10 行块归为同组），以其对应代码块内容为基准，在其他 occurrence 的 block content 中定位匹配子区间（取交集），返回交集部分行号与 ±5 行上下文，使前端精确高亮"与源代码块真正重复"的部分；未传时退化为原行为
