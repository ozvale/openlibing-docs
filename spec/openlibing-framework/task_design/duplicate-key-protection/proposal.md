# 唯一约束与防重复插入

## 需求背景

`user_role_info` 表在双实例部署下存在并发重复插入问题。仅靠应用层 `SELECT ... FOR UPDATE` 在 `REPEATABLE_READ` 隔离级别下无法完全阻止 Check-then-Insert 的并发竞态。

需要在数据库层面添加唯一约束兜底，同时在应用层捕获 `DuplicateKeyException` 返回用户友好提示。

## 功能描述

- 为 `product_info.product_name`、`project_info.project_name`、`role_type_info.role` + `role_type_info.role_name` 添加数据库唯一约束
- 在对应的 Service 层捕获 `DuplicateKeyException`，返回业务友好的错误信息，去除异常堆栈避免敏感信息泄露
- 仅影响新增操作，兼容存量数据

## 验收标准

- [ ] `product_info.product_name` 唯一约束生效，重复插入返回"组织已存在"
- [ ] `project_info.project_name` 唯一约束生效，重复插入返回"项目已存在"
- [ ] `role_type_info.role` 和 `role_type_info.role_name` 唯一约束生效，重复插入返回"角色已存在"
- [ ] 异常信息不包含数据库结构或异常堆栈
- [ ] 不影响存量重复数据
- [ ] 全量单元测试通过

## 影响范围

| 模块 | 影响 |
|------|------|
| ProductServiceImpl | 新增 DuplicateKeyException 捕获 |
| ProjectServiceImpl | 新增 DuplicateKeyException 捕获 |
| RoleServiceImpl | 新增 DuplicateKeyException 捕获 |
| 数据库 | 3 张表新增唯一约束（兼容存量） |