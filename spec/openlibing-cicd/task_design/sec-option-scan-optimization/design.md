# 安全编译选项扫描能力优化 技术设计

> 单仓 Standard 模式。涉及 security-compilation-options-action（插件）、openlibing-cicd（后端）、openlibing-cicd-web（前端）。设计细节对齐《requirement-design.md》与《interface-design.md》。

## 1. 方案设计

### 1.1 核心思路

解决四个问题——概览满足率不自洽、扫描项不可裁剪、无例外备案机制、前端信息过载。核心交付：

1. **插件**：filePath 源头相对化；summary 增加 `totalScannedFiles`；纯 Go fortify/ftrapv 返回 N/A；按失败文件数上报部分成功状态(0/1/2)。
2. **后端**：备案不落快照，查询实时 `LEFT JOIN sec_option_filing` 关联；overview/file-detail 出参补全未扫描项标识与覆盖率；/overview 分页与排序下推 SQL。
3. **前端**：三级页面 + 独立备案记录页 + 文件详情矩阵弹窗 + 角色控制备案写操作。

### 1.2 覆盖率口径

```
实际参与数 = 满足数 + 不满足数（N/A 不参与分母）
检测结果覆盖率 = 满足数 / 实际参与数 × 100%
确认结果覆盖率 = 备案后满足数 / 实际参与数 × 100%  // 备案 YES 改判满足、NO 改判不满足；无备案时 == 检测覆盖率
```

### 1.3 关键架构决策

| 决策点       | 选择                                                                                                  | 理由                                                                                      |
| ------------ | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 备案存储     | 不落 filed_options 快照，查询实时 LEFT JOIN `sec_option_filing`                                       | 备案独立表，同一产物历史/未来所有扫描记录天然可见最新备案；无需回填与重算，避免双写不一致 |
| 未扫描项标识 | overview `{"scanned":false}`；file-detail 值 `"UNSCANNED"`                                            | 查询出参时注入，上报数据与存量记录无需迁移                                                |
| 备案匹配键   | projectId + gitUrl + packageName + filePath + optionKey（自然键唯一）                                 | 精确匹配，避免误伤同包不同文件/选项                                                       |
| 备案审计     | filer_id/filer_name/filing_time 直接落备案表                                                          | 备案记录即审计主体，去重冗余日志表；查询/筛选天然支持                                     |
| 备案鉴权     | 网关纵向校验角色码 `security_compilation_options_filing_approver`（或 admin）+ 服务侧项目成员横向校验 | 备案为豁免敏感操作，复用既有角色体系，零新权限表                                          |
| 产物包覆盖   | 与每天具体构建解耦                                                                                    | 备案按"仓库+产物包+文件相对路径+选项"匹配，产物文件名变化时备案自然失效不误伤             |
| 关注项裁剪   | 复用插件 scan-options 数据链路，出参补全标识                                                          | 零新表，插件仅读 JSON key 即可还原 scanOptions                                            |

### 1.4 备案交互方案

- 方案一（采用）：页面"待备案项列表"降维为扁平行，默认只看 NO 项，筛选 + 全选当前筛选结果（跨页）+ 批量备案为 YES。
- 方案二（备选记录，本期不实现）：CSV/Excel 模板下载 → 离线填写 → 上传 OBS → 后端解析入库。仅适用"千级文件离线批量"极端场景；数据模型与查询可复用。

## 2. 实现逻辑设计

### 2.1 插件（security-compilation-options-action）

1. filePath 相对化：`relpath(file_path, scan_root)`，`/` 分隔、去 `./`。
2. summary 增加 `totalScannedFiles`。
3. 纯 Go fortify/ftrapv 返回 N/A。
4. scanner 依据 `summary.failedCount`/`totalScannedFiles` 计算 status(0/1/2)。

### 2.2 后端（openlibing-cicd）

1. 上报入库：file_detail 存 rawOptions（原始）+ 查询时实时关联备案。
2. 备案 CRUD：`save`（批量 upsert）/`cancel`（按 id 删除），写操作需角色鉴权。
3. 出参注入：overview 补全 14 项、未扫描项 scanned=false、行级 totalScannedFiles/filingCoverage/applicableFiles；file-detail 拆 options（仅已备案= FILED）与 rawOptions（全量原始值，未扫描=UNSCANNED）。
4. `/overview` 分页与排序下推 SQL（LIMIT/OFFSET + COUNT），去掉内存分页。
5. 备案记录查询（record-list）与备案人名单（filer-list）。

### 2.3 前端（openlibing-cicd-web）

三级页面 + 独立备案记录页 + 文件详情矩阵弹窗，详见 §6 路由与《requirement-design.md》§2.3。

## 3. 类设计

| 类                                                                                        | 路径                      | 改动                                                                              |
| ----------------------------------------------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------- |
| `SecOptionScanServiceImpl`                                                                | business/service/impl     | 修改（上报、出参注入、备案关联查询、record-list、filer-list、/overview 分页下推） |
| `SecOptionScanRecordMapper`                                                               | business/mapper           | 修改（/overview 分页查询）                                                        |
| `SecOptionScanService`                                                                    | business/service          | 修改（新增备案/记录查询方法签名）                                                 |
| `SecOptionFilingEntity`                                                                   | business/entity/secoption | 新增（含 filerId/filerName/filingTime）                                           |
| `SecOptionFilingMapper`(+.xml)                                                            | business/mapper           | 新增（filing 分页/关联查询 SQL）                                                  |
| `SecOptionScanFileDetailEntity`                                                           | business/entity/secoption | 修改（rawOptions）                                                                |
| `SecOptionFilingDTO`                                                                      | dto/secoption             | 新增（save 请求，items 批量）                                                     |
| `SecOptionFilingCancelDTO`                                                                | dto/secoption             | 新增（cancel 请求，独立 DTO）                                                     |
| `SecOptionFilingRowQueryDTO` / `SecOptionFilingRecordQueryDTO` / `SecOptionFilerQueryDTO` | dto/secoption             | 新增                                                                              |
| `SecOptionFilingRowVO` / `SecOptionFilingRecordVO` / `SecOptionFilerVO`                   | vo/secoption              | 新增                                                                              |
| `SecOptionRecordItem` / `FileSecOptionItem`                                               | vo/secoption              | 修改（新增字段）                                                                  |
| `BuildArtifactController`                                                                 | business/controller       | 修改（新增备案接口 + 记录/名单查询接口）                                          |
| `SecOptionRoleConstant`                                                                   | common/constants          | 新增（角色码 `security_compilation_options_filing_approver`）                     |
| Liquibase changeSet                                                                       | resources/db/changelog    | 新增备案表                                                                        |

## 4. 数据模型设计

### 4.1 新增表 `sec_option_filing`

| 列                                  | 类型                     | 说明              |
| ----------------------------------- | ------------------------ | ----------------- |
| id                                  | BIGINT UNSIGNED PK       | 雪花 ID           |
| project_id                          | VARCHAR(64)              | 项目隔离          |
| git_url                             | VARCHAR(512)             | 代码仓            |
| package_name                        | VARCHAR(512)             | 产物包名          |
| file_path                           | VARCHAR(512)             | 文件相对路径      |
| option_key                          | VARCHAR(64)              | 扫描项 key        |
| filing_value                        | VARCHAR(16)              | 备案值（YES/NO）  |
| reason                              | VARCHAR(512)             | 备案理由          |
| filer_id / filer_name / filing_time | VARCHAR/VARCHAR/DATETIME | 备案人 + 备案时间 |
| created_at / updated_at             | DATETIME                 | 审计              |

索引：唯一键 `uk_filing_project_repo_pkg_file_opt(project_id, git_url, package_name, file_path, option_key)`；`idx_filing_project_time(project_id, filing_time)`；`idx_filing_repo_pkg(git_url, package_name)`。

### 4.2 修改表 `sec_option_scan_file_detail`

新增列 `raw_options` JSON（存原始扫描值）；`options` 列保留但语义为"仅已备案项"（或由查询实时组装，见接口 §4.2）。

> 注：备案实时 LEFT JOIN 后，file_detail 的 options 由查询关联产出；上报仍写原始值，不依赖回填。

## 5. 性能设计

- 备案查询在 pageSize 命中行内做内存 map 关联（按 projectId+gitUrl+packageName 一次查备案），百级行内等价 O(1) 命中，无额外 SQL。
- /overview 分页与排序下推 SQL（LIMIT/OFFSET + COUNT），避免全量加载与深分页；排序优先复用物理列 `detection_completed_at`，数值指标最佳努力（无排序列时降级）。
- filing/list 扁平行 COUNT + LIMIT 由 SQL 下推；filing 关联走唯一键索引。
- record-list 走 `idx_filing_project_time` + `idx_filing_repo_pkg`。

## 6. API 接口设计

> 全部挂载 `BuildArtifactController`（`@RequestMapping("/build-artifact")`），POST + JSON。完整字段与示例见《interface-design.md》。

| 接口         | 方法+路径                                            | 用途                          | 变更 |
| ------------ | ---------------------------------------------------- | ----------------------------- | ---- |
| 概览列表     | `POST /build-artifact/sec-option/overview`           | 一级概览（产物包分页）        | 增强 |
| 文件详情     | `POST /build-artifact/sec-option/file-detail`        | 包内文件逐项结果              | 增强 |
| 保存备案     | `POST /build-artifact/sec-option/filing/save`        | upsert（批量），需审批人角色  | 新增 |
| 取消备案     | `POST /build-artifact/sec-option/filing/cancel`      | 按 id 删除，需审批人角色      | 新增 |
| 待备案项列表 | `POST /build-artifact/sec-option/filing/list`        | 文件×扫描项扁平行（SQL 分页） | 新增 |
| 备案人名单   | `POST /build-artifact/sec-option/filing/filer-list`  | 备案人下拉                    | 新增 |
| 备案记录列表 | `POST /build-artifact/sec-option/filing/record-list` | 独立备案记录页（跨包）        | 新增 |
| 扫描结果上报 | `POST /build-artifact/sec-option/report`             | 插件调用                      | 不变 |

关键字段（覆盖现有接口增强）：

- overview：`SecOptionRecordItem` 新增 `totalScannedFiles`、`filingCoverage`；`overviewData.options` 补全 14 项、每项含 `{scanned,totalFiles,applicableFiles,yesCount,rate,confirmedFiles,confirmationCoverage}`；未扫描 `{scanned:false}`；分页下推 SQL。
- file-detail：`FileSecOptionItem` 输出 `filePath`（相对路径）、`fileName`、`options`（仅已备案项= `"FILED"`）、`rawOptions`（全量原始值，未扫描= `"UNSCANNED"`）。
- filing/list：`SecOptionFilingRow`（id/filePath/optionKey/rawValue/filingValue/filerId/filerName/filingTime/reason），未备案行 id 为 null。
- 鉴权：save/cancel 需角色码 `security_compilation_options_filing_approver`（网关纵向）+ 项目成员（服务横向）；只读接口仅项目成员。

## 7. 安全设计

- 备案写操作叠加专用角色鉴权（网关校验角色或 admin），仅审批人可备案/取消。
- 项目隔离：save/cancel/record-list 均校验 `projectId`，cancel 另校验备案记录 `projectId` 与请求一致；file-detail/list 校验记录所属仓属于项目（git 仓名大小写不敏感）。
- 备案人/备案时间取自 gateway 注入的 `userId`/`userName`，前端不传、不信任入参。
- 备案值仅 YES/NO 枚举校验，拒绝任意字符串。
- filePath 已相对化，避免绝对路径泄露；不落 token/凭证等敏感信息。
