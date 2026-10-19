# 下线机机接口管理功能 — 归档文档

## 关联信息

- **业务 Issue**: openlibing/openlibing-framework#180
- **业务 PR**: https://gitcode.com/openlibing/openlibing-framework/merge_requests/473
- **目标分支**: release_20261019_iter1
- **开发分支**: ZZT_202610_MachineInterface
- **核心提交**: `2a50b7ca2`（模块下线）、`1e6407077`（保留 machine_interface 表定义）
- **归档日期**: 2026-10-19

## 执行摘要

下线 openlibing-framework 中的「机机接口管理」模块全部功能，包括 1 个 Controller（12 个端点）、Service 接口与实现、4 对 Mapper、Entity/DTO/Convertor、2 个 AOP 日志处理器、3 个单元测试，并清理共享日志基础设施（`LogOperationAndModule` 常量、`LogDataCollectionName` 常量与映射、`GetLogsMapper.xml` 表名分支）及 `AGENTS.md` 描述。

## 变更统计

| 类别       | 数量                    |
| ---------- | ----------------------- |
| 删除文件   | 29                      |
| 编辑文件   | 4                       |
| 提交数量   | 2                       |
| 删除代码行 | -4331                   |
| 新增代码行 | +1                      |
| 测试用例   | 2252 passed, 0 failures |

## 下线的 HTTP 接口（12 个）

`/manage/machine-interface/**`：addMachineInterface、queryMachineInterfaceList、updateMachineInterface、batchDeleteMachineInterface、addMachineInterfaceAccount、queryMachineInterfaceAccountList、queryInterfaceListByAccount、updateMachineInterfaceAccount、batchDeleteMachineInterfaceAccount、updateAccountSecretKey、updateInterfacePermission、queryMachineInterfaceLog。

## 设计偏差与取舍

### 单阶段提交 vs 分阶段提交

**先例做法**: 技术委员会下线按依赖顺序拆分为 42 次提交，每阶段编译验证。

**本次做法**: 模块规模较小（29 个文件、单一 Controller），采用一次性删除 + 全量编译 + 单测验证，降低提交噪音。

**结论**: 模块边界清晰、无跨模块引用时，单阶段提交 + 全量验证可行且高效。

### 数据库表保留

下线仅移除代码，`machine_interface*`、`log_machine_interface` 物理表保留，历史数据不删除，避免误删存量数据。

`machine_interface` 表由另一位同事的服务负责删除（其服务涉及查库），因此 framework 侧（含 h2 测试库 `schema.sql`）保留该表定义，不做删除。此为人工修正项，已同步修订设计文档与任务清单。

## 可复用经验

### 1. 下线模块时的共享基础设施清理清单

下线一个业务模块时，除业务代码外还需检查并清理以下共享引用，避免遗留死配置：

- 操作日志常量类（如 `LogOperationAndModule`）中该模块的常量段。
- 日志表名常量与日志查询映射（如 `LogDataCollectionName` 的常量与 `MANAGEMENT_LOG` JSON 项）。
- 日志表名动态 SQL 分支（如 `GetLogsMapper.xml` 的 `<when>` 节点）。
- 测试库建表脚本（如 `h2/schema.sql`）。
- 仓级 `AGENTS.md` 中该模块的能力描述。

### 2. 残留引用扫描

删除后用 `rg "ClassName|table_name" src` 全量扫描，确认仅剩待清理的共享文件，再逐一编辑。本次扫描确认模块外无任何调用方。

## 后续工作

- **前端清理**: 机机接口相关页面与调用需同步下线（另行处理）。
- **数据库清理**: 如需删除 `machine_interface*`、`log_machine_interface` 表，由 DBA 评估后执行。
- **权限枚举**: `service_interface_info.url_flag=2`（机机接口标识）属权限管理既有枚举，本次未改动。

## 总结

模块边界清晰、无跨模块引用的小型下线任务，通过「一次性删除 + 共享引用清理 + 全量编译与单测验证」即可高质量完成。清理共享日志基础设施是下线任务易遗漏的关键环节，已沉淀为可复用清单。
