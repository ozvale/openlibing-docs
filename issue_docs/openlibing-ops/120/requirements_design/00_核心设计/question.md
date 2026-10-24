# 代码安全检查评分看板 · 需求澄清问题清单（question.md）

> 用途：数据获取与链路设计前，必须澄清的口径问题。涉及数据来源、计算逻辑、数据质量风险、业务设计合理性、边界处理五类。
> 已用 Doris MCP 查证上游表结构与字段，问题基于真实表字段提出。

---

## 一、数据来源（哪张表/字段/层级）

**Q1. 前 90 天 commit 的取数来源与口径**

- 指标1明细要「90天commitid」。上游现有两种：
  - `raw_repo_commit_log`（本次新建，`commit_time` 为 author 时间，`branch_name` 区分分支）
  - 已有 `commits` 表（`author_date`，但无 `repo_id`，仅有 `repository_name`，且无分支维度）
- 确认：commit 统计用 `raw_repo_commit_log` ，但是不要直接用 ，我让清洗了一个sdi层的表：sdi_repo_commit_log，用这个表
- 确认：只统计默认分支（`sdi_repo_branch_info.default_branch`），还是全部分支聚合？上游按道理处理好的sdi_repo_commit_log表 就都是默认分支了，直接取。

**Q2. 前 90 天 issue 的取数与判定**

- `sdi_repo_issue_info` 有 `created_at`、`state`。确认 issue 活跃数统计口径：
  - 是「这 90 天内**新建**的 issue 数」？ 是，= 90 天内新建的 issue 数（按 `created_at`），已确认

**Q3. 指标2/4「最近30次已合入PR」的取数表**

- 表格指定 `dwi_rd_efc_pr_info_sum`，以 `repo_url + number` 为唯一键，字段含 `creator/merged_at/state`。
- 确认「最近 30 次已合入」排序字段：用 `merged_at` 倒序取 30 条？合入时间来源可靠度如何？无需担心 直接取即可
- 该表是 GitHub/GitCode/Gitee 已归一化？还是只覆盖部分平台？ 当前全局只考虑gitcode

**Q4. 指标3 分支保护/PR设置接口的归属**

- 分支保护数据表中只有 gitcode 接口文档。确认扫描仓库覆盖平台（gitcode/github/gitee）分别怎么取分支保护、PR设置、webhook、release、contributors 数据？ 当前全局只考虑gitcode
- 是否需要对这些接口逐平台写 raw 建表任务？ 当前全局只考虑gitcode

**Q5. 指标15 已知漏洞的数据来源表**

- 表格写"openLiBing-漏洞管理-漏洞视图表，表位置已在绿区发送"。需要提供**具体库.表名**（当前 openlibing 库未确认对应表）。
- 需要确认：`issue_plan_closed_time` / `issue_created_time` / 状态字段所在表。
- 这个指标先预留位置即可 最终是通过SQL可以直接查到的 会有表提供的 暂时不考虑

**Q6. 仓库扫描范围**

- 需要扫描的仓库是 `sdi_repo_info` 全量，还是有白名单/黑名单？`sdi_repo_scan_whitelist` 是否作为扫描范围依据？ 用这表 sdi_rd_efc_repo_operate_conf is_opertaed =1

---

## 二、计算逻辑（分子/分母/汇聚维度）

**Q7. 指标2 代码评审的分子分母**

- 得分 = 已评审数 / 总PR数 × 10。 是
- 分母「总PR数」= 最近30次已合入PR中**剔除机器人创建后**的数量？ 是
- 分子「已评审数」=「非机器人创建人+非机器人评审人进行了评审」的PR数？ 是
- 确认机器人判定规则统一为：gitcode 评论人名称含 `bot`；github 评论 `type=bot`。两者是否合并进同一 `sdi_rd_efc_pr_review_reviewer` 表？ github不做

**Q8. 指标4 每个PR是否跑CI 的关联口径**

- 表格写通过 `dm_rd_efc_project_pipeline_relation` 判断。该表以 `pipeline_project/pipeline_id` 关联，字段无 `repo_id/number` 直接到 PR。这个表确实不对，你找一下，肯定能找到这张表。
- 确认 PR→流水线的关联链：`PR → 关联的 pipeline → 该PR是否有对应 run` 具体是通过哪张关系表、哪个字段串起来？
- **已定位正确表**：`dwi_rd_efc_pr_workflow_run`
  - 唯一键 `(repo_url, number, commit_sha, workflow_run_id)`
  - 该表在 `repo_url + number` 上直接关联到 PR，一行=该PR的某次commit触发的一次workflow run（含 `conclusion/created_at/run_started_time/run_end_time`）
  - 判定「该PR是否跑CI」：按 `repo_url+number` 是否在该表存在 workflow run 记录；「CI是否通过」：看 `conclusion`
  - 备选：`dwi_pull_request_pipeline_statistics`（键 `(repo_id, pr_id, pipeline_status)`，含 `execute_count/execute_success_count`，走 CodeArts pipeline 链路时用）

**Q9. 指标3 各项要求判定后的计分**

- 分支保护有多项要求（基本保护/PR流程/状态检查/高级审查），逐项满足判定。确认每条要求的权重或"一票否决"规则？还是每满足一项得固定分？答案：评分分为 5 个层级，各层级分值依次为 3 分、3 分、2 分、1 分、1 分，总计 10 分。必须完整满足当前层级的所有保护规则才能获得该层级的全部分值，未满足任一条则该层级得 0 分，且后续层级不再计分。

  Score = T₁ + T₂ + T₃ + T₄ + T₅

  T₁=3（阻止删除+强制推送），T₂=3（PR审查+状态检查前置），T₃=2（状态检查通过），T₄=1（≥2审查者+CODEOWNERS），T₅=1（取消过期审查+管理员约束）

  每层需全部满足才得分，未满足则该层及后续层级均不得分，第五层先空着。具体规则没给。

**Q10. 指标16 二进制制品扫描范围**

- 得分 = 10 - 二进制文件数（下限0）。确认：
  - 二进制文件后缀清单由谁定？（Excel未给明确清单`.exe`、`.dll`、`.so`、`.dylib`、`.a`、`.o`、`.obj`、`.pyc`、`.class`、`.jar`、`.war`、`.ear`、`.zip`、`.tar`、`.gz`、`.7z`、`.rar`、`.bz2`、`.xz`、`.pdf`、`.doc`、`.docx`、`.xls`、`.xlsx`）
  - 扫描范围是否排除依赖目录（如 node_modules/.git/build）？还是有 `.gitignore` 语义？ 先不排除

---

## 三、数据质量风险（IFNULL/NULL语义/除零/汇聚失真）

**Q11. 指标1 公式除零与 NA**

- Score = min(10, 10×(commit_{90}+issue_{90})/13)。若某仓库90天内 commit+issue 很大，`min` 截断到10，需确认无问题。 是的
- 归档或创建不足90天的仓库处理为 NA「不参与后续分数汇聚」。确认 NA 在 dwi/宽表里的表示：`score=NULL` + `is_na=1`？宽表里该列存 NULL。 是的

**Q12. 指标2 分母为 0**

- 若某仓库最近30次已合入PR全为机器人创建（剔除后分母=0），得分怎么算？直接给 0 还是 NA？ NA 后续为NULL

**Q13. commit/issue 数据缺失时**

- 若 `raw_repo_commit_log` 某仓无数据（未扫描到/增量遗漏），是当作 0 统计，还是标记 NA 并告警？——涉及"空数据被当成低分"的失真风险。 呈现为NULL

**Q14. 平台数据不全**

- GitHub PR 评论、GitCode 评论、Gitee 数据覆盖度不一致时，指标2 是否会产生"跨平台口径不一致"导致失真？是否需要按平台分列记录？ 只会统计gitcode

---

## 四、业务设计合理性（冲突/更优方案）

**Q15. 指标5 危险工作流为0分制**

- 指标5 是「任一不满足即 0 分、皆满足 10 分」的二元判定，打分跳变大是否合理？确认无分级需求。 正常

**Q16. 指标12 SAST 仅判断"是否存在 pre-commit 配置"**

- 表格写"有 pre-commit 配置文件即可"。一个**仅存在配置文件但实际未在 CI 中执行**的仓库是否也算满足？可能是口径漏洞，确认是否需要加"流水线/CI中确实调用"的校验。 正常

**Q17. 指标9 Packaging 的三判定冲突**

- 规则是：有workflow→10分；或用openEuler固定工程匹配→10分；都不满足→不计入（NA?）。正常
- 确认优先级：先看workflow，再看工程匹配，"都不满足则不计入评分" 是 NA 还是 0 分？正常

---

## 五、边界处理（空数据/异常/时间范围）

**Q18. 扫描时间戳与历史**

- dwi/dm 以 `scan_time`（本次入库时间）标识每次扫描。确认是否需要保留历史多批次（即同一 repo 多次 scan_time 都保留，用于趋势）？还是只保留最新一批覆盖？是的 ，都保留。

**Q19. 仓库创建时间不足 90 天判定**

- 依据 `sdi_repo_info.create_time`（varchar(20) 字符串类型）。确认格式与解析方式；归档判定用 `sdi_repo_info.status='archived'`。是的

**Q20. 依赖已建 raw 表的兼容**

- `raw_repo_commit_log` 唯一键 `(repo_id, branch_name, commit_hash)`。若按默认分支统计，是否需要额外建唯一键/分区策略支撑 90 天窗口查询的量级？不需要吧，现在已经洗了SDI表。

---

## 六、重点口径补充（用户已确认）

**指标 18 · 版权合规（Copyright，规则，权重10）扫描明细**

- 扫描固定后缀文件：`.go` `.java` `.py` `.js` `.c` `.cpp` `.rs` `.ts` `.sh` `.bat`
- 判定规则：文件内是否存在版权合规声明 `Copyright(c) 2026 Huawei Technologies Co.`
  - 时间 `2026` 为四位数字、可替换
  - 其余文本全匹配
- 记录明细：每种后缀文件是否满足要求及匹配内容；得分
- 落表：合入 `dwi_rd_efc_security_file_scan`（Python 扫描）

**扫描范围口径确认**

- 仓库扫描范围：取 `sdi_rd_efc_repo_operate_conf` 且 `is_operated = 1`
- 全局平台：只考虑 gitcode（github/gitee 本轮不做）
- 指标9 二进制后缀清单已明确：`.exe .dll .so .dylib .a .o .obj .pyc .class .jar .war .ear .zip .tar .gz .7z .rar .bz2 .xz .pdf .doc .docx .xls .xlsx`；先不排除目录
- 指标15 漏洞：先预留字段，最终由 SQL 查表提供，暂不设计

---

## 附：开放/遗留问题

- Excel 末尾「分数汇聚到项目层级的公式是什么」——按你的说明，本次仓库层只做到「查明细→打分→入宽表」，项目层汇聚暂不涉及。是否需要我在 dm 预留 `project_id` 以备用？

忽略 你不管
