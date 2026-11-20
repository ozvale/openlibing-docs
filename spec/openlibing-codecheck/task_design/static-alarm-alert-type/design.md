# 静态告警三分类与安全统计（alert_type）— codecheck 落地详细设计

| 项目     | 内容                                                                                                                                                            |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 需求名称 | 开源代码检查支持统计安全静态告警（告警三分类 + 安全统计）                                                                                                       |
| 涉及仓   | openlibing-codecheck（后端）、openlibing-docs（口径数据）、openlibing-web（前端）、openlibing-ops（看板，另行实施）                                             |
| 关联现状 | 34 个开源检查工具经 GitCode Action 产出 SARIF 上报，解析入库 `static_alarm_issue`；告警无类型属性，安全/缺陷/坏味道混在一起，无法单独度量安全静态告警           |
| 设计基线 | 口径以《静态代码检查告警分类与统计平台设计方案》v1.0（评审稿）为**唯一权威**；本文为其在 codecheck 服务内的落地设计（v5，2026-11-18），不引入基准之外的设计决策 |
| 口径数据 | docs 仓 `static-code-analysis/solutions/full-analysis/alert-type/`（tools.yml + mappings/*.yml）唯一承载                                                        |

---

## 1. 方案总览

```text
docs 仓 static-code-analysis/solutions/full-analysis/alert-type/
├── tools.yml          ─┐  @Scheduled 每 5 分钟轮询（每实例独立执行）
└── mappings/*.yml      ┴─┬─► 比对目录 commit SHA ──► 不一致则拉取 / 校验 ──► 进程内缓存（volatile）
                           │                                            │
                           ▼                                            ▼
                    分类引擎（策略接口 + 工厂）◄──── L1 短路 / L2 元数据 / L3 规则映射直查本地内存 → 兜底 code_smell
                            ▼
                        static_alarm_issue 新增字段 alert_type
                            ▼
              列表 / 计数 / 导出 / 筛选项（alertTypes 多选） ──► 前端筛选 + 三色标签 ──► 看板统计
```

分层职责：采集层（CI 工具产出 SARIF）只上报不分类；接入层解析归一化；分类引擎纯查表 + 元数据判断定型；存储层仅存告警事实；统计层共用同一 `alert_type` 字段保证口径天然一致。

## 2. 分类口径（权威基准摘要）

### 2.1 三分类定义

对齐 SonarQube 质量模型三值简化版（Vulnerability 与 Security Hotspot 统一归 `security`）：

| alert_type   | 中文名 | 定义                                                                   | 判别问题                 |
| ------------ | ------ | ---------------------------------------------------------------------- | ------------------------ |
| `security`   | 安全   | 可能被攻击者利用的安全风险（注入、密钥泄露、弱加密、不安全反序列化等） | 代码可能被利用吗？       |
| `bug`        | 缺陷   | 运行时大概率出错的正确性/可靠性问题                                    | 代码确凿或大概率有错吗？ |
| `code_smell` | 坏味道 | 功能正常但有改进空间：格式、命名、复杂度、重复、性能、拼写、文档等     | 其余全部                 |

### 2.2 判别决策树与裁决规则

```text
1. 存在安全风险？           → security   # 多信号命中按 security > bug > code_smell 裁决
2. 运行时确凿/大概率出错？  → bug
3. 其余                     → code_smell
```

- **互斥单值 MECE**：一条告警仅一个 `alert_type`，三分类占比之和恒 100%，`GROUP BY alert_type` 直接可用；
- **完备无兜底桶之外的第四类**：拼写/文档/格式均属 code_smell；纯度量类输出（圈复杂度数值等）不属于告警，不进告警表；
- **冲突裁决**：规则同时命中多类信号按 `security > bug > code_smell` 优先级取主类型（如 Clang-Tidy 同时命中 `cert-` 与 `bugprone-` 归 security）；
- **边界规则基准**：Mypy 类型错误 → bug；Clippy `perf*` / Cppcheck performance → code_smell；ShellCheck 按 severity 拆（error/warning → bug，style/info → code_smell）；密钥泄露（Gitleaks 等）→ security。

### 2.3 统计口径

| 指标           | 定义                                             |
| -------------- | ------------------------------------------------ |
| 总告警数       | `count(status='open')`                           |
| 安全静态告警数 | `count(alert_type='security' AND status='open')` |

所有报表（安全与非安全）共用同一 `alert_type` 字段，口径天然一致；报表页脚注明口径版本（= alert-type 目录 commit SHA）。

## 3. 分类引擎设计

### 3.1 三级判别流水线

```text
告警解析入库 ─► L1 工具级：tools.yml default_alert_type 为固定值？ ──是──► 直接定型（security/bug/code_smell）
                    │ mixed
                    ▼
               L2 SARIF 元数据（仅判安全，满足任一即 security）：
                 ① properties.tags 含 security
                 ② properties 存在 security-severity 键
                 ③ properties.tags 含 cwe-* / external/cwe/cwe-*（CWE 编号同时提取入库，正则 cwe-?(\d+)）
                    │ 否
                    ▼
               L3 规则映射表：(tool, rule_id) 查 mappings/*.yml，
                 rule_pattern / level_pattern / ruleset_pattern / tags_pattern 命中即取映射 alert_type
                    │ 未命中
                    ▼
               兜底 code_smell
```

- **L1 固定类型短路**：security 工具（Bandit、Gosec、Gitleaks、Detect-Secrets）、bug 工具（Mypy、ErrorProne）、code_smell 工具（Prettier、Checkstyle、Codespell 等 15 个格式化/拼写/风格工具）全量直接定型；
- **L2 仅判安全**：CodeQL 的 `correctness → bug` 等非安全定型规则**不进 L2**，外置于 `mappings/codeql.yml`（`tags_pattern` 维度）由 L3 承接，保持 L2 纯「仅判安全」语义；
- **L3 pattern 语义**：`rule_pattern` 为正则（前缀 `^S`、精确 `^S608$`）；severity 维度工具（ShellCheck / Cppcheck）用 `level_pattern` 匹配 `results[].level`；category 维度（PMD）用 `ruleset_pattern` 匹配 `rules[].properties.ruleset`；富元数据工具（CodeQL）用 `tags_pattern` 匹配 `rules[].properties.tags` 任一标签；多条命中按 `security > bug > code_smell` 取序。

### 3.2 伪代码（判定流程唯一依据）

```python
def classify(alert, tool_registry, rule_mapping):
    tool = tool_registry.get(alert.tool)
    if tool is None:
        return "code_smell"                  # 未注册工具（新工具首报/别名差异/落位表遗漏）兜底，不抛异常
    if tool.default_alert_type != "mixed":          # L1 工具级短路
        return tool.default_alert_type
    tags = [t.lower() for t in alert.rule_properties.get("tags", [])]
    if "security" in tags or "security-severity" in alert.rule_properties \
       or extract_cwe(tags):                        # L2 元数据仅判安全
        return "security"
    hit = rule_mapping.lookup(alert.tool, alert.rule_id)   # L3 规则映射
    if hit:
        return hit.alert_type
    return "code_smell"                             # 兜底
```

### 3.3 codecheck 侧实现形态

- 引擎实现为**策略接口 + 工厂路由**（风格同仓内现有 `ISarifParser` / `SarifParserFactory`）：接口 `supportedTool()` 返回混合工具名（L2/L3 判别），固定类型工具由 `tools.yml` 注册数据在工厂层短路；
- SARIF 解析入库链路接入：解析每条 result 取 `tool`（`runs[].tool.driver.name`）+ `ruleId` → 引擎 `classify(...)` → 写入 `alert_type`，**不阻塞入库**；
- **存量稳定（生效语义）**：upsert 命中已有 issue 时保持既有 `alert_type` 不变，口径变更仅对新告警生效；已修复历史告警不会因口径变化被重新拉回，统计趋势稳定；
- 映射未覆盖的新 ruleId → 兜底 `code_smell` 入库，补映射走 docs 仓 MR，下次扫描起生效。

## 4. 口径数据设计（docs 仓承载）

### 4.1 目录结构与 schema

```text
static-code-analysis/solutions/full-analysis/alert-type/
├── README.md          # 目录说明：口径定义、判别决策树、治理流程、文件规范
├── tools.yml          # 工具注册数据（default_alert_type、enabled 等）
└── mappings/          # 规则映射，按工具一文件（13 个混合工具）
    ├── codeql.yml / clang-tidy.yml / cppcheck.yml / eslint.yml / typescript-eslint.yml
    ├── ruff.yml / pylint.yml / clippy.yml / golangci-lint.yml / spotbugs.yml
    ├── pmd.yml / shellcheck.yml / codearts-check.yml
    └── ...
```

**tools.yml**（工具注册，供 L1）：`tool`（PK，与告警上报 tool 字段一致）/ `display_name` / `default_alert_type`（`security` / `bug` / `code_smell` / `mixed`）/ `enabled`。

**mappings/\*.yml**（规则映射，供 L3）：`tool` / `rule_pattern` / `level_pattern`（可选）/ `ruleset_pattern`（可选）/ `tags_pattern`（可选）/ `alert_type` / `note` / `enabled`。

约束：`(tool, rule_pattern)` 唯一，禁止同一规则双类型；每行只填一个 pattern 维度字段，各自维度内唯一；映射表只承载分类口径，CWE、autofix 等规则级属性由引擎运行时从 SARIF 元数据提取入库。

### 4.2 工具落位（34 工具概要）

完整逐条穷举清单以 `mappings/*.yml` 与 [design-review.html](./design-review.html) 第五章为准，此处仅录落位策略：

| 工具                                                                                                                                                                                  | 落位策略                                                                                                                                                   | 定型       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Bandit / Gosec / Gitleaks / Detect-Secrets                                                                                                                                            | L1 固定                                                                                                                                                    | security   |
| Mypy / ErrorProne                                                                                                                                                                     | L1 固定                                                                                                                                                    | bug        |
| Prettier / ClangFormat / Google-Java-Format / Scalafmt / Rustfmt / Shfmt / StyLua / Spotless / Checkstyle / Markdownlint / Xmrlint / Codespell / Typos / Luacheck / Scalafix（15 个） | L1 固定                                                                                                                                                    | code_smell |
| CodeQL                                                                                                                                                                                | L2 安全标签先行；L3 `tags_pattern: ^correctness$` → bug + catch-all → code_smell                                                                           | 混合       |
| Ruff                                                                                                                                                                                  | 61 个官方前缀逐行穷尽，按官方 group 多数派定型（885 条全覆盖）                                                                                             | 混合       |
| Pylint                                                                                                                                                                                | 前缀：`^E` / `^F` → bug；`^(C\|W\|R\|I)` → code_smell                                                                                                      | 混合       |
| ESLint                                                                                                                                                                                | `^security/` 插件 15 条 + 核心安全白名单 21 条 → security；`meta.type = problem` → bug；其余 → code_smell（物料 727 行落盘）                               | 混合       |
| TypeScript-ESLint                                                                                                                                                                     | SARIF ruleId 裸名逐规则穷举（194 行）：镜像核心白名单 2 条 security；problem 类 → bug；suggestion/deprecated 类 → code_smell                               | 混合       |
| Clang-Tidy                                                                                                                                                                            | `^cert-`、`^clang-analyzer-security\.` → security；bugprone/concurrency/clang-analyzer/clang-diagnostic → bug；其余 18+ 模块前缀 → code_smell              | 混合       |
| Cppcheck                                                                                                                                                                              | `^cert-` → security；level error/warning → bug；style/performance/portability/information/debug → code_smell                                               | 混合       |
| ShellCheck                                                                                                                                                                            | level error/warning → bug；style/info → code_smell                                                                                                         | 混合       |
| Clippy                                                                                                                                                                                | 逐规则穷举 872 行（`^clippy::<lint>$`）：correctness/suspicious 154 条 → bug；其余 7 组 + legacy → code_smell                                              | 混合       |
| Golangci-Lint                                                                                                                                                                         | `^G[1-6]\d{2}$`（gosec 编码）+ 安全 linter 名/凭据类前缀 → security；其余 linter 兜底 code_smell                                                           | 混合       |
| SpotBugs                                                                                                                                                                              | FindSecBugs SECURITY pattern 144 条精确正则 → security；其余 pattern → bug                                                                                 | 混合       |
| PMD                                                                                                                                                                                   | ruleset：security → security；errorprone/multithreading → bug；其余 → code_smell                                                                           | 混合       |
| CodeArts Check                                                                                                                                                                        | Criterion UUID 逐条枚举 1280 行（`mappings/codearts-check.yml`）：安全类 402 条 → security；缺陷类 877 条 → bug；代码坏味道 9203 条 catch-all → code_smell | 混合       |

### 4.3 变更治理（MR 流程）

1. **提案**：新工具接入或口径调整 → docs 仓 alert-type 目录 MR（工具/规则/alert_type/依据）；
2. **评审**：安全团队确认 security 归类（重点核验「误判为安全」），工程团队确认 bug / code_smell 边界（依据 2.2 决策树）；CI 自动校验格式与唯一性约束；
3. **生效**：MR 合并后各实例轮询感知（最长 5 分钟），**下次扫描起对新告警生效**，存量不变；
4. **审计**：变更历史即 git 历史，口径版本 = alert-type 目录 commit SHA。

## 5. 口径缓存与刷新

**缓存形态：单机进程内缓存（volatile 引用），不依赖 Redis / webhook / MQ**

- 口径数据（L1 工具注册 + L3 规则映射）构建为前缀树/哈希结构整体存进程内存，volatile 引用持有，刷新时**整体替换引用**（读侧无锁，原子可见）；
- 引擎判定直查本地内存：零网络 RTT（微秒级），口径常驻 JVM——Redis / MQ / webhook 任一基础设施故障都不影响判定主链路（最多用旧口径，符合「存量定型、新告警按新口径」宽容语义）；
- 不采用 Redis 的原因：`RedisHelper.get` 故障时返回 null 且与「key 不存在」不可区分，引擎无法表达「口径不可用、保留旧值」语义，且每条判定多一次网络 RTT；不采用 webhook 的原因：免公网端点注册、免 payload 解析、免防丢包补偿。

**刷新：@Scheduled 每 5 分钟轮询（每实例独立执行）**

| 环节       | 设计                                                                                                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 定时比对   | 每实例每 5 分钟调 1 次目录级 API 取 alert-type 目录最新 commit SHA，与进程内已加载 SHA 比对：一致 → 跳过（绝大多数轮询命中此分支，仅 1 个轻量 GET）                       |
| 拉取与校验 | 从 docs 仓 raw 地址拉 yml 全量 → 解析校验（tool 唯一性、`(tool, rule_pattern)` 唯一、pattern 合法性）→ **校验失败拒绝刷新、保留旧口径并告警**（口径错误比口径过期危害大） |
| 写入生效   | 校验通过后 volatile 原子替换缓存引用 + 更新已加载 SHA                                                                                                                     |

API 消耗：288 次/天/实例（3 实例约 864 次/天）全为轻量 GET，远低于 GitCode 限流阈值（50 次/分钟、4000 次/小时），且与 docs 仓推送量无关。

**口径版本：目录 commit SHA（不设 version 字段）**：SHA 取 alert-type 目录最后一次变更 commit，docs 仓其他目录变更不影响比对（天然按路径免疫）；启动兜底场景构建打包 yml 时注入打包时点 SHA，兜底加载后参与后续比对。

**启动兜底**：进程内无口径数据时（首次部署/重启）从随构建打包的 yml 加载，首个轮询周期到达后自动对齐最新口径。

**多实例偏斜**：各实例独立轮询独立刷新，实例间存在 ≤5 分钟口径版本偏斜窗口；结合「存量保持入库时值、仅新告警按当前口径定型」语义，偏斜影响可忽略（同一次扫描任务内口径一致）。

## 6. 数据落地

`static_alarm_issue` **仅新增一个字段**：

| 字段         | 类型          | 说明                                                                      |
| ------------ | ------------- | ------------------------------------------------------------------------- |
| `alert_type` | ENUM NOT NULL | `security` / `bug` / `code_smell`（互斥单值，分类引擎写入；兜底保证非空） |

- 不新增 Mongo 口径集合：口径由 docs 仓 yml 唯一承载，DB 仅存告警事实；
- 索引：`alert_type` 基数为 3，不单独建索引，列表 `$in` 过滤复用现有索引结果集；
- 与指纹/去重键无冲突：纯新增展示/筛选字段，不参与 `fingerprint_key` 计算与 upsert 匹配。

## 7. 存量数据初始化

### 7.1 前置：映射初始整理（一次性，先于回填）

按落位表 + 各工具官方归组生成 `mappings/*.yml` 提 MR 评审（Ruff 61 前缀 / Pylint 前缀 / ESLint 白名单 + 物料 727 行 / SpotBugs 144 条 / TypeScript-ESLint 194 行 / Clippy 872 行 / Cppcheck 与 ShellCheck severity 批量 / PMD category / golangci-lint gosec 编码 / Clang-Tidy 模块前缀 / CodeQL tags_pattern 等，见 4.2）。

### 7.2 一次性回填（XXL-Job）

| 项   | 设计                                                                                                                                                        |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 触发 | XXL-Job 手动触发一次；幂等可重跑（已回填数据不再命中扫描条件，二次执行空跑）                                                                                |
| 扫描 | `alert_type` 为空的数据，`_id` 游标分页全量过滤（一次性场景不建空值索引），低峰执行                                                                         |
| 聚合 | 内存 `DISTINCT (tool, rule_id)` 组合                                                                                                                        |
| 判定 | 逐组合调用**与入库同源**的分类引擎（同一缓存实例）：L1 短路 → L2（存量判据：已落库 `security_severity` 存在性 + `cwe_tags`）→ L3 正则查表 → 兜底 code_smell |
| 回填 | 按组合批量 `UPDATE ... WHERE tool = ? AND rule_id = ? AND alert_type 为空`，只写空值、不覆盖任何已有值                                                      |
| 失败 | 单组合失败记录日志跳过继续；依赖幂等重跑恢复，不做断点续传                                                                                                  |
| 统计 | 扫描组合数、回填行数（按三分类分列）、失败组合数                                                                                                            |

## 8. 接口落地（无新增接口）

现有接口扩展（`/static-alarm/v1`）：

| 接口                                              | 变更                                                                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /static-alarm/v1/list`                      | 入参 `StaticAlarmQueryDTO` 新增 `alertTypes: List<String>`（三值 $in 多选，空不过滤）；出参 `StaticAlarmIssueListVO` 每行新增 `alertType` |
| `POST /static-alarm/v1/issue/count`（及批量计数） | 入参同步新增 `alertTypes`，计数口径与列表一致                                                                                             |
| `POST /static-alarm/v1/list/export`               | 入参同步新增 `alertTypes`（导出遵循同一过滤语义）                                                                                         |
| `POST /static-alarm/v1/issue/filter-options`      | 出参新增告警类型候选：固定三项 `{value: security/bug/code_smell, label: 安全/缺陷/坏味道}`                                                |

## 9. 前端落地（openlibing-web，交接实施）

| 位置     | 规则                                                                                                                                           |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 表头筛选 | 「责任人」与「问题级别」之间插入「告警类型」多选筛选，交互同现有 `GithubHeaderFilter`；选中写入查询条件 `alertTypes`                           |
| 行内标签 | 标题行顺序：扫描类别 → **告警类型** → 问题级别（pinned 最右）；三分类均展示标签；点击标签按该类型筛选                                          |
| 标签颜色 | security `#cf222e`（红）｜ bug `#bc4c00`（橙）｜ code_smell `#8250df`（紫）                                                                    |
| 前端枚举 | 集中维护枚举模块：`AlertType = 'security' \| 'bug' \| 'code_smell'` + 常量表（code / label / cssClass / dotColor）+ 工具方法；禁止页面写死文案 |

## 10. 看板统计（openlibing-ops，另行实施）

「代码检查看板」为 ops iframe 页面（`/ops/dashboard/code-check`），统计接口在 ops 仓，不在本次改造范围。ops 侧按 2.3 口径落地：安全静态告警数 / 总告警数 / `GROUP BY alert_type` 分类分布。codecheck 配合项：提供分类数据源（共享 `static_alarm_issue.alert_type` 字段或接口，随看板详细设计确定）。

## 11. 性能与安全设计

| 项             | 评估                                                                                                              |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| 引擎判定       | 口径直查进程内存：零网络 RTT + 前缀树/正则匹配微秒级；相对 SARIF 解析、指纹计算、Mongo upsert 现有成本，增量 < 1% |
| 缓存刷新       | 每 5 分钟比对目录 SHA（见 §5），288 次/天/实例轻量 GET，无限流风险；启动兜底从打包 yml 加载                       |
| 列表/计数/导出 | `alertTypes` 为 $in 等值条件追加现有查询，基数 3 复用现有索引结果集，单次增量 < 10ms                              |
| 看板聚合       | `GROUP BY alert_type` 与现有按 severity 聚合同构，复用现有统计链路                                                |
| 存量回填       | 游标全量扫描 + 万级组合批量 UPDATE，低峰执行，幂等可重跑（见 §7）                                                 |
| 鉴权           | 继承原有逻辑；本需求无新增写接口，仅查询条件扩展                                                                  |
| 敏感信息       | 分类数据非敏感；不打印 SARIF 原文与源码片段日志，不新增明文存储                                                   |
| 口径审计       | git 历史天然承担，报表可按 yml 版本追溯口径，口径版本 = alert-type 目录 commit SHA                                |

## 12. 风险与验收

### 12.1 风险与应对

| 风险                               | 影响                         | 应对                                                                             |
| ---------------------------------- | ---------------------------- | -------------------------------------------------------------------------------- |
| 映射表误判（错标/漏标）            | 统计口径失真                 | 映射变更走评审（安全团队 + 工程团队），下次扫描起自动修正                        |
| bug 与 code_smell 边界争议         | 映射评审反复                 | 2.2 决策树与边界规则为裁决基准，争议案例沉淀进边界规则表                         |
| 工具升级新增/更名规则              | 新规则落入兜底（code_smell） | 工具版本入库；升级时比对规则集差异并补映射                                       |
| SARIF 质量参差（无元数据、无指纹） | L2 判别失效、去重漂移        | 转换器统一补齐指纹；L3 映射兜底                                                  |
| 海量告警性能                       | 入库与查询变慢               | 批量 upsert、分区表、聚合预计算                                                  |
| 口径理解不一致                     | 各团队统计对不上             | v1.0 README 为唯一口径来源，报表页脚注明口径版本（= alert-type 目录 commit SHA） |

### 12.2 验收标准

见 [proposal.md](./proposal.md) 验收标准章节（分类覆盖率 100% / 工具级正确性 / 抽样准确率 ≥ 95% / 口径一致性 / 存量稳定性）。

## 13. 原型与评审

- 设计评审页：[design-review.html](./design-review.html)（含完整工具落位穷举表格）
- 规则配置交互原型：[prototype.html](./prototype.html)
