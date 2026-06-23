# repo-info-default-update-at

## 需求背景

`repo_info` 表中 `update_at` 字段当前默认为空（`DATETIME DEFAULT NULL`），新建代码仓录入时 `update_at` 列未显式写入，导致入库后该字段长期为 NULL。

- 录入新代码仓时，业务期望 `update_at` 与 `create_at` 保持一致（即"新建即更新"语义），便于后续按更新时间排序、按更新时间筛选仓库等场景使用。
- 历史已存在的 `update_at IS NULL` 数据也应回填为 `create_at`，避免脏数据影响查询/统计。

## 功能描述

通过 Liquibase 在 `openlibing-coderepo` 仓 `db.changelog.xml` 末尾增加一个 changeset，修改 `repo_info` 表 `update_at` 字段的默认值为当前时间戳（与 `create_at` 在 insert 时取到同一时间值），同时对历史 `update_at IS NULL` 的存量数据进行回填。

具体 DDL 行为：

1. 将 `repo_info.update_at` 列默认值改为 `CURRENT_TIMESTAMP`（insert 时若未显式传入，则使用当前时间，与 `create_at` 保持等价）。
2. 对存量 `update_at IS NULL` 的记录执行 `UPDATE repo_info SET update_at = create_at WHERE update_at IS NULL`。
3. 提供对应 rollback：恢复 `update_at` 默认值为 NULL，并回滚上述更新。

## 使用场景

- 用户在代码仓管理页面录入新代码仓时，入库后 `update_at` 不再为 NULL，等于录入时间。
- 运营/管理后台按 `update_at` 排序、过滤时不再出现 NULL 异常或错位。

## 验收标准

- [ ] Liquibase 启动时新增 changeset 成功执行；`repo_info.update_at` 默认值为 `CURRENT_TIMESTAMP`。
- [ ] 存量 `update_at IS NULL` 的记录被回填为 `create_at`。
- [ ] 新建代码仓记录时，未显式传入 `update_at`，入库后 `update_at = create_at`。
- [ ] 后续更新代码仓时，`update_at` 仍按现有 Java 逻辑被显式更新。
- [ ] 提供可回滚的 `rollback` 语句，恢复列默认值为 NULL。

## 影响范围

- 涉及文件：`src/main/resources/db/changelog/db.changelog.xml`
- 涉及表：`repo_info`
- 不修改任何 Java 业务代码，不影响现有接口签名与返回结构。
- 不涉及接口/数据迁移/部署链路重大变更。

## 关联 Issue/PR

- 业务 Issue：openlibing/openlibing-coderepo#53
- 与 openlibing-coderepo#40（`/query-repo` 接口返回 `updateTime` 字段）相关但不同：本次仅修复数据库默认值为空的缺陷。
