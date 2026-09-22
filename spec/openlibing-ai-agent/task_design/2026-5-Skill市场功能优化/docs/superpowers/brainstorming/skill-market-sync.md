# Brainstorming: skill-market-sync

**Change ID**: skill-market-sync
**Issue**: #6 - [需求]: AI插件市场建设 - Skill市场功能优化及数据同步更新
**Date**: 2026-05-12

## Problem Definition

基于 openlibing 上线的初版 skillhub，针对部分后端功能问题做出相应优化：
1. 优化 openlibing 插件市场用户体验
2. 新增 skill 市场数据同步更新能力

## Success Criteria

- Skill 详情页文件树中的文件链接可点击跳转到对应源码位置
- 每天凌晨1点自动同步所有 Skill 的外部内容，保持数据时效性
- 同步结果通过邮件通知管理员，失败 Skill 信息被记录
- 多实例部署时不会重复同步同一个 Skill
- 管理后台接口不再需要 token 校验，由前端角色权限管控

## Constraints

- 服务多实例部署，需分布式锁保证同步安全
- Skill 被外部删除时不直接删除数据库记录，仅标记为过时
- 支持 GitHub 和 GitCode 两个平台
- 邮件通知使用 SMTP

## Key Decisions

### D1: 文件树 URL 计算 — 后端计算
- 新增 `FileTreeItem(path, url)` 模型和 `fileTreeWithUrls` 字段
- 后端根据 `sourceUrl` 解析 base URL，为每个文件路径拼接完整链接
- 复用 `platform.py` 的 `parse_source_url` + `build_source_url`

### D2: 同步策略 — 基于 source_url 逐个更新
- 从数据库获取所有有 `source_url` 的 Skill
- 通过 Raw API 拉取最新内容（SKILL.md、文件树、README.md）
- 不 clone 整个仓库，按 Skill 粒度拉取
- 外部文件 404 时标记为"过时"，不删除

### D3: 定时任务 — 进程内 APScheduler
- 在 FastAPI 进程内运行 APScheduler
- 每天凌晨 1 点执行同步

### D4: 分布式锁 — 任务级粗粒度锁
- 采用任务级粗粒度锁：每天只允许一个实例执行同步，该实例串行同步所有 Skill
- 选择粗粒度锁的理由：Skill 数量有限（几十到几百），单实例可完成；API 限流是瓶颈，多实例并发反而加剧限流；实现简单可靠
- 新增 `sync_task` 表，利用唯一索引防并发（即使竞态条件也只有一个 INSERT 成功）
- INSERT 成功 → 执行同步；失败 → 跳过
- 死锁兜底：running 状态超过 2 小时允许新实例接管
- 同步操作幂等：重复拉取同一 Skill 对比更新，结果一致，崩溃后重新执行无副作用
- 保留 30 天同步历史

### D5: 邮件通知 — SMTP 直接发送
- 同步完成后汇总结果，通过 SMTP 发送邮件给管理员
- 邮件包含：同步统计、更新成功列表、过时 Skill 列表

### D6: 权限改造 — 完全移除 require_admin
- 移除所有 `/api/admin/*` 接口的 `Depends(require_admin)` 依赖
- 删除 `/api/admin/login` 接口
- 删除 `app/auth.py` 文件
- 前端负责角色路由守卫

## Excluded

- 不实现增量 git pull 同步
- 不实现 Celery 异步任务
- 不实现 API 限流保护（管理后台接口）
- 不修改前端代码（仅后端变更）

## Risks

- GitHub API 限流（未认证 60次/小时，认证 5000次/小时）→ 需配置 GitHub Token，指数退避重试
- GitCode API 可用性不确定 → 需测试 Raw API 端点，指数退避重试
- 移除 admin 认证后接口暴露 → 需确保前端路由守卫到位
