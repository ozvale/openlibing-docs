# TEP Executor 日志增强 — 实现任务

## 进度: 0/7 complete

## 实现任务

- [ ] **Task 1**: 修改 `tepexecor_frame/cte/log.py` - 新增 tep_executor_logger 和文件处理器
  - 新增 `tep_executor_logger` logger
  - 新增 `ExtRotatingFileHandler` 处理器
  - 配置 20MB 轮转，保留 25 份

- [ ] **Task 2**: 修改 `tepexecor_frame/cte/log.py` - 新增 `change_tep_executor_logger_file_handler` 函数
  - 参考 `change_logger_file_handler` 实现
  - 支持按 group_id 动态修改日志文件

- [ ] **Task 3**: 修改 `tepexecor_frame/executor.py` - 增强 `_add_file_to_zip` 方法
  - 增加 `[ADD]` 和 `[SKIP]` 日志打印到 tep_executor_logger

- [ ] **Task 4**: 修改 `tepexecor_frame/executor.py` - 增强 `_get_all_testset_files` 方法
  - 打印 `_tmp_testset_files` 文件列表到 tep_executor_logger

- [ ] **Task 5**: 修改 `tepexecor_frame/executor.py` - 增强 `generate_logs` 方法
  - 打印所有日志文件 URL 到 tep_executor_logger

- [ ] **Task 6**: 修改 `tepexecor_frame/test_set.py` - 增强 `TestSet.gen` 方法
  - 打印 `Valid testset files` 到 tep_executor_logger

- [ ] **Task 7**: 修改 `tepexecor_frame/cte/utils.py` - 增强 `get_metadata_info_from_testset` 函数
  - 打印 `process testset file` 到 tep_executor_logger

## 验证任务

- [ ] **Task 8**: 本地运行测试，验证 tep-executor.log 生成
- [ ] **Task 9**: 验证 `change_tep_executor_logger_file_handler` 动态修改日志文件功能
- [ ] **Task 10**: 验证压缩文件日志打印
- [ ] **Task 11**: 验证日志文件 URL 打印
