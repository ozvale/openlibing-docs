# TEP Executor 日志增强

## 需求背景

当前 `openlibing-tep-executor` 测试执行器的日志系统需要增强，主要问题：
1. 环境日志收集仅按 IP 判断，无法直接收集本地 localhost 日志
2. 缺少独立的 tep-executor.log 日志文件
3. 部分关键日志散落在其他日志中，不便于问题追踪
4. 日志文件 URL 未统一打印

## 功能描述

### 1. 新增 tep-executor.log 日志文件
- 创建独立的 `tep-executor.log` 日志文件
- 与现有的 `hutafagent.log` 独立
- 便于问题定位和日志分析

### 2. 增强环境日志收集逻辑
在 `zip_files_in_conf_log` 函数中增加不判断 IP 直接收集 localhost 日志的功能。

### 3. 日志场景增强
需要收集并打印到 `tep-executor.log` 的日志场景：
- `get_metadata_info_from_testset` 的 process testset file 打印
- `TestSet.gen` 的 Valid testset files 打印，增加 `_tmp_testset_files` 文件列表
- `zip_files_in_conf_log` 函数及其内部调用的函数，增加压缩文件相关打印

### 4. 日志文件 URL 打印
在 `generate_logs` 中打印所有日志文件的 URL。

## 验收标准

- [ ] `tep-executor.log` 日志文件独立生成
- [ ] localhost 环境日志被正确收集
- [ ] `get_metadata_info_from_testset` 打印日志到 tep-executor.log
- [ ] `TestSet.gen` 打印 `Valid testset files` 到 tep-executor.log
- [ ] `_get_all_testset_files` 打印 `_tmp_testset_files` 文件列表
- [ ] 压缩文件时打印 `[ADD]` 和 `[SKIP]` 日志
- [ ] `generate_logs` 打印所有日志文件 URL

## 影响范围

- 修改文件：
  - `tepexecor_frame/cte/log.py`
  - `tepexecor_frame/executor.py`
  - `tepexecor_frame/test_set.py`
  - `tepexecor_frame/cte/utils.py`
