# 唯一约束与防重复插入 — 技术设计

## 方案概述

数据库唯一约束兜底 + 应用层 `DuplicateKeyException` 捕获。

## 架构决策

| 决策         | 选择方案                   | 备选方案         | 原因                                                        |
| ------------ | -------------------------- | ---------------- | ----------------------------------------------------------- |
| 并发兜底机制 | 数据库唯一约束             | 应用层分布式锁   | 唯一约束不依赖网络/锁服务，是最根本的兜底机制；兼容存量数据 |
| 异常处理     | 捕获 DuplicateKeyException | 预检查（SELECT） | 预检查在 REPEATABLE_READ 下有快照问题，无法彻底防竞态       |
| 日志级别     | 去堆栈的 warn 日志         | error + 堆栈     | 避免数据库结构泄露到应用日志                                |

## 涉及文件

| 文件                      | 操作 | 说明                                                         |
| ------------------------- | ---- | ------------------------------------------------------------ |
| `ProductServiceImpl.java` | 修改 | 捕获 DuplicateKeyException，返回"组织已存在"                 |
| `ProjectServiceImpl.java` | 修改 | 捕获 DuplicateKeyException，返回"项目已存在"                 |
| `RoleServiceImpl.java`    | 修改 | 捕获 DuplicateKeyException，返回"角色已存在"                 |
| `product_info.xml`        | 新增 | `product_name` 唯一约束 changelog                            |
| `project_info.xml`        | 新增 | `project_name` 唯一约束 changelog                            |
| `role_type_info.xml`      | 新增 | `role` 和 `role_name` 唯一约束 changelog（含 not-null 升级） |
| `db.changelog.xml`        | 修改 | 注册新增的 3 个 changelog                                    |

## 风险 & 缓解

| 风险                         | 缓解                                                 |
| ---------------------------- | ---------------------------------------------------- |
| 唯一约束对存量重复数据不生效 | 已有重复数据需业务侧评估处理，代码约束仅防止新增重复 |
| constraint name 冲突         | 使用表名+列名命名约定，避免与已有约束冲突            |

## 跨仓影响

无。
