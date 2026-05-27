# Proposal: metadata-path-filter

## Summary

支持按指定路径过滤 metadata 收集范围，仅在配置路径中的用例才被记录到 metadata.xml。

## Problem

当前 metadata 收集机制会收集所有 testSet 文件中的用例信息，无法按路径进行筛选。当用户只想收集特定模块或目录的用例元数据时，无法实现精细化控制。

**Issue**: #11 - 元数据上报支持不同路径统计

## Solution

从 `--config` 参数指定的 JSON 配置文件中读取 `testPaths` 字段（列表类型），在 `get_testcase_metadata()` 方法中根据用例的 `file_path` 属性进行过滤匹配，仅收集匹配路径下的用例信息。

## Scope

- 仅修改 `executor.py` 文件
- 新增 `testPaths` 配置字段解析
- 新增路径过滤逻辑
- 保持向后兼容：`testPaths` 为空时维持原有全量收集行为

## Out of Scope

- 不修改 testSet 文件搜索逻辑
- 不影响其他 metadata 相关功能