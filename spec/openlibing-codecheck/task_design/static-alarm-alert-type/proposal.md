# 静态告警三分类与安全统计（alert_type）— 需求提案（codecheck 后端 + docs 口径数据）

## 需求背景

平台已集成 34 个开源代码检查工具（格式化、Lint、安全扫描等，工具矩阵见 docs 仓 static-code-analysis 目录），各类告警混合入 `static_alarm_issue`。安全团队需要单独度量「安全静态告警」（注入风险、密钥泄露、弱加密等），工程效率团队关注缺陷与可维护性告警，两者统计口径必须区分。

核心矛盾：**多数工具不做告警分类**，类型属性只能由平台侧统一定义和提取。方案为告警三分类（`security` / `bug` / `code_smell`，对齐 SonarQube 质量模型三值简化版）+ 入库时自动分类 + 按口径统计。

方案演进：口径与平台设计 v1.1（2026-11-26）→ codecheck 落地设计 v7（2026-11-26），均已随实现（!422，Issue #430）同步；权威基准为口径 README，本文档归档两者的合并落地口径。

## 功能描述

- **统一三分类口径**：`alert_type` 三值互斥 MECE，判别决策树（安全风险 → security；运行时出错 → bug；其余 → code_smell）与冲突裁决（`security > bug > code_smell`）全仓唯一
- **自动分类引擎**：SARIF 告警入库时按口径未加载返回 null 留空待回填 → L1 工具级短路（含 `aliases` 别名匹配，生产上送名大小写/格式差异不再静默兜底）→ L2 SARIF 元数据（仅判安全）→ L3 规则映射表三级流水线定型，口径已加载时兜底 `code_smell` 保证非空，不依赖人工打标
- **口径数据 docs 仓承载**：`tools.yml`（34 工具注册）+ `mappings/*.yml`（13 个混合工具规则映射，含 CodeArtsCheck 1280 行）落 docs 仓 `static-code-analysis/solutions/full-analysis/alert-type/`，变更走 MR 治理，引擎 @Scheduled 每 5 分钟轮询目录 commit SHA 感知刷新；口径唯一来源为远端仓库（启动 ApplicationReady 异步对齐，无本地打包兜底），发布顺序必须口径先就位
- **数据落地**：`static_alarm_issue` 新增 `alert_type`（ENUM 可空：security / bug / code_smell，互斥单值；口径已加载后兜底保证非空，口径未加载窗口期入库为空、留空待存量回填任务补齐）+ `rule_tags` / `rule_ruleset`（规则元数据落库，支撑存量回填多维度重放）共三个字段
- **存量回填**：XXL-Job 一次性回填存量告警分类，幂等可重跑，只写空值不覆盖
- **接口扩展**（无新增接口）：`/static-alarm/v1` 的 list / issue/count / list/export 入参增 `alertTypes` 多选过滤、出参行增 `alertType`；filter-options 入参增 `alertTypes` 收窄其余维度候选、出参增固定三项候选（label：安全/缺陷/代码坏味道，预留字段前端暂未消费）
- **前端**：列表页「告警类型」多选筛选 + 行内三色标签（security 红 / bug 橙 / code_smell 紫）
- **看板统计**：安全静态告警数 = `count(alert_type='security' AND status='open')`，分类分布 `GROUP BY alert_type` 占比恒 100%

## 不做什么

- 不新增独立接口，仅扩展现有 `/static-alarm/v1` 四个接口
- 口径数据不落 Mongo（docs 仓 yml 唯一承载，DB 仅存告警事实）
- 纯度量类输出（圈复杂度数值等）不属于告警，不进告警表
- `alert_type` 不参与指纹 `fingerprint_key` 计算与 upsert 匹配，不单独建索引（基数为 3）；存量回填另建 `idx_issue_tool_rule (tool, rule_id)` 支撑按组合批量更新
- openlibing-ops「代码检查看板」统计接口为 ops 仓独立实施，本任务仅提供分类数据源
- codecheck 侧不另行定义工具子集或补充判定规则，全部口径以 docs 仓 yml 为准

## 验收标准

- [ ] 分类覆盖率：已加载口径后入库的告警 `alert_type` 非空比例 = 100%；口径未加载窗口期入库的告警允许为空，由存量回填任务补齐
- [ ] 工具级正确性：Bandit、Gosec、Gitleaks、Detect-Secrets 告警 100% 归 security；Mypy、ErrorProne 告警 100% 归 bug
- [ ] 抽样准确率：人工抽查 200 条分类结果，三类型合计准确率 ≥ 95%（每类不少于 50 条）
- [ ] 口径一致性：报表数值与统计口径定义（总告警数 = `count(status='open')`；安全静态告警数 = `count(alert_type='security' AND status='open')`）完全一致
- [ ] 存量稳定性：映射变更后存量告警 `alert_type` 与状态（open/fixed）不受影响，新扫描告警按新映射分类

## 影响范围

- openlibing-codecheck：`static_alarm_issue` 加字段、分类引擎（策略接口 + 工厂）、口径缓存与轮询刷新、SARIF 解析入库链路接入、4 个接口扩展、存量回填 XXL-Job
- openlibing-docs：新增 `static-code-analysis/solutions/full-analysis/alert-type/`（tools.yml + mappings/*.yml + README）
- openlibing-web：静态告警列表筛选与行内标签（交接前端实施）
- openlibing-ops：看板统计口径落地（另行实施，配合项）
