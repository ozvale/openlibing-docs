# scheduler-reliability-202610

## 需求背景

`openlibing-pytest-executor/pytest-executor` 在生产环境运行中暴露出五类稳定性问题，属于父 issue openlibing/openlibing-pytest-executor#65 中第 6 项"pytest 可靠性优化"的子任务：

1. `pytest-testkit` 通过本地 whl 上传到调度容器安装，部署链路冗长且版本受构建机限制；
2. openlibing 上传元数据接口一旦发生瞬时网络抖动或服务端 5xx，整次报告上传失败，结果丢失；
3. pytest 命令行直接拼接用例 ID（含特殊字符、参数化标记），运维按用例名 `pkill -f` 排查时极易误杀整个 pytest 调度进程；
4. `_validate_execution_results` 在 local/remote xml 缺失时静默通过，导致 local SSH 失败时仍报 JOB SUCCESS；
5. K8s 动态调度环境在用例执行过程中被调度服务误判失联、自动释放（无心跳保活），且用例执行异常中止时调度机拿不到已执行用例的结果。

五个子需求合并在一个 PR 中交付，沿用父 issue 的"框架可靠性优化"主线。

## 功能描述

### 子需求 1：testkit 安装切换

- 默认 `pip install pytest-testkit`，来源复用 `Config.python_mirror_repo`，包版本取最新；
- 保留 whl 兜底：原 `--pytest_testkit_path` 改名为 `--pytest_testkit_whl_path`（强制改参数名，断绝旧调用点误传），传入时优先按 whl 安装；不传走 pip；
- `pyproject.toml` 的 `dependencies` 补齐 `pytest-testkit`。

### 子需求 2：上传接口重试

- `ApiHandler.upload_data_to_openlibing` 接入 `api_handler.py` 已有的 `_retry_request`（指数退避 1→2→4s，最多 3 次），5xx 与网络异常触发重试，4xx 不重试；
- 失败语义沿用：retry 全部失败时仍按现状抛异常 / 返回 `[]`；
- 不为重试参数新增 Config 暴露（与 K8s API 行为对齐，保持模块级常量）。

### 子需求 3：用例名文件化

- runner / remote / local 三种执行模式下，pytest 命令行不再直接出现用例 ID，改为 `python -m pytest @<cases_file>`，每行一个 nodeid；
- `cases_file` 落在当前执行 cwd（runner 模式落在 `/home/<name>`、remote 模式落在 `self.test_dir`、local 模式 scp 上传到 `/home/<name>`），文件名本期实现用 `.cases_<suffix>.txt`，无命名规则限制；
- 进程 cmdline 不再含具体用例名，运维 `pgrep -f <case_name>` 不再命中 pytest 调度进程；
- 行为无开关：直接改为文件执行方式（与子需求 1 的 whl 兜底开关不同）。

### 不做什么

- 不为重试增加 Config 暴露（与 K8s API 行为对齐，保持模块级常量）；
- 不动 `pytest-testkit` 源仓的 `pyproject.toml` / `device.py`（testkit 仓独立维护）；
- 不在本次引入 unittest 框架改动、白名单名单/单元测试套件改造；
- 不重写 `run_scheduler` 主流程、不动环境申请/释放逻辑（仅合入 `env_manager.py` 的日志位置微调）。

### 子需求 4：`_validate_execution_results` 兜住 xml 缺失

排查子需求 1-3 的过程中发现的次生 bug：

- 根因：[run_scheduler.py:188-203](file:///c:/work/code/openlibing/openlibing-pytest-executor/pytest-executor/src/run_scheduler.py#L188-L203) 的 `if local_results_xml and local_results_xml not in xml_files:` 在 `local_results_xml = None` 时短路跳过整段校验。
- 复现场景：2 个 local 用例因目标机 22 端口不可达未执行，但 1 个 remote case 在本调度机 self.test_dir 上跑过、生成 `remote_results_*.xml` 且 PASSED，调度器因 xml 缺失校验被跳过而报 SUCCESS。
- 修复：按 `case_list` 里 `case.remote_run` 标记判断"该 env 是否预期有 local/remote 用例"，预期有但对应 xml 字段为 None → 直接 return False。
- 不做：expected vs actual 用例名一致性校验（用例 name 在 report 中可能做过处理，字符串格式不可控）；不接 `_execute_remote_cases` 内部 `_prepare_test_environment` 返回值（silent degradation 源头，单独 issue 跟踪）。

### 子需求 5：K8s 动态调度环境心跳保活

接入 `C:\work\lease-heartbeat-api.md` 协议（外部接口文档）：

- **POST `/api/v1/envs/{env_id}/heartbeat`**，Authorization Bearer k8s_auth
- 响应 200：`{"last_heartbeat_at": "2026-10-13T10:00:00+08:00"}`
- 行为契约：
  - 200：成功，**仅打印**响应里 `last_heartbeat_at`（仅日志佐证），**不维护**任何客户端状态
  - 404/409/400：终态，**立即停止**心跳线程（重试无意义）
  - 5xx / 网络异常：WARNING，**不重试当前次**，按原间隔等下次自然 tick
- 调度主流程：
  - 正常模式：`Config.lease_health_ttl_seconds = 600`（默认），心跳线程每 200s 上报一次（health_ttl/3），任务结束正常释放环境
  - 调试模式：通过主入口隐藏参数 `--debug_keep_env` 打开，`Config.lease_health_ttl_seconds = -1`，**不启动**心跳线程，**不释放**环境（`release_env` / `release_all` 内部跳过），便于人工登入目标机排查
- 不做：
  - 心跳不延长 TTL，仅重置判死起点
  - 调度服务的"降级接入"——即使没心跳线程，调度端也接受心跳请求（不报错）
  - 上层"主流程在终态时主动 abort"的实现（仅打 ERROR + 停线程，调用方有责任检查 `_stop_reason`）

## 验收标准

- [ ] **AC-1 testkit 安装切换**
  - [ ] `pytest-executor` 默认通过 `pip install pytest-testkit`（最新版本，来源复用 `python_mirror_repo`）安装到目标机；
  - [ ] 保留 whl 兜底：`--pytest_testkit_path` 改名为 `--pytest_testkit_whl_path`，老参数仍被 argparse 接收（兼容），传值时仅打 deprecation 警告并强制走 pip install；新参数传入时才真正按 whl 安装；
  - [ ] `pyproject.toml` 的 `dependencies` 补齐 `pytest-testkit`；`requirements.txt` 已有无需改；
  - [ ] 远端 `/home/<name>` 不再残留 testkit whl 文件（除非显式走 whl 分支）。
- [ ] **AC-2 上传接口重试**
  - [ ] `ApiHandler.upload_data_to_openlibing` 接入 `_retry_request`（指数退避 1→2→4s，最多 3 次）；
  - [ ] **上传重试范围**：重试仅作用于 openlibing 报告上传链路；
  - [ ] 重试全部失败时沿用现有失败语义；
  - [ ] 新增单测覆盖：5xx→重试、4xx→不重试、网络异常→重试（仅针对 openlibing 上传）。
- [ ] **AC-3 用例名文件化**
  - [ ] runner / remote / local 三种执行模式下，pytest 命令行不再直接出现用例 ID；
  - [ ] `cases_file` 落在当前执行 cwd；
  - [ ] 进程 cmdline 不再含具体用例名；
  - [ ] 新增单测：cases_file 内容与原 case_list 一致、含特殊字符用例名不抛异常。
- [ ] **AC-4 `_validate_execution_results` 兜底**
  - [ ] local 模式 SSH 失败（local_results_xml 缺失）时 `_validate_execution_results` 返回 False、JOB 失败；
  - [ ] remote 模式 xml 缺失时同样返回 False；
  - [ ] 仅 local case 或仅 remote case 时，另一字段为 None 不再误报；
  - [ ] 单测覆盖：4 个核心场景 + 4 个回归场景；
- [ ] **AC-5 心跳保活**
  - [ ] `--debug_keep_env`（SUPPRESS 隐藏）打开时 `lease_health_ttl_seconds=-1`，不启动心跳线程，调度结束时 `release_env` / `release_all` 跳过；
  - [ ] 正常模式 ttl=600 时心跳线程每 200s 触发一次，INFO 日志含 `Heartbeat sending env_id=...`；
  - [ ] 收到 404/409/400 时线程立即停止（`stop_reason=http_xxx`），ERROR 日志；
  - [ ] 5xx / 网络异常仅 WARNING，不重试当前次，等下次自然 tick；
  - [ ] 单测 12 个全过：3 个 send_heartbeat_k8s 分支 + 8 个 LeaseHeartbeatClient 状态码分支 + 1 个 daemon 线程生命周期；
- [ ] **AC-6 通用收尾**
  - [ ] 五个子需求的代码改动合并为一个 PR；
  - [ ] PR 关联父 issue `#65` 与子 issue `#66` / `#69` / `#73`；
  - [ ] PR 加 `ai-assisted` 标签；
  - [ ] 沿用 Standard 模式，commit 粒度 = 一轮 AI 编码交付。

## 影响范围

| 文件                                                       | 操作   | 说明                                                                                                              |
| ---------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| `pytest-executor/main.py`                                  | 修改   | `--pytest_testkit_path` 改名为 `--pytest_testkit_whl_path`；新增 `--debug_keep_env` 隐藏参数                      |
| `pytest-executor/src/scheduler/scheduler_config.py`        | 修改   | `pytest_testkit_path` 保留兼容读取（deprecated）；新增 `lease_health_ttl_seconds` / `debug_keep_env`              |
| `pytest-executor/src/executor/pytest_executor.py`          | 修改   | 三处执行入口走 pip install / `pytest @cases_file`                                                                 |
| `pytest-executor/src/api/api_handler.py`                   | 修改   | `upload_data_to_openlibing` 接入 `_retry_request`；新增 `send_heartbeat_k8s` 静态方法 + `LeaseHeartbeatClient` 类 |
| `pytest-executor/src/api/obs_client.py`                    | 不修改 | 保持现有上传行为，不纳入本期重试范围                                                                              |
| `pytest-executor/src/scheduler/env_manager.py`             | 修改   | K8s 申请时透传 `health_ttl` 字段（payload 顶层）；`release_env` / `release_all` 增加调试模式跳过                  |
| `pytest-executor/src/run_scheduler.py`                     | 修改   | `_allocate_environments_and_execute` 内启动/停止心跳线程；`_validate_execution_results` 增 16 行兜底              |
| `pytest-executor/pyproject.toml`                           | 修改   | `dependencies` 补 `pytest-testkit`                                                                                |
| `pytest-executor/tests/test_api_handler_retry.py`          | 新增   | openlibing 上传重试单测                                                                                           |
| `pytest-executor/tests/test_write_cases_file.py`           | 新增   | cases_file 落盘单测                                                                                               |
| `pytest-executor/tests/test_validate_execution_results.py` | 新增   | xml 缺失兜底单测                                                                                                  |
| `pytest-executor/tests/test_lease_heartbeat.py`            | 新增   | 心跳保活单测                                                                                                      |

## 关联

- 父需求：openlibing/openlibing-pytest-executor#65（蓝区测试框架及插件优化第 6 项）
- 业务 Issue：
  - openlibing/openlibing-pytest-executor#66（testkit / 上传重试 / cases file）
  - openlibing/openlibing-pytest-executor#69（`_validate_execution_results` 兜底）
  - openlibing/openlibing-pytest-executor#73（K8s 心跳保活）
