# 下线机机接口管理功能 — 需求提案

## 关联信息

- **业务 Issue**: openlibing/openlibing-framework#180
- **目标仓**: openlibing-framework
- **目标分支**: release_20261019_iter1
- **流程模式**: Full

## 背景

openlibing-framework 的「机机接口管理」模块（`MachineInterfaceController`，`/manage/machine-interface`）需整体下线，移除全部对外接口及后端实现，降低维护面与安全暴露面。

## 下线范围（12 个接口）

| #   | 方法 | 路径                                                         |
| --- | ---- | ------------------------------------------------------------ |
| 1   | POST | /manage/machine-interface/addMachineInterface                |
| 2   | POST | /manage/machine-interface/queryMachineInterfaceList          |
| 3   | POST | /manage/machine-interface/updateMachineInterface             |
| 4   | POST | /manage/machine-interface/batchDeleteMachineInterface        |
| 5   | POST | /manage/machine-interface/addMachineInterfaceAccount         |
| 6   | POST | /manage/machine-interface/queryMachineInterfaceAccountList   |
| 7   | POST | /manage/machine-interface/queryInterfaceListByAccount        |
| 8   | POST | /manage/machine-interface/updateMachineInterfaceAccount      |
| 9   | POST | /manage/machine-interface/batchDeleteMachineInterfaceAccount |
| 10  | POST | /manage/machine-interface/updateAccountSecretKey             |
| 11  | POST | /manage/machine-interface/updateInterfacePermission          |
| 12  | POST | /manage/machine-interface/queryMachineInterfaceLog           |

## 验收标准

- [x] 工程编译通过
- [x] 单元测试全部通过
- [x] 全仓无 `MachineInterface` 残留引用
- [x] 相关接口不可用
