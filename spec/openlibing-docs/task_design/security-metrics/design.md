# 代码安全检查评分看板 · 技术方案（design）

## 架构概览

```text
通道①接口拉取(raw→sdi)      通道②已有表SQL直算        通道③仓库文件Python扫描      通道④外部清单拉取
 分支保护/PR设置              commit/issue/PR/workflow   workflow yml/LICENSE/        OSS-Fuzz projects/
 Webhook/Release              漏洞视图表                 SECURITY.md/二进制/版权/      openEuler固定工程
 用户orgs/PR评论(复用)                                    pre-commit/Dockerfile/sh
        │                          │                          │                        │
        └──────────────┬───────────┴──────────┬───────────────┴──────────┬──────────────┘
                       ▼                      ▼                          ▼
                  DWI 明细结果表（7 张，按任务类型）                            │
                       └──────────────────────┬───────────────────────────┘
                                              ▼
                       DM 宽表 dm_security_scan_score（repo × scan_time × 18 指标 + 加权总分 + 亮灯）
```

## 数据生产链路

DolphinScheduler 定时任务 → Doris 分层数仓（raw → sdi → dwi → dm）→ 前端看板读取 dm

### DolphinScheduler 项目：`security_check_scoring`

```text
01 接口拉取层（每日，遍历 is_operated=1 仓库）✅ 6 接口任务已建
   ├ task_repo_branch_protection(T1a) → raw_repo_branch_protection (指标8，⚠️token权限不足，暂缓)
   ├ task_repo_pr_setting(T1b)        → raw_repo_pr_setting        (指标8，⚠️token权限不足，暂缓)
   ├ task_repo_webhook(T5)            → raw_repo_webhook           (指标9，✅password_is_null已补)
   ├ task_repo_release(T3)            → raw_repo_release_info      (指标11)
   ├ task_repo_contributors(T4a)      → raw_repo_contribute_info   (指标18)
   ├ task_contrib_organize(T4b)       → raw_contrib_organize       (指标18)
   └ task_pr_comment                  → raw_pr_comment_gitcode     (指标7，已有复用)
02 外部清单拉取
   ├ task_openeuler_project_repos ✅任务已建 → sdi_rd_efc_euler_package (指标12)
   └ task_ossfuzz_projects        ⏸️ 暂缓 (指标13)
03 commit 采集（"1" 链路）
   └ git log 扫描 → raw_repo_commit_log → sdi_repo_commit_log (指标17)
04 清洗 sdi（依赖01/02/03，sdi 表 DDL+DML 已写未执行）
   ├ [1] sdi_rd_efc_branch_protection ⏸️ 暂缓
   ├ [2] sdi_rd_efc_pr_setting        ⏸️ 暂缓
   ├ [3] sdi_rd_efc_release
   ├ [4] sdi_rd_efc_repo_contributor
   ├ [5] sdi_rd_efc_repo_webhook      (✅password_is_null已采集)
   ├ [6] sdi_rd_efc_pr_review_reviewer
   └ commit链路: raw_repo_commit_log → sdi_repo_commit_log
05 文件扫描（Python，clone 仓库）
   ├ copyright / dangerous_wf / token_perm / binary_artifacts
   ├ packaging(含openEuler比对) / sast / security_policy → dwi_security_file_scan
   └ license(scancode) → dwi_security_license_scan
06 指标计算 & 汇聚（SQL）
   ├ D1: 指标7+10   → dwi_security_pr_scan
   ├ D2: 指标9/11/18 → dwi_security_meta_api_scan
   ├ D3: 指标17      → dwi_security_maintained_scan
   ├ 指标8           → dwi_security_branch_protect_scan ⏸️ 暂缓
   ├ 指标16          → dwi_security_vuln_scan          ⏸️ 暂缓
   └ D4: 全指标汇聚 → dm_security_scan_score
```

## 目标表设计

### DM 宽表：`dm_security_scan_score`

仓库 × 批次时间戳 × 18 指标得分 + 仓库加权总分（两套）+ 亮灯

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| repo_id | INT | 仓库 ID |
| repo_url | VARCHAR(512) | 仓库地址 |
| scan_time | DATETIME | 批次扫描时间戳 |
| score_license | DECIMAL(5,2) | 指标1 开源许可证(规则7.5) |
| score_copyright | DECIMAL(5,2) | 指标2 版权合规(规则10) |
| score_dangerous_wf | DECIMAL(5,2) | 指标3 危险工作流(规则10) |
| score_token_perm | DECIMAL(5,2) | 指标4 令牌权限(规则7.5) |
| score_pinned_dep | DECIMAL(5,2) | 指标5 依赖锁定(建议5) ⏸️ 暂为 NULL |
| score_binary_artifacts | DECIMAL(5,2) | 指标6 二进制制品(规则7.5) |
| score_code_review | DECIMAL(5,2) | 指标7 代码评审(规则7.5) |
| score_branch_protection | DECIMAL(5,2) | 指标8 分支保护(规则7.5) ⏸️ 暂为 NULL |
| score_webhooks | DECIMAL(5,2) | 指标9 Webhook(规则10) |
| score_ci_tests | DECIMAL(5,2) | 指标10 CI测试(规则2.5) |
| score_signed_releases | DECIMAL(5,2) | 指标11 发布签名(建议5) |
| score_packaging | DECIMAL(5,2) | 指标12 软件包发布(规则5) |
| score_fuzzing | DECIMAL(5,2) | 指标13 模糊测试(建议5) ⏸️ 暂为 NULL |
| score_sast | DECIMAL(5,2) | 指标14 SAST(建议5) |
| score_security_policy | DECIMAL(5,2) | 指标15 安全策略(规则5) |
| score_vulns | DECIMAL(5,2) | 指标16 已知漏洞(规则7.5) ⏸️ 暂为 NULL |
| score_maintained | DECIMAL(5,2) | 指标17 项目维护(规则2.5) |
| score_contributors | DECIMAL(5,2) | 指标18 贡献者多样性(建议2.5) |
| score_rule_weighted | DECIMAL(5,2) | 规则项加权总分（权重和 75，NA 剔除） |
| score_all_weighted | DECIMAL(5,2) | 全部指标加权总分（权重和 87.5，仅展示） |
| rule_light | TINYINT | 仓库亮灯：1绿(≥80%) 2黄(≥50%) 3红(<50%) |
| etl_time | DATETIME | ETL 时间 |

唯一键：UNIQUE KEY (repo_id, scan_time)

### DWI 明细表（7 张）

1. **dwi_security_pr_scan** — 指标7 CODE_REVIEW + 指标10 CI_TESTS（同批近 30 次已合入 PR）
2. **dwi_security_meta_api_scan** — 指标9 WEBHOOKS + 11 SIGNED_RELEASES + 18 CONTRIBUTORS（接口→sdi→SQL）
3. **dwi_security_maintained_scan** — 指标17 MAINTAINED（sdi_repo_commit_log + sdi_repo_issue_info）
4. **dwi_security_file_scan** — 指标2/3/4/6/12/14/15（Python clone 扫描）
5. **dwi_security_license_scan** — 指标1 LICENSE（Python scancode）
6. **dwi_security_branch_protect_scan** — 指标8 ⏸️ 暂缓
7. **dwi_security_vuln_scan** — 指标16 ⏸️ 暂缓

通用约定：score 0~10；is_na=1 则 score=NULL；scan_time = 批次时间；detail_json 结构化原因明细。

## 汇聚与亮灯规则

1. **仓库得分分两套**：规则项（类型=规则 13 项，权重和 90）用于项目层级；全部（18 项，权重和 112.5）仅展示
2. **得分公式**：`仓库得分 = Σ(单项得分 × 权重) / Σ权重`；NA + 暂缓项（5/8/13/16）分子分母同时剔除
3. **仓库亮灯**：得分率（仓库得分/10）≥80% 绿，≥50% 黄，<50% 红。按规则项得分计算
4. **项目层级得分**：`Σ仓库规则项得分 / 仓库数量`；亮灯取最低灯

## 关键打分规则摘要

| 指标 | 打分规则 | NA 条件 |
| --- | --- | --- |
| 1 LICENSE | 阶梯：有5→模板8→版权正确9→OSI/FSF10；无0 | 无 |
| 2 COPYRIGHT | 10 × 含声明文件数 / 目标文件数（正则 `Copyright\(c\)\s*\d{4}\s+Huawei Technologies Co\.`） | 仓库无目标后缀文件 |
| 3 DANGEROUS_WF | 发现任意危险模式=0，未发现=10 | 无 workflow 文件 |
| 4 TOKEN_PERM | 5 条规则（全读10/全写0/未配且有写0/未配全读9/部分写 `10×(1-带写文件数/总文件数)`） | 无 workflow 文件 |
| 6 BINARY_ARTIFACTS | max(0, 10 - 二进制文件数) | 无 |
| 7 CODE_REVIEW | 10 × 已评审数 / 总PR数（近 30 次已合入 PR，非机器人非创建人 /lgtm 或 /approve） | 剔除机器人后 PR=0 |
| 9 WEBHOOKS | ⌊10 × 配置密钥的Webhook数 / 活跃Webhook数⌋；无活跃钩=10 | 无 |
| 10 CI_TESTS | 10 × 有CI的PR数 / 合并PR数（codearts 关联表单表判定） | 无 PR |
| 11 SIGNED_RELEASES | 最近 30 个正式版本，全部含签名或 SLSA=10，任一不满足=0 | 无 release |
| 12 PACKAGING | 10（有 workflow 或在 openEuler 工程内） | 无 workflow 且不在 openEuler 工程 |
| 14 SAST | 有 pre-commit=10，无=0 | 无 |
| 15 SECURITY_POLICY | 仓内有 SECURITY.md=10，社区=5，都无=0 | 无 |
| 17 MAINTAINED | min(10, 10 × (commit数₉₀d + issue数₉₀d) / 13) | 已归档或创建不足 90 天 |
| 18 CONTRIBUTORS | min(10, 10 × N / 3)，N = 近 30 次 PR ≥5 的组织数 | 近 30 次 PR=0 |

## 外部依赖与遗留项

| 遗留项 | 指标 | 依赖 | 当前状态 |
| --- | --- | --- | --- |
| C8 | 8 分支保护 | token 提权 + sdi 补字段 | 暂缓 |
| C9 | 13 模糊测试 | 原生 fuzz 规则细化 | 暂缓 |
| C10 | 16 已知漏洞 | 漏洞视图表名 | 暂缓 |
| - | 4 令牌权限 | gitcode 权限映射（待李洪峰） | 不阻塞其他项 |
| - | 5 依赖锁定 | openUBMC 社区支持（待徐海军） | 暂缓 |

## 详细规则来源

本 design.md 为简版，完整指标规则（含打分公式、NA 条件、dwi 明细结构、仲裁记录 C1~C11）见项目原始设计文档 `docs/0912/design.md v4 终版`。
