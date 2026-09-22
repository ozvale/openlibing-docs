# Proposal: log_project 前端回显值更名

## 需求背景

属于 "openlibing-coderepo 日志完备记录整改" 任务的一部分。当前 `log_project` 表在前端日志分类回显的分类名称为"项目空间管理"，该名称不能准确体现日志覆盖范围（项目空间 + 代码仓库），需要调整为"项目空间与代码仓管理"。

## 目标

将 `LogDataCollectionName.MANAGEMENT_LOG` 配置块中 `"项目空间管理": "log_project"` 改为 `"项目空间与代码仓管理": "log_project"`，并同步更新相关单元测试中的字符串。

## 影响范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/framework/common/log/LogDataCollectionName.java` | 修改 | `MANAGEMENT_LOG` JSON 配置块中 key 更名 |
| `src/test/java/com/openlibing/framework/business/service/impl/InternalServerImplTest.java` | 修改 | 测试入参字符串同步更新 |
| `src/test/java/com/openlibing/framework/business/service/impl/LoggingServiceImplTest.java` | 修改 | 测试断言字符串同步更新 |

## 验收标准

- [x] 前端日志分类回显由"项目空间管理"变为"项目空间与代码仓管理"
- [x] `InternalServerImplTest` 全部通过
- [x] `LoggingServiceImplTest` 全部通过
- [x] 不影响其他日志分类的回显

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-framework/issues/55
- 业务 PR: https://gitcode.com/openlibing/openlibing-framework/pulls/328
