# openlibing-ai-agent AI Memory

本文档保存 `openlibing-ai-agent` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-ai-agent` 负责 OpenLibing AI 能力的 Agent 侧实现，后续系统级职责、工具边界、任务执行链路、安全约束需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Agent 工具调用、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 管理后台鉴权

- 管理后台使用白名单访问控制，不再使用用户名密码 + HMAC token 登录。
- 白名单配置从 Apollo 读取（`admin_whitelist`），值为逗号分隔的用户 ID 字符串。
- 白名单校验逻辑在 `app/auth.py`，依赖项为 `require_whitelist_user`。
- 前端通过 `X-User-Id` 请求头传递用户标识，后端校验是否在白名单中。
- 所有 `/api/admin/*` 接口使用 `dependencies=[Depends(require_whitelist_user)]` 保护。
- 无 `X-User-Id` 返回 401，非白名单用户返回 403。
- `/api/admin/login` 和 `/api/admin/me` 接口已删除。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| 修改鉴权逻辑后遗漏 import 清理 | 全局搜索 `from app.auth`、`require_admin`、`admin_headers` 确保无残留引用 | 2026-5-admin-whitelist-auth |
| 测试环境 Python 3.14 与 SQLAlchemy 不兼容 | 集成测试依赖 `app_client` fixture 会触发 SQLAlchemy 初始化，本地环境需确保依赖版本兼容 | 2026-5-admin-whitelist-auth |
