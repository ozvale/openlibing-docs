# openlibing-ops 代码仓 commit + 版权合规扫描指标 ETL 整体方案

> 仓库范围：openlibing-ops（数据链路：DolphinScheduler → Doris）
> 文档定位：分层框架 + 指标/表/脚本归属 + 明细 + 汇总
> 生成时间：2026-09-12

---

## 一、目标

统一梳理「代码仓扫描」类指标的采集与加工链路，做到：

1. **同源数据共用一个采集脚本、一个明细表**，避免每指标各写一套拉取克隆逻辑。
2. 按 **raw → sdi → dwi/dm** 分层，明确每层存什么明细、如何汇总。
3. 支持每天增量调度，首次全量、后续按时间窗口增量且防丢，重复扫描自动覆盖不堆积。

---

## 二、分层架构

```text
DolphinScheduler（每天定时）
   │
   ├──① commit 采集脚本（git log）        → raw_repo_commit_log
   │        │
   │        └── SQL 清洗（作者规范化）    → sdi_repo_commit_log
   │                       │
   │                       └── 汇总 SQL  → dwi/dm（commit 指标）
   │
   └──② 仓库扫描脚本（文件/语言/版权）   → raw_repo_quality_scan
            │
            └── SQL 清洗/汇总            → sdi / dwi（代码仓质量指标，含版权合规）
```

**架构原则（「共用一个脚本、共用一个表」的落点）**

- **commit 类指标**（提交数、作者、活跃度）共用 `commit 采集脚本`，明细统一落 `raw_repo_commit_log`。
- **仓库文件类指标**（代码质量、版权合规声明）共用 `代码仓拉取脚本`，明细统一落 `raw_repo_quality_scan` 的 `data_json`。
- 版权合规属文件级扫描，**复用质量扫描链路的 clone 框架**，作为质量扫描的一个指标项计入，不单独拉仓库。

---

## 三、指标清单与归属

| #      | 指标名                                     | 类型      | 所属链路     | 数据来源                 | 明细位置                            |
| ------ | ------------------------------------------ | --------- | ------------ | ------------------------ | ----------------------------------- |
| 1-15   | 代码仓质量扫描指标（代码风格/质量/语言等） | 文件级    | 质量扫描     | clone 仓库扫描           | raw_repo_quality_scan.data_json     |
| 16     | commit 提交数 / 作者 / 活跃度              | commit 级 | commit 采集  | git log                  | raw_repo_commit_log                 |
| **17** | **版权合规声明扫描**                       | 文件级    | **质量扫描** | clone 仓库按后缀遍历文件 | **raw_repo_quality_scan.data_json** |

### 指标 17：版权合规声明扫描（补充）

**口径**：扫描固定后缀文件，判断是否包含版权合规声明。

- **后缀白名单**：`.go` `.java` `.py` `.js` `.c` `.cpp` `.rs` `.ts` `.sh` `.bat`
- **合规声明模板**（匹配规则）：
  - 固定文本：`Copyright(c) ` + **四位数字年份**（`\d{4}`，任何四位年份均可）+ ` Huawei Technologies Co.`
  - 即正则：`Copyright\(c\)\s+\d{4}\s+Huawei Technologies Co\.`
- **判定**：文件内容命中上述正则 → 该文件有合规声明；未命中 → 无。
- **汇总产物**（指标口径，供 dwi/dm 层使用）：
  - `copyright_files_count`：有合规声明的文件数
  - `total_files_count`：后缀白名单内被扫描文件总数
  - `copyright_compliance_ratio`：合规覆盖率 = 有声明文件数 / 白名单文件总数
- **注意**：`Copyright(c)` 与 `Huawei Technologies` 之间可含空格差异（`2026 Huawei`），但年份固定 4 位数字；跨版本扫描建议用 `\s+` 容忍空白变化。

---

## 四、表设计

### 4.1 raw 层（采集原样落地，一行一次扫描）

**表 A：`raw_repo_commit_log`**

- 粒度：`repo_id + branch_name + commit_hash`（天然唯一）
- 明细字段：repo_id / repo_git_url / repo_name / branch_name / commit_hash / author_name / author_email / commit_time / commit_title / scan_time
- 模型：`UNIQUE KEY (repo_id, branch_name, commit_hash)` → 重复扫描自动覆盖，不堆积
- 文件：[create_raw_repo_commit_log.sql](../../docs/0912/create_raw_repo_commit_log.sql)

**表 B：`raw_repo_quality_scan`**（既有）

- 粒度：`repo_id + branch_name` 一次扫描一行
- 明细：repo_id / repo_git_url / repo_name / branch_name / scan_time / **data_json**（JSON 存该次全部文件级扫描指标，覆盖代码风格、质量、以及本次新增的「版权合规」块）
- 模型：DUPLICATE KEY（历史可回溯，最新一次以 scan_time 取）
- 版权合规作为新指标块加入 `data_json`，结构示例：
  ```json
  "copyright": {
      "total_files_count": 120,
      "copyright_files_count": 105,
      "compliance_ratio": 0.875,
      "scan_suffixes": [".go", ".java", ".py", ".js", ".c", ".cpp", ".rs", ".ts", ".sh", ".bat"],
      "detail": "OK"
  }
  ```
  建表参考：[create_raw_repo_quality_scan.sql](../../docs/202606/create_raw_repo_quality_scan.sql)

### 4.2 sdi 层（简单加工、规范化，供下游复用）

**表 C：`sdi_repo_commit_log`**

- 粒度：与 raw 一致 `repo_id + branch_name + commit_hash`
- 内容：raw 明细 + 作者规范化派生列
  - `author_username`（邮箱 @ 前缀）、`author_domain`（邮箱域名）、`author_name_clean`（trim+合并空白，空回退 unknown）、`is_bot`（0/1/2）
- 模型：UNIQUE KEY 覆盖
- 文件：[create_sdi_repo_commit_log.sql](../../docs/0912/create_sdi_repo_commit_log.sql) + [清洗 SQL](../../docs/0912/clean_to_sdi_repo_commit_log.sql)
- 说明：版权合规属文件级细颗粒，不在此 sdi 表，保留在质量扫描 data_json；如需结构化可另建 `sdi_repo_copyright`（按 repo 一行，含三栏合规指标）。

### 4.3 汇总层（dwi/dm，按日聚合，供 API/前端查询）

**表 D：`dwi_repo_commit_stat_day`（建议新建）**

- 粒度：`repo_id + branch_name + data_time`
- 明细：commit_count / active_author_count / bot_commit_count / avg_commit_per_author / latest_commit_time / first_commit_time
- 汇总来源：`sdi_repo_commit_log`（按 commit_time 日期 + author 去重）
- **占位说明**：当前「指标只需分层框架」，此表列出但暂不出明细 SQL，待指标确认后补。

**表 E：`dwr/dm 代码仓质量日汇总`**（建议新建，覆盖版权合规）

- 粒度：`repo_id + data_time`
- 明细：`copyright_files_count` / `total_files_count` / `copyright_compliance_ratio`（从 raw_repo_quality_scan 最新扫描的 data_json 解出）
- 汇总来源：`raw_repo_quality_scan.data_json.copyright`

---

## 五、脚本设计

### 5.1 commit 采集脚本（共用脚本①）

- 文件：[代码仓commit扫描脚本.py](../../docs/0912/代码仓commit扫描脚本.py)
- 复用原质量拉取脚本的框架：
  1. 接收 repo_url / auth_login / auth_token / repo_id / show_branch / `since`（调度参数传入）
  2. 复用处理脚本预 clone 的仓库，同步到 show_branch
  3. `git log --pretty` 抓 commit 基础元数据
  4. 批量写 `raw_repo_commit_log`
- **增量策略**：首次 since 传空=全量；每日传「当天前推 4 天（3 天 + 1 天缓冲防丢）」；UNIQUE KEY 自动覆盖同键。

### 5.2 仓库质量/版权扫描脚本（共用脚本②，扩展现有质量拉取脚本）

- 文件：[代码仓拉取脚本.py](../../docs/0912/代码仓拉取脚本.py)（现有，作基座）
- **新增版权合规扫描函数**（复用其 clone + 分支同步框架）：
  ```python
  COPYRIGHT_SUFFIXES = ['.go', '.java', '.py', '.js', '.c', '.cpp', '.rs', '.ts', '.sh', '.bat']
  COPYRIGHT_RE = re.compile(r'Copyright\(c\)\s+\d{4}\s+Huawei Technologies Co\.')

  def check_copyright(repo_path):
      total = 0; matched = 0
      for root, _dirs, files in os.walk(repo_path):
          for f in files:
              ext = os.path.splitext(f)[1].lower()
              if ext in COPYRIGHT_SUFFIXES:
                  total += 1
                  fp = os.path.join(root, f)
                  try:
                      with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                          if COPYRIGHT_RE.search(fh.read()):
                              matched += 1
                  except Exception:
                      pass
      ratio = round(matched / total, 4) if total else 0
      return {"total_files_count": total, "copyright_files_count": matched,
              "compliance_ratio": ratio, "scan_suffixes": COPYRIGHT_SUFFIXES}
  ```
- 结果并入 `raw_repo_quality_scan.data_json.copyright` 写入既有表。（或按 4.2 说明另建 sdi 表）

---

## 六、汇总方式（如何汇总）

| 层级       | 汇总逻辑                                                                                          | 产出表                   |
| ---------- | ------------------------------------------------------------------------------------------------- | ------------------------ |
| raw→sdi    | INSERT INTO ... SELECT，UNIQUE KEY 覆盖；作者规范化（邮箱拆 username/domain、is_bot、name_clean） | sdi_repo_commit_log      |
| sdi→dwi    | 按 `commit_time` 日期 + repo/branch 聚合：count、去重作者数、bot 占比、人均                       | dwi_repo_commit_stat_day |
| raw→dwr/dm | 解 data_json.copyright，按 repo + 最新 scan_time 汇总覆盖率                                       | 质量日汇总表             |

- commit 汇总 SQL 主体为 `GROUP BY repo_id, branch_name, DATE(commit_time)`，配合 `COUNT(DISTINCT author_username)` 计算活跃作者、`SUM(is_bot=1)` 计算机器人提交、`COPYRIGHT` 用 `data_json` 解码统计覆盖率。
- 版权合规覆盖率口径直接来自扫描脚本统计的 `copyright_files_count / total_files_count`，汇总层无需重算，仅透传。

---

## 七、增量与防丢策略（统一）

- 每天 1 次，首次跑全量（since 空 / clone 全量扫描）。
- 增量窗口 = 上次扫描点前推 **4 天**（3 天正常 + 1 天缓冲），防调度偶发漏跑。
- **覆盖而非堆积**：
  - commit → UNIQUE KEY(repo_id, branch_name, commit_hash)（同键替换，值不可变，无副作用）
  - 质量扫描 → 保留历史，最新一次以 scan_time 取，或按需分区清理
- 重复区间写入，靠键去重天然防数据重复脏读。

---

## 八、待确认 / 后续迭代项

- [ ] 指标 1-15 是否需在本方案内展开明细（当前只列共用的分层框架）。
- [ ] 版权合规：直接并入 `raw_repo_quality_scan.data_json` 还是另建 `raw_repo_copyright_scan` 独立表（同 clone 复用、不同表）——取决于下游是否要独立深度检索。
- [ ] dwi/dm 两款汇总表的字段、口径、以及是否还需要按「作者」维度的汇总层。
- [ ] 版权扫描的 `Copyright(c)` 是否区分大小写、是否需要匹配 `Huawei Technologies Co., Ltd.` 等变体（当前按最精模板，其他全匹配）。
