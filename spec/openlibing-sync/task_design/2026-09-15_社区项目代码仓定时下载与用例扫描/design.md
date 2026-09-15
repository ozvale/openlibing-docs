# 设计方案：社区项目代码仓定时下载与用例扫描

## 整体架构

复用 `openlibing-sync` 现有定时任务框架，新增一个 `CommunityRepoScanJob`：

```
┌─────────────────┐   CRON 触发   ┌──────────────────────────┐
│  Scheduler      │──────────────▶│ CommunityRepoScanJob     │
│ (已有 APSched)  │               │                          │
└─────────────────┘               │  1. 加载白名单            │
                                  │  2. 并发克隆仓            │
                                  │  3. 扫描用例              │
                                  │  4. 写入 Doris            │
                                  │  5. 清理工作区            │
                                  └──────────┬───────────────┘
                                             │
                                             ▼
                                  ┌──────────────────────────┐
                                  │  community_repo_scan     │
                                  │  community_testcase_sum  │
                                  │  (Doris)                 │
                                  └──────────────────────────┘
```

## 关键模块

### 1. 仓库白名单管理
- 配置来源：Doris 配置表 `community_repo_whitelist`
-  字段：`repo_url`、`branch`、`enabled`、`scan_priority`、`last_status`、`last_scan_at`
-  支持通过 API 增删改（复用 `openlibing-sync` 现有管理 API）

### 2. 克隆与刷新
- 优先使用 `git clone --depth 1 --branch <branch> <url>`
- 已存在目录：`git fetch --depth 1 origin <branch>` + `git checkout FETCH_HEAD`
- 超时：单仓默认 5 分钟，可配置
- 鉴权：私有仓通过 `secrets.GITCODE_TOKEN` 注入

### 3. 用例扫描引擎
- **方案 A（推荐）**：调用 `openlibing-pytest-executor` 的 REST API（需新开放 `scan_repository` 端点）
- **方案 B**：在 `openlibing-sync` 内嵌轻量扫描（仅做文件级统计与用例名解析）
- 输出字段：`test_file_count`、`testcase_count`、`skipped_count`、`avg_lines_per_case`、`namespaces[]`

### 4. 错误处理与重试
- 三层重试：
  - L1 任务级：单仓失败 → 标记 `last_status=failed`，下个周期优先重试（重试上限 3 次）
  - L2 调度级：CRON 任务整体失败 → 报警（邮件 / 钉钉）
  - L3 资源级：磁盘空间不足 → 暂停任务并发报警

### 5. 工作区管理
- 每次扫描使用独立目录：`/tmp/sync/repo-scan/<repo_id>-<scan_id>/`
- 扫描完成后立即清理（除非开启 `keep_workspace=true` 调试模式）
- 总磁盘占用上限：可配置（默认 20GB），超额时按 LRU 清理

## 数据模型

### `community_repo_scan_record`（Doris）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| scan_id | VARCHAR(64) | 单次扫描唯一 ID |
| repo_url | VARCHAR(512) | 仓库地址 |
| repo_id | VARCHAR(128) | 解析出的项目 ID |
| branch | VARCHAR(128) | 分支 |
| scan_at | DATETIME | 扫描时间 |
| status | VARCHAR(16) | success/failed/timeout |
| duration_ms | INT | 耗时 |
| error_msg | VARCHAR(1024) | 失败原因 |
| testcase_count | INT | 用例总数 |
| test_file_count | INT | 测试文件数 |

### `community_testcase_summary`（Doris）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| scan_id | VARCHAR(64) | 关联 scan_record |
| repo_id | VARCHAR(128) | 项目 ID |
| namespace | VARCHAR(256) | 命名空间 / 模块名 |
| testcase_count | INT | 用例数 |
| skipped_count | INT | 跳过数 |

## 安全与权限
- GitCode Token 通过 `secrets.*` 注入，禁止硬编码
- 扫描结果含代码仓库信息但不含代码内容，不存在敏感代码外泄风险
- Doris 表权限：写权限仅授予 `openlibing-sync` 服务账号

## 监控埋点
- `openlibing_sync_repo_scan_duration_seconds`（Histogram，按 repo 标签）
- `openlibing_sync_repo_scan_total`（Counter，按 status 标签）
- `openlibing_sync_repo_scan_testcase_total`（Counter，按 repo 标签）
- 失败 / 超时：单独 Counter + 报警