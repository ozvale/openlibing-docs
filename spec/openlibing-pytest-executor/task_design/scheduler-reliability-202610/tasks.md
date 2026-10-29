# scheduler-reliability-202610 — 实现任务

## 进度

### 子需求 1-3 (Issue #66, 已交付 commit 490b84a + auto-fix 34945ef)

- [x] Task 1: `pytest-executor/main.py` 新增 `--pytest_testkit_whl_path` + 老参数兼容
- [x] Task 2: `pytest_executor.py` 三处执行入口走 pip install / `pytest @cases_file`
- [x] Task 3: `api_handler.upload_data_to_openlibing` 接入 `_retry_request`
- [x] Task 4: 对象存储上传链路保持现有行为，不纳入本期重试范围
- [x] Task 5: `pyproject.toml` `dependencies` 补 `pytest-testkit`
- [x] Task 6: `env_manager.py` 合入现有 `apply_env_res` 日志位置小改动
- [x] Task 7: 单测 `test_api_handler_retry.py` + `test_write_cases_file.py`
- [x] Task 8: 跑全量单测 9 passed

### 子需求 4 (Issue #69, 已交付 commit 34945ef)

- [x] Task 9: `run_scheduler.py` `_validate_execution_results` 加 16 行兜底（按 `case_list.remote_run` 标记判断）
- [x] Task 10: 单测 `test_validate_execution_results.py` 8 个分支

### 子需求 5 (Issue #73, 本期新增)

- [x] Task 11: `scheduler_config.py` 加 `lease_health_ttl_seconds` / `debug_keep_env` 字段
- [x] Task 12: `main.py` 新增 `--debug_keep_env` 隐藏参数 + Config.set
- [x] Task 13: `api_handler.py` 新增 `send_heartbeat_k8s` 静态方法 + `LeaseHeartbeatClient` 类
- [x] Task 14: `env_manager.py` K8s 申请时透传 `health_ttl` 字段（payload 顶层）；`release_env` / `release_all` 增加调试模式跳过
- [x] Task 15: `run_scheduler.py` `_allocate_environments_and_execute` 启动/停止心跳线程 (try/finally)
- [x] Task 16: 单测 `test_lease_heartbeat.py` 12 个用例

## 验证清单

### 需求 1-3

- [x] `pytest pytest-executor/tests/test_api_handler_retry.py` 5 passed
- [x] `pytest pytest-executor/tests/test_write_cases_file.py` 4 passed
- [x] argparse 老参数 `--pytest_testkit_path` 仍可接收，传值时打 deprecation 警告
- [x] 远端 `python -m pytest --version` 加载 `pytest_testkit-1.0.2` (从 PyPI 拉取)
- [x] 记录目标机实际安装版本（`pip show pytest-testkit`），便于问题复现
- [ ] cases_file 路径 `/home/<name>/.cases_<suffix>.txt` 在执行后被清理
  - [ ] 覆盖 pytest 非 0 返回分支
  - [ ] 覆盖 SSH 中断 / 异常退出分支
  - [ ] 覆盖 local 模式远端 `rm -f` 清理（`cleanup_step`）
- [ ] cases_file 命名安全性自测：`<suffix>` 不含路径分隔符与 `..`，写入路径不逃逸出 `self.test_dir` / `/home/<name>`；并发两任务文件名不冲突

### 需求 4

- [x] `pytest pytest-executor/tests/test_validate_execution_results.py` 8 passed
- [x] local 失败时 `_validate_execution_results` 返回 False、JOB FAILURE (生产日志 `Finished: FAILURE`)

### 需求 5

- [x] `pytest pytest-executor/tests/test_lease_heartbeat.py` 12 passed
- [ ] 调度机自测：--debug_keep_env 不释放环境
- [ ] 调度机自测：正常模式心跳线程启动 + INFO 日志可见
- [ ] 调度机自测：调度服务 404/409 模拟时线程停止
- [ ] 调度机自测：`debug_keep_env` 打开时启动处与跳过释放处出现 WARNING 日志
- [ ] 调度机自测：调试模式下 K8s 申请 payload 的 `health_ttl` 未透传 `-1`（发默认值 600 或不发送）
- [ ] 边界自测：`ttl_seconds=0` / `1` / `2` 时 `interval <= 0`，不启动心跳线程且无忙循环（打 WARNING）
