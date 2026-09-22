# Design: skill-market-sync

**Change ID**: skill-market-sync

## Architecture Overview

三个独立功能模块，互不依赖，可并行开发：

```
┌─────────────────────────────────────────────────┐
│                   FastAPI App                     │
├─────────────┬──────────────┬────────────────────┤
│  Feature 1  │  Feature 2   │    Feature 3       │
│ File Tree   │  Sync        │  Admin Auth        │
│ URLs        │  Service     │  Removal           │
├─────────────┼──────────────┼────────────────────┤
│ schemas/    │ services/    │ routers/           │
│ skill.py    │ sync_service │ admin.py           │
│             │ .py          │                    │
│ routers/    │ utils/       │ (auth.py 删除)     │
│ skills.py   │ remote_      │                    │
│             │ fetcher.py   │                    │
│ utils/      │ models/      │                    │
│ platform.py │ sync_task.py │                    │
│ (复用)      │              │                    │
└─────────────┴──────────────┴────────────────────┘
```

## Feature 1: File Tree URLs

### Data Model

```python
class FileTreeItem(BaseModel):
    path: str
    url: str

class SkillDetail(SkillListItem):
    # ... existing fields ...
    fileTree: list[str] | None = None
    fileTreeWithUrls: list[FileTreeItem] | None = None  # NEW
```

### URL Construction Logic

1. 从 `sourceUrl` 解析出 `platform`, `owner`, `repo`, `branch`, `dirPath`
2. 复用 `platform.py` 的 `parse_source_url()` 获取仓库信息
3. 从 `sourceUrl` 提取 SKILL.md 所在目录的相对路径
4. 为 `fileTree` 中每个文件路径拼接完整 URL：
   - GitHub: `https://github.com/{owner}/{repo}/blob/{branch}/{dirPath}/{filePath}`
   - GitCode: `https://gitcode.com/{owner}/{repo}/blob/{branch}/{dirPath}/{filePath}`

### API Change

`GET /api/skills/{name}` 响应新增 `fileTreeWithUrls` 字段，前端可选择性使用。

## Feature 2: Sync Service

### Components

1. **SyncTask Model** — 数据库表，分布式锁 + 同步历史
2. **RemoteFetcher** — 封装 GitHub/GitCode Raw API 调用
3. **SyncService** — 同步核心逻辑
4. **EmailService** — SMTP 邮件通知
5. **APScheduler** — 定时任务调度

### SyncTask Table

```sql
CREATE TABLE ai_agent_sync_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,      -- 'running', 'completed', 'failed'
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    result_summary TEXT,               -- JSON
    instance_id VARCHAR(128),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_sync_task_running 
    ON ai_agent_sync_tasks (task_type, status) 
    WHERE status = 'running';
```

> 注意：MySQL 不支持 partial index，改用应用层逻辑：INSERT 前先 SELECT 检查是否有 running 记录。

### RemoteFetcher

```python
class RemoteFetcher:
    async def fetch_file_content(self, source_url: str) -> str | None
    async def fetch_directory_tree(self, source_url: str) -> list[str] | None
    async def fetch_readme(self, source_url: str) -> str | None
```

**GitHub Raw URL**: `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
**GitCode Raw URL**: `https://gitcode.com/{owner}/{repo}/raw/{branch}/{path}`

**GitHub Contents API**: `GET https://api.github.com/repos/{owner}/{repo}/contents/{dir}?ref={branch}`
**GitCode Contents API**: `GET https://api.gitcode.com/api/v5/repos/{owner}/{repo}/contents/{dir}?ref={branch}&access_token={token}`

### Exponential Backoff Retry

当调用 GitHub/GitCode API 遇到超时或限流（HTTP 429/5xx）时，采用指数退避 + 随机抖动重试：

```python
import random

RETRY_DELAYS = {
    "timeout": [10, 30, 60],       # 超时：10s → 30s → 60s
    "server_error": [10, 30, 60],  # 5xx：10s → 30s → 60s
    "rate_limited": [30, 90, 120], # 429：30s → 90s → 120s
}

def _get_retry_delay(self, retry_type: str, attempt: int) -> float:
    base = RETRY_DELAYS[retry_type][attempt]
    jitter = base * 0.25 * (random.random() * 2 - 1)  # ±25% 抖动
    return max(1, base + jitter)

async def _request_with_retry(self, url: str, max_retries: int = 3) -> Response:
    for attempt in range(max_retries + 1):
        try:
            response = await client.get(url, timeout=30)
            if response.status_code == 429:
                if attempt == max_retries:
                    raise RateLimitError(f"Rate limited after {max_retries} retries")
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    delay = int(retry_after)
                else:
                    delay = self._get_retry_delay("rate_limited", attempt)
                await asyncio.sleep(delay)
                continue
            if response.status_code >= 500:
                if attempt == max_retries:
                    raise ServerError(f"Server error after {max_retries} retries")
                await asyncio.sleep(self._get_retry_delay("server_error", attempt))
                continue
            return response
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == max_retries:
                raise
            await asyncio.sleep(self._get_retry_delay("timeout", attempt))
    return response
```

- 超时 / 5xx：10s → 30s → 60s（服务端短暂故障通常 1-2 分钟内恢复）
- 429 限流：30s → 90s → 120s（限流窗口较长，需更多等待时间）
- 429 响应优先使用 `Retry-After` header 指定的等待时间
- 每次等待加入 ±25% 随机抖动，防止多实例同时重试造成惊群效应
- 最多重试 3 次（共 4 次请求），超过后抛出异常，该 Skill 标记为"更新失败"

### Sync Flow

```
APScheduler 触发 (每天凌晨1点)
    │
    ▼
尝试获取分布式锁 (INSERT sync_task)
    │
    ├─ 失败 → 跳过（其他实例在执行）
    │
    ▼ 成功
从数据库获取所有有 source_url 的 Skill
    │
    ▼
遍历每个 Skill:
    ├─ 通过 RemoteFetcher 拉取最新 SKILL.md
    ├─ 拉取最新文件树
    ├─ 拉取最新 README.md
    ├─ 对比内容是否有变化
    │   ├─ 有变化 → 更新数据库
    │   └─ 无变化 → 跳过
    └─ 外部文件 404 → 标记为"过时"
    │
    ▼
汇总同步结果
    │
    ▼
通过 SMTP 发送邮件给管理员
    │
    ▼
更新 sync_task 状态为 completed
```

### Distributed Lock Logic

采用**任务级粗粒度锁**：每天只允许一个实例执行同步任务，该实例负责同步所有 Skill。其他实例跳过，不参与同步。

#### 为什么选择粗粒度锁而非细粒度锁

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **粗粒度锁（当前方案）** | 任务级锁，一个实例同步全部 Skill | 实现简单；天然避免同一 Skill 被重复更新；API 请求集中在一个实例，便于控制限流 | 单实例承担全部负载；实例中途崩溃需等待 2 小时超时 |
| 细粒度锁（Per-Skill） | 每个 Skill 一把锁，多实例可并行同步不同 Skill | 负载分散；单 Skill 失败不影响其他 | 实现复杂（需 work-queue 或 skill_lock 表）；多实例并发请求 API 加剧限流风险；需协调邮件汇总 |

**选择粗粒度锁的理由：**

1. **Skill 数量有限**：当前 Skill 数量在几十到几百级别，单实例串行同步完全可在 1-2 小时内完成
2. **API 限流是主要瓶颈**：GitHub 未认证 60 次/小时，认证 5000 次/小时。多实例并发反而会更快耗尽配额
3. **实现简单可靠**：无需复杂的任务分发和结果聚合，一个实例从头到尾串行执行即可
4. **数据一致性**：单实例串行更新，不存在两个实例同时写同一 Skill 的问题

#### 锁获取流程

```
实例 A (凌晨1点触发)          实例 B (凌晨1点触发)
        │                            │
        ▼                            ▼
  SELECT sync_task                SELECT sync_task
  WHERE status='running'         WHERE status='running'
        │                            │
        ▼ 无 running 记录            ▼ 无 running 记录
  INSERT sync_task               INSERT sync_task
  (status='running')             (status='running')
        │                            │
        ▼ INSERT 成功                 ▼ INSERT 失败（唯一索引冲突）
  执行同步全部 Skill                   │
        │                            ▼
        ▼                       SELECT sync_task
  更新 status='completed'       WHERE status='running'
                                      │
                                      ▼ 发现实例 A 的记录
                                   跳过，不执行同步
```

> **关键**：即使两个实例同时 SELECT 未发现 running 记录，唯一索引保证只有一个 INSERT 成功，另一个抛出唯一约束异常，从而确保只有一个实例执行同步。

#### 锁获取代码

```python
async def acquire_sync_lock(session, instance_id):
    # 1. 检查是否有 running 状态的记录
    running = await session.execute(
        select(SyncTask).where(
            SyncTask.task_type == "skill_sync",
            SyncTask.status == "running"
        )
    )
    existing = running.scalars().first()
    
    if existing:
        # 2. 死锁兜底：超过2小时视为死锁，允许接管
        if (datetime.utcnow() - existing.started_at).total_seconds() > 7200:
            existing.status = "failed"
            existing.result_summary = json.dumps({"error": "deadlock_timeout"})
            existing.completed_at = datetime.utcnow()
            await session.flush()
            # 继续往下创建新记录
        else:
            return None  # 其他实例在执行，跳过
    
    # 3. 创建新的同步任务记录（唯一索引保证只有一个实例成功）
    task = SyncTask(
        task_type="skill_sync",
        status="running",
        started_at=datetime.utcnow(),
        instance_id=instance_id,
    )
    session.add(task)
    try:
        await session.commit()
        return task
    except IntegrityError:
        # 唯一索引冲突，说明另一个实例已抢先插入
        await session.rollback()
        return None
```

#### 同步过程中的容错

单实例串行同步时，单个 Skill 失败不影响其他 Skill：

```
同步 Skill 列表: [A, B, C, D, E]
                    │
    ├─ A: 成功更新 ✓
    ├─ B: API 超时，重试3次仍失败 → 记录为"更新失败"，继续下一个
    ├─ C: 无变化 → 跳过
    ├─ D: 404 → 标记为"过时"，继续下一个
    └─ E: 成功更新 ✓
                    │
                    ▼
    汇总结果 → 发送邮件 → 更新 sync_task 为 completed
```

#### 实例崩溃恢复

| 场景 | 处理方式 |
|------|---------|
| 实例在同步过程中崩溃 | `sync_task` 记录保持 `running` 状态，2 小时后新实例检测到超时，标记为 `failed` 并接管 |
| 实例在同步完成后、更新状态前崩溃 | 同上，2 小时超时后重新执行（幂等，重复同步无副作用） |
| 实例在发送邮件前崩溃 | 同步结果已写入 `sync_task.result_summary`，新实例接管后可从上次断点继续或重新执行 |

> **幂等性保证**：同步操作是幂等的——重复拉取同一 Skill 的内容并对比更新，结果一致。因此即使因崩溃导致重新执行，也不会产生数据错误。

### Email Format

```
Subject: [SkillHub] 数据同步报告 - {date}

同步统计：
- 总计：{total} 个 Skill
- 更新成功：{updated} 个
- 更新失败：{failed} 个
- 无变化：{unchanged} 个
- 已过时（外部文件不存在）：{outdated} 个

更新成功列表：
- {skill_name}: {change_description}

更新失败列表：
- {skill_name} ({source_url}) - {error_message}

已过时 Skill 列表：
- {skill_name} ({source_url}) - {error_message}

请管理员确认是否需要手动处理更新失败和已过时的 Skill。
```

### Configuration

```python
class Settings(BaseSettings):
    # Sync
    sync_cron_hour: int = 1
    sync_lock_timeout_hours: int = 2
    sync_max_retries: int = 3
    sync_retry_delays_timeout: str = "10,30,60"
    sync_retry_delays_server_error: str = "10,30,60"
    sync_retry_delays_rate_limited: str = "30,90,120"
    sync_retry_jitter_ratio: float = 0.25
    
    # SMTP
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    admin_emails: str = ""
    
    # API Tokens
    github_token: str = ""
    gitcode_token: str = ""
```

## Feature 3: Admin Auth Removal

### Changes

移除 `app/routers/admin.py` 中所有路由的 `dependencies=[Depends(require_admin)]`：

- `GET /api/admin/me` — 移除依赖
- `POST /api/admin/skills` — 移除依赖
- `POST /api/admin/skills/{name}` — 移除依赖
- `POST /api/admin/skills/{name}/delete` — 移除依赖
- `GET /api/admin/projects` — 移除依赖
- `GET /api/admin/projects/{name}` — 移除依赖
- `POST /api/admin/projects` — 移除依赖
- `POST /api/admin/projects/{name}` — 移除依赖
- 以及所有其他 admin 路由

删除 `/api/admin/login` 接口（不再需要）

删除 `app/auth.py` 文件（不再有任何引用）

### Preserved

（无保留项，`auth.py` 和 `/api/admin/login` 均删除）

## Alternatives Considered

### A1: 前端计算文件树 URL
- 优点：后端改动最小
- 缺点：前端需理解 sourceUrl 结构，多平台逻辑重复
- 决定：不采用，后端计算更可靠

### A2: Celery 异步任务
- 优点：更健壮的任务队列
- 缺点：引入 Redis/RabbitMQ 依赖，架构复杂度增加
- 决定：不采用，APScheduler 足够

### A3: 全量 clone 同步
- 优点：复用现有 import_service
- 缺点：开销大，按 Skill 粒度拉取更高效
- 决定：不采用，按 source_url 逐个更新

### A4: Redis 分布式锁
- 优点：性能更好
- 缺点：增加 Redis 依赖
- 决定：不采用，数据库锁足够且可记录历史
