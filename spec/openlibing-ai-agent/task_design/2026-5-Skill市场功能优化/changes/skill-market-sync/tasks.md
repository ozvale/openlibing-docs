# Tasks: skill-market-sync

**Change ID**: skill-market-sync

## Task 1: 新增 FileTreeItem 模型和 fileTreeWithUrls 字段
- 在 `schemas/skill.py` 中新增 `FileTreeItem` 模型
- 在 `SkillDetail` 中新增 `fileTreeWithUrls` 字段
- 在 `skill_repo.py` 的 `get_by_name` 方法中计算 fileTreeWithUrls
- 在 `platform.py` 中新增 `build_file_url` 工具函数

## Task 2: 文件树 URL 计算逻辑
- 实现 `build_file_url(source_url, file_path)` 函数
- 解析 sourceUrl 获取目录路径，拼接文件路径生成完整 URL
- 处理 sourceUrl 为空或格式异常的情况
- 编写单元测试覆盖 GitHub/GitCode 两种平台

## Task 3: 新增 SyncTask 数据模型
- 在 `models/sync_task.py` 中定义 SyncTask ORM 模型
- 创建 Alembic 迁移脚本
- 字段：id, task_type, status, started_at, completed_at, result_summary, instance_id, created_at

## Task 4: 新增 RemoteFetcher 工具
- 在 `utils/remote_fetcher.py` 中实现 `RemoteFetcher` 类
- 实现 `fetch_file_content(source_url)` — 通过 Raw API 拉取文件内容
- 实现 `fetch_directory_tree(source_url)` — 通过 Contents API 获取目录结构
- 实现 `fetch_readme(source_url)` — 拉取 README.md 内容
- 支持 GitHub 和 GitCode 两个平台
- 处理 404（文件不存在）、限流等异常
- 实现指数退避 + 随机抖动重试：超时/5xx 按 10s → 30s → 60s，429 按 30s → 90s → 120s，最多 3 次
- 429 响应优先使用 `Retry-After` header
- 每次等待加入 ±25% 随机抖动，防止惊群效应

## Task 5: 新增 SyncService 同步服务
- 在 `services/sync_service.py` 中实现 `SyncService` 类
- 实现分布式锁获取/释放逻辑
- 实现同步核心流程：遍历 Skill → 拉取内容 → 对比 → 更新
- 处理"过时"Skill 标记逻辑
- 实现同步历史清理（30天）

## Task 6: 新增 EmailService 邮件服务
- 在 `services/email_service.py` 中实现 `EmailService` 类
- 实现 SMTP 邮件发送
- 实现同步报告邮件模板
- 处理 SMTP 发送失败（记录日志，不阻塞）

## Task 7: 配置项扩展
- 在 `config.py` 中新增同步和邮件相关配置项
- 支持 Apollo 配置中心加载
- 配置项：sync_cron_hour, sync_max_retries, sync_retry_delays_timeout, sync_retry_delays_server_error, sync_retry_delays_rate_limited, sync_retry_jitter_ratio, smtp_host, smtp_port, smtp_user, smtp_password, admin_emails, github_token, gitcode_token

## Task 8: APScheduler 集成
- 在 `main.py` 中集成 APScheduler
- 配置定时任务（每天凌晨1点执行同步）
- 在 FastAPI lifespan 中启动/关闭 scheduler

## Task 9: 移除管理后台 token 校验
- 移除 `admin.py` 中所有路由的 `dependencies=[Depends(require_admin)]`
- 删除 `/api/admin/login` 接口
- 删除 `app/auth.py` 文件

## Task 10: 集成测试
- 测试文件树 URL 计算的端到端流程
- 测试同步服务的分布式锁逻辑
- 测试管理后台接口无 token 访问
- 测试 `/api/admin/login` 返回 404
- 测试 `auth.py` 已删除
- 测试邮件发送（mock SMTP）
- 测试 API 超时/限流时的指数退避重试
