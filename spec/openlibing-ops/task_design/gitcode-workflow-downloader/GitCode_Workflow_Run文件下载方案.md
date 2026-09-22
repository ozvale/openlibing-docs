# GitCode Workflow Run 文件下载方案

| 项目 | 内容 |
|---|---|
| 方案目标 | 从 `sdi_rd_efc_workflow_run_raw_gitcode` 读取 workflow 文件信息，调用 GitCode Raw API 下载文件内容，并保存到固定路径 |
| 调度方式 | DolphinScheduler Shell 任务 |
| 数据来源表 | `sdi_rd_efc_workflow_run_raw_gitcode` |
| 下载记录表 | `sdi_rd_efc_workflow_run_file_gitcode` |
| Raw API | `GET https://raw.gitcode.com/{owner}/{repo}/raw/{head_sha}/{name}` |
| 落盘路径 | `openlibing/workflow/gitcode/$workflow_id/$workflow_run_id/$filename` |
| 回绑字段 | `repo_url`、`workflow_id`、`workflow_run_id` |

---

## 1. 方案结论

当前任务只需要完成一条直接链路：

```text
DolphinScheduler 定时触发
        ↓
Python 脚本读取 Doris 基础表
        ↓
从 repo_url 解析 owner / repo
        ↓
使用 head_sha + file_path 拼接 GitCode Raw URL
        ↓
HTTP GET 获取文件内容
        ↓
写入 openlibing/workflow/gitcode/$workflow_id/$workflow_run_id/$filename
        ↓
写入 sdi_rd_efc_workflow_run_file_gitcode 记录下载状态和本地文件路径
```

本方案不使用 SeaTunnel。SeaTunnel 更适合结构化数据同步，而这里的核心动作是“逐行读取数据库、发送 HTTP 请求、将响应内容写成机器文件”。DolphinScheduler 负责调度、重试和日志，Python 负责下载逻辑。

---

## 2. 基础表

基础表为 `sdi_rd_efc_workflow_run_raw_gitcode`：

```sql
CREATE TABLE `sdi_rd_efc_workflow_run_raw_gitcode` (
  `repo_url` varchar(512) NULL COMMENT '仓库链接',
  `workflow_id` varchar(32) NULL COMMENT 'workflow ID',
  `workflow_run_id` varchar(32) NULL COMMENT 'workflow 运行ID',
  `stage_id` varchar(32) NULL COMMENT '阶段ID',
  `job_id` varchar(32) NULL COMMENT '任务ID',
  `step_id` varchar(32) NULL COMMENT '步骤ID',
  `workflow_name` varchar(512) NULL COMMENT 'workflow 名称',
  `file_path` varchar(1024) NULL COMMENT 'workflow 文件路径',
  `title` varchar(1024) NULL COMMENT '标题',
  `status` varchar(16) NULL COMMENT '状态',
  `event` varchar(16) NULL COMMENT '触发事件',
  `run_number` int NULL COMMENT '运行编号',
  `head_branch` varchar(256) NULL COMMENT 'head分支',
  `head_sha` varchar(64) NULL COMMENT 'head SHA'
) ENGINE=OLAP
UNIQUE KEY(`repo_url`, `workflow_id`, `workflow_run_id`, `stage_id`, `job_id`, `step_id`)
COMMENT 'gitcode平台workflow信息表'
DISTRIBUTED BY HASH(`repo_url`) BUCKETS 10;
```

本方案直接使用基础表中的以下字段：

| 字段 | 用途 |
|---|---|
| `repo_url` | 解析 GitCode 仓库 `owner` 和 `repo`；同时作为下载记录表回绑字段 |
| `workflow_id` | 参与生成本地路径；同时作为下载记录表回绑字段 |
| `workflow_run_id` | 参与生成本地路径；同时作为下载记录表回绑字段 |
| `file_path` | 作为 Raw API 的文件路径参数 `name` |
| `head_sha` | 作为 Raw API 的 `head_sha` 参数 |

其他字段，例如 `workflow_name`、`status`、`event`、`run_number`、`head_branch`、`stage_id`、`job_id`、`step_id`，不进入下载记录表。如果后续查询需要这些信息，通过 `repo_url + workflow_id + workflow_run_id` 回连基础表获取。

---

## 3. 下载记录表

下载记录表为：

```text
sdi_rd_efc_workflow_run_file_gitcode
```

该表只保留必要字段：

1. 回绑基础表的三个字段；
2. 下载状态；
3. 本地文件路径。

### 3.1 推荐 DDL

```sql
CREATE TABLE IF NOT EXISTS `sdi_rd_efc_workflow_run_file_gitcode` (
  `repo_url` varchar(512) NULL COMMENT '仓库链接',
  `workflow_id` varchar(32) NULL COMMENT 'workflow ID',
  `workflow_run_id` varchar(32) NULL COMMENT 'workflow 运行ID',
  `download_status` varchar(16) NULL COMMENT '下载状态：SUCCESS/FAILED',
  `local_file_path` varchar(2048) NULL COMMENT '本地保存文件路径'
) ENGINE=OLAP
UNIQUE KEY(`repo_url`, `workflow_id`, `workflow_run_id`)
COMMENT 'GitCode workflow run 文件下载记录表'
DISTRIBUTED BY HASH(`repo_url`) BUCKETS 10
PROPERTIES (
  "replication_allocation" = "tag.location.default: 2",
  "min_load_replica_num" = "-1",
  "is_being_synced" = "false",
  "storage_medium" = "hdd",
  "storage_format" = "V2",
  "inverted_index_storage_format" = "V1",
  "enable_unique_key_merge_on_write" = "true",
  "light_schema_change" = "true",
  "disable_auto_compaction" = "false",
  "enable_single_replica_compaction" = "false",
  "group_commit_interval_ms" = "10000",
  "group_commit_data_bytes" = "134217728",
  "enable_mow_light_delete" = "false"
);
```

### 3.2 字段说明

| 字段 | 说明 |
|---|---|
| `repo_url` | 与基础表回绑 |
| `workflow_id` | 与基础表回绑；本地路径一级目录 |
| `workflow_run_id` | 与基础表回绑；本地路径二级目录 |
| `download_status` | 下载状态，建议值为 `SUCCESS` 或 `FAILED` |
| `local_file_path` | 文件最终保存路径 |

### 3.3 为什么不保留更多字段

`file_path`、`head_sha`、`workflow_name`、`head_branch`、`status` 等字段基础表中已经存在。下载记录表只负责说明某个 workflow run 的文件是否已经下载，以及下载到了哪里。需要更多上下文时，通过下面三个字段回连基础表：

```text
repo_url + workflow_id + workflow_run_id
```

---

## 4. 一个 workflow_run_id 对应一个文件

本方案遵循一个约束：

```text
一个 workflow_run_id 对应一个下载文件
```

因此本地路径可以固定为：

```text
openlibing/workflow/gitcode/$workflow_id/$workflow_run_id/$filename
```

如果机器保存根目录为 `/data`，则最终路径为：

```text
/data/openlibing/workflow/gitcode/$workflow_id/$workflow_run_id/$filename
```

例如：

```text
/data/openlibing/workflow/gitcode/10001/90000001/build.yml
/data/openlibing/workflow/gitcode/10001/90000002/deploy.yaml
```

---

## 5. 文件名生成规则

`filename` 从基础表的 `file_path` 取最后一段：

```python
filename = os.path.basename(file_path.lstrip('/'))
```

示例：

| `file_path` | `filename` |
|---|---|
| `/.gitcode/workflows/build.yml` | `build.yml` |
| `.gitcode/workflows/deploy.yaml` | `deploy.yaml` |
| `/workflow.yml` | `workflow.yml` |

如果 `file_path` 为空或最后一段取不到文件名，兜底使用：

```text
workflow_file.yml
```

---

## 6. GitCode Raw URL 拼接规则

GitCode Raw API 格式：

```http
GET https://raw.gitcode.com/{owner}/{repo}/raw/{head_sha}/{name}
```

字段映射如下：

| API 参数 | 来源字段 | 处理方式 |
|---|---|---|
| `owner` | `repo_url` | 从仓库 URL 解析 |
| `repo` | `repo_url` | 从仓库 URL 解析，去掉 `.git` 后缀 |
| `head_sha` | `head_sha` | 直接使用 |
| `name` | `file_path` | 去掉前导 `/` 后使用 |

示例：

```text
repo_url  = https://gitcode.com/openlibing/workflow.git
head_sha  = 8a1b2c3d4e5f
file_path = /.gitcode/workflows/build.yml
```

拼接后的 URL：

```text
https://raw.gitcode.com/openlibing/workflow/raw/8a1b2c3d4e5f/.gitcode/workflows/build.yml
```

仓库解析逻辑：

```python
import re

pattern = r"gitcode\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$"
match = re.search(pattern, repo_url.strip())
owner = match.group(1)
repo = match.group(2)
```

---

## 7. 待读取 SQL

### 7.1 基础读取 SQL

```sql
SELECT
    repo_url,
    workflow_id,
    workflow_run_id,
    head_sha,
    file_path
FROM sdi_rd_efc_workflow_run_raw_gitcode
WHERE repo_url IS NOT NULL
  AND workflow_id IS NOT NULL
  AND workflow_run_id IS NOT NULL
  AND head_sha IS NOT NULL
  AND file_path IS NOT NULL
LIMIT 1000;
```

### 7.2 排除已下载成功记录

生产任务建议排除已经成功下载的记录：

```sql
SELECT
    t.repo_url,
    t.workflow_id,
    t.workflow_run_id,
    t.head_sha,
    t.file_path
FROM sdi_rd_efc_workflow_run_raw_gitcode t
LEFT JOIN sdi_rd_efc_workflow_run_file_gitcode r
  ON t.repo_url = r.repo_url
 AND t.workflow_id = r.workflow_id
 AND t.workflow_run_id = r.workflow_run_id
WHERE t.repo_url IS NOT NULL
  AND t.workflow_id IS NOT NULL
  AND t.workflow_run_id IS NOT NULL
  AND t.head_sha IS NOT NULL
  AND t.file_path IS NOT NULL
  AND (r.download_status IS NULL OR r.download_status <> 'SUCCESS')
LIMIT 1000;
```

该 SQL 会选出：

- 从未下载过的记录；
- 或者曾下载失败、需要重新处理的记录。

---

## 8. 下载脚本核心逻辑

### 8.1 依赖

```bash
pip install requests pymysql
```

Doris 兼容 MySQL 协议，Python 可以通过 `pymysql` 连接 Doris FE。

### 8.2 核心 Python 逻辑

```python
import os
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_SAVE_ROOT = "/data"
RELATIVE_ROOT = "openlibing/workflow/gitcode"
CONCURRENCY = 8
TIMEOUT = 30
MAX_RETRIES = 3


def parse_repo_url(repo_url):
    m = re.search(r"gitcode\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url.strip())
    if not m:
        raise ValueError(f"无法解析 repo_url: {repo_url}")
    return m.group(1), m.group(2)


def build_download_url(repo_url, head_sha, file_path):
    owner, repo = parse_repo_url(repo_url)
    name = file_path.lstrip("/")
    return f"https://raw.gitcode.com/{owner}/{repo}/raw/{head_sha}/{name}"


def get_file_name(file_path):
    name = os.path.basename(file_path.lstrip("/"))
    return name or "workflow_file.yml"


def build_local_path(workflow_id, workflow_run_id, file_path):
    filename = get_file_name(file_path)
    return os.path.join(
        BASE_SAVE_ROOT,
        RELATIVE_ROOT,
        workflow_id,
        workflow_run_id,
        filename
    )


def download_one(row):
    repo_url = row["repo_url"]
    workflow_id = row["workflow_id"]
    workflow_run_id = row["workflow_run_id"]
    head_sha = row["head_sha"]
    file_path = row["file_path"]

    download_url = build_download_url(repo_url, head_sha, file_path)
    local_file_path = build_local_path(workflow_id, workflow_run_id, file_path)
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

    download_status = "FAILED"

    for i in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(download_url, timeout=TIMEOUT)
            resp.raise_for_status()
            with open(local_file_path, "wb") as f:
                f.write(resp.content)
            download_status = "SUCCESS"
            break
        except Exception:
            time.sleep(min(2 ** i, 30))

    return {
        "repo_url": repo_url,
        "workflow_id": workflow_id,
        "workflow_run_id": workflow_run_id,
        "download_status": download_status,
        "local_file_path": local_file_path,
    }
```

### 8.3 写入下载记录表

```python
def write_results(conn, results):
    sql = """
        INSERT INTO sdi_rd_efc_workflow_run_file_gitcode
        (
            repo_url,
            workflow_id,
            workflow_run_id,
            download_status,
            local_file_path
        )
        VALUES
        (
            %(repo_url)s,
            %(workflow_id)s,
            %(workflow_run_id)s,
            %(download_status)s,
            %(local_file_path)s
        )
    """
    with conn.cursor() as cur:
        cur.executemany(sql, results)
    conn.commit()
```

Doris Unique Key 表开启 Merge-on-Write 后，同一组：

```text
repo_url + workflow_id + workflow_run_id
```

重复写入会更新旧记录，适合失败重试后覆盖下载状态。

---

## 9. DolphinScheduler 集成

使用 DolphinScheduler 的 Shell 节点：

```bash
cd /opt/gitcode-workflow-downloader

python download_gitcode_workflow_files.py \
  --doris-host ${DORIS_HOST} \
  --doris-port ${DORIS_PORT} \
  --doris-user ${DORIS_USER} \
  --doris-password ${DORIS_PASSWORD} \
  --doris-db ${DORIS_DB} \
  --base-save-root /data \
  --relative-root openlibing/workflow/gitcode \
  --batch-size 1000 \
  --concurrency 8
```

DolphinScheduler 参数建议：

| 参数 | 建议值 |
|---|---|
| 任务类型 | Shell |
| 调度周期 | 每 10~30 分钟一次 |
| 任务超时 | 30~60 分钟 |
| 失败重试次数 | 2 |
| 失败重试间隔 | 3~5 分钟 |
| Worker 分组 | 指定可以写 `/data/openlibing/workflow/gitcode` 的 Worker |
| 告警 | 任务失败时通知负责人 |

---

## 10. 运行流程

```text
1. DolphinScheduler 触发 Shell 节点
2. Python 连接 Doris
3. 查询 sdi_rd_efc_workflow_run_raw_gitcode
4. 排除 sdi_rd_efc_workflow_run_file_gitcode 中已 SUCCESS 的记录
5. 拼接 GitCode Raw URL
6. HTTP GET 下载文件内容
7. 保存到 /data/openlibing/workflow/gitcode/$workflow_id/$workflow_run_id/$filename
8. 将 repo_url、workflow_id、workflow_run_id、download_status、local_file_path 写入结果表
9. 下一轮调度继续处理未成功或新增记录
```

---

## 11. 回绑查询

需要查看完整信息时，下载记录表连基础表即可：

```sql
SELECT
    t.repo_url,
    t.workflow_id,
    t.workflow_run_id,
    t.workflow_name,
    t.file_path,
    t.head_sha,
    t.status,
    t.event,
    t.run_number,
    t.head_branch,
    r.download_status,
    r.local_file_path
FROM sdi_rd_efc_workflow_run_raw_gitcode t
LEFT JOIN sdi_rd_efc_workflow_run_file_gitcode r
  ON t.repo_url = r.repo_url
 AND t.workflow_id = r.workflow_id
 AND t.workflow_run_id = r.workflow_run_id
LIMIT 100;
```

查看下载状态分布：

```sql
SELECT download_status, COUNT(*)
FROM sdi_rd_efc_workflow_run_file_gitcode
GROUP BY download_status;
```

查看待下载数量：

```sql
SELECT COUNT(*)
FROM sdi_rd_efc_workflow_run_raw_gitcode t
LEFT JOIN sdi_rd_efc_workflow_run_file_gitcode r
  ON t.repo_url = r.repo_url
 AND t.workflow_id = r.workflow_id
 AND t.workflow_run_id = r.workflow_run_id
WHERE t.repo_url IS NOT NULL
  AND t.workflow_id IS NOT NULL
  AND t.workflow_run_id IS NOT NULL
  AND t.head_sha IS NOT NULL
  AND t.file_path IS NOT NULL
  AND (r.download_status IS NULL OR r.download_status <> 'SUCCESS');
```

---

## 12. 路径和权限

在 DolphinScheduler Worker 机器上提前创建目录：

```bash
mkdir -p /data/openlibing/workflow/gitcode
chown -R dolphinscheduler:dolphinscheduler /data/openlibing/workflow/gitcode
chmod -R 755 /data/openlibing/workflow/gitcode
```

如果实际运行用户不是 `dolphinscheduler`，替换为实际用户。

---

## 13. 错误处理

| 问题 | 原因 | 处理 |
|---|---|---|
| 404 | `head_sha` 不存在或 `file_path` 不存在 | 写入 `download_status='FAILED'` |
| 403 | 私有仓库或限流 | 增加 token 或降低并发 |
| 429 | 请求过多 | 降低 `concurrency`，增加重试间隔 |
| Timeout | 网络不稳定 | 脚本重试，DS 任务也重试 |
| 写文件失败 | 目录权限不足或磁盘满 | 检查 Worker 目录权限和磁盘空间 |
| Doris 写入失败 | 连接异常或表结构不匹配 | 记录日志，任务失败后由 DS 重试 |

由于结果表不保留错误详情，如果需要追踪错误原因，建议通过 DolphinScheduler 日志查看。若后续需要长期保存错误详情，可以再扩展 `err_msg` 字段。

---

## 14. 最终方案摘要

最终方案固定为：

```text
DolphinScheduler Shell 调度
+ Python requests 下载
+ Doris 读取 sdi_rd_efc_workflow_run_raw_gitcode
+ GitCode Raw API 获取文件内容
+ 文件保存到 openlibing/workflow/gitcode/$workflow_id/$workflow_run_id/$filename
+ 下载记录写入 sdi_rd_efc_workflow_run_file_gitcode
```

结果表最小字段为：

```text
repo_url
workflow_id
workflow_run_id
download_status
local_file_path
```

回绑关系固定为：

```text
repo_url + workflow_id + workflow_run_id
```

其它信息全部通过连基础表 `sdi_rd_efc_workflow_run_raw_gitcode` 获取。