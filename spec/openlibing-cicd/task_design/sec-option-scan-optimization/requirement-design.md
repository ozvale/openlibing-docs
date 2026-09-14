# 安全编译选项扫描能力优化 需求设计文档

> 单仓 Standard 模式需求设计文档。涉及 `security-compilation-options-action`（插件）、`openlibing-cicd-fork`（后端）、`openlibing-cicd-web`（前端，vue3 + Element Plus）。
>
> 目标：解决安全编译选项扫描能力的四个问题——① 概览展示的"总扫描数/满足数"无法自洽得到满足率；② 扫描项无法按项目关注范围裁剪，默认返回全部 14 项；③ 后端不支持对"指定文件的指定扫描项"做例外备案（NO 值被用户接受后应能覆盖统计）；④ 前端三级页面交互 + 插件 filePath 规范化由源头解决。另顺带修复纯 Go 二进制 fortify/ftrapv 恒 NO 拉低开启率的问题。备案/取消备案为审计敏感操作，通过**专用角色「安全编译选项例外备案审批人」**鉴权；备案人、备案时间**直接落在例外备案表**，不再单独维护操作日志表。

## 1. 方案设计

### 1.1 背景与目标

安全编译选项扫描插件（security-compilation-options-action）已具备 14 项扫描 + 上报 + 概览/文件详情查询能力，现有实现存在以下问题：

| 问题           | 现状                                                                                                                    | 目标                                                                                                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 实际扫描数缺失 | 概览展示的 totalFiles 是"参与该项检测的文件总数"，与 yesCount 相除得到的是"满足数/总文件数"，无法得到用户理解的"满足率" | 透出"实际扫描数/实际参与数"，使满足率 = 满足数 / 实际参与数自洽                                                 |
| 扫描项不可裁剪 | 默认返回全部 14 项结果，项目无法只关注部分项                                                                            | 复用插件 scan-options 链路，未扫描项带标识，前端不展示                                                          |
| 无毒例外的备案 | 后端不涉及任何例外备案/豁免/覆写机制，NO 值每次扫描都原样返回                                                           | 支持按"项目+仓库+产物包+文件+选项"做例外备案，备案值覆盖扫描值参与统计，后续扫描自动生效                        |
| 前端信息过载   | 概览页每个扫描项都展示总文件数/满足数/开启率，信息过多                                                                  | 三级页面 + 独立备案记录页：概览（汇总）→ 详情（逐扫描项明细）→ 待备案项列表（批量备案）→ 备案记录页（跨包总览） |

**确认结果覆盖率语义**（二级详情页核心对比指标，分母沿用"实际参与数"）：

```
检测结果覆盖率 = 满足数 / 实际参与数 × 100%           // 实际参与数 = 满足数 + 不满足数（N/A 不参与）
确认结果覆盖率 = 备案后满足数 / 实际参与数 × 100%      // 备案值为 YES 的文件改判满足，为 NO 的改判不满足
  · 未备案文件按原扫描值计入
  · 用户不做任何备案时，确认结果覆盖率 == 检测结果覆盖率
```

### 1.2 整体架构

```
security-compilation-options-action（插件）
  ① filePath 源头规范化：上报"包内相对路径"（相对扫描根，'/' 分隔，去除随机解压临时目录前缀）
  ② summary 增加 totalScannedFiles（实际扫描 ELF 文件总数，修复日志"Total files 恒为 0"）
  ③ 纯 Go 二进制 fortify/ftrapv 返回 N/A（与 sp 一致）
        │ 上报（payload 结构不变，字段值增强）
        ▼
openlibing-cicd-fork（后端）
  ④ 上报入库应用生效备案：sec_option_scan_file_detail 存 rawOptions（原始值）+ options（备案覆盖后值），
     overview_data 用备案后值统计
  ⑤ 备案增删改时，重算该（项目+仓库+产物包）最新一条记录 options 与 overview_data
  ⑥ /overview、/file-detail 出参按记录实际扫描项返回，未扫描项带 UNSCANNED 标识，
     透出 totalScannedFiles / applicableFiles / 检测覆盖率 / 确认覆盖率 / 已确认文件数 / 备案标识与原值
  ⑦ 备案/取消备案仅限「安全编译选项例外备案审批人」角色操作；备案表直接落备案人 + 备案时间
        │
        ▼
openlibing-cicd-web（前端，vue3）
  ⑧ 三级页面：概览（基础信息+汇总）→ 详情（逐扫描项明细+备案）→ 待备案项列表（NO 项筛选+批量备案）
  ⑨ 文件详情弹窗：详情页点击检测结果数字进入，文件×扫描项矩阵展示所有文件的扫描值与备案值，每列表头（文件路径 + 各扫描项）提供筛选按钮，支持按路径关键词与扫描项值（YES/NO/N/A）逐列筛选、分页
  ⑩ 隐藏 UNSCANNED 扫描项；备案操作集中在二级详情页与三级列表页（方案一）；文件上传解析作为备选方案（方案二，见 §1.6）
  ⑪ 前端最外层（页面顶部导航）新增「备案记录」入口，进入独立「安全编译选项备案记录」页面，展示所有产物包备案记录，支持按产物包/扫描项/备案时间/备案人筛选
  ⑫ `/overview` 分页由内存分页下推为 SQL 分页（LIMIT/OFFSET + COUNT），避免项目记录量大时全量加载
```

> 注：备案为新功能，不兼容历史数据，因此 filePath 只需插件源头相对化，后端不再做 normalize 存量兜底。

### 1.3 关键设计决策

| 决策点          | 选择                                                                          | 理由                                                                                                                                                      |
| --------------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 关注项裁剪      | 复用插件 scan-options 数据链路，后端出参补全标识，不新建配置表                | scan-options 未扫描项 key 本就不写入 overviewData/fileDetails 的 options，后端已能从 JSON key 提取 scanOptions；零新表、插件零改动，避免额外配置接口      |
| 未扫描项标识    | overview 未扫描项 `{"scanned":false}`；file-detail 未扫描项值 `"UNSCANNED"`   | 标识在查询出参时注入，插件上报数据与存量记录均无需迁移                                                                                                    |
| 例外备案方式    | 方案一·页面列表筛选批量备案（推荐）；方案二·文件上传解析（备选，见 §1.6）     | 方案一直击用户高频场景（处理 NO 项），把"文件×选项矩阵"降维为"NO 项列表"，数据量天然大幅减少，避免大矩阵渲染卡顿；批量场景用筛选+全选跨页保留勾选即可完成 |
| 备案存储物化    | file_detail 存 rawOptions + options 两列；备案为独立表，查看时动态应用        | 备案增删改只重算最新一条记录，查询路径零额外 JOIN；保留 rawOptions 便于展示"原值→备案值"                                                                  |
| 备案匹配键      | 项目 + 仓库(gitUrl) + 产物包(packageName) + 文件相对路径(filePath) + 选项 key | 精确匹配，避免误伤同包内不同文件或不同选项                                                                                                                |
| filePath 规范化 | 插件源头相对化，后端不做 normalize 存量兜底                                   | 备案为新功能、不兼容历史数据；源头消除随机临时目录前缀即可保证每次扫描文件名一致                                                                          |
| 产物包覆盖      | 备案按"仓库+产物包+文件相对路径+选项"匹配，不依赖每天具体构建                 | 每天同名产物包覆盖后，相对路径仍是稳定的匹配键；产物文件名变化时备案自然失效，不误伤                                                                      |
| 备案审计方式    | 备案人 + 备案时间直接落在 `sec_option_filing` 表，不单独建操作日志表          | 备案记录本身即审计主体，去重冗余日志表、避免双写不一致；字段集中在备案表上，查询/筛选天然支持                                                             |
| 备案操作鉴权    | 专用角色「安全编译选项例外备案审批人」控制备案写操作                          | 备案为豁免敏感操作，需与普通查看权限区分；复用既有 `user_role_info` 角色体系按角色名校验，零新权限表                                                      |

### 1.4 流程模式与风险

**Standard 模式**。判定依据：

- 改动规模约 200-400 行，跨 3 个仓（插件/后端/前端），单模块内多文件。
- 无外部接口契约变化（现有上报/查询接口不新增路径，仅扩展字段）；有 schema 变化（新增备案表 + file_detail 新增 rawOptions 列）。
- 安全影响低（备案为项目内自操作，需专用角色鉴权但无新凭证/无注入风险面扩展）。

| 风险                                                     | 对策                                                                                                                   |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 产物文件名跨构建变化（工具链/CANN 版本变化）导致备案失效 | 备案按相对路径精确匹配，失效不误伤；靠备案记录页管理清理失效项                                                         |
| 备案表与扫描记录不同步                                   | 备案独立表，key 不依赖 record id；重算逻辑幂等                                                                         |
| 前端 wujie 子应用新标签页跨路由同步失效                  | 在 App.vue hostRouteMap 补充新路由映射                                                                                 |
| 未配置「安全编译选项例外备案审批人」角色导致无人可备案   | 角色为外部数据（user_role_info），上线前由管理员为相关用户赋权；后端角色校验失败直接返回无权限，前端隐藏备案写操作入口 |

### 1.5 回滚

- 存量为 base，备份 `overview_data` JSON 后重算即可回滚。归档文档保留，设计结论不依赖单一仓。

### 1.6 例外备案交互方式方案对比

针对"产物包文件数过多时的备案性能与操作效率"问题，评估两种方案：

#### 方案一：页面列表筛选 + 批量备案

将"文件×选项矩阵"降维为"待备案项列表"：

- **默认只展示 NO（不满足）项**：用户做备案的高频场景是"处理 NO 项"，YES/N/A 不需要操作。数据量从 `文件数 × 选项数`（如 500×14=7000）降到 `NO 项数`（通常几十到几百），天然解决渲染卡顿。
- **筛选 + 全选当前筛选结果（跨页保留勾选）**：按扫描项筛选（如只看 fortify）→ 全选当前筛选结果 → 批量备案为 YES，三步完成批量场景。
- **分页每页 50-100 条**，跨页保留勾选状态，顶部批量操作栏显示已选数。

| 维度         | 评价                                          |
| ------------ | --------------------------------------------- |
| 渲染性能     | 好（NO 项数远小于矩阵单元格数，无需虚拟滚动） |
| 操作效率     | 高（筛选+全选+批量，直击高频场景）            |
| 即时反馈     | 有（备案后确认覆盖率实时更新）                |
| 增删改对称   | 是（页面增删体验一致）                        |
| 基础设施依赖 | 无                                            |
| 适用规模     | NO 项百级以内完美；千级仍可分页但优于矩阵     |

#### 方案二：文件上传解析（备选）

下载含全部扫描结果的模板文件（CSV/Excel）→ 用户离线填写备案列 → 上传到 OBS 桶 → 后端解析应用备案。

| 维度         | 评价                                                                 |
| ------------ | -------------------------------------------------------------------- |
| 渲染性能     | 好（后端流式解析，前端无渲染压力）                                   |
| 操作效率     | 低（下载-填写-上传多步，离线填写看不到实时效果；增量操作需重传全量） |
| 即时反馈     | 无（上传解析完才知道结果）                                           |
| 增删改对称   | 否（删除备案需重新生成全量文件上传）                                 |
| 基础设施依赖 | 高（OBS 桶、文件版本管理、失效清理、覆盖冲突）                       |
| 适用规模     | 大（千级文件超大批量离线处理才有优势）                               |

**选型结论**：方案一直击用户高频场景（处理 NO 项）且无额外基础设施依赖，本期采用方案一。方案二以"用管理复杂度换渲染性能"为代价，且只解决渲染问题不提升操作效率，仅在"产物包文件数千级以上、且需离线批量处理"的极端场景才有优势，作为备选方案记录，本期不实现。如后续出现该场景，方案二的备案数据模型（§4）与重算逻辑（§2.2）可复用，仅需新增"模板下载 + 文件上传 + 解析入库"链路，与方案一不冲突。

## 2. 实现逻辑设计

### 2.1 插件侧（security-compilation-options-action）

1. **filePath 源头相对化**：`scan_directory` 遍历时记录扫描根目录（压缩包解压根或 artifact-path 目录本身），`analyze_single` 产出的 `filePath` 改为 `os.path.relpath(file_path, scan_root)`，统一 `/` 分隔、去除 `./` 前缀。备案为新功能，仅源头相对化即可，后端无需 normalize 存量兜底。
2. **totalScannedFiles**：summary 增加 `totalScannedFiles`，统计实际解析的 ELF 文件总数。
3. **纯 Go 豁免**：`fortify()`、`ftrapv()` 增加 `is_go_file() and not is_cgo_file()` 时返回 N/A（与 `sp()` 一致）。

### 2.2 后端（openlibing-cicd-fork）

#### 2.2.1 上报入库（reportScan）

- `file_detail` 表新增 `raw_options` 列，原 `options` 列存"备案覆盖后值"。
- 上报时对每个 file 的 options 应用当前生效备案：命中备案的选项用备案值覆盖，未命中的保持原值；`raw_options` 存原始扫描值。
- `overview_data.options` 的 totalFiles/yesCount/rate 用备案后值重算（applicableFiles = 参与检测且非 N/A 的文件数）。

#### 2.2.2 备案 CRUD（新增，含角色鉴权）

- 备案独立表 `sec_option_filing`，增删改后重算该（项目+仓库+产物包）**最新一条**成功记录的 file_detail.options 与 record.overview_data。
- 重算幂等：先读该记录所有 file_detail 的 raw_options，再按备案表覆盖，回写 options + overview_data。
- **角色鉴权**：`saveFiling` / `deleteFiling` 仅允许「安全编译选项例外备案审批人」角色操作。后端从请求 Cookie 的 `token` 解析当前登录 userId，调用 `UserRoleMapper.hasRole(userId, role)` 校验是否持有该角色，否则抛 `PermissionException`（403）。
- **备案人/备案时间**：`saveFiling` 写入时直接落 `filer_id`（当前登录 userId）、`filer_name`（账号名）、`filing_time`（当前时间）；`deleteFiling` 为删除操作，不留一行专用日志（审计由备案记录的增删本身体现）。

#### 2.2.3 出参标识注入（overview / file-detail）

- overview：`overviewData.options` 按 14 项枚举补全，未扫描项 `{"scanned":false}`，已扫描项透出 `{totalFiles, applicableFiles, yesCount, rate}`。
- overview 记录级新增 `totalScannedFiles`、`filingCoverage`（确认结果覆盖率）。
- file-detail：`options` 按 14 项枚举补全，未扫描项值 `"UNSCANNED"`；每项透出备案标识与原值（`filedOptions`）。

#### 2.2.4 备案记录查询（独立「安全编译选项备案记录」页）

备案记录跨产物包统一查看，直接查 `sec_option_filing` 表：

- 新增分页查询接口，支持按 **产物包（packageName，模糊）**、**扫描项（optionKey，精确）**、**备案时间（filingStartTime/filingEndTime）**、**备案人（filerName，模糊）** 筛选，另支持代码仓（repoUrl，模糊）筛选与 `projectId` 项目隔离。
- 排序：按 `filing_time` 升/降序（默认降序），`sortByField/sort` 参数下发 SQL（字段白名单）。
- 出参每条含：`repoUrl`、`packageName`、`filePath`、`optionKey`、`filingValue`（备案值）、`reason`、`filerName`（备案人）、`filingTime`（备案时间）。

#### 2.2.5 `/overview` 分页下推 SQL

现网 `/overview` 为内存分页：`queryRecords` 用 `selectList` 全量查出后，在内存 `paginateList`（subList）并配合 `sortRecords` 内存排序。项目记录量大时存在全量加载、排序压力与深分页性能问题。本次将分页与排序下推数据库：

- `queryRecords` 改为 MyBatis-Plus 分页查询（`Page` 对象），`git_url IN (...)`、模糊匹配、时间范围等 WHERE 条件不变，`orderBy` 下推 SQL；`overview` 排序仍支持 `sortByField`（detectionCompletedAt / 数值指标），统一由 SQL `ORDER BY` 执行。
- 分页结果通过 `IPage` 直接返回（total 取 count 查询），去掉 `paginateList` 与 `sortRecords` 内存环节。
- 兼容点：`overview_data.options` 内的数值指标（如 `rate`）现状用于内存数值排序；下推 SQL 后，若按指标排序需在 `overview_data` JSON 中抽取排序列，MySQL 对 JSON 数值排序可借助 `CAST(JSON_EXTRACT(...))` 或新增冗余排序列，优先复用现有 `detection_completed_at` 等物理列排序，指标排序保留为最佳努力（无指标排序列时降级按 `detection_completed_at` 排序）。
- 影响范围：`SecOptionScanServiceImpl.queryRecords`、`SecOptionScanRecordMapper`（新增 `selectPage` / 复用 BaseMapper `selectPage`）、`getOverview` 组装逻辑；出参结构不变（`total/pageNum/pageSize/records`）。

### 2.3 前端（openlibing-cicd-web）

三级页面 + 独立备案记录页：

| 级别              | 路由                         | 展示                                                                                                           | 操作                                                                                  |
| ----------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 一级·概览         | `/sec-option`                | 每行一个产物包记录：代码仓、流水线、产物包名、扫描时间、扫描状态、扫描项数、总文件数                           | 筛选/排序/分页；查看详情；进入备案记录页                                              |
| 二级·详情         | `/sec-option-detail`         | 基础信息 + 安全编译选项汇总表（描述/满足数/实际参与数/检测覆盖率/已确认文件数/确认覆盖率）                     | 备案增删改；进入待备案项列表                                                          |
| 三级·待备案项列表 | `/sec-option-filing-list`    | NO 项展开为行（文件路径/扫描项/扫描值/备案值），默认只展示未备案的 NO 项；分页每页 50-100 条，跨页保留勾选状态 | 按扫描项/路径筛选 + 全选当前筛选结果 + 批量备案为 YES（统一理由）；已备案行高亮可取消 |
| 独立·备案记录     | `/sec-option-filing-records` | 所有产物包的备案记录（代码仓/产物包/文件路径/扫描项/备案值/备案理由/备案人/备案时间）                          | 按产物包/扫描项/备案时间/备案人筛选 + 排序/分页                                       |

- 概览页不展示每个扫描项的覆盖率数字，只保留基础信息（含扫描状态/扫描项数/总文件数）。
- 二级详情页不展示总体的综合开启率/确认覆盖率/需确认项/已确认项，改为逐扫描项对比"检测覆盖率 vs 确认覆盖率"，两个比值均附公式说明；**不再展示本包例外备案列表**（备案记录统一去独立备案记录页查看）。
- 三级列表页**默认只展示 NO（不满足）项**，把"文件×选项矩阵"降维为"NO 项列表"，数据量从 `文件数×选项数` 降到 `NO 项数`（通常远小于前者），避免大矩阵渲染卡顿。批量场景：按扫描项筛选 → 全选当前筛选结果（跨页）→ 批量备案为 YES。YES/N/A 项默认隐藏，取消"只看 NO"可只读查看全貌。
- **文件详情弹窗**（用于包内文件总览，不承担批量备案）：二级详情页"安全编译选项汇总"表的"检测结果（覆盖率）"单元格可点击，弹窗以"文件×扫描项"矩阵展示该产物包所有文件的扫描结果与备案值（所有扫描项列全量罗列）。弹窗每列表头（文件路径 + 各扫描项）提供筛选按钮，点击弹出筛选面板：文件路径列提供路径关键词输入，各扫描项列按值多选（YES/NO/N/A）——筛选按"生效值"判断，即**若该文件该扫描项有备案值，以备案值为准**；有备案的单元格显示"备案值 + 划线原值"，无备案显示原值。矩阵支持分页（每页 10/20/50/100）。该弹窗只读，不提供备案勾选（备案操作在三级列表页完成）。
- 备案方式方案二（文件上传解析）见 §1.6，作为备选能力记录，本期不实现。
- **备案记录展示（独立页面）**：前端最外层（页面顶部导航）新增「备案记录」入口，进入独立的「安全编译选项备案记录」页面，复用现有表格 + 筛选组件：顶部多维筛选（产物包/扫描项/备案时间/备案人），表格展示代码仓/产物包/文件路径/扫描项/备案值/备案理由/备案人/备案时间九列（支持排序与分页）。同一数据（备案表）仅此一处查看，不另设操作日志入口。
- **角色权限**：仅「安全编译选项例外备案审批人」可见/可用备案写操作（详情页备案增删、三级列表批量备案、备案记录页删除）；非该角色用户只读（查看详情/备案记录），备案按钮隐藏或置灰。
- 交互原型见 `demo.html`。

## 3. 类设计

### 3.1 后端新增/修改类清单

| 类                                 | 路径                                                                    | 改动类型                                                                           |
| ---------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `SecOptionScanServiceImpl`         | `business/service/impl/SecOptionScanServiceImpl.java`                   | 修改（上报应用备案、出参标识注入、备案重算、备案记录查询、/overview 分页下推 SQL） |
| `SecOptionScanRecordMapper`        | `business/mapper/SecOptionScanRecordMapper.java`                        | 修改（/overview 分页下推 SQL：复用 BaseMapper `selectPage` 或新增分页查询）        |
| `SecOptionScanService`             | `business/service/SecOptionScanService.java`                            | 修改（新增备案方法签名 + 备案记录查询方法签名）                                    |
| `SecOptionFilingEntity`            | `business/entity/secoption/SecOptionFilingEntity.java`                  | 新增（含 filerId/filerName/filingTime）                                            |
| `SecOptionFilingMapper`            | `business/mapper/SecOptionFilingMapper.java`                            | 新增                                                                               |
| `SecOptionFilingMapper.xml`        | `resources/mapper/SecOptionFilingMapper.xml`                            | 新增（备案记录分页查询 SQL）                                                       |
| `SecOptionScanFileDetailEntity`    | `business/entity/secoption/SecOptionScanFileDetailEntity.java`          | 新增 rawOptions 字段                                                               |
| `SecOptionFileDetailDTO`（内部类） | `dto/secoption/SecOptionScanReportDTO.java`                             | 无变化（上报仍传 options，rawOptions 后端生成）                                    |
| `SecOptionFilingDTO`               | `dto/secoption/SecOptionFilingDTO.java`                                 | 新增（备案增删请求）                                                               |
| `SecOptionFilingRecordQueryDTO`    | `dto/secoption/SecOptionFilingRecordQueryDTO.java`                      | 新增（备案记录分页查询请求，含筛选/排序字段）                                      |
| `SecOptionFilingRecordItem`        | `vo/secoption/SecOptionFilingRecordVO.java`                             | 新增（备案记录出参）                                                               |
| `SecOptionRecordItem`              | `vo/secoption/SecOptionOverviewVO.java`                                 | 修改（新增 totalScannedFiles/filingCoverage）                                      |
| `FileSecOptionItem`                | `vo/secoption/SecOptionFileDetailVO.java`                               | 修改（新增 filedOptions）                                                          |
| `BuildArtifactController`          | `business/controller/BuildArtifactController.java`                      | 修改（新增备案接口 + 备案记录查询接口，备案写接口加角色鉴权）                      |
| `UserRoleMapper`                   | `business/mapper/UserRoleMapper.java`                                   | 修改（新增 `hasRole(userId, role)` 查询）                                          |
| `UserRoleMapper.xml`               | `resources/mapper/UserRoleMapper.xml`                                   | 修改（新增按 userId + role 查询 SQL）                                              |
| `SecOptionRoleConstant`            | `common/constants/SecOptionRoleConstant.java`（或复用 ProjectConstant） | 新增（角色名常量 `安全编译选项例外备案审批人`）                                    |
| Liquibase changeset                | `resources/db/changelog/db.changelog.xml`                               | 新增备案表（含 filerId/filerName/filingTime）+ rawOptions 列                       |

### 3.2 新增服务方法

```java
// 备案增删改（支持批量：request 内通过 items 一次携带多个（文件×扫描项）备案项）
DataResult<List<String>> saveFiling(SecOptionFilingDTO request);   // 批量 create/update（记录备案人 + 备案时间），返回备案记录ID列表
DataResult<Void> deleteFiling(Long filingId);              // 或按 key 删除
// 备案记录跨包查询（独立「安全编译选项备案记录」页）
DataResult<SecOptionFilingRecordVO> listFilingRecords(SecOptionFilingRecordQueryDTO query);
```

备案后统一调用私有方法 `recomputeRecordFiling(Long recordId)` 重算最新一条记录。

## 4. 数据模型设计

### 4.1 新增表 `sec_option_filing`

| 列           | 类型               | 说明                         |
| ------------ | ------------------ | ---------------------------- |
| id           | BIGINT UNSIGNED PK | 雪花 ID                      |
| project_id   | VARCHAR(64)        | 项目隔离                     |
| git_url      | VARCHAR(512)       | 代码仓链接                   |
| package_name | VARCHAR(512)       | 产物包名                     |
| file_path    | VARCHAR(512)       | 规范化文件相对路径           |
| option_key   | VARCHAR(64)        | 扫描项 key（如 fortify）     |
| filing_value | VARCHAR(16)        | 备案值（YES/NO）             |
| reason       | VARCHAR(512)       | 备案理由                     |
| filer_id     | VARCHAR(64)        | 备案人 ID（当前登录 userId） |
| filer_name   | VARCHAR(64)        | 备案人账号名                 |
| filing_time  | DATETIME           | 备案时间                     |
| created_at   | DATETIME           | 创建时间                     |
| updated_at   | DATETIME           | 更新时间                     |

索引：`uk_filing_project_repo_pkg_file_opt`（project_id, git_url, package_name, file_path, option_key 唯一）；`idx_filing_project_time`（project_id, filing_time）；`idx_filing_repo_pkg`（git_url, package_name）。

### 4.2 修改表 `sec_option_scan_file_detail`

新增列 `raw_options` JSON（Liquibase changeSet），存原始扫描值；现有 `options` 列语义变为"备案覆盖后值"。

### 4.3 无其他 schema 变化

`sec_option_scan_record` 表结构不变（overviewData JSON 字段内新增 applicableFiles/filingCoverage 等 key，属 JSON 内容变化非表结构变化）。备案审计（备案人/备案时间）直接落在 `sec_option_filing` 表，不再单独维护 `log_build_artifact` 操作日志表。

## 5. 性能设计

- 备案重算只针对"最新一条"记录，单次重算只读该记录 file_detail 行 + 备案表匹配，O(n) 且 n = 单包文件数（百级），无全表扫描。
- overview 查询仍透传已有 totalFiles/yesCount，仅出参时内存补全 14 项枚举（常量复杂度），无额外 SQL。
- `/overview` 分页与排序下推 SQL（LIMIT/OFFSET + COUNT），避免全量加载与深分页；WHERE 条件沿用现有 `git_url IN (...)` 项目隔离 + 模糊匹配 + 时间范围。
- 备案记录查询走 `idx_filing_project_time` + `idx_filing_repo_pkg` 索引，按 projectId + 产物包/备案时间等条件缩小扫描范围；排序按 `filing_time` 索引字段。

## 6. API 接口设计

### 6.1 新增备案接口

| 接口                                                 | 说明                                                                                                                                        |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /build-artifact/sec-option/filing/save`        | 创建/更新备案（**支持批量**，入参 SecOptionFilingDTO 的 items 列表一处携带多条，需「安全编译选项例外备案审批人」角色，记录备案人/备案时间） |
| `POST /build-artifact/sec-option/filing/delete`      | 删除备案（按 filingId 或 key，需同角色）                                                                                                    |
| `POST /build-artifact/sec-option/filing/record-list` | 查询所有产物包的备案记录（独立备案记录页，跨包，支持筛选/排序/分页）                                                                        |

### 6.2 现有接口增强

**`POST /build-artifact/sec-option/overview`** 出参变化（一级概览页）：

- `SecOptionRecordItem` 新增 `totalScannedFiles`（Integer）、`filingCoverage`（确认结果覆盖率）字段。
- `overviewData.options` 每项透出 `{totalFiles, applicableFiles, yesCount, rate}`，适用性字段 applicableFiles 补充到 options 内。
- 未扫描项标识：按 14 项枚举补全，未扫描项为 `{"scanned":false}`。
- 分页下推 SQL：`pageNum/pageSize` 下放到 `SecOptionScanRecordMapper` 分页查询（LIMIT/OFFSET + COUNT），出参 `total/pageNum/pageSize/records` 结构不变，前端无需调整。

**`POST /build-artifact/sec-option/file-detail`** 出参变化（二级/三级页）：

- 未扫描项标识：`FileSecOptionItem.options` 按 14 项枚举补全，未扫描项值为 `"UNSCANNED"`。
- `FileSecOptionItem` 新增 `filedOptions`（Map<String,String>：已备案选项 → 原始扫描值）。
- `filePath` 为包内相对路径（插件源头已相对化，后端直接透传）。

### 6.3 新增备案记录查询接口

| 接口                                                 | 说明                                                                                                                                            |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /build-artifact/sec-option/filing/record-list` | 备案记录分页查询（projectId 隔离，支持 packageName / optionKey / filerName / filingStartTime / filingEndTime / repoUrl 筛选 + filingTime 排序） |

出参字段与展示列对应：代码仓 `repoUrl`、产物包 `packageName`、产物文件 `filePath`、扫描项 `optionKey`、备案值 `filingValue`、备案理由 `reason`、备案人 `filerName`、备案时间 `filingTime`。独立备案记录页复用此接口。

## 7. 安全设计

- 备案接口复用现有 sec-option 上报/查询的网关鉴权，并叠加**专用角色「安全编译选项例外备案审批人」校验**：仅持有该角色的用户可备案/取消备案，普通查看用户只读。项目隔离通过 matching key 含 project_id 保证跨项目不串数据。
- filePath 规范化 + 相对化避免绝对路径泄露到前端展示。
- 备案值仅 YES/NO 枚举校验，拒绝任意字符串写入。
- 备案人/备案时间取自后端 JWT（cookie token）解析，不信任前端入参，防止伪造备案人；备案表只增删（更新时保留原始备案人时间或重写，见实现），不落 token/凭证等敏感信息。
- 角色查询仅复用 `user_role_info` 只读校验，无新增第三方 API 调用、无新增凭证、无注入风险面扩展。

## 8. 验收标准

- [ ] 插件上报 filePath 为包内相对路径，每次扫描同一产物包文件名一致；summary 含 totalScannedFiles；纯 Go fortify/ftrapv 为 N/A。
- [ ] 后端入库应用备案，file_detail 同时存 rawOptions 与备案后 options；备案增删改重算最新一条记录。
- [ ] overview 出参含 totalScannedFiles、filingCoverage、applicableFiles；未扫描项 `{"scanned":false}`；/overview 分页下推 SQL（LIMIT/OFFSET + COUNT），total 准确。
- [ ] file-detail 出参 options 未扫描项为 UNSCANNED，新增 filedOptions。
- [ ] 备案接口增删改查正常，唯一键防重复，project_id 隔离；备案/取消备案仅「安全编译选项例外备案审批人」角色可操作，非该角色返回 403。
- [ ] 备案表直接记录备案人（filer_id/filer_name）与备案时间（filing_time）；不存在 log_build_artifact 表及相关逻辑。
- [ ] 前端概览只展示基础信息；详情展示逐扫描项检测覆盖率 vs 确认覆盖率（附公式），检测结果数字可点击弹出文件×扫描项矩阵（全量列罗列、展示备案值、表头逐列筛选、有备案以备案值为准、分页）；待备案项列表默认只展示 NO 项，支持筛选+全选当前筛选结果+批量备案为 YES（跨页保留勾选）；UNSCANNED 项隐藏。
- [ ] 前端最外层「备案记录」入口进入独立「安全编译选项备案记录」页面，展示所有产物包备案记录（代码仓/产物包/文件路径/扫描项/备案值/备案理由/备案人/备案时间），支持按产物包/扫描项/备案时间/备案人筛选与排序分页。
- [ ] 确认结果覆盖率 = 备案后满足数 / 实际参与数（分母为实际参与数）。
