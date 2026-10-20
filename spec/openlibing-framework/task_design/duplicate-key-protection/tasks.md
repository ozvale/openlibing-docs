# 唯一约束与防重复插入 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 编写 3 张表的唯一约束 Liquibase changelog（product_info / project_info / role_type_info）
- [x] Task 2: 在 ProductServiceImpl / ProjectServiceImpl / RoleServiceImpl 中添加 DuplicateKeyException 捕获
- [x] Task 3: 去除异常堆栈日志，使用 `LOG.warn("msg")` 避免敏感信息泄露
- [x] Task 4: 安全设计文档编写（威胁模型 + 安全设计）
