# 静态告警三分类与安全统计（alert_type）— 实现任务（docs 口径数据 + codecheck 后端）

## 进度: 0/10

> 设计归档基线（2026-11-19）：codecheck 仓与 docs 仓均未开始实施。

## 准备

- [ ] T0 分支创建：openlibing-codecheck `feat-static-alarm-alert-type`（基于 master）；openlibing-docs 口径数据 MR 分支（基于 master）

## openlibing-docs（口径数据）

- [ ] T1 创建 `static-code-analysis/solutions/full-analysis/alert-type/`：README.md（口径定义、决策树、治理流程、文件规范）+ tools.yml（34 工具注册：security 4 / bug 2 / code_smell 15 / mixed 13）
- [ ] T2 mappings/*.yml 初始整理（12 个混合工具，按落位表逐条穷举）并提 MR 评审：ruff（61 前缀）/ pylint（E/F/C/W/R/I 前缀）/ eslint（security/ 插件 15 条 + 核心安全白名单 21 条 + 物料 727 行）/ typescript-eslint（194 行裸名精确匹配）/ clang-tidy（模块前缀 + cert-/security. 安全分支）/ cppcheck（cert- + level 批量）/ shellcheck（level 批量）/ clippy（872 行逐规则）/ golangci-lint（gosec 编码 + 安全 linter 名）/ spotbugs（FindSecBugs 144 条 + catch-all bug）/ pmd（ruleset 维度）/ codeql（correctness tags_pattern + catch-all code_smell）
- [ ] T3 CI 校验：yml 格式与唯一性约束（tool 唯一、`(tool, rule_pattern)` 唯一、每行仅一个 pattern 维度字段）

## openlibing-codecheck（后端）

- [ ] T4 数据落地：`static_alarm_issue` 实体新增 `alert_type` 字段（ENUM 语义 security/bug/code_smell，兜底 code_smell 保证非空）；不建索引、不入指纹
- [ ] T5 分类引擎：策略接口 + 工厂路由（同 `ISarifParser` / `SarifParserFactory` 风格）；L1 工具级短路 / L2 元数据仅判安全（tags security、security-severity、cwe-*，CWE 编号正则提取入库）/ L3 四维 pattern 查表（rule_pattern / level_pattern / ruleset_pattern / tags_pattern）/ 兜底 code_smell；判定流程对齐 design.md §3.2 伪代码
- [ ] T6 口径缓存与刷新：进程内缓存（前缀树/哈希 + volatile 整体替换）；@Scheduled 每 5 分钟轮询 alert-type 目录 commit SHA，不一致拉全量校验后原子替换，校验失败保留旧口径并告警；构建打包 yml 注入打包时点 SHA 作启动兜底
- [ ] T7 SARIF 解析入库链路接入：result 解析取 tool + ruleId → classify → 写入 alert_type；upsert 存量保持入库时值（口径变更仅对新告警生效）
- [ ] T8 接口扩展（无新增接口）：list / issue/count / list/export 入参增 `alertTypes` 多选、list 出参行增 `alertType`；filter-options 出参增固定三项候选
- [ ] T9 存量回填 XXL-Job：`_id` 游标扫描空值 → DISTINCT (tool, rule_id) → 同源引擎判定 → 按组合批量 UPDATE 只写空值；幂等可重跑；输出组合数/回填行数（三分类分列）/失败组合数
- [ ] T10 单测：引擎三级判定矩阵（L1 短路 / L2 三判据 / L3 四维 pattern / 优先级裁决 / 兜底）、缓存刷新（SHA 一致跳过 / 校验失败拒绝刷新 / volatile 替换）、回填幂等（只写空值 / 失败跳过 / 二次空跑）、接口 alertTypes 过滤与计数一致性

## 交接（另行实施，不在本任务验收范围）

- [ ] T11 openlibing-web：告警类型多选筛选（`GithubHeaderFilter` 同交互）+ 行内三色标签（红/橙/紫）+ 枚举模块集中维护
- [ ] T12 openlibing-ops：看板安全静态告警数 / 分类分布统计（口径 = design.md §2.3；数据源配合项随看板详细设计确定）
