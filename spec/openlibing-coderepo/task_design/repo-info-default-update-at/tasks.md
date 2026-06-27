# repo-info-default-update-at — 实现任务

## 进度: 0/2 complete

- [ ] Task 1: 在 `src/main/resources/db/changelog/db.changelog.xml` 中新增 changeset `20260623_default_repo_info_update_at`：将 `repo_info.update_at` 列默认值改为 `CURRENT_TIMESTAMP`，并对存量 `update_at IS NULL` 的记录回填为 `create_at`；提供对应 `rollback`。
- [ ] Task 2: 验证 XML 语法与 Liquibase 格式正确（`mvn -q -DskipTests compile` 通过即可，不做数据库联机迁移验证）。
