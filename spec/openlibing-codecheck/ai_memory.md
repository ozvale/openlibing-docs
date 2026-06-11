# openlibing-codecheck AI Memory

## MongoDB 性能
- `codecheck_rule_account` 表已有复合索引 `{rule_id, user_name, domain_name, region, project_id}`，用于加速 batchUpdate/batchDelete
- `queryRules` 方法查询条件为 `{user_name, domain_name, region, project_id}`（无 rule_id），无法复用上述索引前缀，如后续变慢需单独加索引
- `batchUpdateRuleAccountEntities` 和 `batchDeleteRuleAccountEntities` 是逐条操作（for 循环），非真正批量，数据量大时考虑改用 BulkOperations
- 凌晨 2:00 有两个定时任务并发（`getAllAccountRule` + `syncRepoSelectedRuleSetTask`），共享 `ruleSetTaskExecutor` 线程池（核心10，最大20）

## 定时任务时间表
| 任务 | cron | 说明 |
|------|------|------|
| `getAllAccountRule` | 0 0 2 | 遍历租户同步规则，写 codecheck_rule_account |
| `syncRule` | 0 0 3 | 全量同步规则，写 codecheck_rule |
| `getProjectRuleSets` | 0 0 4 | 遍历租户同步规则集，写 codecheck_rule_set |
| `syncRepoSelectedRuleSetTask` | 0 0 2 | 遍历 repo 同步已选规则集，写 sig_rule_set |

## Liquibase 注意事项
- MongoDB 索引通过 Liquibase changelog 管理，路径 `db/changelog/mongo/`
- 新增 XML 文件后需在 `db/changelog/db.mongodb.changelog.xml` 中 include
- 新增文件必须确认被打包进 JAR，否则启动会报 ChangeLogParseException
