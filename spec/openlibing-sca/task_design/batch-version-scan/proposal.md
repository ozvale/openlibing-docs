# 版本扫描批量操作

## 需求背景

SCA 系统中 `ManualVersionScanController` 的 `/version/scan/startVersionScan` 接口原本只支持逐条触发版本扫描。在大规模运营场景下，运营人员需要同时触发多个仓库分支的版本扫描，逐条调用效率低下。此外，前端在多选版本扫描记录后需要批量删除能力，当前缺少对应的后端批量删除接口。

本次改造将版本扫描的触发与删除从单条操作升级为批量操作，提升运营效率。

## 需求目标

1. **批量触发版本扫描**：`startScan` 接口支持一次请求传入多个仓库分支，逐条独立执行，单条失败不影响其他条
2. **批量删除扫描记录**：新增 `deleteByIds` 接口，支持按 ID 集合批量删除 `tbl_manual_version_scan` 表记录
3. **单条失败隔离**：批量操作中任意单条失败不抛出全局异常阻断整体流程，而是通过逐条结果标识成功/失败

## 验收标准

- [ ] `POST /version/scan/startVersionScan` 接收 `List<ManualVersionScanStartPo>`，返回 `List<ManualVersionScanStartResultVO>`，每条独立标识成功/失败及错误原因
- [ ] 传入空列表或 null 时返回空结果列表（不抛异常）
- [ ] 批量触发中单条失败（如仓库未添加、仓库信息不存在、repoId/branchId 为 null）不影响其他条继续执行
- [ ] `POST /version/scan/deleteByIds` 接收 `List<String>` ID 集合，返回删除条数
- [ ] 传入空列表或 null 时跳过 Mapper 调用，返回 0
- [ ] 单元测试覆盖：多条目成功、空列表、部分失败、单条/批量删除、异常场景

## 关联 PR

[openlibing/openlibing-sca#255](https://gitcode.com/openlibing/openlibing-sca/pull/255)
