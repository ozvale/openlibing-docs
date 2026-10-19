# 下线机机接口管理功能 — 实现任务

## 进度: 4/4 complete

### Task 1: 删除机机接口模块代码（29 个文件）

- [x] 删除 Controller：`MachineInterfaceController.java`
- [x] 删除 Service 接口与实现：`MachineInterfaceService.java`、`MachineInterfaceServiceImpl.java`
- [x] 删除 Mapper 接口：`MachineInterface{,Account,Permission,Log}Mapper.java`
- [x] 删除 Mapper XML：`MachineInterface{,Account,Permission,Log}Mapper.xml`
- [x] 删除 Entity：`entity/machine/`（4）
- [x] 删除 DTO：`dto/machine/`（5）
- [x] 删除 Convertor：`MachineInterface{,Account,Permission,Log}Convertor.java`
- [x] 删除 AOP：`MachineInterface{,Account}LogHandler.java`
- [x] 删除测试：`MachineInterface{,Account}LogHandlerTest.java`、`MachineInterfaceServiceImplTest.java`

### Task 2: 清理共享引用（4 个文件）

- [x] `LogOperationAndModule.java`：移除机机接口常量段
- [x] `LogDataCollectionName.java`：移除 `MACHINE_INTERFACE_LOG` 常量与 JSON 映射
- [x] `GetLogsMapper.xml`：移除 `log_machine_interface` 表名分支
- [x] `h2/schema.sql`：移除 `machine_interface` 表

### Task 3: 更新文档（1 个文件）

- [x] `AGENTS.md`：移除机机接口模块描述

### Task 4: 验证

- [x] 残留引用扫描：`src` 下无 `MachineInterface` 引用
- [x] 编译：`mvn clean compile` — BUILD SUCCESS
- [x] 单元测试：Tests run: 2252, Failures: 0, Errors: 0, Skipped: 0
- [x] pre-commit：全部通过
