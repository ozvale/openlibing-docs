# 安全编译选项扫描能力优化

## 需求背景

安全编译选项扫描插件（security-compilation-options-action）已具备 14 项扫描 + 上报 + 概览/文件详情查询能力，现有实现存在四个问题：

| 问题           | 现状                                                                                                          | 目标                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 实际扫描数缺失 | 概览 totalFiles 是"参与该项检测的文件总数"，与 yesCount 相除得到"满足数/总文件数"，无法得到用户理解的"满足率" | 透出"实际扫描数/实际参与数"，使满足率 = 满足数 / 实际参与数 自洽                       |
| 扫描项不可裁剪 | 默认返回全部 14 项结果，项目无法只关注部分项                                                                  | 复用插件 scan-options 链路，未扫描项带标识，前端不展示                                 |
| 无毒例外的备案 | 后端不涉及任何例外备案/豁免/覆写机制，NO 值每次扫描都原样返回                                                 | 支持按"项目+仓库+产物包+文件+选项"例外备案，备案值覆盖扫描值参与统计，后续扫描自动生效 |
| 前端信息过载   | 概览页每个扫描项都展示总文件数/满足数/开启率，信息过多                                                        | 三级页面 + 独立备案记录页：概览 → 详情 → 待备案项列表 → 备案记录页                     |

## 功能描述

### 做什么

- **插件侧（security-compilation-options-action）**：filePath 源头相对化；summary 增加 `totalScannedFiles`；纯 Go 二进制 fortify/ftrapv 返回 N/A；按失败文件数上报部分成功状态(0/1/2)。
- **后端（openlibing-cicd）**：上报入库应用生效备案；新增例外备案增删查接口（需「安全编译选项例外备案审批人」角色）；overview/file-detail 出参补全未扫描项标识与覆盖率口径；/overview 分页与排序下推 SQL。
- **前端（openlibing-cicd-web）**：三级页面 + 独立备案记录页；文件详情弹窗（文件×扫描项矩阵，逐列筛选）；按角色控制备案写操作。

### 不做什么

- 不改变现有上报/查询接口路径（仅扩展字段）。
- 不做存量 filePath normalize 兜底（备案为新功能，不回填历史）。
- 本期不实现"文件上传解析"备案备选方案（方案二，见设计文档 §1.6），仅记录。
- 不复建 `log_build_artifact` 操作日志表（备案审计直接落在备案表）。

## 验收标准

- [ ] 插件上报 filePath 为包内相对路径，每次扫描同一产物包文件名一致；summary 含 totalScannedFiles；纯 Go fortify/ftrapv 为 N/A。
- [ ] 后端入库应用备案，查询实时 LEFT JOIN `sec_option_filing` 关联最新备案；备案增删改无需重算快照。
- [ ] overview 出参含 totalScannedFiles、filingCoverage、applicableFiles；未扫描项 `{"scanned":false}`；/overview 分页下推 SQL（LIMIT/OFFSET + COUNT），total 准确。
- [ ] file-detail 出参 options（已备案项= FILED）与 rawOptions（全部原始值，未扫描=UNSCANNED）分离；optionFilters 支持 YES/NO/N/A（按 rawOptions）与 FILED（按备案存在性）筛选。
- [ ] filing/list 扁平行列表 SQL 分页，支持 filePath 模糊 / optionKeys 多选 / scanValues 多选 / filedStatus / filerName 精确 / 备案时间区间筛选。
- [ ] 备案/取消备案仅「安全编译选项例外备案审批人」角色可操作（网关纵向鉴权 + 项目成员横向校验），非该角色 403。
- [ ] 备案记录页（record-list）跨包展示备案人/备案时间，支持产物包/扫描项/备案人/时间筛选 + 排序分页；filer-list 提供备案人名单下拉。
- [ ] 前端概览只展示基础信息；详情展示逐扫描项检测覆盖率 vs 确认覆盖率（附公式）；待备案项列表默认只展示 NO 项，支持筛选+全选当前筛选结果+批量备案（跨页保留勾选）；UNSCANNED 项隐藏。
- [ ] 确认结果覆盖率 = 备案后满足数 / 实际参与数（分母为实际参与数）。

## 影响范围

| 仓                                  | 影响类型     | 说明                                                                  |
| ----------------------------------- | ------------ | --------------------------------------------------------------------- |
| security-compilation-options-action | 插件         | dist/ 下 scanner/detector/入口脚本改动                                |
| openlibing-cicd                     | 后端         | 新增备案表 + file_detail 查询实时关联 + 备案接口 + /overview 分页下推 |
| openlibing-cicd-web                 | 前端         | 三级页面 + 独立备案记录页 + 文件详情弹窗 + 角色控制                   |
| code-metrics-scan                   | 插件（镜像） | `.gitcode/actions/sec-option-scan/` 与 security 仓同步                |
