# Plan: skill-market-sync

**Change ID**: skill-market-sync
**Branch**: dev_zxy_skillhub
**Date**: 2026-05-13

## 执行顺序

三个 Feature 相互独立，按 Feature 1 → Feature 3 → Feature 2 顺序执行（Feature 1 最简单，Feature 3 改动最小但需先清理 auth 以便后续测试，Feature 2 最复杂）。

---

## Task 1: 新增 FileTreeItem 模型和 fileTreeWithUrls 字段

### 实现步骤

1. **Red**: 编写测试 `tests/test_file_tree_urls.py`
   - 测试 `FileTreeItem` 模型序列化
   - 测试 `SkillDetail` 包含 `fileTreeWithUrls` 字段
   - 测试 `build_file_url` 函数：GitHub source_url + file_path → 完整 URL
   - 测试 `build_file_url` 函数：GitCode source_url + file_path → 完整 URL
   - 测试 `build_file_url`：source_url 为空返回 None
   - 测试 `build_file_url`：source_url 格式异常返回 None

2. **Green**: 在 `app/utils/platform.py` 中新增 `build_file_url(source_url, file_path)` 函数
   - 复用 `parse_source_url()` 解析出 platform/owner/repo/branch/path
   - 从 path 中提取 SKILL.md 所在目录的相对路径（dirname）
   - 拼接：`{dirPath}/{filePath}`
   - GitHub: `https://github.com/{owner}/{repo}/blob/{branch}/{dirPath}/{filePath}`
   - GitCode: `https://gitcode.com/{owner}/{repo}/blob/{branch}/{dirPath}/{filePath}`

3. **Green**: 在 `app/schemas/skill.py` 中新增 `FileTreeItem(BaseModel)` 和 `SkillDetail.fileTreeWithUrls` 字段

4. **Green**: 在 `app/repositories/skill_repo.py` 的 `get_by_name` 方法中计算 `fileTreeWithUrls`
   - 遍历 `fileTree` 列表，对每个 path 调用 `build_file_url` 生成 URL
   - source_url 为空时 `fileTreeWithUrls` 为 None

5. **Refactor**: 清理重复代码

### 验收标准
- `GET /api/skills/{name}` 响应包含 `fileTreeWithUrls` 字段
- GitHub/GitCode URL 格式正确
- source_url 为空时不报错，返回 None

### 涉及文件
- `app/utils/platform.py` — 新增 `build_file_url`
- `app/schemas/skill.py` — 新增 `FileTreeItem`、`SkillDetail.fileTreeWithUrls`
- `app/repositories/skill_repo.py` — `get_by_name` 中计算 `fileTreeWithUrls`
- `tests/test_file_tree_urls.py` — 新增测试文件

---

## Task 2: 新增 SyncTask 数据模型

### 实现步骤

1. **Red**: 编写测试 `tests/test_sync_task.py`
   - 测试 SyncTask 模型字段正确
   - 测试 SyncTask 可以被正确创建和查询

2. **Green**: 在 `app/models/sync_task.py` 中定义 SyncTask ORM 模型
   - 字段：id, task_type, status, started_at, completed_at, result_summary, instance_id, created_at
   - 表名：`ai_agent_sync_tasks`

3. **Green**: 在 `app/models/skill.py` 的 `Base` 中注册（或确保 import 链正确）
   - 在 `app/main.py` 的 lifespan 中确保 `Base.metadata.create_all` 包含 SyncTask

### 验收标准
- SyncTask 表可正确创建
- 字段类型和约束与 design.md 一致

### 涉及文件
- `app/models/sync_task.py` — 新增
- `app/main.py` — 确保 import SyncTask 以注册表

---

## Task 3: 新增 RemoteFetcher 工具

### 实现步骤

1. **Red**: 编写测试 `tests/test_remote_fetcher.py`
   - 测试 `fetch_file_content`：GitHub Raw URL 成功返回内容
   - 测试 `fetch_file_content`：GitCode Raw URL 成功返回内容
   - 测试 `fetch_directory_tree`：GitHub Contents API 返回文件列表
   - 测试 `fetch_directory_tree`：GitCode Contents API 返回文件列表
   - 测试 `fetch_readme`：成功返回 README.md 内容
   - 测试 404 响应返回 None
   - 测试超时触发指数退避重试（mock sleep）
   - 测试 429 限流触发指数退避重试（mock sleep）
   - 测试 5xx 触发指数退避重试（mock sleep）
   - 测试 429 优先使用 Retry-After header
   - 测试超过最大重试次数抛出异常
   - 测试随机抖动在 ±25% 范围内

2. **Green**: 在 `app/utils/remote_fetcher.py` 中实现 `RemoteFetcher` 类
   - `__init__` 接收 settings（github_token, gitcode_token, retry 配置）
   - `_parse_source_url_to_parts(source_url)` — 解析 source_url 获取各部分
   - `_build_raw_url(platform, owner, repo, branch, path)` — 构建 Raw API URL
   - `_build_contents_url(platform, owner, repo, dir_path, branch)` — 构建 Contents API URL
   - `_get_retry_delay(retry_type, attempt)` — 计算带抖动的重试延迟
   - `_request_with_retry(url, max_retries)` — 带重试的 HTTP 请求
   - `fetch_file_content(source_url)` → `str | None`
   - `fetch_directory_tree(source_url)` → `list[str] | None`
   - `fetch_readme(source_url)` → `str | None`
   - 使用 httpx.AsyncClient

3. **Refactor**: 提取公共逻辑

### 验收标准
- GitHub/GitCode 两种平台的 Raw API 和 Contents API 均可调用
- 404 返回 None，不抛异常
- 超时/429/5xx 触发指数退避重试
- 429 优先使用 Retry-After
- 超过重试次数抛出异常

### 涉及文件
- `app/utils/remote_fetcher.py` — 新增
- `tests/test_remote_fetcher.py` — 新增

---

## Task 4: 新增 EmailService 邮件服务

### 实现步骤

1. **Red**: 编写测试 `tests/test_email_service.py`
   - 测试邮件模板生成（包含统计、更新成功列表、更新失败列表、过时列表）
   - 测试 SMTP 发送成功
   - 测试 SMTP 发送失败不抛异常，仅记录日志

2. **Green**: 在 `app/services/email_service.py` 中实现 `EmailService` 类
   - `__init__` 接收 settings（smtp_host, smtp_port, smtp_user, smtp_password, admin_emails）
   - `build_sync_report(result_summary)` → 构建邮件正文
   - `send_sync_report(result_summary)` → 发送邮件
   - 使用 aiosmtplib 异步发送
   - 捕获异常，记录日志，不阻塞

### 验收标准
- 邮件模板包含：统计、更新成功、更新失败、过时 Skill 列表
- SMTP 失败不阻塞同步流程

### 涉及文件
- `app/services/email_service.py` — 新增
- `tests/test_email_service.py` — 新增

---

## Task 5: 新增 SyncService 同步服务

### 实现步骤

1. **Red**: 编写测试 `tests/test_sync_service.py`
   - 测试 `acquire_sync_lock`：无 running 记录时成功获取锁
   - 测试 `acquire_sync_lock`：有 running 记录时返回 None
   - 测试 `acquire_sync_lock`：running 记录超时 2 小时后允许接管
   - 测试 `acquire_sync_lock`：唯一索引冲突返回 None
   - 测试 `sync_all`：成功同步有变化的 Skill
   - 测试 `sync_all`：无变化的 Skill 跳过
   - 测试 `sync_all`：404 标记为过时
   - 测试 `sync_all`：API 失败标记为更新失败，继续下一个
   - 测试 `sync_all`：同步历史清理（30天）
   - 测试 `sync_all`：同步完成后发送邮件

2. **Green**: 在 `app/services/sync_service.py` 中实现 `SyncService` 类
   - `__init__` 接收 session, remote_fetcher, email_service, skill_repo, settings
   - `acquire_sync_lock(instance_id)` → `SyncTask | None`
   - `release_sync_lock(sync_task, result_summary)` → 更新 sync_task 状态
   - `sync_skill(skill)` → 同步单个 Skill（拉取 → 对比 → 更新/标记过时/标记失败）
   - `sync_all()` → 完整同步流程
   - `_cleanup_old_tasks()` → 清理 30 天前的记录

3. **Refactor**: 提取公共逻辑

### 验收标准
- 分布式锁获取/释放正确
- 同步流程完整：拉取 → 对比 → 更新/跳过/标记过时/标记失败
- 单个 Skill 失败不影响其他
- 同步历史自动清理
- 同步完成后发送邮件

### 涉及文件
- `app/services/sync_service.py` — 新增
- `tests/test_sync_service.py` — 新增

---

## Task 6: 配置项扩展

### 实现步骤

1. **Red**: 编写测试验证新配置项可正确读取

2. **Green**: 在 `app/config.py` 的 `Settings` 类中新增配置项
   - Sync: sync_cron_hour, sync_lock_timeout_hours, sync_max_retries, sync_retry_delays_timeout, sync_retry_delays_server_error, sync_retry_delays_rate_limited, sync_retry_jitter_ratio
   - SMTP: smtp_host, smtp_port, smtp_user, smtp_password, smtp_use_tls, admin_emails
   - API Tokens: github_token, gitcode_token
   - 支持 Apollo 配置中心加载（在 `__init__` 中添加 `get_apollo_config` 调用）

3. **Green**: 在 `pyproject.toml` 中新增依赖
   - `apscheduler>=3.10.0`
   - `aiosmtplib>=3.0.0`
   - `httpx>=0.28.0`（dev 依赖中已有，移至主依赖）

### 验收标准
- 所有新配置项可通过环境变量或 Apollo 加载
- 默认值与 design.md 一致

### 涉及文件
- `app/config.py` — 修改
- `pyproject.toml` — 修改

---

## Task 7: APScheduler 集成

### 实现步骤

1. **Red**: 编写测试验证 scheduler 在 lifespan 中启动和关闭

2. **Green**: 在 `app/main.py` 中集成 APScheduler
   - 在 lifespan 中启动 APScheduler
   - 配置定时任务：每天凌晨 `sync_cron_hour` 点执行 `SyncService.sync_all()`
   - 在 lifespan yield 后关闭 scheduler
   - 需要在 lifespan 中初始化 RemoteFetcher, EmailService, SyncService

3. **Refactor**: 确保 import 链正确

### 验收标准
- 应用启动时 scheduler 自动启动
- 应用关闭时 scheduler 自动关闭
- 定时任务配置正确

### 涉及文件
- `app/main.py` — 修改

---

## Task 8: 移除管理后台 token 校验

### 实现步骤

1. **Red**: 编写/更新测试 `tests/test_admin.py`
   - 测试无 token 访问 `POST /api/admin/skills` 返回 200
   - 测试 `POST /api/admin/login` 返回 404（接口已删除）
   - 测试所有 admin 路由不需要 token

2. **Green**: 修改 `app/routers/admin.py`
   - 移除所有路由的 `dependencies=[Depends(require_admin)]`
   - 删除 `/api/admin/login` 路由
   - 移除 `from app.auth import ...` 导入
   - 移除 `AdminLoginRequest`, `AdminLoginResponse` 的导入

3. **Green**: 删除 `app/auth.py` 文件

4. **Green**: 清理 `app/routers/import_.py` 中的 `from app.auth import require_admin` 和相关 `dependencies`

5. **Green**: 更新 `tests/conftest.py`，移除 `admin_token` 和 `admin_headers` fixture

6. **Green**: 更新 `app/schemas/skill.py`，移除 `AdminLoginRequest` 和 `AdminLoginResponse`

### 验收标准
- 所有 `/api/admin/*` 接口无需 token 即可访问
- `/api/admin/login` 返回 404
- `app/auth.py` 已删除
- 现有测试通过

### 涉及文件
- `app/routers/admin.py` — 修改
- `app/routers/import_.py` — 修改
- `app/auth.py` — 删除
- `app/schemas/skill.py` — 修改
- `tests/conftest.py` — 修改
- `tests/test_admin.py` — 修改

---

## Task 9: 集成测试

### 实现步骤

1. 编写端到端测试 `tests/test_integration_sync.py`
   - 测试文件树 URL 计算的端到端流程（创建 Skill → 查询 → 验证 fileTreeWithUrls）
   - 测试同步服务的分布式锁逻辑（两个并发请求只有一个成功）
   - 测试管理后台接口无 token 访问
   - 测试 `/api/admin/login` 返回 404
   - 测试邮件发送（mock SMTP）
   - 测试 API 超时/限流时的指数退避重试

2. 运行全量测试确保无回归

### 验收标准
- 所有集成测试通过
- 无回归问题

### 涉及文件
- `tests/test_integration_sync.py` — 新增

---

## 依赖关系

```
Task 1 (FileTreeItem) ────────────────────────── 独立
Task 8 (Admin Auth Removal) ──────────────────── 独立
Task 6 (Config) ──────────────────────────────── Task 3/4/5/7 的前置
Task 2 (SyncTask Model) ──────────────────────── Task 5 的前置
Task 3 (RemoteFetcher) ───────────────────────── Task 5 的前置
Task 4 (EmailService) ────────────────────────── Task 5 的前置
Task 5 (SyncService) ──────── 依赖 Task 2/3/4/6
Task 7 (APScheduler) ──────── 依赖 Task 5/6
Task 9 (Integration) ──────── 依赖所有 Task
```

## 执行顺序

**Phase A**（可并行）: Task 1 → Task 8 → Task 6 → Task 2
**Phase B**（可并行）: Task 3 → Task 4
**Phase C**（串行）: Task 5 → Task 7 → Task 9
