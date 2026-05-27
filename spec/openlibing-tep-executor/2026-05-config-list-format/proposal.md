# Proposal: config-list-format

## Summary

支持 config JSON 文件使用列表格式，每个列表元素独立组装 testSet 文件，实现多组配置的并行执行。

## Problem

当前 config 参数只支持字典格式的 JSON 文件，当用户需要执行多个独立的测试配置时，需要创建多个配置文件或手动合并，无法实现配置级别的并行和隔离。

**Issue**: #12 - 支持列表格式 config JSON

## Solution

采用简洁优雅的方案：
1. 在 `executor.py accept_para()` 中判断 JSON 格式：
   - 字典格式：保持原有流程（向后兼容）
   - 列表格式：使用第一个元素走原有流程，同时保存整个列表

2. 将 config_list 传递到 `TestSet.__find_testset_files_include_cases()`，根据每个列表元素的 testcase 组装独立的 testSet 文件

3. 新增 `npu_parallel_num` 参数，值为列表元素数量，控制并行执行

## Scope

- 修改 executor.py、uniautos.py、test_set.py
- 新增 config_list 字段传递链路
- 新增 TestSetGenParams 的 config_list 字段
- 保持向后兼容：字典格式完全保持原有行为

## Out of Scope

- 不修改 testcase/userconfig/env_config 的合并逻辑
- 不修改 metadata 收集逻辑（已由 Issue #11 实现）
- 不修改 testSet 文件的搜索逻辑