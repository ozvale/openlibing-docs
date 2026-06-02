# Tasks: 修复 roleMapping 过长导致 5010000 全局异常

## 实现步骤

- [x] 1. Service 层：在 `ProjectConfigServiceImpl.updateGitcodeRoleMapping` 中增加 `keySet.size() > 50` 校验，超出时返回友好错误提示
- [x] 2. 数据库：添加 Liquibase 变更集，将 `role_mapping` 列从 VARCHAR(255) 改为 TEXT
- [x] 3. Mapper XML：将 `jdbcType` 从 VARCHAR 改为 LONGVARCHAR
- [x] 4. 全局异常：`GlobalExceptionHandler` 的 `LOGGER.error` 补充异常堆栈输出
- [x] 5. 单元测试：新增 `testUpdateGitcodeRoleMapping_RoleMappingExceedsMaxCount` 测试用例
- [ ] 6. 手动验证：传入超过 50 个映射关系，确认返回友好错误提示
- [ ] 7. 手动验证：传入正常映射关系，确认接口正常工作
