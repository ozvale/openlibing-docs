# 静态告警三分类与安全统计（alert_type）— 实现任务（docs 口径数据 + codecheck 后端）

## 进度: 10/10 主任务已完成（交接项 T12 另行实施）

> 归档基线（2026-11-26）：codecheck 侧已通过 PR !422 合入 master（分支 `feat/static-alarm-problem-category`，关联 Issue #430），评审修订随 PR !426 迭代——口径未加载时 alert_type 留空待回填（Holder 显式 isLoaded 标志）；docs 仓口径数据已落盘 `static-code-analysis/solutions/full-analysis/alert-type/`。任务内容已按最终实现同步。

## 准备

- [x] T0 分支创建：openlibing-codecheck `feat/static-alarm-problem-category`（基于 master）；openlibing-docs 口径数据 MR 分支（基于 master）

## openlibing-docs（口径数据）

- [x] T1 创建 `static-code-analysis/solutions/full-analysis/alert-type/`：README.md（口径定义、决策树、治理流程、文件规范）+ tools.yml（34 工具注册：security 4 / bug 2 / code_smell 15 / mixed 13；上送名差异工具配 `aliases` 别名，如 Bandit→bandit）
- [x] T2 mappings/*.yml 初始整理（13 个混合工具，文件名与 tool 值完全一致含大小写，按落位表逐条穷举）并提 MR 评审：ruff（61 前缀）/ Pylint（E/F/C/W/R/I 前缀）/ ESLint（security/ 插件 15 条 + 核心安全白名单 + 物料全量落盘）/ typescript-eslint（裸名精确匹配）/ clang-tidy（模块前缀 + cert-/security. 安全分支）/ Cppcheck（cert- + level 批量）/ shellcheck（level 批量）/ clippy（逐规则 `^clippy::<lint>$`）/ golangci-lint（gosec 编码 + 安全 linter 名）/ SpotBugs（FindSecBugs 安全 pattern + catch-all bug）/ PMD（ruleset 维度）/ CodeQL（correctness tags_pattern + catch-all code_smell）/ CodeArtsCheck（Criterion UUID 逐条枚举 + catch-all）
- [x] T3 口径校验（服务端解析时强制，任一失败整体拒绝刷新保留旧口径）：tool 唯一、aliases 无冲突、每条至少一个 pattern 维度（可多维度 AND 组合）、精确形 literal 同工具内唯一、正则合法

## openlibing-codecheck（后端）

- [x] T4 数据落地：`static_alarm_issue` 实体新增 `alert_type`（ENUM 语义 security/bug/code_smell，口径已加载后兜底保证非空；口径未加载窗口期入库留空待回填）与 `rule_tags` / `rule_ruleset`（回填重放依据）三个字段；`alert_type` 不建索引、不入指纹，另建 `idx_issue_tool_rule (tool, rule_id)` 支撑回填批量更新
- [x] T5 分类引擎：策略接口 + 工厂路由（同 `ISarifParser` / `SarifParserFactory` 风格）；口径未加载（isLoaded 为 false）前置返回 null 留空待回填 / L1 工具级短路（aliases 别名回落正名）/ L2 元数据仅判安全四判据（tags security、security-severity、cwe-*、cweTags 非空兜底）/ L3 四维 pattern 查表（可多维度 AND 组合，精确形哈希直查，多命中按 security > bug > code_smell 取序）/ 口径已加载时兜底 code_smell；判定流程对齐 design.md §3.2 伪代码
- [x] T6 口径缓存与刷新：进程内缓存（哈希/正则 + volatile 整体替换）；@Scheduled 每 5 分钟轮询 alert-type 目录 commit SHA（专用单线程执行器执行，在途去重），不一致经 GitCode v5 contents API 拉全量（429/5xx 指数退避重试 3 次），校验失败保留旧口径并告警；启动对齐：ApplicationReady 异步远端刷新，口径唯一来源远端仓库（无本地打包兜底）；token 四级链路（配置直供密文 > 项目公共账号 > 全局 token > 匿名 + enable 强制匿名开关）
- [x] T7 SARIF 解析入库链路接入：result 解析取 tool + ruleId → classify → 写入 alert_type（rule_tags / rule_ruleset 同步落库）；upsert 存量保持入库时值、alert_type 为空时补写本次分类（口径变更仅对新告警生效）
- [x] T8 接口扩展（无新增接口）：list / issue/count / list/export 入参增 `alertTypes` 多选、list 出参行增 `alertType`、导出列头「问题分类」；filter-options 入参增 `alertTypes` 收窄其余维度、出参增固定三项候选（label：安全/缺陷/代码坏味道，预留字段前端暂未消费）
- [x] T9 存量回填 XXL-Job：口径未加载守卫 → `_id` 游标扫描空值 → DISTINCT (tool, rule_id, raw_severity)（聚合 rule_tags 并集 / rule_ruleset）→ 同源引擎判定（注入合成上下文）→ 按组合批量 UPDATE（带 raw_severity 精确匹配）只写空值；幂等可重跑；执行前口径覆盖检查（未注册工具/无映射混合工具清单及受影响条数入摘要）；输出组合数/回填行数（三分类分列）/失败组合数
- [x] T10 单测：引擎三级判定矩阵（L1 短路含别名 / L2 四判据 / L3 四维 pattern 与多命中裁决 / 兜底）、口径解析校验（重复 literal / aliases 冲突 / 非法正则）、缓存刷新（SHA 一致跳过 / 校验失败拒绝刷新 / volatile 替换 / 启动对齐 / 指数退避重试 / token 链路）、回填幂等（只写空值 / 失败跳过 / 二次空跑 / 覆盖检查）、接口 alertTypes 过滤与计数一致性

## 交接（另行实施，不在本任务验收范围）

- [x] T11 openlibing-web：告警类型多选筛选（`GithubHeaderFilter` 同交互）+ 行内三色标签（红/橙/紫）+ 枚举模块集中维护（PR openlibing-web!924；filter-options 的 `alertTypes` 为预留字段暂未消费，后续接入统一使用「代码坏味道」文案）
- [ ] T12 openlibing-ops：看板安全静态告警数 / 分类分布统计（口径 = design.md §2.3；数据源配合项随看板详细设计确定）
