# 下线机机接口管理功能 — 技术方案

## 方案概述

参照「2026-7-后端下线技术委员会」先例，按依赖顺序整体删除机机接口模块代码，并清理其在共享基础设施中的引用。数据库物理表保留，历史数据不删除。

## 删除文件（29）

| 类别 | 文件 |
|------|------|
| Controller | `MachineInterfaceController.java` |
| Service | `MachineInterfaceService.java`、`impl/MachineInterfaceServiceImpl.java` |
| Mapper 接口 | `MachineInterface{,Account,Permission,Log}Mapper.java`（4） |
| Mapper XML | `MachineInterface{,Account,Permission,Log}Mapper.xml`（4） |
| Entity | `entity/machine/*Entity.java`（4） |
| DTO | `dto/machine/*DTO.java`（5） |
| Convertor | `MachineInterface{,Account,Permission,Log}Convertor.java`（4） |
| AOP | `MachineInterfaceLogHandler.java`、`MachineInterfaceAccountLogHandler.java`（2） |
| 测试 | `MachineInterface{,Account}LogHandlerTest.java`、`MachineInterfaceServiceImplTest.java`（3） |

## 编辑文件（4）

| 文件 | 变更 |
|------|------|
| `common/constants/LogOperationAndModule.java` | 移除机机接口常量段（10 个常量） |
| `common/log/LogDataCollectionName.java` | 移除 `MACHINE_INTERFACE_LOG` 常量与 `MANAGEMENT_LOG` 中「机机接口」映射 |
| `resources/mapper/GetLogsMapper.xml` | 移除 `log_machine_interface` 表名分支 |
| `AGENTS.md` | 移除机机接口模块描述 |

## 影响范围

- 12 个 `/manage/machine-interface/**` 接口下线，前端入口与调用方需同步下线。
- 共享日志基础设施：`LoggingServiceImpl`、`InternalServerImpl`、`BatchPersonalDataJob` 通过 `MANAGEMENT_LOG` 遍历日志表，移除「机机接口」映射后日志查询列表不再包含该模块。
- 数据库表 `machine_interface`、`machine_interface_account`、`machine_interface_permission`、`log_machine_interface` 保留，不做物理删除。
- `machine_interface` 表由另一位同事的服务负责删除（其服务涉及查库），framework 侧（含 h2 测试库 `schema.sql`）保留该表定义。

## 兼容性

- 无 DB schema 变更，无 changelog 新增。
- 接口下线为破坏性变更，需确认无存量调用方。
