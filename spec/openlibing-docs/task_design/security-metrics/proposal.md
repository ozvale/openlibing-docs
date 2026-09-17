# 代码安全检查评分看板 · 需求说明（proposal）

## 需求背景

安全合规团队对标 OpenSSF Scorecard 提出 18 项安全合规指标，需要在 openlibing-ops 平台建设"代码安全检查评分看板"，体系化评估公司内代码仓的安全合规水平。当前"1+6"数据源采集链路（6 个接口表 + commit 采集链路）的上游采集任务已在 DolphinScheduler 建好，sdi 层清洗 SQL 与 Python 扫描脚本亦已编写完毕，但尚未在 Doris 上执行落地，指标计算与汇聚 SQL 也待开发。

## 需求目标

1. **数据层落地**：在 Doris 上执行 sdi 层 6 张接口链路表的 DDL + 清洗 DML，完成 commit 链路（建表 + Python 脚本执行 + 清洗），建 euler 清单表。
2. **指标层落地**：分步开发 14 项可实现指标的 DWI 明细计算任务（SQL + Python），暂缓 4 项脚本挂起指标（5 PINNED_DEP / 8 BRANCH_PROTECTION / 13 FUZZING / 16 VULNS）在 DM 中恒为 NULL。
3. **汇聚层落地**：开发 DM 宽表 `dm_security_scan_score` 的汇聚 SQL，计算仓库级规则项加权总分、全部指标加权总分与亮灯。
4. **前端看板**：openlibing-ops-web 安全合规看板消费 DM 宽表数据，展示仓库得分、指标明细、亮灯状态。

## 范围

### 本期开发（14 项指标，权重合计 87.5）

| 编号 | 指标名       | metric_code         | 类型 | 权重 | 获取通道               |
| --- | --------- | ------------------- | -- | -- | ------------------ |
| 1   | 开源许可证     | `LICENSE`           | 规则 | 7.5 | Python scancode    |
| 2   | 版权合规      | `COPYRIGHT`         | 规则 | 10  | Python             |
| 3   | 危险工作流     | `DANGEROUS_WF`      | 规则 | 10  | Python             |
| 4   | 令牌权限      | `TOKEN_PERM`        | 规则 | 7.5 | Python             |
| 6   | 二进制制品     | `BINARY_ARTIFACTS`  | 规则 | 7.5 | Python             |
| 7   | 代码评审      | `CODE_REVIEW`       | 规则 | 7.5 | SQL                |
| 9   | Webhook 安全 | `WEBHOOKS`          | 规则 | 10  | SQL（接口→sdi）       |
| 10  | CI 测试     | `CI_TESTS`          | 规则 | 2.5 | SQL                |
| 11  | 发布签名      | `SIGNED_RELEASES`   | 建议 | 5   | SQL（接口→sdi）       |
| 12  | 软件包发布     | `PACKAGING`         | 规则 | 5   | Python + SQL（接口→sdi） |
| 14  | SAST      | `SAST`              | 建议 | 5   | Python             |
| 15  | 安全策略      | `SECURITY_POLICY`   | 规则 | 5   | Python             |
| 17  | 项目维护      | `MAINTAINED`        | 规则 | 2.5 | SQL                |
| 18  | 贡献者多样性    | `CONTRIBUTORS`      | 建议 | 2.5 | SQL（接口→sdi）       |

### 暂缓项（4 项，脚本开发挂起）

| 编号 | 指标名     | metric_code         | 暂缓原因                        | 恢复条件               |
| --- | ------- | ------------------ | --------------------------- | ------------------ |
| 5   | 依赖版本锁定  | `PINNED_DEP`       | openUBMC 社区支持未明确 + 识别项未补齐 | 上游确认后恢复            |
| 8   | 分支保护    | `BRANCH_PROTECTION` | token 权限不足 + 字段不补齐            | token 提权 + sdi 字段补全 |
| 13  | 模糊测试    | `FUZZING`          | 原生 fuzz 规则未细化                  | 规则明确后恢复            |
| 16  | 已知漏洞    | `VULNS`            | 漏洞视图表名待提供                   | C10 解决后恢复          |

## 验收标准

### 数据层（S1~S3）
- [ ] Doris 上成功创建 sdi_rd_efc_* 共 6 张接口链路 sdi 表（S1）
- [ ] sdi 清洗 DML 执行成功，raw 数据正确转换入 sdi 表（S1）
- [ ] commit 链路 raw_repo_commit_log + sdi_repo_commit_log 两表在 Doris 成功创建（S2）
- [ ] `代码仓commit扫描脚本.py` 在 DolphinScheduler 上能成功执行并写入 raw 表（S2）
- [ ] euler 清单表 sdi_rd_efc_euler_package 成功创建（S3）

### SQL 指标任务（D1~D4）
- [ ] D1：PR 评审 + CI 测试 → dwi_security_pr_scan 写入成功，score 值正确
- [ ] D2：Webhook + 发布签名 + 贡献者 → dwi_security_meta_api_scan 写入成功
- [ ] D3：项目维护 → dwi_security_maintained_scan 写入成功
- [ ] D4：dm_security_scan_score 宽表汇聚成功，暂缓项 5/8/13/16 恒为 NULL，加权分分母正确剔除 NULL 项

### Python 扫描脚本（P1~P2）
- [ ] P1：security_file_scan.py 能成功 clone 仓库并产出 7 个 metric_code 的扫描结果，写入 dwi_security_file_scan
- [ ] P2：security_license_scan.py（scancode）能成功扫描 LICENSE 文件并按阶梯规则打分，写入 dwi_security_license_scan

### 调度与联调
- [ ] DolphinScheduler 项目 security_check_scoring 的 04/05/06 三层任务编排完成，依赖关系正确
- [ ] 完整链路联调成功：从 raw 采集 → sdi 清洗 → dwi 指标 → dm 汇聚
- [ ] DM 宽表可被 openlibing-ops-web 前端看板正常读取展示

### 质量与可追溯
- [ ] 每项指标的 dwi 明细表含 detail_json 结构化明细，看板可下钻
- [ ] 同一批次所有指标使用统一 scan_time，便于批次溯源
- [ ] 历史批次数据全保留，覆盖时用 Unique Key UPSERT

## 关键约束

- **平台限定**：仅 gitcode，github/gitee 本期不做
- **仓库范围**：`sdi_rd_efc_repo_operate_conf` 且 `is_operated=1`
- **NA 语义**：score=NULL + is_na=1；汇聚时分子分母同时剔除权重
- **暂缓项**：dm 中恒为 NULL，汇聚分母自动剔除（同 NA 逻辑）
- **历史批次**：多次 scan_time 全保留，不覆盖
- **每批一致性**：一次扫描所有指标使用同一 scan_time

## 关联 Issue

- 待创建业务 Issue（openlibing-ops 仓）
