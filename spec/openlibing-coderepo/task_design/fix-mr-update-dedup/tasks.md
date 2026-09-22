# Tasks: 修复 MergeRequestEventHandler 更新事件去重逻辑缺陷

## 实现步骤

- [x] 1. 修正更新原因检查条件：移除 `!"gitcode"` 排除逻辑，改为对所有平台统一检查更新原因
- [x] 2. 新增 `isValidSourceUpdateReason` 方法，按平台判断有效更新原因（GitCode: `source update`，Gitee: `source_branch_changed`），补充 else 分支并记录 warn  日志
- [x] 3. 修正 Redis 锁 key 生成逻辑：非代码变更的更新事件不再复用 CREATE key， 返回空 key 跳过处理
- [x] 4. `handle` 方法增加 `StringUtils.isBlank(eventUniqueKey)` 检查
- [x] 5. 提取 `shouldSkipEvent`、`isCreateAction`、`isUpdateAction` 方法，保持 handle 方法在 50 行以内
- [x] 6. `isCreateAction` 局部变量声明移至首次使用行附近
- [x] 7. `generateEventUniqueKey` 中复用 `isCreateAction(action)` 方法

## 修改文件清单

| 文件 | 修改类型 |
|------|---------|
| `src/main/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandler.java` | Bug 修复 |

## 验证方式

- 代码审查确认逻辑正确性
- 编译验证（内部 Maven 仓库认证问题，需在 CI 环境验证）
