# 安全编译选项扫描结果导出方案设计

## 背景与目标

构建产物扫描详情页展示单条扫描记录的完整结果：顶部为产物基础信息，中部为逐安全编译选项的指标明细（满足数、参与数、检测结果覆盖率、已备案文件数、备案后结果覆盖率），文件扫描结果弹窗提供文件级扫描矩阵（每文件 × 14 项选项的 YES/NO/N/A 及备案标注）。目前这些内容仅支持页面查看，无法离线留档与线下分析。

本次改造：详情页提供「导出」能力，按当前扫描记录生成一个 Excel 文件（两个 Sheet：扫描概览、文件扫描结果），文件生成走平台已有的导出中心，用户在导出浮窗看到进度，完成后自动下载。

---

# 1. 方案设计

## 方案目标

在「产物扫描详情页」提供导出能力：用户进入某条扫描记录的详情页后点击「导出」，系统按当前记录生成全量 Excel 文件（扫描概览 + 文件扫描结果，备案项带「已备案」标注），通过主站导出中心浮窗提示进度并在完成后自动下载。

## 涉及模块

- openlibing-cicd `business/controller`：新增详情导出任务创建接口。
- openlibing-cicd `business/service`：新增详情导出服务（任务创建 + 异步生成双 Sheet + 状态回写）。
- openlibing-cicd `common/enums`：新增导出文件类型枚举值。
- openlibing-cicd `common/constants`：新增安全编译选项展示名与描述的映射配置（Excel 列头与 Sheet1 描述列来源）。
- openlibing-cicd-web：产物扫描详情页选项明细表格区右上角新增「导出」文字按钮（导出图标 + 文字，与风险数据看板导出样式一致），提交后唤起主站导出中心。
- 复用（不修改）：framework 导出任务接口（`/export/internal-server/create|update|query`）、OBS 上传能力、主站导出中心浮窗（状态轮询、自动下载、「我的导出」历史）。

## 整体处理方式

复用仓内测试结果导出已验证的异步导出链路（`PipelineServiceImpl` 测试报告导出、`FileDownloadServiceImpl` 日志导出均基于该链路）：前端提交导出请求（仅携带记录标识），后端创建导出任务记录后立即返回；文件由后端异步生成（双 Sheet 流式写入）并上传 OBS；进度展示与下载由主站导出中心统一完成。

## 采用该方案的原因

- 平台导出中心已沉淀了任务记录、状态机、下载链接签发与「我的导出」历史等通用能力，框架侧零改动；
- 仓内已有同构实现（测试结果导出），开发模式、异常处理、状态回写语义均有现成范式，风险与工作量可控；
- 文件级扫描结果矩阵与单文件包内文件数正相关，同步返回会造成接口长阻塞，异步 + 导出中心是平台既有标准交互，用户体验一致。

---

# 2. 实现逻辑设计

## 导出提交流程

| 步骤 | 执行方              | 动作                                                                                                                                                                    |
| ---- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | 用户                | 在产物扫描详情页选项明细表格区右上角点击「导出」按钮                                                                                                                    |
| 2    | openlibing-cicd-web | 调用 `POST /build-artifact/sec-option/detail/export`，携带 projectId 与 recordId                                                                                        |
| 3    | openlibing-cicd     | 校验项目成员权限与记录归属；调用 framework `/export/internal-server/create` 创建导出任务（type=SEC_OPTION_DETAIL，data 保存 projectId 与 recordId），将任务 ID 返回前端 |
| 4    | openlibing-cicd-web | 收到任务 ID 后，通过无界 bus 事件 `host-export-task` 通知主站导出中心（携带任务 ID 与任务名）                                                                           |
| 5    | openlibing-cicd     | 异步生成文件：状态置 BUILDING → 写 Sheet1（基础信息块 + 选项明细）→ 分批写 Sheet2（文件扫描结果）→ 状态置 UPLOADING → 上传 OBS → 成功回写 SUCCESS / 失败回写 FAILED     |
| 6    | 主站导出中心        | 每 3 秒轮询 framework 导出状态并展示进度；成功后获取下载链接并自动下载，失败展示失败原因                                                                                |

## 异步生成核心步骤

1. 状态置为 BUILDING；
2. 按 recordId 查询扫描记录，复用概览记录装配逻辑得到基础信息与逐选项指标（`OverviewOption` 列表，固定 14 项顺序）；
3. 写入 Sheet1「扫描概览」：顶部基础信息块（键值两列），随后写入 14 行选项明细表（EasyExcel `ExcelWriter`，同一 Sheet 分区写入）；
4. 分批循环查询 `sec_option_scan_file_detail`（recordId 维度，每批 1000 条，按文件路径升序，与文件扫描结果弹窗展示顺序一致，游标翻页直至取完），同时一次性加载该记录关联的备案记录集合（文件 × 选项维度）；
5. 每批映射为 Sheet2「文件扫描结果」行，流式写入：每个选项单元格取 YES/NO/N/A，命中备案记录的单元格附加「（已备案）」字样；
6. 状态置为 UPLOADING，将临时文件上传 OBS（objectKey 规则：`日期/UUID`，与现有导出一致）；
7. 上传成功回写 SUCCESS，任一步骤失败回写 FAILED（message 记录失败原因），finally 清理本地临时文件。

## Excel 结构定义

单文件两个 Sheet。

### 导出文件命名

```
安全编译选项扫描详情_{产物名称}_{recordId}.xlsx
```

- 前缀取 `FileTypeEnums.SEC_OPTION_DETAIL` 的 desc（安全编译选项扫描详情），枚举调整时文件名一处生效；
- 产物名称与 recordId 来自当前扫描记录（recordId 为雪花 ID 字符串，全局唯一且稳定，避免运行编号在跨流水线时语义模糊），保证「我的导出」列表中可直接辨识记录，如 `安全编译选项扫描详情_zlib-build-artifacts.tar.gz_2100065859476262912.xlsx`。

### Sheet1「扫描概览」

顶部为基础信息块（键值两列，共 8 行）：

| 键             | 值来源               | 说明                             |
| -------------- | -------------------- | -------------------------------- |
| 代码仓链接     | repoUrl              | 值为超链接，可点击跳转           |
| 产物名称       | packageName          |                                  |
| 流水线名称     | pipelineName         |                                  |
| 流水线运行编号 | runNumber            |                                  |
| 流水线链接     | pipelineLink         | 值为超链接，可点击回跳执行详情   |
| 扫描状态       | status               | 0/1/2 转中文：失败/成功/部分成功 |
| 扫描时间       | detectionCompletedAt |                                  |
| 总文件数       | totalScannedFiles    |                                  |

基础信息块下方为选项明细表（14 行 × 7 列，按 `SecOptionConstants#ALL_OPTION_KEYS` 固定顺序）：

| 列名                 | 来源字段（OverviewOption） | 说明                            |
| -------------------- | -------------------------- | ------------------------------- |
| 安全编译选项         | key → 展示名               | 经选项映射配置转换，如 BIND_NOW |
| 描述                 | key → 描述                 | 经选项映射配置转换，如 立即绑定 |
| 满足数               | yesCount                   |                                 |
| 实际参与数           | applicableFiles            | 排除 N/A 的文件数               |
| 检测结果（覆盖率）   | rate                       | 原样导出，如 `100.00%` 或 `N/A` |
| 已备案文件数         | confirmedFiles             |                                 |
| 备案后结果（覆盖率） | confirmationCoverage       | 原样导出，如 `100.00%` 或 `N/A` |

两个覆盖率列的颜色与详情页展示规则一致（前端 `rateClass`）：≥80% 绿色，50%~79% 黄色，<50% 红色，`N/A` 灰色。

### Sheet2「文件扫描结果」

一条文件记录一行，共 16 列：

| 列          | 来源                          | 说明                                                                                                                            |
| ----------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 文件名      | 文件明细.文件名（fileName）   | 行序按文件路径升序（与弹窗 `ORDER BY file_path` 一致）                                                                          |
| 文件路径    | 文件明细.文件路径（filePath） | 与弹窗「文件路径」列一致                                                                                                        |
| 14 个选项列 | 文件明细.各选项扫描结果       | 列头为选项展示名（BIND_NOW、NX、PIC、PIE、RELRO、SP、NO Rpath、FS、Ftrapv、Strip、ASLR、Fvisibility、Fstackcheck、Fstackclash） |

取值规则：单元格取 YES/NO/N/A；该文件 × 选项存在备案记录时，单元格附加「（已备案）」字样，如 `NO（已备案）`。

不导出的页面字段及原因：`downloadUrl` 为 OBS 临时签名链接，存在时效，写入离线文件后很快失效；`id`、`recordId` 等内部标识对离线阅读无意义。

---

# 3. 类设计

后端（openlibing-cicd）：

| 类                          | 类型 | 职责与主要修改                                                                                                                                   |
| --------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| BuildArtifactController     | 修改 | 新增 `POST /build-artifact/sec-option/detail/export` 接口，接收 projectId/recordId 与 gateway 注入的 userId，转发导出服务                        |
| SecOptionDetailExportDTO    | 新增 | 导出请求 DTO：projectId（必填）+ recordId（必填）                                                                                                |
| SecOptionDetailExportVO     | 新增 | 导出响应 VO：导出任务 ID + 初始化状态                                                                                                            |
| SecOptionScanService        | 修改 | 新增 `exportDetail` 接口方法                                                                                                                     |
| SecOptionScanServiceImpl    | 修改 | 实现导出任务创建（framework create + 返回任务 ID）与异步生成（Sheet1 写入、文件明细分批查询、备案集合装配、Sheet2 流式写入、OBS 上传、状态回写） |
| SecOptionOptionExcelRow     | 新增 | Sheet1 选项明细行模型，`@ExcelProperty` 声明 7 列列头与顺序                                                                                      |
| SecOptionFileResultExcelRow | 新增 | Sheet2 文件结果行模型，`@ExcelProperty` 声明 16 列列头与顺序                                                                                     |
| SecOptionConstants          | 修改 | 新增选项 key → 展示名/描述 的映射，供 Excel 列头与 Sheet1 描述列使用                                                                             |
| FileTypeEnums               | 修改 | 新增枚举值 `SEC_OPTION_DETAIL("安全编译选项扫描详情", "_sec_option_detail")`                                                                     |

复用不修改：FrameworkProjectClient、ObsBucketService、ExportStatus、主站 exportTask store 与「我的导出」。

---

# 4. 数据模型设计

不涉及。

- 导出任务记录复用 framework 导出中心已有存储（obs file 记录），新增记录通过 `type=SEC_OPTION_DETAIL` 区分，无表结构变化；
- `sec_option_scan_record`、`sec_option_scan_file_detail`、`sec_option_filing` 均无变化，导出仅为读取。

---

# 5. 性能设计

- 导出范围为单条扫描记录，数据量与包内文件数正相关；Sheet2 采用分批查询 + 流式写入，单批 1000 条，内存占用与批大小正相关而非文件总数，不因数据量增长而线性膨胀；
- 备案记录集合按 recordId 一次性加载后内存匹配，避免逐文件查询备案表；
- 生成与上传全程异步执行，不占用 Web 请求线程；导出链路与现有测试结果导出共用异步任务执行器，频次为用户手动触发，无高频并发场景；
- 分批查询沿用文件详情查询已有索引（recordId 维度），不引入新的慢查询模式；
- 接口默认：满足 3 秒性能要求（导出提交接口仅创建任务记录即返回）；
- 当前场景为低频手动导出，无需新增缓存。

---

# 6. API 接口设计

新增接口 1 个，既有接口无变化。

## 创建安全编译选项扫描详情导出任务

- URL：`POST /gateway/openlibing-cicd/build-artifact/sec-option/detail/export`
- Method：POST
- 鉴权：与文件详情查询接口一致，userId 由 gateway 解析 JWT 注入；服务层执行项目成员横向校验（当前用户须为 projectId 对应项目成员或系统角色），并校验 recordId 对应记录归属于 projectId，防止跨项目越权导出
- 请求参数（Body）：

| 字段      | 类型   | 必填 | 说明                                            |
| --------- | ------ | ---- | ----------------------------------------------- |
| projectId | String | 是   | 项目 ID，项目隔离                               |
| recordId  | String | 是   | 扫描记录 ID（字符串传递，避免 64 位 Long 失真） |

- 返回参数（DataResult\<SecOptionDetailExportVO\>）：

| 字段         | 类型   | 说明                              |
| ------------ | ------ | --------------------------------- |
| exportTaskId | String | 导出任务 ID，前端据此通知导出中心 |
| message      | String | 初始化状态（INITIALIZED）         |

- 兼容性：纯新增接口，不影响既有接口；导出任务类型为新枚举值，framework 与主站导出中心按通用记录处理，无契约变化。

---

# 7. 安全设计

## 鉴权

- 继承文件详情查询接口的既有鉴权逻辑：gateway 纵向鉴权 + 服务层项目成员横向校验，另校验 recordId 与 projectId 的归属关系，导出数据范围与详情页可见范围严格一致，不支持导出无权查看的数据；
- 导出中心的下载链接获取沿用 framework 既有鉴权，不新增免鉴权路径。

## 敏感信息

- Excel 内容为扫描指标与文件级扫描结果，与页面展示内容一致，不含 token、凭证、源码内容等敏感信息；
- 日志仅记录导出任务 ID、projectId、recordId 与结果状态，不打印请求体全量与用户敏感字段。

## 硬编码

- 无新增 appkey/token/secret；OBS 与 framework 地址沿用既有配置管理。

## 审计日志

- 导出为读操作，不涉及业务数据新增/修改/删除，无需操作日志落库；导出任务记录本身（创建人、创建时间、文件）在导出中心可追溯。

---

# 附录

## 示例文件

- 原型（设计总览 + 双 Sheet 示例）：`安全编译选项导出原型.html`
- 示例 Excel（可直接打开查看）：`安全编译选项详情导出示例.xlsx`
