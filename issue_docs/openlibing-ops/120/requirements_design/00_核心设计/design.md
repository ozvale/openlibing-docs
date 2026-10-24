# 代码安全检查评分看板 · 总体设计（design.md v4 终版）

> **版本记录**
>
> - v4.8（2026-10-20）：指标 7 `CODE_REVIEW` 评审口径收紧——`is_effective_review` 从「命令为 `/lgtm` 或 `/approve`」收紧为**仅 `/lgtm`**，且判定改为 body **token 级匹配**（`(^|[[:space:]])/lgtm($|[^a-z0-9_-])`，以空白符为边界、任意行生效）：适配 `/approve\n/lgtm` 跨行连发（实测 6,531 条）与 `/squash\n/lgtm\n/approve` 命令束（419 对）；独立 `/approve` 不再算评审（评审人×PR 有效对 264,281 → 约 19.8 万，-25%）；`/lgtmfoo`、`/lgtm-cancel` 等粘连形态不误伤（实测排除 5 条）。有效评审的 `review_type` 统一归一 `/lgtm`（指标 8 复用此表按 `review_type='/lgtm'` 统计，口径自动对齐）。改动落 `sdi层清洗DML.sql` [6]；重跑链路 sdi[6] → D1 → D4 → D6 → D7（手动执行）。
> - v4.7（2026-10-16）：三项 NA 口径改满分——① 指标 3 `DANGEROUS_WF`：无 workflow 文件 → **10 分**（原 NA，135 仓实测 117 仓）；② 指标 4 `TOKEN_PERM`：无 workflow 文件 / 有 workflow 但无受检插件引用 → **10 分**（原 NA）；③ 指标 16 `VULNS`：漏洞平台无 CVE 记录覆盖 → **10 分**（原 NA，135 仓实测 90 仓），D5 段无覆盖仓计数 0/明细空/扣分全 0。三指标的「workflow 解析失败 → 整指标 NA」分支保留（没看成≠没问题）。改后 Doris 存量需重跑：P1 脚本（指标 3/4）→ D5 → D4 → D6。
> - v4.6（2026-10-06）：进度交付——① 指标 3 `DANGEROUS_WF` 扫描盲区修复（9/30）：检测项②不可信上下文变量遍历从顶层 `jobs:` 扩展到全部三种 job 结构（`stages.<stage>.jobs` / `post.jobs` / `pre.jobs`，复用 TOKEN_PERM 的 `_extract_wf_jobs`），检测项①为递归实现无此问题；实测影响 39 处命中、13 仓 10→0。② 指标 14 `SAST` 规则改版交付（9/30）：脚本 `scan_sast` 重写（8 工具级检测）+ 明细展示配置双写（classpath `security/detail-conf/SAST.json` 兜底 + Doris 配置表补丁 `detail-conf-patch-sast-rule-v2.sql`，须先重跑脚本后执行 SQL）+ 验证 8/8 PASS；dm 层 D4/D6 无需改（算分在 Python，dm 只透传 score，新 NA 走既有 `score IS NOT NULL` 剔除口径）。Doris 存量 132 行仍是旧口径结果，待全量重跑覆盖。
> - v4.5（2026-09-28）：指标 4 `TOKEN_PERM` 规则改版——检查对象从 permissions 声明级别转为**插件实际生效权限**：13 个 openlibing 插件按官方路径基准表检查（给定权限 repository:read 其余 none），未命中名单的 uses 引用一律按只读检查（原口径为跳过）；生效权限三层 fallback（job>全局>默认读）；违规 = 生效权限含超出基准的 write（读写分离天然成立：job 配 write 则该 job 全部受检插件违规）；违规插件仓库级 Set 去重扣 1 分/个，`score = max(0, 10−违规插件数)`；新增 NA 场景（有 workflow 但无受检插件引用）。C5 五条规则与 v4.2 线性内插口径作废；"权限映射待李洪峰"遗留项以配置表落地关闭。插件基准表落 Doris 配置表 `sdi_sec_token_perm_plugin`（单一数据源，追加/停用插件只改表数据）。
> - v4.4（2026-09-28）：指标 8 `BRANCH_PROTECTION` 规则更新转正（李建鹏）——平台默认管控分支保护，层级递进公式坍缩为**二元计分（8 保底/10 满分）**：T1/T2/T3/T5 默认满足；仅当仓库 `.infra_self_service/rebot.yaml` 配置 `lgtm_need_num=2` 时，检查近 30 个已合入 PR 是否均有**两条不同人**的 `/lgtm` 评论（剔机器人、剔 PR 作者），通过则 +2 满分，否则 8 分（含触发检查但无 PR），无 NA。T1a/T1b 接口链路及 sdi 两表废弃；数据源改为 rebot.yaml（P1 脚本新增 scan_branch_protection，明细入 file_scan 表）+ /lgtm 评论（复用指标 7 链路）；新增 D7 任务、重构 dwi_rd_efc_security_branch_protect_scan 表结构；权重激活后规则分母 82.5→90、全量 95→102.5。
> - v4.1（2026-09-20）：C1 修订——版权正则改为**有空格写法**（实测 12 仓 16571 文件版权头均为 `Copyright (c) 2026 Huawei...`，原无空格口径全量 0 匹配）；P1 仓库清单/分支口径定版：只扫**默认分支**，默认分支取数与 openlibing-ops PR 看板 `repo/branch/all` 接口保持一致（sdi_repo_branch_info.default_branch）。
> - v4.2（2026-09-21）：P1 边界口径拍板——① `DANGEROUS_WF`：workflow 文件解析失败 → 整指标 NA（不当 0 分）；② `COPYRIGHT`：超 8MB/不可读文件分子分母均不计（视同不存在）；③ `TOKEN_PERM` 混合场景（部分顶层只读 + 部分未配置且无写）为 C5 未覆盖缝隙，脚本按 `10 − 未配置占比` 线性内插，**当前 12 仓实测无命中**，命中时需人工复核口径。
> - v4.3（2026-09-22）：指标 16 `VULNS` 接入（C10 关闭）——源表落定 `sdi_rd_efc_cve_details`；拍板口径：① rejected 视为关闭态不扣分；② `cve_level` None/空按 Low 扣 1；③ 源表 `is_overdue_statistics` 不采用（closed 历史超期也标 1），超期自行判定；④ 无 CVE 记录（未覆盖，135 仓实测 90 仓）→ NA。新增 DML [D5] 段 + 权重激活 UPDATE（规则分母 75→82.5、全量 87.5→95）。
> - v4（2026-09-17 终版）：C1~C11 全部仲裁完毕并落入 §5 正文；定版本期开发 14 项、暂缓 4 项（5/8/13/16 脚本开发挂起）；数据源现状定版：commit 链路 + 6 接口链路（"1+6"）采集任务已建、sdi 清洗待执行；CI 判定定版单表；Webhook password_is_null 已补；新增 §11 开发清单。
> - v3（2026-09-16）：合并上游最新规则《安全合规指标分析 (2).xlsx》，全面重写指标获取与打分规则；新增汇聚与亮灯规则；仲裁上游表内矛盾（见 §9）。
> - v2：用户评审 4 条意见落实（明细字段细化 + 全字段注释）。
> - v1：初版基线（question.md 20 问收敛）。
>
> **规则来源与优先级**：上游《安全合规指标分析 (2).xlsx》（最新）> question.md 已确认口径 > 旧《代码安全检查评分表.xlsx》（开发理解版，仅作参考）。
> **指标编号**：v3 起统一采用上游新表序号 **1~18**（与旧表序号不同！），并以 `metric_code` 为稳定标识。

---

## 1. 背景与目标

建设"代码安全检查评分看板"，体系化评估代码仓安全合规水平。指标集来自上游安全合规团队（对标 OpenSSF Scorecard，共 **18 个指标**），规则矛盾已全部仲裁（§9）。**v4.4 现口径：本期开发 16 项，暂缓 2 项**——指标 5 依赖锁定 / 13 模糊测试（仅保留 dm 列位，汇聚分母剔除）；指标 16 已知漏洞已于 2026-09-22 接入（源表 `sdi_rd_efc_cve_details`，[D5] 段）；指标 8 分支保护已于 2026-09-28 规则更新转正（rebot.yaml + /lgtm 评论链路，[D7] 段）。

**数据生产链路**：DolphinScheduler 定时任务 → Doris 分层数仓（raw → sdi → dwi → dm）→ 前端看板读取 dm。

**分层目标**：

1. 按扫描任务类型建 **dwi 明细结果表**：SQL 可兼容的指标合入同一 SQL 任务写同一张表。
2. 汇聚到 **dm 宽表快照**：每仓库 × 每次扫描时间戳 × 18 指标得分 + 仓库加权总分 + 亮灯。
3. 项目层级汇聚规则已由上游给出（§6），实现范围本轮待定。

---

## 2. 指标总览（上游新表序号）

| #   | 指标名       | metric_code         | 类型 | 权重 | 获取通道                         | 本轮状态                                                                  |
| --- | ------------ | ------------------- | ---- | ---- | -------------------------------- | ------------------------------------------------------------------------- |
| 1   | 开源许可证   | `LICENSE`           | 规则 | 7.5  | 文件(scancode)                   | ✅ 可实现                                                                 |
| 2   | 版权合规     | `COPYRIGHT`         | 规则 | 10   | 文件                             | ✅ 可实现（C1 v4.1：有空格正则+匹配率打分）                               |
| 3   | 危险工作流   | `DANGEROUS_WF`      | 规则 | 10   | 文件                             | ✅ 可实现                                                                 |
| 4   | 令牌权限     | `TOKEN_PERM`        | 规则 | 7.5  | 文件                             | ✅ 可实现（C5 已定 5 条规则；映射细节遗留）                               |
| 5   | 依赖版本锁定 | `PINNED_DEP`        | 建议 | 5    | 文件                             | ⏸️ 暂缓（仅设计表字段，脚本挂起）                                         |
| 6   | 二进制制品   | `BINARY_ARTIFACTS`  | 规则 | 7.5  | 文件                             | ✅ 可实现                                                                 |
| 7   | 代码评审     | `CODE_REVIEW`       | 规则 | 7.5  | SQL（已有表+新建评审清洗）       | ✅ 可实现（评审表已建）                                                   |
| 8   | 分支保护     | `BRANCH_PROTECTION` | 规则 | 7.5  | 文件+SQL（rebot.yaml+/lgtm评论） | ✅ 可实现（2026-09-28 规则更新转正，原接口链路废弃）                      |
| 9   | Webhook 安全 | `WEBHOOKS`          | 规则 | 10   | 接口→SQL                         | ✅ 可实现（password_is_null 已补）                                        |
| 10  | CI 测试      | `CI_TESTS`          | 规则 | 2.5  | SQL（codearts关联表）            | ✅ 可实现（单表定版）                                                     |
| 11  | 发布签名     | `SIGNED_RELEASES`   | 建议 | 5    | 接口→SQL                         | ✅ 表已建（C2 已定：近30次/NA/全满足10其他0）                             |
| 12  | 软件包发布   | `PACKAGING`         | 规则 | 5    | 文件+接口(openEuler工程)         | ✅ 可实现（euler任务已建）                                                |
| 13  | 模糊测试     | `FUZZING`           | 建议 | 5    | 外部清单+文件                    | ⏸️ 暂缓（规则未完全确定，C9）                                             |
| 14  | SAST         | `SAST`              | 建议 | 5    | 文件                             | ✅ 可实现（pre-commit 判定；计分待二次确认）                              |
| 15  | 安全策略     | `SECURITY_POLICY`   | 规则 | 5    | 文件                             | ✅ 可实现（2026-10-12 B 口径：无文件0/有文件三项独立加分 1+6+3；C3 作废） |
| 16  | 已知漏洞     | `VULNS`             | 规则 | 7.5  | SQL（sdi_rd_efc_cve_details）    | ✅ 已接入（2026-09-22，C10 关闭）                                         |
| 17  | 项目维护     | `MAINTAINED`        | 规则 | 2.5  | SQL（已有表）                    | ✅ 可实现                                                                 |
| 18  | 贡献者多样性 | `CONTRIBUTORS`      | 建议 | 2.5  | SQL（组织链路已建）              | ✅ 表已建（C6 已定）                                                      |

**权重小计**（用于 §6 汇聚）：规则类 13 项合计 **90**；建议类 5 项合计 **22.5**；全部 18 项合计 **112.5**。
**v4 本期口径**：开发 16 项合计 **102.5**（规则类 13 项 = 90，指标 8 已于 2026-09-28 转正；建议类 3 项 = 12.5，剔除暂缓的指标 5/13）。**暂缓 2 项（5/13）在 dm 中恒为 NULL，汇聚分母自动剔除（同 NA 逻辑）**，后期接入即自动纳入。

---

## 3. 通用口径

| 项                      | 口径                                                                                                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 平台                    | 仅 gitcode（github/gitee 本轮不做）                                                                                                                                                                     |
| 扫描仓库范围            | `sdi_rd_efc_repo_operate_conf` 且 `is_operated=1`；文件扫描（通道③）**只扫默认分支**，默认分支取 `sdi_repo_branch_info.default_branch`（v4.1）                                                          |
| 机器人识别              | gitcode：评论/用户**名称含 `bot`** 即机器人                                                                                                                                                             |
| 90 天基准               | 相对每次扫描时间戳 `scan_time` 往前推 90 天                                                                                                                                                             |
| **NA 语义（全局统一）** | 上游"inconclusive / 不纳入评分"统一落地为：`score=NULL` + `is_na=1`；**汇聚时分子分母同时剔除该项权重**。**0 分是有效得分，参与汇聚**（如 License 无许可证=0 分、Webhook 全部未配密钥=0 分，均不是 NA） |
| 历史批次                | 多次 `scan_time` 全保留，不覆盖                                                                                                                                                                         |
| 每批一致性              | 一次扫描所有指标使用同一 `scan_time`（批次号统一），dwi 各表实际入库时间可不同                                                                                                                          |

---

## 4. 分层架构与数据通道

```text
通道①接口拉取(raw→sdi)      通道②已有表SQL直算        通道③仓库文件Python扫描      通道④外部清单拉取
 分支保护/PR设置              commit/issue/PR/workflow   workflow yml/LICENSE/        OSS-Fuzz projects/
 Webhook/Release              漏洞视图表                 SECURITY.md/二进制/版权/      openEuler固定工程
 用户orgs/PR评论(复用)                                    pre-commit/Dockerfile/sh
        │                          │                          │                        │
        └──────────────┬───────────┴──────────┬───────────────┴──────────┬──────────────┘
                       ▼                      ▼                          ▼
                  DWI 明细结果表（6 张，按任务类型）                            │
                       └──────────────────────┬───────────────────────────┘
                                              ▼
                       DM 宽表 dm_rd_efc_security_scan_score（repo × scan_time × 18 指标 + 加权总分 + 亮灯）
```

---

## 5. 指标获取与打分规则（核心章节 · 18 项）

> 每项统一结构：**数据获取 → 打分规则 → NA 条件 → dwi 记录明细**。打分公式均为上游原文整理；矛盾处标注 C#，推荐方案见 §9。

### 5.1 开源许可证 `LICENSE`（规则，7.5）

- **数据获取**（Python + scancode-toolkit）：
  - 扫描仓库 `./` 或 `./license` 目录下 LICENSE 文件；命令：`scancode --license --copyright --license-text --license-text-diagnostics --json-pp licenses_report.json <repo>/LICENSE`。
  - 取 3 个内容：① SPDX 标识；② 与模板一致性（scancode `score==100` 视为满足模板，否则读 `matched_text_diagnostics` 差异内容并**单独落库**）；③ `copyrights` 字段值且格式 `Copyright (c) <年份> Huawei Technologies Co.`（年份可替换，正则）。
  - OSI/FSF 判定：spdx 许可证名称匹配 `https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json`（忽略大小写）。
- **打分规则**（递进式累加，2026-10-10 口径仲裁改版；高档位预设低档位条件）：有许可证 **+5 分**（总 5，仓库行为）→ 内容与标准模板一致 **再 +3 分**（总 8，文件内容）→ 版权行年份/责任人替换正确 **再 +1 分**（总 9，文件内容）→ 许可证类型 OSI/FSF 认证 **再 +1 分**（总 10）；无许可证 **0 分**（不是 NA）。**变更原因**：原"只取满足的最高档"并联口径下，OSI 认证许可证（如 Apache-2.0）绕过 copyright 检查直接 10 分，致 9 分档对常见开源许可证失效（现网 130+ 仓仅 1 仓 9 分且系 Mulan key 映射 bug 意外掉档）。
- **NA 条件**：无。
- **dwi 记录**：spdx 编号、扫描 json、FSF/OSI 满足情况、模板一致性、copyright 匹配、得分、扫描时间。

### 5.2 版权合规 `COPYRIGHT`（规则，10）--- ✅ 2026-10-06 规则改版（v2 模板化检查，handoff 定稿）

- **数据获取**（Python，security_file_scan.py）：
  - **目标文件**：`.go .java .py .js .c .cpp .rs .ts .sh .bat` 后缀；路径段精确等于 `test`/`tests` 剔除（不匹配 testing 等，计入 `excluded_test_file_count`）；超 8MB/不可读分子分母均不计。
  - **LICENSE 分流三分支**（只读根目录，子目录 LICENSE 不做，§8 拍板）：
    1. 无/不可读 LICENSE → 整仓 NA；
    2. 木兰（12 条正则识别 MulanPSL-2.0/1.0、MulanPubL-2.0/1.0，对原文匹配不可小写化）→ 官方 4 模板严格匹配（含 "a copy of **the** Mulan" 变体重试）；
    3. 非木兰但 LICENSE 印有"如何应用"附录（占位符风格 `Copyright [yyyy] [name of copyright owner]` 或已填值风格 `Copyright 2025 ... + 10 行内 Licensed under the`）→ 印刷归一模板字面严格匹配（版权行变量化，其余文字写错也照查）；
    4. 其余 → 4+1 匹配集（builtin 5 模板 + custom 1 模板任一命中即过，不做协议一致性检查）。
  - **混合协议仓豁免**：LICENSE 含 ≥2 处条款主体结束标记（`END OF [THE] TERMS AND CONDITIONS`）判定为混合协议（如 repo_403209 根 = CANN 条款 + Apache 全文 + Apache 附录），不走 printed 走 4+1（实测 113 仓仅 1 个命中，不影响其余 27 个 printed 仓）。
  - **单文件检查链**：头部提取（64 行窗口，.py docstring 兜底）→ 版权行底线检查（三条正则任一命中：年份在前/owner 在前/无 (c)，owner 固定 Huawei）→ 模板正文归一化全匹配（前 64 行头部 → 注释剥离 → 小写 → 去标点 → (c) 归一 → 折行合并；模板占位符 `{year}`→`\d{4}`、其余→`.+?`，首尾锚定）。
  - **木兰两行短头 = 不合格**（严格派，业务拍板）；`upstream_banner`（`part of the llvm project`）仅标注不改判定。
- **打分规则**（2026-10-08 改扣分制）：`score = max(0, 10 − 0.2 × 不合格文件数)`，每个不合格文件扣 0.2 分、50 个扣完；与 BINARY_ARTIFACTS/TOKEN_PERM 同族。扣分基数=全部不合格文件（含 upstream_banner 标注文件，banner 仅是展示过滤标记不改判定）。替代原比率制 `10 × 合格/目标`。
- **NA 条件**：无/不可读 LICENSE → 整仓 NA；仓库无任何目标后缀文件 → NA。
- **配置表** `dim_copyright_template_config`：10 条种子（mulan 4 + builtin 5 + custom-cann 1），启动时整表加载进内存（status=1），`copyright_template_config.sql` 手动执行建表。软件名只验占位不验内容（2026-10-06 拍板，不建 repo 级软件名配置表）。
- **dwi 记录**：detail_json 保留原 6 字段（target_file_count/matched_count/by_ext/sample/oversize_file_count）+ 新增 7 字段（license_file/license_type[mulan|printed|none|missing]/mulan_license_id/matched_template_id/excluded_test_file_count/unmatched_reasons[no_header|no_copyright_line|owner_mismatch|template_mismatch|upstream_banner]/unmatched_samples）。
- **逐文件明细表**（2026-10-07 明细试验，`security_file_scan-明细试验.py`）：`dwi_rd_efc_security_copyright_file_detail` 全量落不合格文件（file_path/ext/reason/is_banner），一行=一个不合格文件×一个批次，不受 detail_json 200 条截断限制；大仓可达万级行（repo_401712 实测 1.2 万+），按 2000 行分批插入；明细为辅助数据，插入失败仅告警不阻断主表；reason 与主表主原因同口径（upstream_banner 走 is_banner 标记不单列）；看板走 API 分页查询展示完整清单（可按 is_banner 默认过滤上游 banner）。
- **明细分页接口**（2026-10-08 交付，用户拍板**不走 conf_json 统一模板**、独立接口，前端自行渲染）：`POST /security/copyright-file-list`，请求继承 TimeReq（带时间）+ repoId/reason/ext/includeBanner/page/pageSize；响应 PageResult + reasonSummary（三分类计数）+ scanTime，每条记录附 fileUrl（GitCode 文件跳转地址，后端拼装 `{repo_url 去 .git}/blob/{默认分支}/{filePath}`，仓库地址取 operate_conf、分支取 sdi_repo_branch_info 默认分支与扫描口径一致，缺失时 null 前端降级纯文本；实测 111 仓恒非 null）。展示层三分类归并（Service 层做，底层码不丢）：no_header+no_copyright_line→`no_copyright`「无版权声明行」、owner_mismatch→「版权行不规范」、template_mismatch→「版权头与协议模板不匹配」；每条记录返回 reasonCode+中文 reason 双字段；reasonSummary 不受 reason 筛选影响（筛选器稳定渲染）、受 ext 筛选影响；banner 默认过滤，includeBanner=true 开启；批次定位与看板同口径（≤快照日最近批次）。实现：SecurityDashboardController + SecurityCopyrightFileService + SecurityScoreMapper 5 个查询（4 明细 + 1 仓库地址/默认分支，先 MAX(scan_time) 解析批次再精确过滤 + LIMIT OFFSET 分页）。
- **验证**（113 仓本地回归全过，2026-10-06）：35 木兰仓全识别；7 无 LICENSE 仓全 NA；repo_401712 分母对账 12701/剔除 test 33683；repo_401224 CANN 仓 custom-cann 命中 9.49 分；repo_401717 docstring 兜底 9.38 分；短头仓（405549/401250 等）严格派大量 unmatched。
- 历史：初版（2026-09-12）单正则 `Copyright\s*\(c\)\s*\d{4}\s+Huawei Technologies Co.`；v2 改版为模板化检查（需求源：`参考/copyright_metric_handoff.md`）。

### 5.3 危险工作流 `DANGEROUS_WF`（规则，10）

- **数据获取**（Python，clone 后解析.gitcode/workflows下 yml、yaml）：

  1. 不可信代码检出：检测 workflow 文件是否存在 `allow-unsafe-pr-checkout: true`（gitcode 对 `pull_request_target` 检出 PR head.sha 已有默认保护，仅该显式配置视为违规）。
  2. 不可信上下文变量注入：检测步骤中直接使用不可信上下文变量，映射表（github → gitcode/atomgit）：`github.event.issue.title→atomgit.event.issue.title`、`github.event.pull_request.title→atomgit.event.pull_request.title`、`github.event.pull_request.body→atomgit.event.pull_request.body`、`github.event.comment.body→atomgit.event.comment.body`、`github.event.head_commit.message→atomgit.event.commits[].message`、`github.head_ref→atomgit.head_ref`。步骤遍历覆盖全部三种 job 结构：`jobs:` 平铺 / `stages.<stage>.jobs` / `post.jobs`+`pre.jobs`（2026-09-30 盲区修复：原仅遍历顶层 jobs，漏检 stages/post 嵌套结构 39 处命中，复用 TOKEN_PERM 的 `_extract_wf_jobs` 统一提取）。

- **打分规则**：发现任意危险模式 = **0 分**；未发现 = **10 分**。

- **NA 条件**（2026-10-16 口径更新）：无 workflow 文件 → **10 分**（原 NA 改满分，`full_score_reason: no_workflow_file`）；workflow 文件**解析失败 → 整指标 NA**（结论不完整，不当 0 分也不当满分，2026-09-21 拍板，保留）。

- **dwi 记录**：扫描 workflow 数量、每个文件规则检查情况（数组 json）、得分。

  ### 5.4 令牌权限 `TOKEN_PERM`（规则，7.5）--- ✅ 2026-09-28 规则改版（按插件给定权限检查，取代 C5 五条规则与 v4.2 线性内插）

- **规则变更（2026-09-28 拍板）**：检查对象从"permissions 声明级别"转为"**插件实际生效权限**"，按插件给定权限基准比对扣分。

- **数据获取**（Python）：检查 `.gitcode/workflows` 下 yml（`.gitcode/workflow` 单数拼写容错沿用），提取 jobs 下 steps 的 `uses:` 引用；插件名 = `uses` 值截掉 `@tag/sha/branch` 后的完整路径。job 容器兼容三种结构：`jobs:` 平铺 / `stages.<stage>.jobs` 嵌套 / `post.jobs`（.gitcode 独有）。

- **权限基准表**（**Doris 配置表 `sdi_sec_token_perm_plugin`，单一配置源**；脚本扫描时实时加载，追加/停用插件只 INSERT/UPDATE 表数据不动脚本；表无 is_active=1 条目直接报错退出，禁止静默降级）：
  - 13 个 openlibing 插件按官方路径建条目（如 `openlibing/sca-action/sca-pr-action`），给定权限 = `project/pr/issue/note: none, repository: read`，aliases 兼容裸名历史写法（如 `openlibing-pre-commit-action`）；
  - **未命中名单的 `uses` 引用（codearts 插件 / marketplace action / 仓内 action）一律按只读基准检查**（2026-09-28 修正：原口径为跳过）；
  - `.gitcode/workflows/*.yml` 相对路径的 workflow_call 复用引用不是插件，跳过；
  - 13 号 vulnerability-hunting-action（官方名 argus-action）的 CASE1/CASE2 参数化权限忽略，按统一基准处理；codearts 51 插件清单待补，补齐前按未命中只读口径已全覆盖。

- **生效权限三层 fallback**：job 级 `permissions` > 顶层 `permissions` > 默认（全读）。job 配了用 job 的，job 未配用全局的，全局未配用默认的（当前平台默认均为读）。

- **违规判定**：插件所在 job 的生效权限中任一 scope 为 `write` 且超出该插件给定基准（基准 none → 实际 read **不算**违规，只罚 write；`write-all` 直接违规）。**豁免 scope（2026-10-10 拍板）**：`id-token: write` 是 OIDC 联邦身份声明，不授予仓库资源写权限，且平台 PR-pipeline 标准模板默认携带，**不计入超权判定**（`write-all` 仍直接违规，因其覆盖 repository 等全部 scope）；`detail_json` 的 `write_scopes` 仍如实展示，仅不计违规。**读写分离由此天然成立**：一个 job 下挂多个插件，只要有插件需要 write 而给整个 job 配了 write，该 job 下所有基准不含 write 的受检插件全部违规（正确做法是拆两个 job 把 write 收窄到需要的 job）。

- **打分规则**：违规插件按**仓库级 Set 去重**（同一插件多处引用只记一次），`score = max(0, 10 − 违规插件数)`。

- **NA 条件**（2026-10-16 口径更新）：无 workflow 文件 → **10 分**（原 NA 改满分，`full_score_reason: no_workflow_file`）；有 workflow 但无任何受检插件引用（仅复用引用/纯脚本 job）→ **10 分**（原 NA 改满分，`full_score_reason: no_checked_plugin`）；workflow 文件解析失败 → 整指标 NA（对齐 DANGEROUS_WF 2026-09-21 拍板：结论不完整，保留）。

- **dwi 记录**：每个 workflow 扫描结果（顶层/job 生效权限及来源、各 job 插件引用与违规明细）、得分；`detail_json` 结构：`{wf_file_count, files:[{path, top_perm, jobs:{job:{perm, perm_source, has_write, write_scopes, plugins, violations}}}], stat:{checked_count, checked_plugins, violation_count, violations}}`。

- **实测基线（2026-09-28，111 个 gitcode 仓本地验证；2026-09-29 基准表落 Doris 后复验一致）**：参与评分 84 仓（47 仓未声明 permissions 默认读满分；37 仓有违规，集中 2 分档 26 仓——全局 write 模板 + 读写分离的必然结果）；NA 27 仓（无 workflow 20 + 无受检插件 7）；job 级 permissions 现网 0 使用，三层 fallback 中 job 覆盖为纯理论分支。基准表 `sdi_sec_token_perm_plugin` 已于 2026-09-29 建表并 INSERT 13 行（全部 is_active=1，28 个匹配键 = 13 官方路径 + 15 别名）。**dwi 明细表当前 132 行仍是旧声明级口径，待 P1 脚本更新到 DS 重跑覆盖。**

### 5.5 依赖版本锁定 `PINNED_DEP`（建议，5）--- 仅设计相关表字段，暂不做脚本开发

- **数据获取**（Python）：扫描 ① `.github/workflow` 与 `.gitcode/workflow` yml 中 action 引用；② Dockerfile 基础镜像；③ sh 脚本中 `curl`、`apt-get` 等安装命令。识别每条依赖是否锁定版本（action 带 tag/sha、镜像带 tag、安装命令带版本）。Go modules 视为已锁定。
- **打分规则**（简化版，推荐）：`score = 已固定依赖数 / 总依赖数 × 10`。
  （上游另有加权版：官方 Action w=2、第三方 Action w=8、其他依赖 w=10，`10 × Σ(wᵢ×锁定数ᵢ)/Σ(wᵢ×总数ᵢ)`，可作为 P2 精化，见 C5 备注。）
- **NA 条件**：仓库无任何可识别依赖 → NA。
- **dwi 记录**：涉及版本依赖的文件及结果、得分、扫描时间。
- **遗留**：openUBMC 社区额外支持（徐海军）；对标 Scorecard 源码补齐识别项。

### 5.6 二进制制品 `BINARY_ARTIFACTS`（规则，7.5）

- **数据获取**（Python）：全局扫描仓库文件树，命中后缀清单：`.exe .dll .so .dylib .a .o .obj .pyc .class .jar .war .ear .zip .tar .gz .7z .rar .bz2 .xz .pdf .doc .docx .xls .xlsx`（先不排除目录）。
- **打分规则**：`score = max(0, 10 − 二进制文件数)`，每个违规文件扣 1 分。
- **NA 条件**：无。
- **dwi 记录**：不符合文件的路径列表、得分、扫描时间。

### 5.7 代码评审 `CODE_REVIEW`（规则，7.5）

- **数据获取**（SQL）：
  - PR 集合：`dwi_rd_efc_pr_info_sum` 取 `merged_at` 倒序**最近 30 次已合入 PR**（上游已修正：不用 commit 关联，直接取近 30 次已合入 PR），剔除机器人创建的 PR。
  - 评审判定：`sdi_rd_efc_pr_review_reviewer`（**已建表+清洗 DML**，见 `sdi层清洗DML.sql` [6]）：由 `raw_pr_comment_gitcode` 清洗，owner+repo 反查 repo_id；`is_bot` = 名称含 bot/robot/[bot]；`review_type` = body 首个 `/` 命令（小写，仅作展示/追溯）；**`is_effective_review` = 非机器人且 body 任意行存在独立 `/lgtm` 命令**（v4.8 2026-10-20 收紧：token 级正则 `(^|[[:space:]])/lgtm($|[^a-z0-9_-])`，空白符边界——覆盖 `/lgtm` 独发、`/lgtm\n/approve`、`/approve\n/lgtm` 跨行、`/lgtm\n\n/approve` 空行分隔；**独立 `/approve` 不再算评审**；`/lgtmfoo`、`/lgtm-cancel` 粘连不误伤；有效评审的 `review_type` 落库统一归一 `/lgtm`）。某 PR 存在评审记录且**评审人非机器人、非 PR 创建人**（"非创建人"在指标计算层结合 PR 表处理）→ 已评审。
- **打分规则**：`score = 已评审数 / 总PR数 × 10`。
- **NA 条件**：剔除机器人后 PR 数 = 0 → NA。
- **dwi 记录**：PRs 编号列表、不通过评审 PR 数、不通过原因（数组）、得分。

### 5.8 分支保护 `BRANCH_PROTECTION`（规则，7.5）--- ✅ 2026-09-28 规则更新（上游李建鹏），指标转正

- **规则变更（2026-09-28 拍板）**：gitcode 平台已默认管控分支保护，T1/T2/T3/T5 不再逐仓查接口，**全部默认满足**；层级递进公式坍缩为二元计分（8 分保底 / 10 分满分，**不存在中间分**）。原 T1a/T1b 接口链路（protect-branches / pull-request-settings）**废弃**。

- **数据获取**（文件扫描 + SQL，复用已有链路）：
  - **rebot.yaml**：`security_file_scan.py` 新增 `scan_branch_protection`，读仓库 `.infra_self_service/rebot.yaml`（仅默认分支），解析 `lgtm_need_num`，明细写 `dwi_rd_efc_security_file_scan`（`metric_code='BRANCH_PROTECTION'`，score=NULL 由 D7 统一计算）。
  - **/lgtm 评论**：复用指标 7 已有链路 `sdi_rd_efc_pr_review_reviewer`（`review_type='/lgtm'`，非机器人）+ 近 30 次已合入 PR 集合（与指标 7/10 同口径：`merged_at` 倒序、剔除机器人创建的 PR）。v4.8（2026-10-20）起有效评审 `review_type` 统一归一 `/lgtm`，`/approve\n/lgtm` 跨行评论亦计入；纯 `/approve` 评论不计。

- **判定流程**（递进三步）：
  1. 机器人默认 `lgtm_need_num = 1`（无 yaml / yaml 无该项配置均按默认 1 处理）；
  2. 检查仓库是否存在 `.infra_self_service/rebot.yaml`，存在则读 `lgtm_need_num`；
  3. **仅当 `lgtm_need_num = 2`** 时触发检查：近 30 个 PR **每个**都需存在两条 `/lgtm` 评论，且**两条来自不同人**（剔除机器人评论、剔除 PR 作者本人的评论）。其他取值（1/3/…）不触发检查。

- **打分规则**（二元）：
  - `score = 8`（默认）：T1(3)+T2(3)+T3(2) 平台默认满足，得基础 8 分；
  - `score = 10`：存在 rebot.yaml 且 `lgtm_need_num = 2` 且近 30 PR 均满足"两条不同人 /lgtm"（解锁 T4(1)+T5(1) 再得 2 分）；
  - 触发检查但未通过（含 `lgtm_need_num=2` 且近 30 PR 为 0 的情况）→ 仍 8 分。

- **NA 条件**：无（本指标恒有得分，`is_na=0`）。

- **dwi 记录**：`dwi_rd_efc_security_branch_protect_scan`（D7 产出）——`base_pass`（默认满足标记）、`has_rebot_yaml` + `yaml_lgtm_config`（连名带值原文）+ `lgtm_need_num`（数值化）、`pr_lgtm_pass`（是否通过双人 lgtm 检查）、`pr_numbers` + `pr_lgtm_detail`（逐 PR 最后两条 /lgtm 的评论人和时间），见 §7.2-③。

### 5.9 Webhook 安全 `WEBHOOKS`（规则，10）——C7 已解决（password_is_null 已添加）

- **数据获取**（接口 → raw → sdi，**表已建**）：拉取任务 T5（仅公开仓库）→ `raw_repo_webhook`（repo_id+webhook_id，url/active 三态/result_code/created_at，**不取 password 防明文入库**）→ 清洗（`sdi层清洗DML.sql` [5]）→ `sdi_rd_efc_repo_webhook`（is_active 三态透传）。
  - ✅ **C7 已解决（0917 17:30 采集层修正）**：已添加 `password_is_null` 字段（布尔位，不落明文），阻断缺口消除。
- **打分规则**（C7 已定）：`score = ⌊10 × 配置密钥的Webhook数 / 活跃Webhook总数⌋`；**已配置密钥判定 = `active=1 且 password_is_null=0`**；分母 = active=1 的活跃钩子；**无活跃 Webhook = 10 分**（不是 NA，上游明确）；全部未配置密钥 = 0 分。
- **NA 条件**：无。
- **dwi 记录**：激活状态 webhook 详细数据、得分。

### 5.10 CI 测试 `CI_TESTS`（规则，2.5）——单表定版，表结构已复核 ✅

- **数据获取**（SQL，**单表定版 2026-09-17**）：PR 集合与 5.7 完全一致（同批近 30 次已合入 PR）；每个 PR 是否跑 CI 由 `sdi_rd_efc_pipeline_run_pr_relation_codearts` **单表**判定（只要有流水线执行记录即认为有 CI）：
  - 关联键 `git_url + pr_id`（**pr_id 为 varchar，需 `CAST AS INT` 对齐 `number`**；过滤 `git_type='gitcode' AND pr_id IS NOT NULL`）。
  - **表结构已复核（0917）**：project_id / pipeline_id / pipeline_run_id / git_url(KEY) + pipeline_name / git_type / pr_id——满足关联与过滤要求。
  - 实测：gitcode 873 仓 68 万条 PR 触发记录，当前覆盖已合入 PR 的 55.1%，**数据会持续汇聚到此表**（不再 UNION 旧表 `dwi_rd_efc_pr_workflow_run`）。
- **打分规则**：`score = 10 × 有CI测试的PR数 / 合并PR总数`。
- **NA 条件**：无 PR → NA。
- **dwi 记录**：PRs 编号列表（与代码评审一致）、每个 PR 是否跑 CI（数组）、得分。

### 5.11 发布签名 `SIGNED_RELEASES`（建议，5）

- **数据获取**（接口 → raw → sdi，**表已建**）：拉取任务 T3 → `raw_repo_release_info`（repo_id+release_tag，data_json 含 assets 原文）→ 清洗（`sdi层清洗DML.sql` [3]）→ `sdi_rd_efc_release`，sdi 已派生 `has_sha256_asset`（资产名正则 `.sha256/.sha256sum/.md5`）与 `has_signature_asset`（`.asc/.sig/.pgp/.gpg/.minisig/.pem/.crt/.cer/.p7s`）。取**最近 30 个**版本（**2026-10-10 口径调整：含 prerelease 预发布版本，与 GitCode Releases 页面展示对齐，不再排除**）；**忽略仅有源码包（source only）的场景**。draft（草稿）release 暂不排除，维持原样（2026-10-20 决策）。
- **打分规则**（C2 已定 · **2026-10-20 口径调整**）：评估最近 30 个版本（含预发布）——**全部版本均同时含 sha256 校验文件（.sha256/.sha256sum）与数字签名文件（.asc/.sig/.pgp 等）= 10 分；任一版本缺少任一项 = 0 分**。原 C2 版本的"SLSA Provenance 等效判定"（`*.attestation`/SLSA 关键字资产）**移除**——GitCode 生态不产出 SLSA attestation，且现网 544 个 release 中 SLSA 命中为 0、签名文件命中为 0、sha256 命中 70，口径切换对现网分数无增量影响。
- **NA 条件**（C2 已定）：无 release → NA（不进行分数计算）。
- **dwi 记录**：最近 30 次 release 版本号、每个版本资产明细（signed/sha256/签名判断）、满足与不满足列表、得分。

### 5.12 软件包发布 `PACKAGING`（规则，5）

- **数据获取**（文件 + 外部清单）：
  1. 仓库存在 workflow（有 workflow 目录下 yml 文件）→ 满足；
  2. openEuler 固定工程比对：拉取任务**已建好**，数据将清洗到 `sdi_rd_efc_euler_package`（表暂未建，数据到位后建表）。比对口径：仓库 url 前缀 `atomgit.com` **统一归一化为 `gitcode.com`** 后，与 euler_package 仓库清单比对，在工程内 → 满足。
  3. Nightly 流水线：**无法确定使用仓库，该场景暂不支持**（李亮亮）。
- **打分规则**：`score = {10, 检测到自动化打包能力(含openEuler工程内); 0, 未检测到}`。**2026-10-08 口径调整：原"未检测到=NA"改为 0 分**（未检出制品上传插件且未命中 openEuler 包清单，视为未建立自动发包流程）。
- **NA 条件**：无。
- **dwi 记录**：是否存在 workflow、是否在 openEuler 工程（Eluermaker）、Nightly（暂不支持）、得分。

### 5.13 模糊测试 `FUZZING`（建议，5） ---先建表，暂不做脚本开发，规则未完全确定。

- **数据获取**（分期，见 C9）：
  - **P1（本期）**：① OSS-Fuzz 清单比对——拉取 `google/oss-fuzz` 仓 `projects/` 目录，检查某 project 的 `project.yml` 是否含本仓库 url（上游确认 projects 下暂无 gitcode 项目，但需支持扫描）；② ClusterFuzzLite——检测仓库 workflow 是否引用/配置 ClusterFuzzLite。
  - **P2（待细化）**：原生/内置模糊测试函数检测（go test fuzz、libFuzzer、AFL、pytest fuzz 等语言相关规则）；Haskell QuickCheck/Hedgehog/validity/SmallCheck 框架检测。
- **打分规则**（上游阶梯）：集成 OSS-Fuzz = 10；配置 ClusterFuzzLite = 10；原生/内置模糊测试函数 = 5；Haskell 框架命中 = 3；无任何 Fuzzing 活动 = 0。检测到的工具数量不影响评分。
- **NA 条件**：无。
- **dwi 记录**：是否有 OSS-Fuzz、每种方式扫描记录、得分。

### 5.14 SAST `SAST`（建议，5）--- ✅ 2026-09-30 规则改版（已交付：脚本+展示配置+验证 8/8，待全量重跑）

- **数据获取**（Python）：
  - pre-commit 配置文件候选位置：根目录 `.pre-commit-config.yaml` 或 `pre-commit/.pre-commit-config.yaml`，两处同时存在时**合并扫描**（工具取并集）。
  - workflow 文件：`.gitcode/workflows` / `.gitcode/workflow` 下 yml/yaml（与 DANGEROUS_WF 同源）。
  - 检查 pre-commit 配置或 workflow 文件中是否使用 SAST 工具，**不区分语言**，工具清单（8 项）：

    | 工具       | 语言   | pre-commit 检测 id | workflow 检测词 |
    | ---------- | ------ | ------------------ | --------------- |
    | clang-tidy | C/C++  | `clang-tidy`       | `clang-tidy`    |
    | bandit     | Python | `bandit`           | `bandit`        |
    | eslint     | JS/TS  | `eslint`           | `eslint`        |
    | gosec      | Go     | `gosec`            | `gosec`         |
    | clippy     | Rust   | `cargo-clippy`     | `clippy`        |
    | spotbugs   | Java   | `mvn-spotbugs`     | `spotbugs`      |
    | gitleaks   | 通用   | `gitleaks`         | `gitleaks`      |
    | luacheck   | Lua    | `luacheck`         | `luacheck`      |

  - pre-commit 匹配：hook id 精确匹配，YAML 解析 ∪ 逐行正则并集（兼容 `id: xxx` 有空格与 `id:xxx` 无空格两种写法——块级无空格写法 PyYAML 会解析为纯字符串，不能只靠 YAML 解析）。
  - workflow 匹配：单词边界匹配（不区分大小写）。
- **打分规则**：命中任一 SAST 工具 = 10 分（多命中不加分）；有配置文件但 0 命中 = 0 分。
- **NA 条件**：既无 pre-commit 配置文件又无 workflow 文件 → NA（`na_reason: no_config_file`）。
- **dwi 记录**：`has_precommit`、`precommit_paths`（实际检出路径数组）、`wf_file_count`、`tool_count`、`hit_tools`（命中工具码数组）、`tools`（8 工具逐项：tool/lang/precommit/workflow/hit）、`hits`（命中证据：tool/lang/source/path/evidence）。
- 历史：初版（2026-09-12）按"仓库根存在 `.pre-commit-config.yaml` 即 10 分"判定；2026-09-30 改版为工具级检测。上游 CodeQL/SonarCloud 加权版（SAST 权重 3 + CodeQL 权重 7）不适用于 gitcode 落地（codeql 法律风险暂无替代）。

### 5.15 安全策略 `SECURITY_POLICY`（规则，5）

- **数据获取**（Python）：扫描文件路径 `.gitcode/SECURITY.md`、`SECURITY.md`、`docs/SECURITY.md`、`security.md`；三检测：① 漏洞披露关键词（"report"、"vulnerability"、"disclosure" 等）；② 联系链接（正则匹配邮箱 `user@domain`/`mailto:` 或 `https://` URL）；③ 自由文本（非空、非标题行的实质性内容行数）。
- **打分规则**（2026-10-12 口径变更，B 方案生效，C3 作废）：**无 SECURITY.md = 0 分；有 SECURITY.md 时三项独立加分：漏洞披露信息 +1、联系链接 +6、自由文本说明 +3（满分 10）**。（原 C3"仓内 10/社区 5/无 0"口径废弃——"社区存在"判定路径始终无上游数据源，且与明细展示的加分制冲突；三检测由仅落 detail 升级为参与打分。）
- **NA 条件**：无。
- **dwi 记录**：文件路径、三要求满足度（数组或分列）、得分。

### 5.16 已知漏洞 `VULNS`（规则，7.5）--- ✅ 2026-09-22 接入（源表落定，C10 关闭）

- **数据获取**（SQL）：数据源 = **`sdi_rd_efc_cve_details`**（openLiBing 漏洞视图；实测 56318 条 / 2203 仓）。
  - 仓库关联：`affected_repository`（纯仓库名）= `repo_url` 末段（去 `.git`）；135 仓运营清单实测命中 45 仓。
  - **只统计超期且未关闭**：超期判定 = `issue_plan_closed_time` < 当前时间 **且** `issue_state` 非关闭态；**closed / rejected 均视为关闭态**（rejected = 明确不修/不适用，拍板 2026-09-22）。
  - 源表 `is_overdue_statistics` 字段**不采用**（closed 的历史超期也标 1，非"当前超期未关闭"语义）。
- **严重度映射**（拍板 2026-09-22）：`cve_level` = Critical/High/Medium/Low 直接映射致命/高危/中危/低危；**None/空 → 按最低档 Low 计**。
- **打分规则**（C4 已定：按严重度扣分）：初始 10 分，每个致命漏洞扣 10、高危扣 5、中危扣 2、低危扣 1（含 None/空 按 Low 扣 1），`score = max(0, 10 − Σ扣分)`。
- **NA 条件**（2026-10-16 口径更新）：该仓库无漏洞记录覆盖（漏洞平台未跟踪，如 135 仓清单中未命中的 90 仓）→ **10 分**（原 NA 改满分，D5 段计数 0/明细空数组/扣分全 0）；**有覆盖且无超期漏洞 = 10 分**。本指标已无 NA 分支。
- **dwi 记录**：`dwi_rd_efc_security_vuln_scan`（overdue_count 全量计数、vuln_detail 每仓截断 50 条、deduct_detail 分档扣分明细）。
- **dm 激活**：[D5] 投产同步 `UPDATE dm_rd_efc_security_metric_conf SET status='active' WHERE metric_code='VULNS'`，规则项分母 75 → 82.5、全量 87.5 → 95。
- **遗留**：gitcode 专有漏洞平台（longzhifan）、Mind/openEuler 社区独立判断（lihongfeng）、其他社区按公司规范判 SLA（longzhifan）。

### 5.17 项目维护 `MAINTAINED`（规则，2.5）

- **数据获取**（SQL）：
  - 仓库状态：`sdi_repo_info`（`statu='archived'` 归档；`create_time` 判创建不足 90 天）。
  - commit：`sdi_repo_commit_log`（默认分支）近 90 天数量——**采集任务已建、数据暂未到位**（链路文件见 §8-03/04）；issue：`sdi_repo_issue_info` 近 90 天新建数量（已有表 ✅）。
- **打分规则**：`score = min(10, 10 × (commit数₉₀d + issue数₉₀d) / 13)`。
- **NA 条件**：仓库已归档 **或** 创建不足 90 天 → NA（跳过不记录分数；上游计算公式列写 0 分，但操作列与"NA 不参与后续分数汇聚"均按 NA，以 NA 为准）。
- **dwi 记录**：仓库状态是否满足、commit 和 issue 的 ids、得分。

### 5.18 贡献者多样性 `CONTRIBUTORS`（建议，2.5）

- **数据获取**（SQL + 接口，**公司链路表新建**）：
  - **口径变更**：不是全量 contributors，而是**近 30 次已合入 PR 的作者**（与 5.7 同批 PR，作者去重）。
  - **归属口径 v2（2026-10-16 拍板）**：从"平台组织"（T4b orgs 链路，`sdi_rd_efc_repo_contributor.org_login`）切换为**"用户所属公司"**——新链路 T7：`GET /api/v5/users/:username`（company 字段，用户自填）→ `raw_user_company` → 清洗（`sdi层清洗DML.sql` [9]）→ `sdi_rd_efc_user_company`（一人一行）。原因：orgs 是用户加入的平台组织，非受雇公司；company 实测填写率仅 1.6%（2026-10-15 全量 1040 作者实测，见《company字段全量实测报告.md》）。
  - **归属口径 v3（2026-10-20 拍板）**：未填写 company 或采集 404（账号注销/改名，`sdi_rd_efc_user_company` 无该用户行）的作者，统一归入虚拟公司**「未配置公司」**——视为一个公司，与真实公司**平权参与 N 值计分**（v2 的"为空不计入 N"作废）。理由：填写率仅 1.6%，若空值不计入则绝大多数仓库 N=0，指标失去区分度；归入虚拟公司后各仓库先有区分真实公司的动力（补填资料即浮出为真实公司）。明细展示中原样显示「未配置公司」；`D2-18` 的 `author_org` CTE 两分支（未采集到/未填写）均落 `'未配置公司'`，华为归一分支不变。
  - **华为系写法归一**（上游拍板，简单处理）：`LOWER(TRIM(company)) IN ('huawei','hw','华为','华为技术有限公司','华为科技有限公司','上海华为技术有限公司')` → `'华为技术有限公司'`。归一在指标层 D2 处理，sdi 保留原值。
  - 旧组织链路 T4a/T4b 保留不删（对账/回退用），D2-18 不再引用。
- **打分规则**（C6 已定）：`score = min(10, 10 × N / 3)`；**N = 满足"该公司内存在至少 1 名作者其近 30 次 PR 数 ≥ 5"的公司个数**。
- **NA 条件**：近 30 次已合入 PR 为 0 → NA。
- **dwi 记录**：贡献者按公司分组存储、得分。

---

## 6. 汇聚与亮灯规则（上游 Row 20，新增）

1. **仓库得分分两套**：
   - **规则项得分**（类型=规则的 13 项，权重和 90）：用于项目层级分数统计；
   - **全部得分**（18 项，权重和 112.5）：仅展示使用。
2. **得分公式**：`仓库得分 = ∑(单项指标得分 × 对应权重) / ∑权重`；**NA 指标与暂缓指标（本期 5/13，dm 恒 NULL）分子分母同时剔除**——分母 = 已实现且非 NA 指标的权重和（本期上限：规则类 90 / 全部 102.5，v4.4 指标8 接入后）。
3. **仓库亮灯**：得分率（=仓库得分/10）≥80% 绿灯；≥50% 黄灯；<50% 红灯。**C11 暂不考虑**：dm 保留 `rule_light` 字段并按规则项得分计算（与项目层级口径一致），后续如需切换仅改汇聚 SQL。
4. **项目层级得分**：`∑仓库得分 / 仓库数量`，两套同算（规则项 `score_rule` 用于亮灯与统计；`score_all` 规则+建议总得分，仅展示）。**无分仓不进分母**：整仓无分（dm 无该仓记录、或该仓规则项全 NA → `score_rule_weighted` 为 NULL）时 AVG 自动剔除（与仓库级"NA 指标权重不进分母"同构）；`null_repo_count` 单列透明记录无分仓数，不拖低项目安全水位。
5. **项目层级亮灯**：取最低灯（存在红取红；无红有黄取黄）= 仓库 `rule_light` 取 MAX；**亮灯先按规则项口径**（不用总得分算灯）。
6. 实现范围：仓库级两套得分 + 仓库灯 → `dm_rd_efc_security_scan_score` ✅（D4）；项目层级每日快照 → `dm_rd_efc_security_project_score` ✅（D6，2026-09-23，§7.1.1）。

---

## 7. 目标表设计

### 7.1 dm 总表 `dm_rd_efc_security_scan_score`（v3 更新）

```sql
CREATE TABLE dm_rd_efc_security_scan_score (
  repo_id                  INT,
  repo_url                 VARCHAR(512),
  scan_time                DATETIME,      -- 批次扫描时间戳
  score_license            DECIMAL(5,2),  -- 1  开源许可证(规则7.5)
  score_copyright          DECIMAL(5,2),  -- 2  版权合规(规则10)
  score_dangerous_wf       DECIMAL(5,2),  -- 3  危险工作流(规则10)
  score_token_perm         DECIMAL(5,2),  -- 4  令牌权限(规则7.5)
  score_pinned_dep         DECIMAL(5,2),  -- 5  依赖锁定(建议5)
  score_binary_artifacts   DECIMAL(5,2),  -- 6  二进制制品(规则7.5)
  score_code_review        DECIMAL(5,2),  -- 7  代码评审(规则7.5)
  score_branch_protection  DECIMAL(5,2),  -- 8  分支保护(规则7.5)
  score_webhooks           DECIMAL(5,2),  -- 9  Webhook(规则10)
  score_ci_tests           DECIMAL(5,2),  -- 10 CI测试(规则2.5)
  score_signed_releases    DECIMAL(5,2),  -- 11 发布签名(建议5)
  score_packaging          DECIMAL(5,2),  -- 12 软件包发布(规则5)
  score_fuzzing            DECIMAL(5,2),  -- 13 模糊测试(建议5)
  score_sast               DECIMAL(5,2),  -- 14 SAST(建议5)
  score_security_policy    DECIMAL(5,2),  -- 15 安全策略(规则5)
  score_vulns              DECIMAL(5,2),  -- 16 已知漏洞(规则7.5)
  score_maintained         DECIMAL(5,2),  -- 17 项目维护(规则2.5)
  score_contributors       DECIMAL(5,2),  -- 18 贡献者多样性(建议2.5)
  score_rule_weighted      DECIMAL(5,2),  -- 规则项加权总分(权重和90，NA剔除，用于项目层级)
  score_all_weighted       DECIMAL(5,2),  -- 全部指标加权总分(权重和112.5，仅展示)
  rule_light               TINYINT,       -- 仓库亮灯：1绿(>=80%) 2黄(>=50%) 3红(<50%)
  etl_time                 DATETIME
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 16
PROPERTIES ("replication_num" = "3");
```

> NA 指标与暂缓指标（5/8/13）该列存 NULL（指标16 已于 v4.3 接入，不再恒 NULL）；两套加权分与亮灯在 dm 汇聚任务（SQL）中计算，分母剔除 NULL 项权重（同 NA 逻辑）。

### 7.1.1 项目(社区)层级每日分数表 `dm_rd_efc_security_project_score`（2026-09-23 新增）

UNIQUE KEY `project_id + stat_date`（每日一份快照，同日重跑幂等覆盖）。D6 从 `dm_rd_efc_security_scan_score`
取每仓最新批次（与 D4 取数口径一致），经 `sdi_repo_info`（repo_id→project_id）+ `sdi_project_info`
（project_name 冗余）聚合到项目层级：

| 字段                   | 口径                                                                |
| ---------------------- | ------------------------------------------------------------------- |
| score_rule             | AVG(仓库 score_rule_weighted)，无分仓不进分母（0-10，用于项目亮灯） |
| score_all              | AVG(仓库 score_all_weighted)，同上（规则+建议，仅展示）             |
| light                  | MAX(仓库 rule_light)＝取最低灯：1绿 2黄 3红                         |
| repo_count             | 项目下 is_operate=1 应扫仓数（含无分仓）                            |
| null_repo_count        | 无分仓数（dm 无记录或整仓规则项全 NA）                              |
| green/yellow/red_count | 仓库灯分布计数                                                      |

> DDL 见 dwi-dm层建表DDL.sql [10]；DML 见 dwi-dm指标计算DML.sql [D6]；DS 编排在 D4 之后（依赖仓库级 dm 数据）。

### 7.2 dwi 明细结果表（7 张）

> 通用约定：`score` 0~10；`is_na=1` 则 score=NULL；`scan_time`=批次时间；`detail_json` 结构化原因明细，看板直接展开。

**① dwi_rd_efc_security_maintained_scan**（指标17 项目维护 `MAINTAINED` · SQL）——同 v2（repo_status/commit_ids_90d/issue_ids_90d/score/is_na/scan_time）。

**② dwi_rd_efc_security_pr_scan**（指标7 代码评审 `CODE_REVIEW` + 指标10 CI测试 `CI_TESTS` 合表 · SQL）——同 v2（pr_total_count/pr_numbers/pr_reviewed_count/pr_unreviewed_detail/score_review/pr_ci_detail/score_ci/is_na/scan_time）。

**③ dwi_rd_efc_security_branch_protect_scan**（指标8 分支保护 `BRANCH_PROTECTION` · SQL D7 产出，**✅ 2026-09-28 规则更新**——数据源改为 rebot.yaml + /lgtm 评论，原接口链路废弃）：

```sql
CREATE TABLE dwi_rd_efc_security_branch_protect_scan (
  repo_id          INT           COMMENT '仓库ID',
  repo_url         VARCHAR(512)  COMMENT '仓库地址',
  base_pass        TINYINT       COMMENT '默认满足T1/T2/T3(平台默认+机器人lgtm=1)：恒1，得基础8分',
  has_rebot_yaml   TINYINT       COMMENT '是否存在 .infra_self_service/rebot.yaml：1有 0无',
  yaml_lgtm_config VARCHAR(128)  COMMENT 'yaml中lgtm配置原文(连名带值)，如 lgtm_need_num=2；无文件或无该项配置为NULL',
  lgtm_need_num    INT           COMMENT '解析后的lgtm_need_num数值(便于SQL判定)；未配置/无文件为NULL，按默认1处理',
  pr_lgtm_pass     TINYINT       COMMENT '近30PR是否均满足"两条不同人/lgtm"：1是 0否 NULL=未触发检查(need_num!=2或无yaml)',
  pr_numbers       TEXT          COMMENT '参与检查的PR编号列表(近30次已合入，剔机器人创建)',
  pr_lgtm_detail   JSON          COMMENT '逐PR明细[{pr_number, lgtm_count, distinct_author, pass, lgtms:[{login, time}]}]，lgtms取最后两条/lgtm的评论人和时间',
  score            DECIMAL(5,2)  COMMENT '指标8得分：默认8；yaml存在且lgtm_need_num=2且pr_lgtm_pass=1时为10(二元，无中间分)',
  is_na            TINYINT       COMMENT '是否NA(本指标恒0)',
  scan_time        DATETIME      COMMENT '本次扫描时间戳'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**④ dwi_rd_efc_security_file_scan**（指标2 版权合规 `COPYRIGHT` / 指标3 危险工作流 `DANGEROUS_WF` / 指标4 令牌权限 `TOKEN_PERM` / 指标6 二进制制品 `BINARY_ARTIFACTS` / 指标8 分支保护 `BRANCH_PROTECTION`（仅 yaml 明细，score 由 D7 计算）/ 指标12 软件包发布 `PACKAGING` / 指标14 SAST `SAST` / 指标15 安全策略 `SECURITY_POLICY` · Python，v4.4 扩为 8 个 metric_code；暂缓的 5/13 后期追加）：

```sql
CREATE TABLE dwi_rd_efc_security_file_scan (
  repo_id     INT           COMMENT '仓库ID',
  repo_url    VARCHAR(512)  COMMENT '仓库地址',
  metric_code VARCHAR(32)   COMMENT '指标编码：COPYRIGHT/DANGEROUS_WF/TOKEN_PERM/BINARY_ARTIFACTS/BRANCH_PROTECTION/PACKAGING/SAST/SECURITY_POLICY（暂缓项 PINNED_DEP/FUZZING 后期追加）',
  detail_json JSON          COMMENT '按 metric_code 的结构化明细(见下表)',
  score       DECIMAL(5,2)  COMMENT '该指标得分',
  is_na       TINYINT       COMMENT '是否NA',
  scan_time   DATETIME      COMMENT '本次扫描时间戳'
)
UNIQUE KEY (repo_id, metric_code, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

| metric_code          | detail_json 结构                                                                                                                                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `COPYRIGHT`          | `{target_file_count, matched_count, by_ext:[{ext, file_count, matched_count, matched_files:[path], sample}]}`                                                                                                        |
| `DANGEROUS_WF`       | `{wf_file_count, findings:[{path, unsafe_checkout:bool, untrusted_context:[变量名], reason}]}`                                                                                                                       |
| `TOKEN_PERM`         | `{wf_file_count, files:[{path, top_perm, jobs:{job:{perm, perm_source, has_write, write_scopes, plugins, violations}}}], stat:{checked_count, checked_plugins, violation_count, violations}}`（2026-09-28 改版结构） |
| `PINNED_DEP`（暂缓） | `{deps:[{type:action/image/script, file, ref, pinned:bool}], pinned_count, total_count}`                                                                                                                             |
| `BINARY_ARTIFACTS`   | `{binary_count, bad_file_paths:[path]}`                                                                                                                                                                              |
| `BRANCH_PROTECTION`  | `{has_rebot_yaml:bool, yaml_lgtm_config, lgtm_need_num}`（score=NULL/is_na=0，最终得分由 D7 结合评论数据计算）                                                                                                       |
| `PACKAGING`          | `{has_workflow:bool, workflow_paths:[path], in_openeuler_project:bool, openeuler_project, nightly:unsupported}`                                                                                                      |
| `FUZZING`（暂缓）    | `{in_ossfuzz:bool, ossfuzz_project, has_clusterfuzzlite:bool, native_fuzz:bool(P2), signals:[...]}`                                                                                                                  |
| `SAST`               | `{has_precommit:bool, precommit_path, hooks:[...]}`                                                                                                                                                                  |
| `SECURITY_POLICY`    | `{file_path, disclosure:bool, link:bool, free_text:bool}`                                                                                                                                                            |

**⑤ dwi_rd_efc_security_license_scan**（指标1 开源许可证 `LICENSE` · Python scancode，v3 更新阶梯计分）：

```sql
CREATE TABLE dwi_rd_efc_security_license_scan (
  repo_id    INT           COMMENT '仓库ID',
  repo_url   VARCHAR(512)  COMMENT '仓库地址',
  spdx       VARCHAR(64)   COMMENT 'SPDX许可证标识，如 Apache-2.0/MIT',
  has_license      TINYINT COMMENT '是否检出许可证文件：1有(>=5分) 0无(0分)',
  template_match   TINYINT COMMENT '是否满足模板(scancode score=100)：1是(>=8分)',
  copyright_ok     TINYINT COMMENT 'copyright年份/责任人替换正确：1是(递进式总9分)',
  osi_fsf_ok       TINYINT COMMENT '满足OSI/FSF(spdx清单忽略大小写)：1是(递进式总10分；需模板+版权均达标才累加)',
  detail     JSON          COMMENT '原因明细{template_id, matched_text_diagnostics, copyright_matched}',
  raw_json   TEXT          COMMENT 'scancode原始JSON(排查用)',
  score      DECIMAL(5,2)  COMMENT '递进累加分：有5/模板+3/版权+1/OSI-FSF+1/无0',
  is_na      TINYINT       COMMENT '是否NA(本指标恒0)',
  scan_time  DATETIME      COMMENT '本次扫描时间戳'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**⑥ dwi_rd_efc_security_meta_api_scan**（指标9 Webhook安全 `WEBHOOKS` / 指标11 发布签名 `SIGNED_RELEASES` / 指标18 贡献者多样性 `CONTRIBUTORS` · 接口，v3 更新）：

```sql
CREATE TABLE dwi_rd_efc_security_meta_api_scan (
  repo_id     INT           COMMENT '仓库ID',
  repo_url    VARCHAR(512)  COMMENT '仓库地址',
  metric_code VARCHAR(32)   COMMENT '指标编码：WEBHOOKS/SIGNED_RELEASES/CONTRIBUTORS',
  detail_json JSON          COMMENT '按 metric_code 的结构化明细(见下表)',
  score       DECIMAL(5,2)  COMMENT '该指标得分',
  is_na       TINYINT       COMMENT '是否NA',
  scan_time   DATETIME      COMMENT '本次扫描时间戳'
)
UNIQUE KEY (repo_id, metric_code, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

| metric_code       | detail_json 结构                                                                                                                              |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `WEBHOOKS`        | `{active_count, webhooks:[{id, url, active:bool, password_is_null:bool}]}`                                                                    |
| `SIGNED_RELEASES` | `{release_count, releases:[{tag, published_at, assets:[name], has_signature:bool, has_slsa:bool, source_only:bool}], all_signed:bool, score}` |
| `CONTRIBUTORS`    | `{authors:[{login, pr_count, orgs:[org]}], org_groups:[{org, author_count, has_active_author:bool}], n_orgs, n}`                              |

**⑦ dwi_rd_efc_security_vuln_scan**（指标16 已知漏洞 `VULNS` · SQL，**✅ 2026-09-22 接入**——源表 `sdi_rd_efc_cve_details` 落定，C10 关闭，DML [D5] 段产出）：

```sql
CREATE TABLE dwi_rd_efc_security_vuln_scan (
  repo_id        INT          COMMENT '仓库ID',
  repo_url       VARCHAR(512) COMMENT '仓库地址',
  overdue_count  INT          COMMENT '超期未关闭漏洞数(计划完成时间<当前且未关闭)',
  vuln_detail    JSON         COMMENT '超期漏洞明细[{issue_id, cve_num, severity, plan_closed_time, status}](每仓截断50条,按扣分降序)',
  deduct_detail  JSON         COMMENT '扣分明细{critical:n, high:n, medium:n, low:n, deduct_points}',
  score          DECIMAL(5,2) COMMENT '指标16得分=max(0,10-致命*10-高危*5-中危*2-低危*1)',
  is_na          TINYINT      COMMENT '是否NA(数据源未接入/无覆盖)',
  scan_time      DATETIME     COMMENT '本次扫描时间戳'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

---

## 8. DolphinScheduler 任务编排（v4 · "1+6" 采集任务已建，sdi 清洗待执行）

> **现状口径（2026-09-17）**："1+6" 条数据源链路（1 条 commit 链路 + 6 条接口链路）的采集任务/脚本均已建好——**数据源侧处理已完成**；**sdi 层清洗 DDL+DML 已写好但尚未在 Doris 执行**（表未建、数据未入）。

```text
项目：security_check_scoring

【数据源层 · "1+6" 采集任务已建好，sdi 清洗待执行】

01 接口拉取层（每日，遍历 is_operated=1 仓库）✅ 6 接口任务已建
   ├ task_repo_branch_protection(T1a) → raw_repo_branch_protection (❌2026-09-28废弃：指标8改走文件+评论链路)
   ├ task_repo_pr_setting(T1b)        → raw_repo_pr_setting        (❌2026-09-28废弃：同上)
   ├ task_repo_webhook(T5)            → raw_repo_webhook           (指标9，✅password_is_null已补，仅公开仓库)
   ├ task_repo_release(T3)            → raw_repo_release_info      (指标11)
   ├ task_repo_contributors(T4a)      → raw_repo_contribute_info   (指标18，全量贡献者)
   ├ task_contrib_organize(T4b)       → raw_contrib_organize       (指标18，贡献者×组织)
   └ task_pr_comment                  → raw_pr_comment_gitcode     (指标7+8，已有复用；8新增复用/lgtm评论)
02 外部清单拉取
   ├ task_openeuler_project_repos ✅任务已建 → sdi_rd_efc_euler_package (指标12，表暂未建，数据到位后建表；atomgit.com归一化为gitcode.com)
   └ task_ossfuzz_projects        ⏸️ 暂缓 (指标13，随 Fuzzing 挂起)
03 commit 采集（"1" 链路，脚本/SQL 已写：代码仓commit扫描脚本.py + create/clean_to_sdi_repo_commit_log.sql）
   └ git log 扫描 → raw_repo_commit_log → sdi_repo_commit_log (指标17，⚠️Doris 两表均未建、数据未到位)
04 清洗 sdi（依赖01/02/03，⚠️ 6表 DDL+清洗 DML 已写未执行：sdi层6表建表DDL.sql / sdi层清洗DML.sql）
   ├ [1] sdi_rd_efc_branch_protection ❌废弃(2026-09-28，指标8数据源变更，T1a链路不再使用)
   ├ [2] sdi_rd_efc_pr_setting        ❌废弃(2026-09-28，同上，T1b链路不再使用)
   ├ [3] sdi_rd_efc_release           (sha256/签名资产已派生)
   ├ [4] sdi_rd_efc_repo_contributor  (人×组织)
   ├ [5] sdi_rd_efc_repo_webhook      (✅password_is_null已采集)
   ├ [6] sdi_rd_efc_pr_review_reviewer (is_bot/is_effective_review已清洗，v4.8仅/lgtm；指标8复用review_type='/lgtm')
   └ commit链路: raw_repo_commit_log → sdi_repo_commit_log (⚠️表未建，见03)
05 文件扫描（Python，clone 仓库）——8 个 metric_code + license（暂缓项 PINNED_DEP/FUZZING 不在本期）
   ├ copyright / dangerous_wf / token_perm / binary_artifacts
   ├ branch_protection(读 .infra_self_service/rebot.yaml 的 lgtm_need_num，仅存明细) ✅2026-09-28新增
   ├ packaging(含openEuler比对，依赖02) / sast / security_policy → dwi_rd_efc_security_file_scan
   └ license(scancode) → dwi_rd_efc_security_license_scan
06 指标计算 & 汇聚（SQL，依赖01-05，见 §11 D1~D5+D7）
   ├ 指标7+10    → dwi_rd_efc_security_pr_scan        (指标10判定=codearts关联表单表，pr_id需CAST AS INT)
   ├ 指标9/11/18 → dwi_rd_efc_security_meta_api_scan
   ├ 指标17      → dwi_rd_efc_security_maintained_scan (⚠️待commit数据到位)
   ├ 指标8       → dwi_rd_efc_security_branch_protect_scan ✅2026-09-28转正([D7]：file_scan的yaml明细+pr_review_reviewer的/lgtm评论)
   ├ 指标16      → dwi_rd_efc_security_vuln_scan          ✅ 2026-09-22 接入([D5]，源表 sdi_rd_efc_cve_details)
   └ 全指标+两套加权分+亮灯 → dm_rd_efc_security_scan_score (暂缓项5/13恒NULL、汇聚分母剔除；8/16已激活)
```

---

## 9. 上游表内矛盾仲裁记录（C1~C11 · 已全部解答 2026-09-17）

> 上游 Excel 同一指标不同列（计算公式/计算规则/分数计算规则）存在冲突，本设计曾给出推荐。**2026-09-17 用户已逐条解答（"解答"列），结论已全部落入 §5 正文**；本表保留作为仲裁记录。

| #   | 冲突/待确认                         | 上游现状                                                                                                    | 本设计推荐                                                                                                                                          | 影响            | 解答                                                                                                                            |
| --- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| C1  | 版权打分规则 + 正则口径             | 分数规则"待确定"；新表写法 `Copyright (c)`（有空格+年份区间），你此前口径 `Copyright(c)`（无空格+四位年份） | 打分：`10 × 匹配文件数/目标文件总数`；正则兼容两种写法与年份区间：`Copyright\s*\(c\)\s*\d{4}(-\d{4})?\s+Huawei Technologies Co\.`                   | Python 扫描脚本 | 按无空格来，确定                                                                                                                |
| C2  | 发布签名三版矛盾                    | 公式列：最近5个、签名8/SLSA10、均值取整、无release=0；规则列：无release不计算(NA)；分数列：全满足=10其他=0  | 最近5个正式release、签名资产8/SLSA10、`⌊均值⌋`、无release=NA                                                                                        | 接口+SQL        | 规则列：近30次release，无release不计算(NA)；分数列：全满足=10其他=0                                                             |
| C3  | 安全策略两版                        | 分数列：仓内10/社区5/无0                                                                                    | L+K+T（6/3/1）；"社区存在=5分"作为补充分支待上游明确社区文件定义                                                                                    | Python          | 分数列：仓内10/社区5/无0 → **2026-10-12 用户改拍 B 方案：无文件0；有文件独立加分 漏洞披露+1/链接+6/自由文本+3，C3 旧口径作废**  |
| C4  | 漏洞扣分两版                        | 分数列：分数列：致命10/高危5/中危2/低危1                                                                    | 按严重度扣分（分数列版更细）                                                                                                                        | SQL             | 分数列：分数列：致命10/高危5/中危2/低危1                                                                                        |
| C5  | 令牌权限两版                        | 分数列：5条规则                                                                                             | 采用分数列 5 条（1-5）；加权版为 P2 精化                                                                                                            | Python          | 分数列：5条规则                                                                                                                 |
| C6  | 贡献者 N 定义                       | "满足单个作者PR>=5的公司或组织个数"表述模糊                                                                 | N = 组织内存在≥1名作者（近30次PR数≥5）的组织数                                                                                                      | SQL             | 你理解的对，最终就是要这个数据                                                                                                  |
| C7  | Webhook 分母口径 + password 缺口    | 公式：密钥数/总数；规则：只看 active=true 的钩子；raw 表已建但**未采集 password**（防明文）                 | 分母=活跃(active=true)钩子数；无活跃钩子=10；**采集层需补 `password_is_null` 布尔位**（接口返回时派生，不落明文），否则指标 9 分子无数据源、只能 NA | 采集+SQL        | 已经补了password_is_null                                                                                                        |
| C8  | 分支保护 T2"最近推送审批"/T5 两子项 | gitcode 默认支持不扫描，给分方式未定                                                                        | gitcode 默认支持项按"满足"计分（T2 最近推送审批=满足；T5 取消过时审查=满足）；T5 管理员强制执行待 lihongfeng，暂按不满足                            | SQL             | ✅ 2026-09-28 规则整体更新（李建鹏）：T1/T2/T3/T5 全部默认满足，指标坍缩为二元 8/10 分，T1a/T1b 接口链路废弃，C8 原仲裁随之作废 |
| C9  | Fuzzing 原生函数检测                | 规则未识别完毕，"需细化@caoxiaolin"                                                                         | 分期：P1=OSS-Fuzz清单+ClusterFuzzLite（可给10分判定）；P2=原生fuzz函数/ Haskell框架（5/3分档）待细化                                                | Python+清单     | 脚本开发挂起                                                                                                                    |
| C10 | 漏洞视图表具体位置                  | "表位置已在绿区发送"，但库.表名未进设计                                                                     | 2026-09-22 落定 `sdi_rd_efc_cve_details`（字段全齐：cve_level/issue_plan_closed_time/issue_state/affected_repository），D5 段已交付                 | SQL             | ✅ 已接入（v4.3）                                                                                                               |
| C11 | 仓库亮灯基于哪套得分                | 未说明                                                                                                      | 规则项得分（与项目层级口径一致）；若看板想展示全部得分的灯可并列两列                                                                                | dm SQL          | 暂不考虑                                                                                                                        |

---

## 10. 决策记录

| 日期       | 决策                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-09-12 | 平台仅 gitcode；仓库范围 is_operated=1；NA=score NULL+is_na 1；历史批次全保留；文档放 docs/0912 不落仓                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-09-12 | Q2：issue=90天内新建数；指标8(旧3)记分五层3/3/2/1/1；二进制/版权后缀清单确认                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-09-14 | CI 关联表定位 `dwi_rd_efc_pr_workflow_run`（repo_url+number）实测有效                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-09-16 | v3：合并上游新表——18 指标全部有规则；Token-Perm/Pinned-Dep/Fuzzing/Vulns 转正式；Webhook 无钩=10 分；Contributors 改近30次PR作者；新增汇聚亮灯规则（§6）；编号切换为上游新序号；C1~C11 待用户仲裁                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-09-17 | 落地现状同步：指标7/8/9/11/18 的 raw+sdi 6 表与清洗 DML 已建（raw层6表建表DDL.sql / sdi层6表建表DDL.sql / sdi层清洗DML.sql）；指标10 CI 判定实测改为两表 UNION：sdi_rd_efc_pipeline_run_pr_relation_codearts(55.1%) + dwi_rd_efc_pr_workflow_run(额外 3.5%) = 并集 58.5%；Webhook password 未采集为阻断缺口（C7）；分支保护 T1a/T1b 待 token 提权                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-09-17 | **v4 终版**：C1~C11 全部仲裁完毕、结论落入 §5；定版本期开发 14 项（权重 87.5）、暂缓 4 项（5/8/13/16 脚本挂起，dm 恒 NULL、分母剔除）；**CI 判定撤销 UNION 结论、定版单表** sdi_rd_efc_pipeline_run_pr_relation_codearts（数据持续汇聚到此表）；Webhook password_is_null 已补（C7 解决）；"1+6" 采集任务已建、sdi 清洗待执行；commit 链路（脚本/表）已写未落地；新增 §11 开发清单                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-09-22 | **v4.3**：指标 16 VULNS 接入（C10 关闭）——源表 `sdi_rd_efc_cve_details` 落定；四点拍板（rejected=关闭态 / None·空→Low 扣 1 / is_overdue_statistics 不采用 / 未覆盖→NA）；新增 DML [D5] 段 + D4 汇聚补 vuln_scan 分支 + 权重激活 UPDATE（规则分母 75→82.5、全量 87.5→95）；真实数据干跑验证：135 仓 = 90 NA + 31 满分 + 2 八分 + 12 零分                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-09-28 | **v4.4**：指标 8 BRANCH_PROTECTION 规则更新转正（李建鹏）——平台默认管控，T1/T2/T3/T5 默认满足；二元计分 8 分保底 / 10 分满分（yaml 存在 + lgtm_need_num=2 + 近 30 PR 均有两条**不同人** /lgtm（剔机器人、剔作者）再 +2）；**仅 lgtm_need_num=2 触发检查**（其他值一律 8 分），触发但无 PR 也 8 分，无 NA。数据源变更为 rebot.yaml（security_file_scan.py 新增 scan_branch_protection，写 file_scan 表 metric_code='BRANCH_PROTECTION' 仅明细）+ /lgtm 评论（复用指标 7 链路 sdi_rd_efc_pr_review_reviewer）；T1a/T1b 接口链路及 sdi [1][2] 两表废弃；新增 D7 任务 + dwi_rd_efc_security_branch_protect_scan 重构（base_pass/has_rebot_yaml/yaml_lgtm_config/lgtm_need_num/pr_lgtm_pass/pr_numbers/pr_lgtm_detail）；权重激活后规则分母 82.5→90、全量 95→102.5 |
| 2026-10-06 | **指标 2 COPYRIGHT v2 模板化改版**（handoff 定稿）——单正则改为三分支：无 LICENSE→整仓 NA / 木兰（12 正则）→官方 4 模板严格匹配 / 印刷附录→字面严格匹配 / 其余→4+1 匹配集；版权行底线三正则（双语序兼容）；test/tests 精确段剔除；木兰短头严格派不合格；.py docstring 兜底；软件名只验占位不验内容（不建 repo 级配置表）；新增配置表 dim_copyright_template_config（10 条种子，SQL 待手动执行）；detail_json +7 字段；混合协议仓（≥2 处 END OF TERMS 标记）豁免 printed 走 4+1；113 仓本地回归全过（35 木兰全识别、7 无 LICENSE 全 NA、分母 12701 对账 OK）。修复 3 个实现 bug：detect_mulan 小写化、`(\(c\))?` 分组、印刷行 `^\s*` 缩进                                                                                                                       |
| 2026-10-07 | **COPYRIGHT 逐文件明细试验**（用户拍板"试一下"）——新增 dwi_rd_efc_security_copyright_file_detail 表（UNIQUE KEY repo_id+scan_time+file_path）全量落不合格文件（file_path/ext/reason/is_banner），突破 detail_json 每类 200 条截断（repo_401712 单仓 1.2 万+ 不合格文件）；脚本试验版 security_file_scan-明细试验.py：scan_copyright 增第 4 返回值全量清单、2000 行分批插入、明细失败仅告警不阻断主表；实测 beta 环境当日批次数据量约 4-5 万行/130 仓，Doris 压力可忽略；upstream_banner 不单列 reason 走 is_banner 标记                                                                                                                                                                                                                                       |
| 2026-10-08 | **COPYRIGHT 扣分制 + 明细落库 + 独立分页接口**——①打分改扣分制（用户拍板）：`max(0, 10−0.2×不合格数)`，50 个扣完，与 BINARY_ARTIFACTS/TOKEN_PERM 同族，取代比率制；②明细表生产落库 76,450 行/111 仓（首跑暴露 4 元组解包 bug 致全仓 ValueError，修复后复跑闭环）；③新接口 `POST /security/copyright-file-list`（用户与前端拍板不走 conf_json 模板）：展示层三分类（无版权声明行= no_header+no_copyright_line 归并/版权行不规范/版权头与协议模板不匹配），中文文案+reasonCode 双字段，banner 默认过滤，每条记录附 fileUrl 文件跳转地址（`{repo_url 去 .git}/blob/{默认分支}/{filePath}`）；服务级验证通过（401712/401224 与 Doris 精确对账、翻页/筛选/空边界/fileUrl 全过）                                                                                     |

---

## 11. 本期开发清单（v4.4 · 16 项指标）

> 建议开发顺序：**S1 → D1（数据已齐，可最先出结果）→ D2 → P1/P2 → S3（euler 数据到位后）→ D3（待 commit 数据）→ D5/D7（数据已齐可随时跑）→ D4（汇聚联调，最后）**。

### 11.1 前置：sdi 清洗执行（S1~S3 · DDL/DML 已写好，待在 Doris 执行）

| #   | 内容                                    | 输入 → 输出                                         | 支撑指标  | 备注                                                                                                                               |
| --- | --------------------------------------- | --------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| S1  | 执行 6 接口链路 sdi 建表 DDL + 清洗 DML | raw 6 表 → sdi_rd_efc_* 6 表                        | 7/9/11/18 | 文件：`sdi层6表建表DDL.sql` / `sdi层清洗DML.sql`；[1][2] 分支保护两表已废弃（2026-09-28，勿执行）                                  |
| S2  | commit 链路建表 + 采集执行 + 清洗       | git log → raw_repo_commit_log → sdi_repo_commit_log | 17        | 文件：`代码仓commit扫描脚本.py` / `create_raw_repo_commit_log.sql` / `clean_to_sdi_repo_commit_log.sql`；⚠️ 外部依赖：采集数据到位 |
| S3  | euler 清洗建表                          | （拉取任务已建）→ sdi_rd_efc_euler_package          | 12        | 数据到位后建表（P1 的 PACKAGING 比对用）                                                                                           |

### 11.2 SQL 指标任务（D1~D5 · DolphinScheduler SQL 任务）

| #   | 目标表                                           | 指标（metric_code）                               | 依赖                                             | 现状                                                                                                   |
| --- | ------------------------------------------------ | ------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| D1  | dwi_rd_efc_security_pr_scan                      | 7 CODE_REVIEW + 10 CI_TESTS                       | S1[6]（其余表已齐）                              | ✅ **数据基本已齐、可最先开发**（PR 表+codearts 关联表已有）                                           |
| D2  | dwi_rd_efc_security_meta_api_scan                | 9 WEBHOOKS + 11 SIGNED_RELEASES + 18 CONTRIBUTORS | S1[3][4][5]                                      | 打分规则均已定版（C2/C6/C7）                                                                           |
| D3  | dwi_rd_efc_security_maintained_scan              | 17 MAINTAINED                                     | S2                                               | ⚠️ 待 commit 数据到位（issue 侧 sdi_repo_issue_info 已有）                                             |
| D5  | dwi_rd_efc_security_vuln_scan                    | 16 VULNS                                          | 源表 sdi_rd_efc_cve_details（已齐）              | ✅ **2026-09-22 已交付**（[D5] 段 + 激活 UPDATE + 干跑验证：90 NA/31 满分/2 八分/12 零分）             |
| D7  | dwi_rd_efc_security_branch_protect_scan          | 8 BRANCH_PROTECTION                               | P1 的 yaml 明细 + S1[6] 评审表 + PR 表（均已齐） | ✅ **2026-09-28 规则更新交付**（[D7] 段 + 激活 UPDATE：规则分母 82.5→90、全量 95→102.5；二元 8/10 分） |
| D4  | dm_rd_efc_security_scan_score（汇聚）            | 全部 16 项 + 两套加权分 + 亮灯                    | D1+D2+D3+D5+D7+P1+P2                             | 暂缓项 5/13 恒 NULL、分母剔除（§6）；8/16 已纳入汇聚                                                   |
| D6  | dm_rd_efc_security_project_score（项目层级汇聚） | 项目(社区)每日两套得分 + 最低灯 + 灯分布          | D4（仓库级 dm 数据）                             | ✅ **2026-09-23 已交付**（[10] DDL + [D6] DML + 生产干跑验证：JOIN 链路/聚合/类型全通）                |

### 11.3 Python 扫描脚本（P1~P2 · 文件扫描通道）

| #   | 脚本                                 | 指标（metric_code）                                                                                                                                                  | 输出表                           |
| --- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| P1  | security_file_scan.py                | 2 COPYRIGHT + 3 DANGEROUS_WF + 4 TOKEN_PERM + 6 BINARY_ARTIFACTS + 8 BRANCH_PROTECTION（仅 yaml 明细，score 由 D7 算） + 12 PACKAGING + 14 SAST + 15 SECURITY_POLICY | dwi_rd_efc_security_file_scan    |
| P2  | security_license_scan.py（scancode） | 1 LICENSE                                                                                                                                                            | dwi_rd_efc_security_license_scan |

> P1 的 PACKAGING 依赖 S3（euler 清单）；TOKEN_PERM 权限映射已落地（Doris 配置表 `sdi_sec_token_perm_plugin`，2026-09-29，"待李洪峰"遗留关闭）；COPYRIGHT v2 模板化改版依赖 dim_copyright_template_config 建表（2026-10-06）。
> P1 进度（2026-10-06）：指标 14 SAST `scan_sast` 已改版交付（8 工具级检测，单测 8/8 PASS，明细展示配置双写：classpath SAST.json + detail-conf-patch-sast-rule-v2.sql，dm 层无需改）；指标 3 DANGEROUS_WF 盲区修复已交付（步骤遍历覆盖 stages/post 嵌套 job 结构，实测 13 仓 10→0）。**两项均待 DS 全量重跑覆盖 Doris 存量数据**（SAST 须在重跑后执行 conf 补丁 SQL）。

### 11.4 暂缓项与恢复条件

| 指标 | metric_code | 恢复条件                                                                 |
| ---- | ----------- | ------------------------------------------------------------------------ |
| 5    | PINNED_DEP  | 脚本开发解挂：openUBMC 社区支持明确（徐海军）+ 对标 Scorecard 补齐识别项 |
| 13   | FUZZING     | 原生 fuzz 函数规则细化（C9）；OSS-Fuzz 清单链路（02 层）随之一并恢复     |

> 指标 16 VULNS 已于 2026-09-22 接入（v4.3）、指标 8 BRANCH_PROTECTION 已于 2026-09-28 规则更新转正（v4.4），均不再属于暂缓项。

---

---

## 版权声明指标（COPYRIGHT）逐仓明细导出（2026-10-20）

> 数据口径：不合格文件数取 `dwi_rd_efc_security_copyright_file_detail` 逐文件明细表**每仓最新批次**（全局最新 scan_time=2026-10-19 14:27:47）；目标文件总数（分母）取 `dwi_rd_efc_security_file_scan`（metric_code=COPYRIGHT）**每仓最近一次成功批次（is_na=0）** detail_json 的 `target_file_count`（10 类目标后缀、剔除 test/tests 路径段后的文件数）。
> 原因映射：①缺少版权头=`no_header`（64 行内提取不到头部）；②缺少负责人和年份=`no_copyright_line`（有头部但无版权行）；③版权声明存在差异=`owner_mismatch`（版权行不规范，owner/年份不符）+`template_mismatch`（头部与协议模板正文不匹配）。同一文件只落一个主原因，四类互斥、合计=全部不合格文件。

### 总览

| 口径                                                   | 涉及项目数 | 不合格文件总数 | 目标文件总数（全集分母） |
| ------------------------------------------------------ | ---------- | -------------- | ------------------------ |
| 1 缺少版权头（no_header）                              | 93         | 6712           | 104537                   |
| 2 缺少负责人和年份（no_copyright_line）                | 83         | 16065          | 104537                   |
| 3 版权声明存在差异（owner_mismatch+template_mismatch） | 119        | 40547          | 104537                   |

全集分母：143 个仓最近一次成功批次目标文件合计 104537 个；另有 6 个仓最新批次整仓 NA（见附录），不产生不合格明细。

### 1. 缺少版权头（no_header）

64 行头部窗口内提取不到任何头部（含 .py docstring 兜底后仍无）。

| #        | 项目                                                                                                                  | 不合格文件数 | 目标文件总数 |
| -------- | --------------------------------------------------------------------------------------------------------------------- | ------------ | ------------ |
| 1        | [AtlasAccount/torchair](https://gitcode.com/Ascend/torchair.git)                                                      | 1174         | 1222         |
| 2        | [AtlasAccount/pytorch](https://gitcode.com/Ascend/pytorch.git)                                                        | 941          | 1163         |
| 3        | [wangshiling/msdebug](https://gitcode.com/Ascend/msdebug.git)                                                         | 861          | 12701        |
| 4        | [郭鹏/MindSpeed](https://gitcode.com/Ascend/MindSpeed.git)                                                            | 499          | 1200         |
| 5        | [朱彦儒/MindSpeed-MM](https://gitcode.com/Ascend/MindSpeed-MM.git)                                                    | 403          | 881          |
| 6        | [宋世轩/oGRAC](https://gitcode.com/opengauss/oGRAC.git)                                                               | 357          | 1131         |
| 7        | [胡桥/AscendNPU-IR](https://gitcode.com/Ascend/AscendNPU-IR.git)                                                      | 206          | 1062         |
| 8        | [雷珍珍/MindSpeed-LLM](https://gitcode.com/Ascend/MindSpeed-LLM.git)                                                  | 197          | 601          |
| 9        | [周蓓蓉/slime-ascend](https://gitcode.com/Ascend/slime-ascend.git)                                                    | 194          | 315          |
| 10       | [songchangxia/cann-recipes-train](https://gitcode.com/cann/cann-recipes-train.git)                                    | 171          | 491          |
| 11       | [华郁秀/DrivingSDK](https://gitcode.com/Ascend/DrivingSDK.git)                                                        | 128          | 542          |
| 12       | [baijiang/msboost](https://gitcode.com/Ascend/msboost.git)                                                            | 108          | 169          |
| 13       | [满涌/bishengjdk-8](https://gitcode.com/openeuler/bishengjdk-8.git)                                                   | 96           | 20395        |
| 14       | [叶羽铭/AgentSDK](https://gitcode.com/Ascend/AgentSDK.git)                                                            | 84           | 475          |
| 15       | [lijinbo/openGauss-server](https://gitcode.com/opengauss/openGauss-server.git)                                        | 76           | 2550         |
| 16       | [songchangxia/ops-transformer](https://gitcode.com/cann/ops-transformer.git)                                          | 66           | 3334         |
| 17       | [AtlasAccount/op-plugin](https://gitcode.com/Ascend/op-plugin.git)                                                    | 64           | 1049         |
| 18       | [lijinbo/Plugin](https://gitcode.com/opengauss/Plugin.git)                                                            | 60           | 1384         |
| 19       | [songchangxia/amct](https://gitcode.com/cann/amct.git)                                                                | 60           | 658          |
| 20       | [黄鑫/catlass](https://gitcode.com/cann/catlass.git)                                                                  | 59           | 477          |
| 21       | [songchangxia/amct-graph](https://gitcode.com/cann/amct-graph.git)                                                    | 46           | 556          |
| 22       | [duping/MindIE-Motor](https://gitcode.com/Ascend/MindIE-Motor.git)                                                    | 45           | 482          |
| 23       | [李睿/mind-cluster](https://gitcode.com/Ascend/mind-cluster.git)                                                      | 42           | 2359         |
| 24       | [黄诗磊/RecSDK](https://gitcode.com/Ascend/RecSDK.git)                                                                | 38           | 617          |
| 25       | [满涌/openeuler-jenkins](https://gitcode.com/openeuler/openeuler-jenkins.git)                                         | 38           | 130          |
| 26       | [刘建国 00502728/hmpi](https://gitcode.com/kunpengcompute/hmpi.git)                                                   | 38           | 3360         |
| 27       | [于书苹/ascend-deployer](https://gitcode.com/Ascend/ascend-deployer.git)                                              | 37           | 146          |
| 28       | [雷珍珍/MindSpeed-Ops](https://gitcode.com/Ascend/MindSpeed-Ops.git)                                                  | 37           | 156          |
| 29       | [songchangxia/cann-recipes-infer](https://gitcode.com/cann/cann-recipes-infer.git)                                    | 34           | 784          |
| 30       | [刘阳 00584920/KAE](https://gitcode.com/boostkit/KAE.git)                                                             | 33           | 258          |
| 31       | [刘建国 00502728/kunpeng-extension-for-pytorch](https://gitcode.com/kunpengcompute/kunpeng-extension-for-pytorch.git) | 32           | 128          |
| 32       | [songchangxia/cann-recipes-embodied-intelligence](https://gitcode.com/cann/cann-recipes-embodied-intelligence.git)    | 28           | 435          |
| 33       | [尹祺然/catccos](https://gitcode.com/cann/catccos.git)                                                                | 28           | 209          |
| 34       | [卢运杭/cann-recipes-embodied-ai](https://gitcode.com/cann/cann-recipes-embodied-ai.git)                              | 28           | 435          |
| 35       | [lijinbo/openGauss-connector-jdbc](https://gitcode.com/opengauss/openGauss-connector-jdbc.git)                        | 24           | 326          |
| 36       | [杨东/sip](https://gitcode.com/cann/sip.git)                                                                          | 22           | 455          |
| 37       | [songchangxia/cann-recipes-spatial-intelligence](https://gitcode.com/cann/cann-recipes-spatial-intelligence.git)      | 21           | 140          |
| 38       | [songchangxia/mat-chem-sim-pred](https://gitcode.com/cann/mat-chem-sim-pred.git)                                      | 21           | 350          |
| 39       | [-/heolleo](https://gitcode.com/openeuler/heolleo.git)                                                                | 21           | 155          |
| 40       | [雷珍珍/MindSpeed-Bridge](https://gitcode.com/Ascend/MindSpeed-Bridge.git)                                            | 19           | 158          |
| 41       | [-/oeDeploy](https://gitcode.com/openeuler/oeDeploy.git)                                                              | 17           | 95           |
| 42       | [尹祺然/ascend-transformer-boost](https://gitcode.com/cann/ascend-transformer-boost.git)                              | 16           | 843          |
| 43       | [jinxiong/cannbot-skills](https://gitcode.com/cann/cannbot-skills.git)                                                | 16           | 1658         |
| 44       | [zhuchao/libmcpp](https://gitcode.com/openUBMC/libmcpp.git)                                                           | 14           | 516          |
| 45       | [maochen/msmemscope](https://gitcode.com/Ascend/msmemscope.git)                                                       | 12           | 119          |
| 46       | [满涌/eagle](https://gitcode.com/openeuler/eagle.git)                                                                 | 11           | 38           |
| 47       | [songchangxia/runtime](https://gitcode.com/cann/runtime.git)                                                          | 11           | 1258         |
| 48       | [songchangxia/gauss-splat](https://gitcode.com/cann/gauss-splat.git)                                                  | 11           | 83           |
| 49       | [zhangwei/msmonitor](https://gitcode.com/Ascend/msmonitor.git)                                                        | 10           | 74           |
| 50       | [zhaozepeng/msserviceprofiler](https://gitcode.com/Ascend/msserviceprofiler.git)                                      | 10           | 293          |
| 51       | [满涌/oeAware-manager](https://gitcode.com/openeuler/oeAware-manager.git)                                             | 10           | 111          |
| 52       | [huangyuqian/pypto-gym](https://gitcode.com/cann/pypto-gym.git)                                                       | 10           | 992          |
| 53       | [李旭 00934292/Ultrascan](https://gitcode.com/boostkit/Ultrascan.git)                                                 | 10           | 365          |
| 54       | [zhuchao/component_drivers](https://gitcode.com/openUBMC/component_drivers.git)                                       | 9            | 1005         |
| 55       | [易浩/RAGSDK](https://gitcode.com/Ascend/RAGSDK.git)                                                                  | 8            | 187          |
| 56       | [刘建国 00502728/hucx](https://gitcode.com/kunpengcompute/hucx.git)                                                   | 8            | 363          |
| 57       | [尹祺然/shmem](https://gitcode.com/cann/shmem.git)                                                                    | 7            | 269          |
| 58       | [songchangxia/ops-math](https://gitcode.com/cann/ops-math.git)                                                        | 5            | 4345         |
| 59       | [易浩/IndexSDK](https://gitcode.com/Ascend/IndexSDK.git)                                                              | 5            | 743          |
| 60       | [zhangwei/msprof](https://gitcode.com/Ascend/msprof.git)                                                              | 5            | 1043         |
| 61       | [满涌/powerapi](https://gitcode.com/openeuler/powerapi.git)                                                           | 5            | 39           |
| 62       | [yangxu/pypto](https://gitcode.com/cann/pypto.git)                                                                    | 5            | 857          |
| 63       | [zhuchao/devmon](https://gitcode.com/openUBMC/devmon.git)                                                             | 4            | 60           |
| 64       | [songchagnxia/ops-nn](https://gitcode.com/cann/ops-nn.git)                                                            | 4            | 6484         |
| 65       | [songchangxia/graph-autofusion](https://gitcode.com/cann/graph-autofusion.git)                                        | 4            | 604          |
| 66       | [liaoyan/msinsight](https://gitcode.com/Ascend/msinsight.git)                                                         | 4            | 1077         |
| 67       | [panyangjie/msmodelslim](https://gitcode.com/Ascend/msmodelslim.git)                                                  | 4            | 1176         |
| 68       | [-/euler-copilot-shell](https://gitcode.com/openeuler/euler-copilot-shell.git)                                        | 4            | 73           |
| 69       | [刑凯鹏/ascend-boost-comm](https://gitcode.com/cann/ascend-boost-comm.git)                                            | 3            | 75           |
| 70       | [songchangxia/hixl](https://gitcode.com/cann/hixl.git)                                                                | 3            | 127          |
| 71       | [wangtao/ge](https://gitcode.com/cann/ge.git)                                                                         | 3            | 738          |
| 72       | [易浩/MultimodalSDK](https://gitcode.com/Ascend/MultimodalSDK.git)                                                    | 3            | 169          |
| 73       | [wangdongming/cann-recipes-harmony-infer](https://gitcode.com/cann/cann-recipes-harmony-infer.git)                    | 2            | 226          |
| 74       | [songchangxia/torchtitan-npu](https://gitcode.com/cann/torchtitan-npu.git)                                            | 2            | 408          |
| 75       | [songchangxia/triton-inference-server-ge-backend](https://gitcode.com/cann/triton-inference-server-ge-backend.git)    | 2            | 8            |
| 76       | [liaoyan/msagent](https://gitcode.com/Ascend/msagent.git)                                                             | 2            | 280          |
| 77       | [zhuchao/webui](https://gitcode.com/openUBMC/webui.git)                                                               | 1            | 568          |
| 78       | [duping/MindIE-SD](https://gitcode.com/Ascend/MindIE-SD.git)                                                          | 1            | 351          |
| 79       | [songchangxia/opbase](https://gitcode.com/cann/opbase.git)                                                            | 1            | 148          |
| 80       | [songchangxai/tensorflow](https://gitcode.com/cann/tensorflow.git)                                                    | 1            | 143          |
| 81       | [songchangxia/asc-tools](https://gitcode.com/cann/asc-tools.git)                                                      | 1            | 265          |
| 82       | [wangshiling/msopgen](https://gitcode.com/Ascend/msopgen.git)                                                         | 1            | 118          |
| 83       | [songchangxia/oam-tools](https://gitcode.com/cann/oam-tools.git)                                                      | 1            | 361          |
| 84       | [杨云易/cache_tuner](https://gitcode.com/openeuler/cache_tuner.git)                                                   | 1            | 1            |
| 85       | [李博/elec-ops-inspection](https://gitcode.com/cann/elec-ops-inspection.git)                                          | 1            | 15           |
| 86       | [雷珍珍/TransformerEngineNPU](https://gitcode.com/Ascend/TransformerEngineNPU.git)                                    | 1            | 153          |
| 87       | [刘建国 00502728/xucg](https://gitcode.com/kunpengcompute/xucg.git)                                                   | 1            | 193          |
| 88       | [刘建国 00502728/kuqcd](https://gitcode.com/kunpengcompute/kuqcd.git)                                                 | 1            | 19           |
| 89       | [李旭 00934292/KTAG](https://gitcode.com/boostkit/KTAG.git)                                                           | 1            | 12           |
| 90       | [robot/sensor_mgmt](https://gitcode.com/openUBMC/sensor_mgmt.git)                                                     | 1            | 48           |
| 91       | [robot/event_mgmt](https://gitcode.com/openUBMC/event_mgmt.git)                                                       | 1            | 50           |
| 92       | [robot/ipmi_mgmt](https://gitcode.com/openUBMC/ipmi_mgmt.git)                                                         | 1            | 86           |
| 93       | [廖思睿 00564343/Megascan](https://gitcode.com/boostkit/Megascan.git)                                                 | 1            | 19           |
| **合计** | **93 个项目**                                                                                                         | **6712**     | **92790**    |

### 2. 版权声明缺少负责人和年份（no_copyright_line）

有头部块但无版权行（连 copyright 字样都没有，即负责人、年份均缺失）。

| #        | 项目                                                                                                                  | 不合格文件数 | 目标文件总数 |
| -------- | --------------------------------------------------------------------------------------------------------------------- | ------------ | ------------ |
| 1        | [wangshiling/msdebug](https://gitcode.com/Ascend/msdebug.git)                                                         | 11586        | 12701        |
| 2        | [满涌/bishengjdk-8](https://gitcode.com/openeuler/bishengjdk-8.git)                                                   | 1616         | 20395        |
| 3        | [胡桥/AscendNPU-IR](https://gitcode.com/Ascend/AscendNPU-IR.git)                                                      | 222          | 1062         |
| 4        | [lijinbo/openGauss-server](https://gitcode.com/opengauss/openGauss-server.git)                                        | 209          | 2550         |
| 5        | [朱彦儒/MindSpeed-MM](https://gitcode.com/Ascend/MindSpeed-MM.git)                                                    | 184          | 881          |
| 6        | [AtlasAccount/pytorch](https://gitcode.com/Ascend/pytorch.git)                                                        | 155          | 1163         |
| 7        | [songchangxia/cann-recipes-train](https://gitcode.com/cann/cann-recipes-train.git)                                    | 150          | 491          |
| 8        | [宋世轩/oGRAC](https://gitcode.com/opengauss/oGRAC.git)                                                               | 138          | 1131         |
| 9        | [卢运杭/cann-recipes-embodied-ai](https://gitcode.com/cann/cann-recipes-embodied-ai.git)                              | 124          | 435          |
| 10       | [周蓓蓉/slime-ascend](https://gitcode.com/Ascend/slime-ascend.git)                                                    | 115          | 315          |
| 11       | [刘阳 00584920/KAE](https://gitcode.com/boostkit/KAE.git)                                                             | 92           | 258          |
| 12       | [郭鹏/MindSpeed](https://gitcode.com/Ascend/MindSpeed.git)                                                            | 91           | 1200         |
| 13       | [叶羽铭/AgentSDK](https://gitcode.com/Ascend/AgentSDK.git)                                                            | 85           | 475          |
| 14       | [songchangxia/cann-recipes-embodied-intelligence](https://gitcode.com/cann/cann-recipes-embodied-intelligence.git)    | 84           | 435          |
| 15       | [songchangxia/oam-tools](https://gitcode.com/cann/oam-tools.git)                                                      | 73           | 361          |
| 16       | [songchangxia/graph-autofusion](https://gitcode.com/cann/graph-autofusion.git)                                        | 70           | 604          |
| 17       | [雷珍珍/MindSpeed-LLM](https://gitcode.com/Ascend/MindSpeed-LLM.git)                                                  | 70           | 601          |
| 18       | [-/euler-copilot-shell](https://gitcode.com/openeuler/euler-copilot-shell.git)                                        | 68           | 73           |
| 19       | [jinxiong/cannbot-skills](https://gitcode.com/cann/cannbot-skills.git)                                                | 67           | 1658         |
| 20       | [黄鑫/catlass](https://gitcode.com/cann/catlass.git)                                                                  | 64           | 477          |
| 21       | [李睿/mind-cluster](https://gitcode.com/Ascend/mind-cluster.git)                                                      | 59           | 2359         |
| 22       | [songchangxia/torchtitan-npu](https://gitcode.com/cann/torchtitan-npu.git)                                            | 56           | 408          |
| 23       | [songchangxia/cann-recipes-spatial-intelligence](https://gitcode.com/cann/cann-recipes-spatial-intelligence.git)      | 49           | 140          |
| 24       | [-/oeDeploy](https://gitcode.com/openeuler/oeDeploy.git)                                                              | 48           | 95           |
| 25       | [songchangxia/mat-chem-sim-pred](https://gitcode.com/cann/mat-chem-sim-pred.git)                                      | 46           | 350          |
| 26       | [AtlasAccount/torchair](https://gitcode.com/Ascend/torchair.git)                                                      | 44           | 1222         |
| 27       | [华郁秀/DrivingSDK](https://gitcode.com/Ascend/DrivingSDK.git)                                                        | 43           | 542          |
| 28       | [songchangxia/cann-recipes-infer](https://gitcode.com/cann/cann-recipes-infer.git)                                    | 37           | 784          |
| 29       | [刘建国 00502728/kunpeng-extension-for-pytorch](https://gitcode.com/kunpengcompute/kunpeng-extension-for-pytorch.git) | 32           | 128          |
| 30       | [duping/MindIE-SD](https://gitcode.com/Ascend/MindIE-SD.git)                                                          | 31           | 351          |
| 31       | [刘建国 00502728/hmpi](https://gitcode.com/kunpengcompute/hmpi.git)                                                   | 24           | 3360         |
| 32       | [lijinbo/Plugin](https://gitcode.com/opengauss/Plugin.git)                                                            | 22           | 1384         |
| 33       | [雷珍珍/MindSpeed-Bridge](https://gitcode.com/Ascend/MindSpeed-Bridge.git)                                            | 22           | 158          |
| 34       | [duping/MindIE-Motor](https://gitcode.com/Ascend/MindIE-Motor.git)                                                    | 20           | 482          |
| 35       | [雷珍珍/MindSpeed-Ops](https://gitcode.com/Ascend/MindSpeed-Ops.git)                                                  | 18           | 156          |
| 36       | [lijinbo/openGauss-connector-jdbc](https://gitcode.com/opengauss/openGauss-connector-jdbc.git)                        | 17           | 326          |
| 37       | [zhuchao/libmcpp](https://gitcode.com/openUBMC/libmcpp.git)                                                           | 14           | 516          |
| 38       | [满涌/openeuler-jenkins](https://gitcode.com/openeuler/openeuler-jenkins.git)                                         | 13           | 130          |
| 39       | [zhangwei/msprof](https://gitcode.com/Ascend/msprof.git)                                                              | 12           | 1043         |
| 40       | [panyangjie/msmodelslim](https://gitcode.com/Ascend/msmodelslim.git)                                                  | 12           | 1176         |
| 41       | [yangxu/pypto](https://gitcode.com/cann/pypto.git)                                                                    | 12           | 857          |
| 42       | [songchagnxia/asnumpy](https://gitcode.com/cann/asnumpy.git)                                                          | 11           | 86           |
| 43       | [AtlasAccount/op-plugin](https://gitcode.com/Ascend/op-plugin.git)                                                    | 11           | 1049         |
| 44       | [songchangxia/amct](https://gitcode.com/cann/amct.git)                                                                | 11           | 658          |
| 45       | [liaoyan/msagent](https://gitcode.com/Ascend/msagent.git)                                                             | 10           | 280          |
| 46       | [雷珍珍/TransformerEngineNPU](https://gitcode.com/Ascend/TransformerEngineNPU.git)                                    | 10           | 153          |
| 47       | [-/heolleo](https://gitcode.com/openeuler/heolleo.git)                                                                | 9            | 155          |
| 48       | [baijiang/msboost](https://gitcode.com/Ascend/msboost.git)                                                            | 8            | 169          |
| 49       | [zhuchao/component_drivers](https://gitcode.com/openUBMC/component_drivers.git)                                       | 7            | 1005         |
| 50       | [huangyuqian/pypto-gym](https://gitcode.com/cann/pypto-gym.git)                                                       | 7            | 992          |
| 51       | [yushikang/xla-npu](https://gitcode.com/cann/xla-npu.git)                                                             | 6            | 53           |
| 52       | [尹祺然/catccos](https://gitcode.com/cann/catccos.git)                                                                | 6            | 209          |
| 53       | [余启涛/asc-stl](https://gitcode.com/cann/asc-stl.git)                                                                | 6            | 25           |
| 54       | [zhaozepeng/msserviceprofiler](https://gitcode.com/Ascend/msserviceprofiler.git)                                      | 5            | 293          |
| 55       | [maochen/msmemscope](https://gitcode.com/Ascend/msmemscope.git)                                                       | 5            | 119          |
| 56       | [易浩/MultimodalSDK](https://gitcode.com/Ascend/MultimodalSDK.git)                                                    | 5            | 169          |
| 57       | [李旭 00934292/Ultrascan](https://gitcode.com/boostkit/Ultrascan.git)                                                 | 5            | 365          |
| 58       | [于书苹/ascend-deployer](https://gitcode.com/Ascend/ascend-deployer.git)                                              | 4            | 146          |
| 59       | [杨东/sip](https://gitcode.com/cann/sip.git)                                                                          | 4            | 455          |
| 60       | [刘建国 00502728/hucx](https://gitcode.com/kunpengcompute/hucx.git)                                                   | 4            | 363          |
| 61       | [朱泽旭/oeDevPlugin](https://gitcode.com/openeuler/oeDevPlugin.git)                                                   | 4            | 25           |
| 62       | [songchagnxia/ops-nn](https://gitcode.com/cann/ops-nn.git)                                                            | 3            | 6484         |
| 63       | [songchangxia/runtime](https://gitcode.com/cann/runtime.git)                                                          | 3            | 1258         |
| 64       | [满涌/oeAware-manager](https://gitcode.com/openeuler/oeAware-manager.git)                                             | 3            | 111          |
| 65       | [易浩/RAGSDK](https://gitcode.com/Ascend/RAGSDK.git)                                                                  | 2            | 187          |
| 66       | [liaoyan/msinsight](https://gitcode.com/Ascend/msinsight.git)                                                         | 2            | 1077         |
| 67       | [尹祺然/shmem](https://gitcode.com/cann/shmem.git)                                                                    | 2            | 269          |
| 68       | [wangzitao/ops-blas](https://gitcode.com/cann/ops-blas.git)                                                           | 2            | 368          |
| 69       | [robot/sensor_mgmt](https://gitcode.com/openUBMC/sensor_mgmt.git)                                                     | 2            | 48           |
| 70       | [zhuchao/devmon](https://gitcode.com/openUBMC/devmon.git)                                                             | 1            | 60           |
| 71       | [songchangxia/ops-math](https://gitcode.com/cann/ops-math.git)                                                        | 1            | 4345         |
| 72       | [songchangxia/ops-transformer](https://gitcode.com/cann/ops-transformer.git)                                          | 1            | 3334         |
| 73       | [songchangxia/asc-tools](https://gitcode.com/cann/asc-tools.git)                                                      | 1            | 265          |
| 74       | [易浩/IndexSDK](https://gitcode.com/Ascend/IndexSDK.git)                                                              | 1            | 743          |
| 75       | [wangshiling/msopgen](https://gitcode.com/Ascend/msopgen.git)                                                         | 1            | 118          |
| 76       | [满涌/powerapi](https://gitcode.com/openeuler/powerapi.git)                                                           | 1            | 39           |
| 77       | [满涌/eagle](https://gitcode.com/openeuler/eagle.git)                                                                 | 1            | 38           |
| 78       | [李博/elec-ops-inspection](https://gitcode.com/cann/elec-ops-inspection.git)                                          | 1            | 15           |
| 79       | [songchangxia/gauss-splat](https://gitcode.com/cann/gauss-splat.git)                                                  | 1            | 83           |
| 80       | [songkai/ops-multimodal-fusion](https://gitcode.com/cann/ops-multimodal-fusion.git)                                   | 1            | 104          |
| 81       | [robot/event_mgmt](https://gitcode.com/openUBMC/event_mgmt.git)                                                       | 1            | 50           |
| 82       | [robot/ipmi_mgmt](https://gitcode.com/openUBMC/ipmi_mgmt.git)                                                         | 1            | 86           |
| 83       | [songchangxia/its-matrix-computation](https://gitcode.com/cann/its-matrix-computation.git)                            | 1            | 7            |
| **合计** | **83 个项目**                                                                                                         | **16065**    | **89091**    |

### 3.1 版权行不规范（owner_mismatch）

有 copyright 字样但版权行不合规：owner 不是固定 Huawei 或年份/格式不符（三条底线正则任一未命中）。

| #        | 项目                                                                                                                  | 不合格文件数 | 目标文件总数 |
| -------- | --------------------------------------------------------------------------------------------------------------------- | ------------ | ------------ |
| 1        | [满涌/bishengjdk-8](https://gitcode.com/openeuler/bishengjdk-8.git)                                                   | 18680        | 20395        |
| 2        | [刘建国 00502728/hmpi](https://gitcode.com/kunpengcompute/hmpi.git)                                                   | 3259         | 3360         |
| 3        | [李睿/mind-cluster](https://gitcode.com/Ascend/mind-cluster.git)                                                      | 1489         | 2359         |
| 4        | [lijinbo/Plugin](https://gitcode.com/opengauss/Plugin.git)                                                            | 1254         | 1384         |
| 5        | [lijinbo/openGauss-server](https://gitcode.com/opengauss/openGauss-server.git)                                        | 682          | 2550         |
| 6        | [郭鹏/MindSpeed](https://gitcode.com/Ascend/MindSpeed.git)                                                            | 486          | 1200         |
| 7        | [李旭 00934292/Ultrascan](https://gitcode.com/boostkit/Ultrascan.git)                                                 | 346          | 365          |
| 8        | [刘建国 00502728/hucx](https://gitcode.com/kunpengcompute/hucx.git)                                                   | 301          | 363          |
| 9        | [雷珍珍/MindSpeed-LLM](https://gitcode.com/Ascend/MindSpeed-LLM.git)                                                  | 292          | 601          |
| 10       | [songchangxia/ops-math](https://gitcode.com/cann/ops-math.git)                                                        | 282          | 4345         |
| 11       | [朱彦儒/MindSpeed-MM](https://gitcode.com/Ascend/MindSpeed-MM.git)                                                    | 280          | 881          |
| 12       | [lijinbo/openGauss-connector-jdbc](https://gitcode.com/opengauss/openGauss-connector-jdbc.git)                        | 229          | 326          |
| 13       | [songchangxia/cann-recipes-embodied-intelligence](https://gitcode.com/cann/cann-recipes-embodied-intelligence.git)    | 221          | 435          |
| 14       | [wangshiling/msdebug](https://gitcode.com/Ascend/msdebug.git)                                                         | 214          | 12701        |
| 15       | [wangdongming/cann-recipes-harmony-infer](https://gitcode.com/cann/cann-recipes-harmony-infer.git)                    | 199          | 226          |
| 16       | [卢运杭/cann-recipes-embodied-ai](https://gitcode.com/cann/cann-recipes-embodied-ai.git)                              | 181          | 435          |
| 17       | [雷珍珍/TransformerEngineNPU](https://gitcode.com/Ascend/TransformerEngineNPU.git)                                    | 142          | 153          |
| 18       | [songchagnxia/ops-nn](https://gitcode.com/cann/ops-nn.git)                                                            | 138          | 6484         |
| 19       | [-/heolleo](https://gitcode.com/openeuler/heolleo.git)                                                                | 125          | 155          |
| 20       | [雷珍珍/MindSpeed-Bridge](https://gitcode.com/Ascend/MindSpeed-Bridge.git)                                            | 117          | 158          |
| 21       | [黄诗磊/RecSDK](https://gitcode.com/Ascend/RecSDK.git)                                                                | 103          | 617          |
| 22       | [songchagnxia/asnumpy](https://gitcode.com/cann/asnumpy.git)                                                          | 73           | 86           |
| 23       | [刘阳 00584920/KAE](https://gitcode.com/boostkit/KAE.git)                                                             | 72           | 258          |
| 24       | [雷珍珍/MindSpeed-Ops](https://gitcode.com/Ascend/MindSpeed-Ops.git)                                                  | 70           | 156          |
| 25       | [songchangxia/cann-recipes-infer](https://gitcode.com/cann/cann-recipes-infer.git)                                    | 52           | 784          |
| 26       | [AtlasAccount/pytorch](https://gitcode.com/Ascend/pytorch.git)                                                        | 42           | 1163         |
| 27       | [songchangxia/cann-recipes-train](https://gitcode.com/cann/cann-recipes-train.git)                                    | 37           | 491          |
| 28       | [songchangxia/pyasc](https://gitcode.com/cann/pyasc.git)                                                              | 37           | 332          |
| 29       | [刘建国 00502728/kunpeng-extension-for-pytorch](https://gitcode.com/kunpengcompute/kunpeng-extension-for-pytorch.git) | 33           | 128          |
| 30       | [宋世轩/oGRAC](https://gitcode.com/opengauss/oGRAC.git)                                                               | 26           | 1131         |
| 31       | [songchangxia/torchtitan-npu](https://gitcode.com/cann/torchtitan-npu.git)                                            | 23           | 408          |
| 32       | [huangyuqian/pypto-gym](https://gitcode.com/cann/pypto-gym.git)                                                       | 23           | 992          |
| 33       | [胡桥/AscendNPU-IR](https://gitcode.com/Ascend/AscendNPU-IR.git)                                                      | 22           | 1062         |
| 34       | [叶羽铭/AgentSDK](https://gitcode.com/Ascend/AgentSDK.git)                                                            | 22           | 475          |
| 35       | [songchangxia/cann-recipes-spatial-intelligence](https://gitcode.com/cann/cann-recipes-spatial-intelligence.git)      | 21           | 140          |
| 36       | [zhangwei/msmonitor](https://gitcode.com/Ascend/msmonitor.git)                                                        | 21           | 74           |
| 37       | [panyangjie/msmodelslim](https://gitcode.com/Ascend/msmodelslim.git)                                                  | 20           | 1176         |
| 38       | [余启涛/asc-stl](https://gitcode.com/cann/asc-stl.git)                                                                | 18           | 25           |
| 39       | [华郁秀/DrivingSDK](https://gitcode.com/Ascend/DrivingSDK.git)                                                        | 14           | 542          |
| 40       | [AtlasAccount/op-plugin](https://gitcode.com/Ascend/op-plugin.git)                                                    | 12           | 1049         |
| 41       | [zhangwei/msprof](https://gitcode.com/Ascend/msprof.git)                                                              | 10           | 1043         |
| 42       | [songkai/ops-multimodal-fusion](https://gitcode.com/cann/ops-multimodal-fusion.git)                                   | 9            | 104          |
| 43       | [baijiang/msboost](https://gitcode.com/Ascend/msboost.git)                                                            | 9            | 169          |
| 44       | [李博/elec-ops-inspection](https://gitcode.com/cann/elec-ops-inspection.git)                                          | 8            | 15           |
| 45       | [songchangxia/ops-sparse](https://gitcode.com/cann/ops-sparse.git)                                                    | 8            | 165          |
| 46       | [songchangxia/amct](https://gitcode.com/cann/amct.git)                                                                | 6            | 658          |
| 47       | [周蓓蓉/slime-ascend](https://gitcode.com/Ascend/slime-ascend.git)                                                    | 6            | 315          |
| 48       | [songchangxia/its-matrix-computation](https://gitcode.com/cann/its-matrix-computation.git)                            | 6            | 7            |
| 49       | [李博/elec-ops-prediction](https://gitcode.com/cann/elec-ops-prediction.git)                                          | 5            | 5            |
| 50       | [liaoyan/msinsight](https://gitcode.com/Ascend/msinsight.git)                                                         | 4            | 1077         |
| 51       | [songchangxia/ops-cv](https://gitcode.com/cann/ops-cv.git)                                                            | 3            | 871          |
| 52       | [zhuchao/component_drivers](https://gitcode.com/openUBMC/component_drivers.git)                                       | 2            | 1005         |
| 53       | [zhaozepeng/msserviceprofiler](https://gitcode.com/Ascend/msserviceprofiler.git)                                      | 2            | 293          |
| 54       | [wangshiling/msopgen](https://gitcode.com/Ascend/msopgen.git)                                                         | 2            | 118          |
| 55       | [yangxu/pypto](https://gitcode.com/cann/pypto.git)                                                                    | 2            | 857          |
| 56       | [刘建国 00502728/xucg](https://gitcode.com/kunpengcompute/xucg.git)                                                   | 2            | 193          |
| 57       | [songchangxia/gauss-splat](https://gitcode.com/cann/gauss-splat.git)                                                  | 2            | 83           |
| 58       | [duping/MindIE-SD](https://gitcode.com/Ascend/MindIE-SD.git)                                                          | 1            | 351          |
| 59       | [尹祺然/ascend-transformer-boost](https://gitcode.com/cann/ascend-transformer-boost.git)                              | 1            | 843          |
| 60       | [songchangxia/asc-tools](https://gitcode.com/cann/asc-tools.git)                                                      | 1            | 265          |
| 61       | [满涌/openeuler-jenkins](https://gitcode.com/openeuler/openeuler-jenkins.git)                                         | 1            | 130          |
| 62       | [songchangxia/triton-inference-server-ge-backend](https://gitcode.com/cann/triton-inference-server-ge-backend.git)    | 1            | 8            |
| 63       | [songchangxia/amct-graph](https://gitcode.com/cann/amct-graph.git)                                                    | 1            | 556          |
| 64       | [liaoyan/msagent](https://gitcode.com/Ascend/msagent.git)                                                             | 1            | 280          |
| **合计** | **64 个项目**                                                                                                         | **29751**    | **79376**    |

### 3.2 版权头与协议模板不匹配（template_mismatch）

版权行达标但头部正文与 LICENSE 模板归一化全匹配失败。

| #        | 项目                                                                                                               | 不合格文件数 | 目标文件总数 |
| -------- | ------------------------------------------------------------------------------------------------------------------ | ------------ | ------------ |
| 1        | [易浩/IndexSDK](https://gitcode.com/Ascend/IndexSDK.git)                                                           | 737          | 743          |
| 2        | [胡桥/AscendNPU-IR](https://gitcode.com/Ascend/AscendNPU-IR.git)                                                   | 612          | 1062         |
| 3        | [lijinbo/openGauss-server](https://gitcode.com/opengauss/openGauss-server.git)                                     | 610          | 2550         |
| 4        | [songchangxia/amct](https://gitcode.com/cann/amct.git)                                                             | 553          | 658          |
| 5        | [jinxiong/cannbot-skills](https://gitcode.com/cann/cannbot-skills.git)                                             | 542          | 1658         |
| 6        | [songchangxia/amct-graph](https://gitcode.com/cann/amct-graph.git)                                                 | 509          | 556          |
| 7        | [songchangxia/cann-recipes-infer](https://gitcode.com/cann/cann-recipes-infer.git)                                 | 497          | 784          |
| 8        | [黄诗磊/RecSDK](https://gitcode.com/Ascend/RecSDK.git)                                                             | 476          | 617          |
| 9        | [songchagnxia/ops-nn](https://gitcode.com/cann/ops-nn.git)                                                         | 462          | 6484         |
| 10       | [zhangwei/msprof-analyze](https://gitcode.com/Ascend/msprof-analyze.git)                                           | 451          | 451          |
| 11       | [李睿/mind-cluster](https://gitcode.com/Ascend/mind-cluster.git)                                                   | 364          | 2359         |
| 12       | [华郁秀/DrivingSDK](https://gitcode.com/Ascend/DrivingSDK.git)                                                     | 357          | 542          |
| 13       | [songchangxia/torchtitan-npu](https://gitcode.com/cann/torchtitan-npu.git)                                         | 324          | 408          |
| 14       | [叶羽铭/AgentSDK](https://gitcode.com/Ascend/AgentSDK.git)                                                         | 284          | 475          |
| 15       | [songchangxia/mat-chem-sim-pred](https://gitcode.com/cann/mat-chem-sim-pred.git)                                   | 283          | 350          |
| 16       | [songchangxia/ops-math](https://gitcode.com/cann/ops-math.git)                                                     | 209          | 4345         |
| 17       | [刘建国 00502728/xucg](https://gitcode.com/kunpengcompute/xucg.git)                                                | 190          | 193          |
| 18       | [易浩/RAGSDK](https://gitcode.com/Ascend/RAGSDK.git)                                                               | 177          | 187          |
| 19       | [尹祺然/catccos](https://gitcode.com/cann/catccos.git)                                                             | 170          | 209          |
| 20       | [易浩/MultimodalSDK](https://gitcode.com/Ascend/MultimodalSDK.git)                                                 | 161          | 169          |
| 21       | [duping/MindIE-Motor](https://gitcode.com/Ascend/MindIE-Motor.git)                                                 | 160          | 482          |
| 22       | [AtlasAccount/op-plugin](https://gitcode.com/Ascend/op-plugin.git)                                                 | 159          | 1049         |
| 23       | [songchangxia/ops-transformer](https://gitcode.com/cann/ops-transformer.git)                                       | 157          | 3334         |
| 24       | [huangyuqian/pypto-gym](https://gitcode.com/cann/pypto-gym.git)                                                    | 128          | 992          |
| 25       | [郭鹏/MindSpeed](https://gitcode.com/Ascend/MindSpeed.git)                                                         | 124          | 1200         |
| 26       | [songchangxia/oam-tools](https://gitcode.com/cann/oam-tools.git)                                                   | 109          | 361          |
| 27       | [songchangxia/cann-recipes-embodied-intelligence](https://gitcode.com/cann/cann-recipes-embodied-intelligence.git) | 100          | 435          |
| 28       | [卢运杭/cann-recipes-embodied-ai](https://gitcode.com/cann/cann-recipes-embodied-ai.git)                           | 100          | 435          |
| 29       | [黄鑫/catlass](https://gitcode.com/cann/catlass.git)                                                               | 95           | 477          |
| 30       | [满涌/openeuler-jenkins](https://gitcode.com/openeuler/openeuler-jenkins.git)                                      | 78           | 130          |
| 31       | [尹祺然/ascend-transformer-boost](https://gitcode.com/cann/ascend-transformer-boost.git)                           | 77           | 843          |
| 32       | [于书苹/ascend-deployer](https://gitcode.com/Ascend/ascend-deployer.git)                                           | 76           | 146          |
| 33       | [wangshiling/msopgen](https://gitcode.com/Ascend/msopgen.git)                                                      | 64           | 118          |
| 34       | [songkai/ops-multimodal-fusion](https://gitcode.com/cann/ops-multimodal-fusion.git)                                | 57           | 104          |
| 35       | [lijinbo/openGauss-connector-jdbc](https://gitcode.com/opengauss/openGauss-connector-jdbc.git)                     | 56           | 326          |
| 36       | [songchangxia/cann-recipes-train](https://gitcode.com/cann/cann-recipes-train.git)                                 | 55           | 491          |
| 37       | [yangxu/pypto](https://gitcode.com/cann/pypto.git)                                                                 | 54           | 857          |
| 38       | [刘建国 00502728/hucx](https://gitcode.com/kunpengcompute/hucx.git)                                                | 50           | 363          |
| 39       | [liaoyan/msinsight](https://gitcode.com/Ascend/msinsight.git)                                                      | 49           | 1077         |
| 40       | [songchangxia/cann-recipes-spatial-intelligence](https://gitcode.com/cann/cann-recipes-spatial-intelligence.git)   | 47           | 140          |
| 41       | [songchangxia/graph-autofusion](https://gitcode.com/cann/graph-autofusion.git)                                     | 45           | 604          |
| 42       | [duping/MindIE-SD](https://gitcode.com/Ascend/MindIE-SD.git)                                                       | 44           | 351          |
| 43       | [baijiang/msboost](https://gitcode.com/Ascend/msboost.git)                                                         | 44           | 169          |
| 44       | [zhangwei/msmonitor](https://gitcode.com/Ascend/msmonitor.git)                                                     | 43           | 74           |
| 45       | [雷珍珍/MindSpeed-LLM](https://gitcode.com/Ascend/MindSpeed-LLM.git)                                               | 42           | 601          |
| 46       | [lijinbo/Plugin](https://gitcode.com/opengauss/Plugin.git)                                                         | 41           | 1384         |
| 47       | [songchangxia/ops-sparse](https://gitcode.com/cann/ops-sparse.git)                                                 | 41           | 165          |
| 48       | [wangzitao/ops-blas](https://gitcode.com/cann/ops-blas.git)                                                        | 40           | 368          |
| 49       | [zhuchao/component_drivers](https://gitcode.com/openUBMC/component_drivers.git)                                    | 39           | 1005         |
| 50       | [刘建国 00502728/hmpi](https://gitcode.com/kunpengcompute/hmpi.git)                                                | 39           | 3360         |
| 51       | [刘阳 00584920/KAE](https://gitcode.com/boostkit/KAE.git)                                                          | 36           | 258          |
| 52       | [songchangxia/ops-ras](https://gitcode.com/cann/ops-ras.git)                                                       | 35           | 101          |
| 53       | [wangtao/ge](https://gitcode.com/cann/ge.git)                                                                      | 34           | 738          |
| 54       | [满涌/powerapi](https://gitcode.com/openeuler/powerapi.git)                                                        | 33           | 39           |
| 55       | [雷珍珍/MindSpeed-Ops](https://gitcode.com/Ascend/MindSpeed-Ops.git)                                               | 31           | 156          |
| 56       | [-/oeDeploy](https://gitcode.com/openeuler/oeDeploy.git)                                                           | 30           | 95           |
| 57       | [panyangjie/msmodelslim](https://gitcode.com/Ascend/msmodelslim.git)                                               | 26           | 1176         |
| 58       | [满涌/eagle](https://gitcode.com/openeuler/eagle.git)                                                              | 26           | 38           |
| 59       | [满涌/oeAware-manager](https://gitcode.com/openeuler/oeAware-manager.git)                                          | 25           | 111          |
| 60       | [songkai/ops-tensor](https://gitcode.com/cann/ops-tensor.git)                                                      | 22           | 76           |
| 61       | [songchangxia/gauss-splat](https://gitcode.com/cann/gauss-splat.git)                                               | 22           | 83           |
| 62       | [robot/ipmi_mgmt](https://gitcode.com/openUBMC/ipmi_mgmt.git)                                                      | 22           | 86           |
| 63       | [宋世轩/oGRAC](https://gitcode.com/opengauss/oGRAC.git)                                                            | 21           | 1131         |
| 64       | [zhuchao/libmcpp](https://gitcode.com/openUBMC/libmcpp.git)                                                        | 19           | 516          |
| 65       | [廖思睿 00564343/Megascan](https://gitcode.com/boostkit/Megascan.git)                                              | 18           | 19           |
| 66       | [zhuchao/webui](https://gitcode.com/openUBMC/webui.git)                                                            | 15           | 568          |
| 67       | [songchangxia/ops-cv](https://gitcode.com/cann/ops-cv.git)                                                         | 15           | 871          |
| 68       | [wangdongming/cann-recipes-harmony-infer](https://gitcode.com/cann/cann-recipes-harmony-infer.git)                 | 15           | 226          |
| 69       | [AtlasAccount/pytorch](https://gitcode.com/Ascend/pytorch.git)                                                     | 14           | 1163         |
| 70       | [朱彦儒/MindSpeed-MM](https://gitcode.com/Ascend/MindSpeed-MM.git)                                                 | 14           | 881          |
| 71       | [尹祺然/shmem](https://gitcode.com/cann/shmem.git)                                                                 | 13           | 269          |
| 72       | [songchangxia/runtime](https://gitcode.com/cann/runtime.git)                                                       | 12           | 1258         |
| 73       | [李旭 00934292/KTAG](https://gitcode.com/boostkit/KTAG.git)                                                        | 11           | 12           |
| 74       | [yushikang/xla-npu](https://gitcode.com/cann/xla-npu.git)                                                          | 9            | 53           |
| 75       | [zhangwei/msprof](https://gitcode.com/Ascend/msprof.git)                                                           | 7            | 1043         |
| 76       | [zhangwei/mspti](https://gitcode.com/Ascend/mspti.git)                                                             | 6            | 92           |
| 77       | [songchangxia/triton-inference-server-ge-backend](https://gitcode.com/cann/triton-inference-server-ge-backend.git) | 5            | 8            |
| 78       | [李博/elec-ops-inspection](https://gitcode.com/cann/elec-ops-inspection.git)                                       | 5            | 15           |
| 79       | [robot/event_mgmt](https://gitcode.com/openUBMC/event_mgmt.git)                                                    | 5            | 50           |
| 80       | [wangshiling/msopprof](https://gitcode.com/Ascend/msopprof.git)                                                    | 4            | 131          |
| 81       | [陈一帆 00939336/kqmalloc](https://gitcode.com/boostkit/kqmalloc.git)                                              | 4            | 4            |
| 82       | [李旭 00934292/Ultrascan](https://gitcode.com/boostkit/Ultrascan.git)                                              | 4            | 365          |
| 83       | [songchagnxia/metadef](https://gitcode.com/cann/metadef.git)                                                       | 3            | 23           |
| 84       | [杨东/sip](https://gitcode.com/cann/sip.git)                                                                       | 3            | 455          |
| 85       | [songchangxia/pypto-tools](https://gitcode.com/cann/pypto-tools.git)                                               | 3            | 263          |
| 86       | [AtlasAccount/torchair](https://gitcode.com/Ascend/torchair.git)                                                   | 3            | 1222         |
| 87       | [songchangxia/pto-tile-lib](https://gitcode.com/cann/pto-tile-lib.git)                                             | 3            | 55           |
| 88       | [songchangxia/asc-tools](https://gitcode.com/cann/asc-tools.git)                                                   | 3            | 265          |
| 89       | [maochen/msmemscope](https://gitcode.com/Ascend/msmemscope.git)                                                    | 3            | 119          |
| 90       | [满涌/bishengjdk-8](https://gitcode.com/openeuler/bishengjdk-8.git)                                                | 3            | 20395        |
| 91       | [songkai/ops-rand](https://gitcode.com/cann/ops-rand.git)                                                          | 3            | 32           |
| 92       | [李博/elec-ops-simulation](https://gitcode.com/cann/elec-ops-simulation.git)                                       | 3            | 3            |
| 93       | [songkai/ops-fft](https://gitcode.com/cann/ops-fft.git)                                                            | 3            | 58           |
| 94       | [songchangxia/ops-solver](https://gitcode.com/cann/ops-solver.git)                                                 | 3            | 25           |
| 95       | [songchangxia/ops-df](https://gitcode.com/cann/ops-df.git)                                                         | 3            | 176          |
| 96       | [zhuchao/devmon](https://gitcode.com/openUBMC/devmon.git)                                                          | 2            | 60           |
| 97       | [songchagnxia/asnumpy](https://gitcode.com/cann/asnumpy.git)                                                       | 2            | 86           |
| 98       | [wangshiling/msdebug](https://gitcode.com/Ascend/msdebug.git)                                                      | 2            | 12701        |
| 99       | [songchangxia/hixl](https://gitcode.com/cann/hixl.git)                                                             | 1            | 127          |
| 100      | [songchangxia/atcos](https://gitcode.com/cann/atcos.git)                                                           | 1            | 49           |
| 101      | [songchangxia/pyasc](https://gitcode.com/cann/pyasc.git)                                                           | 1            | 332          |
| 102      | [songchangxia/atvoss](https://gitcode.com/cann/atvoss.git)                                                         | 1            | 10           |
| 103      | [wangshiling/msopcom](https://gitcode.com/Ascend/msopcom.git)                                                      | 1            | 180          |
| 104      | [menfeifei/mskl](https://gitcode.com/Ascend/mskl.git)                                                              | 1            | 26           |
| 105      | [wangshiling/mssanitizer](https://gitcode.com/Ascend/mssanitizer.git)                                              | 1            | 187          |
| 106      | [zhangjian/pto-isa](https://gitcode.com/cann/pto-isa.git)                                                          | 1            | 204          |
| 107      | [刘建国 00502728/kudnn](https://gitcode.com/kunpengcompute/kudnn.git)                                              | 1            | 143          |
| 108      | [-/euler-copilot-shell](https://gitcode.com/openeuler/euler-copilot-shell.git)                                     | 1            | 73           |
| 109      | [余启涛/asc-stl](https://gitcode.com/cann/asc-stl.git)                                                             | 1            | 25           |
| 110      | [robot/sensor_mgmt](https://gitcode.com/openUBMC/sensor_mgmt.git)                                                  | 1            | 48           |
| **合计** | **110 个项目**                                                                                                     | **10796**    | **95215**    |

### 附：整仓 NA 仓说明

以下 6 个仓最新批次整仓 NA（无/不可读 LICENSE、无目标后缀文件或近期 clone 失败），不产生不合格明细（目标文件数取该仓最近一次落表值）：

| repo_id | 项目           | 目标文件数 |
| ------- | -------------- | ---------- |
| 401239  | acl-extend     | 0          |
| 401243  | astile-python  | 0          |
| 402012  | osinfor        | 0          |
| 402015  | yuanrong-serve | 0          |
| 402113  | kernel         | 0          |
| 403136  | diffrast       | 0          |

> 数据质量提示：MindSpeed-LLM(402336)、MindSpeed-MM(402339)、DrivingSDK(402340)、MindSpeed-Bridge(403114)、TransformerEngineNPU(403118)、pypto-gym(403209)、KTAG(404348) 等仓在 2026-10-15 起主表连续整仓 NA（score=NULL，疑似 clone 失败），其明细表数据为更早成功批次所留，成功批次恢复后需复核。
