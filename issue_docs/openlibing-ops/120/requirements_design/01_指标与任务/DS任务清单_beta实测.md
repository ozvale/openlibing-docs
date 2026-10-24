# 安全合规看板 · DolphinScheduler 任务清单（beta 实测）

> 实测时间：2026-10-24
> 实测方式：DolphinScheduler MCP（ds_workflow_list / ds_task_list / ds_instance_list）
> 实测环境：`https://1.95.74.1:12345`，实例运行主机 `openlibing-dolphinscheduler-master-beta-0`（即 beta）
> 项目：`openlibing`（project code `169400948446944`）
> 注意：design.md 中写的项目名为 `security_check_scoring`，与现网实际项目 `openlibing` 不一致。

---

## 1. beta 已建任务（安全合规专用）

| #   | Workflow                                                      | Workflow Code   | 状态/版本      | 内部节点（code / 名称 / 类型）                                                                                                                                             | 目标表                                                                  | 最近实例                                                                                                                 |
| --- | ------------------------------------------------------------- | --------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 1   | [安全合规][job][raw]获取仓库webhook激活状态                   | 184353840916386 | ONLINE v5      | 184353840916384 / 获取仓库webhook激活状态 / SEATUNNEL；184353840916385 / 清空代码仓webhook / SQL                                                                           | raw_repo_webhook                                                        | 10211（2026-10-15 15:18）SUCCESS 39s；10190（2026-10-10 11:52）SUCCESS 35s                                               |
| 2   | [安全合规][job][raw]获取代码仓发布签名检查（Signed-Releases） | 184260614994849 | ONLINE v9      | 184260614994848 / 获取仓库release信息-发布签名检查 / SEATUNNEL；184331308873632 / 情况代码仓发布签名检查raw表 / SQL；185388365232032 / 获取代码仓发布签名检查数据 / PYTHON | raw_repo_release_info                                                   | 10210（2026-10-15 15:17）SUCCESS 39s；10187（2026-10-10 10:10）SUCCESS 35s                                               |
| 3   | [安全合规][job][raw]获取仓库贡献者信息及组织                  | 184261380734881 | ONLINE v11     | 184416477750176 / 获取仓库贡献者列表 / SEATUNNEL；184416534613920 / 获取贡献者所属领域 / SEATUNNEL；187360620128160 / 清洗贡献者组织信息sdi_rd_efc_user_company表 / SQL    | raw_repo_contribute_info、raw_contrib_organize、sdi_rd_efc_user_company | 10240（2026-10-19 18:31）FAILURE 1m59s；10239（2026-10-19 10:27）SUCCESS 12m54s；10188（2026-10-10 10:29）SUCCESS 24m25s |
| 4   | [安全合规][job][raw]获取EulerMaker对应软件包信息              | 184538836850594 | ONLINE v3      | 184538836850592 / 获取EulerMaker软件包信息 / SEATUNNEL；184538836850593 / 清空代码仓EulerMaker / SQL                                                                       | sdi_rd_efc_euler_package（表尚未建）                                    | 10189（2026-10-10 11:51）SUCCESS 10s                                                                                     |
| 5   | [job][sdi]安全合规看板同步mongo漏洞数据                       | 184945723732896 | ONLINE v5      | 184945543936928 / 同步mongo漏洞数据 / SEATUNNEL                                                                                                                            | sdi_rd_efc_cve_details                                                  | 10212（2026-10-15 15:46）FAILURE 2m39s（唯一一次）                                                                       |
| 6   | [安全合规][job][raw]获取仓库保护分支禁止强制推送配置          | 184262810550177 | **OFFLINE** v3 | 1 个节点                                                                                                                                                                   | raw_repo_branch_protection                                              | 已废弃（T1a，2026-09-28 指标 8 改数据源）                                                                                |
| 7   | [安全合规][job][raw]获取代码仓Pull Request相关配置            | 184258879717280 | **OFFLINE** v3 | 1 个节点                                                                                                                                                                   | raw_repo_pr_setting                                                     | 已废弃（T1b，同上）                                                                                                      |

## 2. 被安全指标复用的通用任务

| Workflow                                           | Workflow Code   | 状态       | 用途                                                                                       | 实例情况               |
| -------------------------------------------------- | --------------- | ---------- | ------------------------------------------------------------------------------------------ | ---------------------- |
| [workflow][raw][gitcode]gitcode_PR评论信息获取任务 | 179281636229440 | ONLINE v2  | 指标 7 CODE_REVIEW / 指标 8 BRANCH_PROTECTION 复用 `/lgtm` 评论，落 raw_pr_comment_gitcode | **0 实例（从未执行）** |
| [job][raw][GitCode]获取gitcode pr评论信息          | 174699436039520 | ONLINE v23 | 同上，底层采集任务                                                                         | **0 实例（从未执行）** |

---

## 3. 设计要求但 beta 未建的任务

| 阶段     | 任务                                                                                                                                       | 设计编号 | 目标表                                                                    | 现状                   |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------- | ---------------------- |
| sdi 清洗 | 6 接口链路 sdi 建表 + 清洗                                                                                                                 | S1       | sdi_rd_efc_release / repo_contributor / repo_webhook / pr_review_reviewer | 无 DS 任务             |
| sdi 清洗 | commit 链路建表 + 采集 + 清洗                                                                                                              | S2       | raw_repo_commit_log / sdi_repo_commit_log                                 | 无 DS 任务，两表也未建 |
| sdi 清洗 | euler 清单清洗建表                                                                                                                         | S3       | sdi_rd_efc_euler_package                                                  | 无 DS 任务，表未建     |
| 指标计算 | PR 扫描（7 CODE_REVIEW + 10 CI_TESTS）                                                                                                     | D1       | dwi_rd_efc_security_pr_scan                                               | 无 DS 任务             |
| 指标计算 | 接口类指标（9 WEBHOOKS + 11 SIGNED_RELEASES + 18 CONTRIBUTORS）                                                                            | D2       | dwi_rd_efc_security_meta_api_scan                                         | 无 DS 任务             |
| 指标计算 | 项目维护（17 MAINTAINED）                                                                                                                  | D3       | dwi_rd_efc_security_maintained_scan                                       | 无 DS 任务             |
| 指标计算 | 仓库级汇聚 + 加权分 + 亮灯                                                                                                                 | D4       | dm_rd_efc_security_scan_score                                             | 无 DS 任务             |
| 指标计算 | 漏洞（16 VULNS）                                                                                                                           | D5       | dwi_rd_efc_security_vuln_scan                                             | 无 DS 任务             |
| 指标计算 | 项目级汇聚                                                                                                                                 | D6       | dm_rd_efc_security_project_score                                          | 无 DS 任务             |
| 指标计算 | 分支保护（8 BRANCH_PROTECTION）                                                                                                            | D7       | dwi_rd_efc_security_branch_protect_scan                                   | 无 DS 任务             |
| 文件扫描 | security_file_scan.py（COPYRIGHT / DANGEROUS_WF / TOKEN_PERM / BINARY_ARTIFACTS / BRANCH_PROTECTION / PACKAGING / SAST / SECURITY_POLICY） | P1       | dwi_rd_efc_security_file_scan                                             | 无 PYTHON 任务         |
| 文件扫描 | security_license_scan.py（scancode）                                                                                                       | P2       | dwi_rd_efc_security_license_scan                                          | 无 PYTHON 任务         |
| 明细     | 版权逐文件明细                                                                                                                             | —        | dwi_rd_efc_security_copyright_file_detail                                 | 无 DS 任务             |

结论：beta 目前只落地了「raw 采集层」的 4 条链路（webhook / release / contributors / euler），**sdi 清洗、全部指标计算 SQL、两个 Python 扫描脚本均未建 DS 任务**。

---

## 4. 调度现状

- 上述任务实例仅有 2026-10-10、10-15、10-19 三次零星触发，**没有看到每日实例**，判断为手动/临时执行。
- `ds_schedule_list` 接口返回 405（当前 DS 版本不支持），无法读取 cron 配置，调度需到 DS 页面确认。

## 5. 差异与风险（需注意）

1. 项目名：设计 `security_check_scoring` vs 现网 `openlibing`。
2. 设计称「6 接口任务已建」，实际**在线只有 4 条**；branch_protection、pr_setting 已 OFFLINE 废弃。
3. 发布签名任务内含 **PYTHON 节点**（185388365232032），非纯接口采集。
4. 贡献者任务最新版本新增 SQL 节点写 `sdi_rd_efc_user_company`，且 2026-10-19 18:31 那次 FAILURE。
5. 漏洞 mongo 同步任务存在，但唯一一次执行 FAILURE。
6. PR 评论两条任务 0 实例，指标 7/8 的评论数据实际尚未跑通。
7. euler 采集任务已跑通，但目标表 `sdi_rd_efc_euler_package` 尚未建。

## 6. 待确认

- 生产环境 DS 地址/凭证（当前 MCP 只配置了 beta 一个环境，无法核实生产任务）。
- 生产是否已有部分 SQL 指标任务。
- 是否需要按本清单补齐 beta/prod 的 S1/S2/S3、D1~D7、P1/P2 任务。
