# License 文件兼容性分析继承逻辑 — 需求提案

## 1. 需求背景

OpenLibing SCA 平台的版本扫描功能会对纳管仓库中每个文件进行 License 兼容性自动分析，输出兼容（Yes）/ 不兼容（No）/ 未识别（Unrecognized）三种结论。

对于自动判定为"不兼容"或"未识别"的文件，运营人员需逐条进行人工分析并标注风险等级。然而在实际运营中存在以下痛点：

- **重复劳动**：同一开源文件（如 GPL 协议头）在多个仓库、多个分支、多次扫描中反复出现，每次都需要重新人工判定。
- **结论不一致**：不同运营人员对相同文件可能给出不同结论，缺乏全局统一机制。
- **效率瓶颈**：大仓单次扫描可产生数千条待确认文件，人工逐条处理耗时严重。

## 2. 需求目标

实现**基于文件内容哈希的人工分析结论继承机制**：

1. 运营人员对某文件做出人工分析后，结论以文件内容 MD5 为键持久化。
2. 后续任何扫描（不限仓库、分支、时间）遇到相同内容的文件时，自动继承已有的人工结论。
3. 人工结论优先级高于自动判定，继承后同步覆盖兼容性结论。

## 3. 验收标准

| # | 验收项 | 预期结果 |
|---|--------|----------|
| AC-1 | 人工分析保存 | 调用批量分析接口后，MongoDB 中对应 LicenseIssue 的 manualRiskLevel / manualDescription / compatible 被更新；MySQL `tbl_license_manual_analysis` 新增或更新对应记录 |
| AC-2 | 扫描继承 | 对已有人工分析结论的文件内容发起新版本扫描，扫描结果中该文件自动携带 manualRiskLevel / manualDescription，且 compatible 被覆盖为人工结论 |
| AC-3 | 跨仓库继承 | 仓库 A 中文件 X 已人工标注，仓库 B 中存在内容相同的文件 X'，扫描仓库 B 后 X' 继承 X 的结论 |
| AC-4 | 无结论不继承 | 文件内容从未被人工分析过时，扫描结果仅保留自动判定，manualRiskLevel 为空 |
| AC-5 | 继承容错 | MySQL 查询异常时扫描不中断，仅记录 warn 日志，文件保留自动判定结论 |
| AC-6 | 风险等级联动 | HAS_RISK → compatible="No"；NO_RISK → compatible="Yes"，保存与继承行为一致 |

## 4. 影响范围

- **后端**：openlibing-sca 仓（扫描引擎 + License 服务）
- **数据库**：MySQL 新增 `tbl_license_manual_analysis` 表；MongoDB `license_issue` 集合新增 3 个字段
- **接口**：新增 `POST /license/manualAnalysis/batch`、`POST /license/cache/refresh`
- **前端**：文件详情展示人工分析状态（本 PR 不含前端改动）

## 5. 关联信息

- PR：openlibing/openlibing-sca#255
- 分支：dev_20260730 → release_20260730
- Issue：#51（sca文件历史审核信息查询慢）、#54（版本批量扫描、继承逻辑和notice生成优化）
