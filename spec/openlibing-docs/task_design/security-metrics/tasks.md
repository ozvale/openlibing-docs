# 代码安全检查评分看板 · 分步落地任务（tasks）

> 建议开发顺序：**S1 → D1 → D2 → P1 → P2 → S3 → S2 → D3 → D4**
>
> 核心依据：原始设计 `docs/0912/design.md v4 终版` §11 开发清单

---

## Phase 0：前置准备

- [ ] [P0-1] 在 Doris 上执行 sdi 层已落地的外部依赖表 DDL（如仓库基础信息表、PR 表、codearts 关联表等），确认下游依赖均已到位
- [ ] [P0-2] 在 DolphinScheduler 项目 `security_check_scoring` 确认"1+6"采集任务（01/02/03 层）均已创建，raw 表有最新数据
- [ ] [P0-3] 原始 SQL/Python 脚本文件已归档到 openlibing-docs（或确认路径）：`docs/0912/` 下的 raw 层 DDL、sdi 层 DDL、sdi 层 DML、commit 扫描脚本、拉取脚本
- [ ] [P0-4] 确认 Doris 连接、DolphinScheduler API 凭证、GitCode token（Python clone 用）均可用

---

## Phase 1：S1 — sdi 接口链路清洗（6 表 DDL + DML）

> DDL/DML 已写好（`sdi层6表建表DDL.sql` / `sdi层清洗DML.sql`），在 Doris 执行即可。

- [ ] [S1-1] 在 Doris 执行 `sdi层6表建表DDL.sql` 创建 6 张 sdi 表
  - [ ] `sdi_rd_efc_branch_protection`（暂缓，DDL 保留待用）
  - [ ] `sdi_rd_efc_pr_setting`（暂缓，DDL 保留待用）
  - [ ] `sdi_rd_efc_release`
  - [ ] `sdi_rd_efc_repo_contributor`
  - [ ] `sdi_rd_efc_repo_webhook`
  - [ ] `sdi_rd_efc_pr_review_reviewer`
- [ ] [S1-2] 执行 `sdi层清洗DML.sql` 的 [3][4][5][6] 四组清洗逻辑（[1][2] 暂缓）
- [ ] [S1-3] 验证 sdi 表数据正确性：
  - [ ] webhook.password_is_null 列有值（非 NULL）
  - [ ] release 表 has_sha256_asset / has_signature_asset 派生正确
  - [ ] contributor 表 user_login + org_login 关联成功
  - [ ] pr_review_reviewer 表 is_bot / is_effective_review 清洗正确
- [ ] [S1-4] 在 DolphinScheduler 04 层创建 4 个 sdi 清洗 SQL 任务（依赖 01 接口拉取层）

---

## Phase 2：D1 — PR 评审 + CI 测试（最先出结果）

> 数据已齐（PR 表 + codearts 关联表已有），可最先开发。

- [ ] [D1-1] 在 Doris 建 `dwi_security_pr_scan` 表
- [ ] [D1-2] 编写 D1 SQL — 指标 7 CODE_REVIEW
  - [ ] 取近 30 次已合入 PR（剔除机器人）
  - [ ] 关联 sdi_rd_efc_pr_review_reviewer 判定 is_effective_review（非机器人且 /lgtm 或 /approve）
  - [ ] 排除 PR 创建人自己的评审
  - [ ] 打分：`score = 已评审数 / 总PR数 × 10`
  - [ ] NA：剔除机器人后 PR=0 → is_na=1
- [ ] [D1-3] 编写 D1 SQL — 指标 10 CI_TESTS
  - [ ] 同批近 30 次已合入 PR
  - [ ] 关联 `sdi_rd_efc_pipeline_run_pr_relation_codearts` 单表（git_url + CAST(pr_id AS INT) 对齐）
  - [ ] 过滤 git_type='gitcode' AND pr_id IS NOT NULL
  - [ ] 打分：`score = 10 × 有CI的PR数 / 合并PR数`
  - [ ] NA：无 PR → is_na=1
- [ ] [D1-4] 合并两个指标写入 dwi_security_pr_scan（同 repo + scan_time，score_review / score_ci 分列）
- [ ] [D1-5] 全链路验证：抽查 3~5 个仓库，手动 count 比对 SQL 结果
- [ ] [D1-6] 在 DolphinScheduler 06 层创建 D1 SQL 任务

---

## Phase 3：D2 — Webhook + 发布签名 + 贡献者

> 依赖 S1[3][4][5] sdi 表。

- [ ] [D2-1] 在 Doris 建 `dwi_security_meta_api_scan` 表（metric_code 维度一行）
- [ ] [D2-2] 编写 D2 SQL — 指标 9 WEBHOOKS
  - [ ] 取 sdi_rd_efc_repo_webhook 活跃（active=1）Webhook
  - [ ] 打分：`score = ⌊10 × 配置密钥数 / 活跃数⌋`（配置密钥 = active=1 且 password_is_null=0）
  - [ ] 无活跃 Webhook → 10 分（不是 NA）
  - [ ] detail_json 含 webhook 列表
- [ ] [D2-3] 编写 D2 SQL — 指标 11 SIGNED_RELEASES
  - [ ] 取 sdi_rd_efc_release 最近 30 个正式版本（忽略 source only）
  - [ ] 全签名或全 SLSA → 10 分；任一不满足 → 0 分
  - [ ] 无 release → NA
- [ ] [D2-4] 编写 D2 SQL — 指标 18 CONTRIBUTORS
  - [ ] 取近 30 次已合入 PR 的作者去重列表
  - [ ] 关联 sdi_rd_efc_repo_contributor 按 user_login 取 org_login
  - [ ] N = 组织内存在 ≥1 名作者（近 30 次 PR 数 ≥5）的组织数
  - [ ] 打分：`min(10, 10 × N / 3)`
  - [ ] 无 PR → NA
- [ ] [D2-5] 三个 metric_code 统一写入 dwi_security_meta_api_scan
- [ ] [D2-6] 全链路验证 + DolphinScheduler 06 层创建 D2 SQL 任务

---

## Phase 4：P1 — 文件扫描脚本（7 个 metric_code）

> 除 PACKAGING 外 6 个 metric_code 无外部依赖，可先行开发。

- [ ] [P1-1] 在 Doris 建 `dwi_security_file_scan` 表
- [ ] [P1-2] 编写 `security_file_scan.py` 主框架
  - [ ] 参数解析：仓库列表 + scan_time + 输出目标表
  - [ ] clone + checkout 默认分支（使用 GitCode token）
  - [ ] 遍历文件树，按 metric_code 分发扫描器
  - [ ] 结果批量写入 Doris（Unique Key UPSERT）
- [ ] [P1-3] 实现 COPYRIGHT 扫描器（指标 2）
  - [ ] 目标后缀：`.go .java .py .js .c .cpp .rs .ts .sh .bat`
  - [ ] 正则：`Copyright\(c\)\s*\d{4}\s+Huawei Technologies Co\.`
  - [ ] 打分：`10 × 匹配文件数 / 目标文件数`
  - [ ] NA：无目标后缀文件
- [ ] [P1-4] 实现 DANGEROUS_WF 扫描器（指标 3）
  - [ ] 扫描 `.gitcode/workflows/*.{yml,yaml}`
  - [ ] 检测 `allow-unsafe-pr-checkout: true`
  - [ ] 检测不可信上下文变量注入
  - [ ] 打分：发现任意危险=0，未发现=10
  - [ ] NA：无 workflow 文件
- [ ] [P1-5] 实现 TOKEN_PERM 扫描器（指标 4）
  - [ ] 解析 workflow yml 顶层和 job 级 permissions
  - [ ] 5 条规则打分
  - [ ] 备注：gitcode 权限映射细节待李洪峰（不阻塞其他）
- [ ] [P1-6] 实现 BINARY_ARTIFACTS 扫描器（指标 6）
  - [ ] 命中后缀清单（.exe/.dll/.so/.jar/.zip 等）
  - [ ] 打分：`max(0, 10 - 二进制文件数)`
- [ ] [P1-7] 实现 SAST 扫描器（指标 14）
  - [ ] 检测 `.pre-commit-config.yaml` 是否存在
  - [ ] 打分：有=10，无=0
- [ ] [P1-8] 实现 SECURITY_POLICY 扫描器（指标 15）
  - [ ] 扫描 `SECURITY.md` / `.gitcode/SECURITY.md` / `docs/SECURITY.md` / `security.md`
  - [ ] 打分：仓内存在=10
- [ ] [P1-9] 实现 PACKAGING 扫描器（指标 12）
  - [ ] 检测 workflow 存在 → 满足
  - [ ] openEuler 工程比对（依赖 S3 的 sdi_rd_efc_euler_package）
  - [ ] atomgit.com 归一化为 gitcode.com
  - [ ] 打分：10（满足）/ NA（不满足）
- [ ] [P1-10] 本地联调：挑 2~3 个仓库跑全流程，验证各 metric_code 得分
- [ ] [P1-11] 在 DolphinScheduler 05 层创建 P1 Python 脚本任务

---

## Phase 5：P2 — LICENSE 扫描脚本（scancode）

- [ ] [P2-1] 在 Doris 建 `dwi_security_license_scan` 表
- [ ] [P2-2] 编写 `security_license_scan.py`
  - [ ] 集成 scancode-toolkit：`scancode --license --copyright --license-text --license-text-diagnostics --json-pp licenses_report.json <repo>/LICENSE`
  - [ ] 解析 SPDX 标识、模板一致性（score=100）、OSI/FSF 判定
  - [ ] 阶梯打分：有5 → 模板8 → 版权正确9 → OSI/FSF10；无0
- [ ] [P2-3] 本地联调 + DolphinScheduler 05 层创建 P2 Python 脚本任务

---

## Phase 6：S3 + S2 — euler 清洗 + commit 链路

- [ ] [S3-1] 在 Doris 建 `sdi_rd_efc_euler_package` 表（数据到位后即可建）
- [ ] [S3-2] euler 拉取任务数据入表，验证 atomgit.com → gitcode.com 归一化
- [ ] [S2-1] 在 Doris 建 `raw_repo_commit_log` + `sdi_repo_commit_log` 两表（DDL 见原始脚本）
- [ ] [S2-2] 在 DolphinScheduler 03 层创建 commit 采集 Python 脚本任务（`代码仓commit扫描脚本.py`）
- [ ] [S2-3] 执行 commit 清洗 SQL（raw → sdi），建 DolphinScheduler 04 层 commit 清洗任务
- [ ] [S2-4] 验证 sdi_repo_commit_log 数据可用于 D3 项目维护指标

---

## Phase 7：D3 — 项目维护

> 依赖 S2 commit 数据。

- [ ] [D3-1] 在 Doris 建 `dwi_security_maintained_scan` 表
- [ ] [D3-2] 编写 D3 SQL — 指标 17 MAINTAINED
  - [ ] 仓库状态：sdi_repo_info 判 archived / create_time 不足 90 天
  - [ ] commit：sdi_repo_commit_log 默认分支近 90 天数量
  - [ ] issue：sdi_repo_issue_info 近 90 天新建数量
  - [ ] 打分：`min(10, 10 × (commit数₉₀d + issue数₉₀d) / 13)`
  - [ ] NA：已归档或创建不足 90 天
- [ ] [D3-3] 全链路验证 + DolphinScheduler 06 层创建 D3 SQL 任务

---

## Phase 8：D4 — DM 汇聚（全指标 + 加权分 + 亮灯）

> 依赖 D1 + D2 + D3 + P1 + P2。

- [ ] [D4-1] 在 Doris 建 `dm_security_scan_score` 表（DDL 见 design.md §7.1）
- [ ] [D4-2] 编写 D4 汇聚 SQL
  - [ ] 从 7 张 dwi 表 LEFT JOIN 合并 18 项指标得分
  - [ ] 暂缓项 5/8/13/16 恒为 NULL
  - [ ] 计算规则项加权总分（score_rule_weighted）：只汇总 is_na=0 且非暂缓的规则类指标，权重和上限 75
  - [ ] 计算全部指标加权总分（score_all_weighted）：同上，权重和上限 87.5
  - [ ] 计算 rule_light：规则项得分率（score_rule_weighted / 10）≥80 绿，≥50 黄，<50 红
  - [ ] Unique Key (repo_id, scan_time) UPSERT
- [ ] [D4-3] 全链路联调：选一批仓库跑 01~06 全链路，验证 dm 表数据
- [ ] [D4-4] DolphinScheduler 06 层创建 D4 汇聚 SQL 任务
- [ ] [D4-5] 配置 04/05/06 层之间的完整依赖 DAG

---

## Phase 9：暂缓项恢复条件跟踪

| 指标 | metric_code | 恢复条件 | 跟踪人 |
| --- | --- | --- | --- |
| 5 | PINNED_DEP | openUBMC 社区支持 + Scorecard 补齐识别项 | 徐海军 |
| 8 | BRANCH_PROTECTION | token 提权全量跑通 + sdi 字段补全（禁止删除/CODEOWNERS/T5） | C8 |
| 13 | FUZZING | 原生 fuzz 函数规则细化 | C9 |
| 16 | VULNS | 漏洞视图表名提供 | C10 |

---

## 产出物清单

| # | 产出物 | 落地位置 |
| --- | --- | --- |
| 1 | sdi 层 4 表 DDL（接口链路） | Doris 直接执行 |
| 2 | sdi 层 4 表清洗 DML | DolphinScheduler SQL 任务 |
| 3 | commit 链路 raw+sdi 2 表 DDL | Doris 直接执行 |
| 4 | euler sdi 表 DDL | Doris 直接执行 |
| 5 | dwi_security_pr_scan DDL + D1 SQL | Doris + DolphinScheduler |
| 6 | dwi_security_meta_api_scan DDL + D2 SQL | Doris + DolphinScheduler |
| 7 | dwi_security_maintained_scan DDL + D3 SQL | Doris + DolphinScheduler |
| 8 | dwi_security_file_scan DDL + security_file_scan.py（7 个 metric_code） | Doris + Python 脚本 |
| 9 | dwi_security_license_scan DDL + security_license_scan.py（scancode） | Doris + Python 脚本 |
| 10 | dm_security_scan_score DDL + D4 汇聚 SQL | Doris + DolphinScheduler |
| 11 | DolphinScheduler DAG 编排（04/05/06 层） | DolphinScheduler UI |
