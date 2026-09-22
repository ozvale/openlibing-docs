# Proposal: skill-market-sync

**Change ID**: skill-market-sync
**Status**: proposed
**Issue**: #6
**Author**: Trae AI Assistant

## Summary

基于 openlibing 上线的初版 skillhub，针对部分后端功能问题做出优化：
1. Skill 详情页文件树超链接跳转功能
2. Skill 市场数据同步更新能力
3. 管理后台接口权限管控模式改造

## Goals

- 用户在 Skill 详情页点击文件树中的文件，可跳转到对应源码位置
- 每天凌晨1点自动同步所有 Skill 的外部内容，保持数据时效性
- 同步结果通过邮件通知管理员，失败 Skill 信息被记录
- 多实例部署时不会重复同步同一个 Skill
- 管理后台接口不再需要 token 校验，由前端角色权限管控

## Non-Goals

- 不实现增量 git pull 同步
- 不实现 Celery 异步任务框架
- 不实现管理后台 API 限流保护
- 不修改前端代码（仅后端变更）

## Impact

### API 变更
- `GET /api/skills/{name}` 响应新增 `fileTreeWithUrls` 字段
- `POST /api/admin/*` 接口移除 token 校验
- `POST /api/admin/login` 接口删除

### 数据库变更
- 新增 `sync_task` 表（同步任务记录 + 分布式锁）

### 新增依赖
- `apscheduler` — 进程内定时任务
- `aiosmtplib` — 异步 SMTP 邮件发送

### 配置变更
- 新增 Apollo/环境变量：`sync_cron_hour`, `sync_max_retries`, `sync_retry_delays_timeout`, `sync_retry_delays_server_error`, `sync_retry_delays_rate_limited`, `sync_retry_jitter_ratio`, `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `admin_emails`, `github_token`, `gitcode_token`

## Risks

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| GitHub API 限流 | 同步失败 | 配置 GitHub Token，指数退避重试 |
| GitCode Raw API 不可用 | 同步失败 | 测试验证 API 端点，指数退避重试 |
| 移除 admin 认证 | 接口暴露 | 确保前端路由守卫到位 |
| 多实例同时同步 | 数据重复更新 | sync_task 表唯一索引分布式锁 |
| SMTP 服务不可用 | 邮件发送失败 | 记录日志，不阻塞同步流程 |
