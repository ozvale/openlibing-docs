# Proposal: 实时用例上报功能

## 背景

当前 Executor 在执行测试用例时，用例结果仅在任务完成后批量上报。为支持实时监控测试进度，需要实现用例执行过程中的实时上报能力，对接 libing 接口将用例状态实时推送。

本需求涉及两个仓库的协同修改：
1. **openlibing-tep-executor**：实现实时上报的基础设施（libing_api.py 模块）
2. **UniAutosPython3**：在测试框架中集成实时上报功能

## 需求来源

关联 Issue: openlibing/openlibing-tep-executor#16

## 功能描述

### openlibing-tep-executor 仓

1. 在 `cte` 目录下创建对接 libing 接口的 utils 文件（`libing_api.py`），实现 JSON 数据上报接口
2. 参考 `uniautos.py` 中 `run_parallel` 和 `run_together` 函数的 PYTHONPATH 设置方式，支持从 cte 目录直接 import 模块
3. 为 `testcase_list` 每个元素增加 `id` 字段，使用 uuid 生成唯一标识
4. 增加 `testcase_map` 成员，key 为 testcase 的 number，value 为 testcase 元素，便于快速查询和更新
5. 生成上报 JSON 数据结构，包含 pipelineId、pipelineRunId、jobId、hwProjectId 和 testCasesResult

### UniAutosPython3 仓

1. 用例执行前，能够上报 `running` 状态到 libing 接口
2. 用例执行结束后，能够上报全量状态（包含开始时间、结束时间、执行结果等）
3. 能够正确传递 pipeline_id、pipeline_run_id、job_id 参数
4. 不影响现有用例执行流程

## 验收标准

### openlibing-tep-executor 仓

- [x] cte 目录下新增 `libing_api.py` 文件，包含上报接口函数
  - 提交：c123aa5961602e747f02eaea128fc691a29c38a2
  - 包含完整实现：set_pipeline_info、get_pipeline_info、build_report_json、report_testcase_status 等
  - 支持日志文件上传到 OBS
  - 支持通过环境变量跨进程传递数据
- [x] PYTHONPATH 设置支持从 cte 目录导入模块
  - 提交：c123aa5961602e747f02eaea128fc691a29c38a2
  - 在 uniautos.py 中设置 PYTHONPATH 包含 tepexecor_frame 父目录
- [x] `testcase_list` 每个元素包含 `id` 字段（uuid 格式）
  - 提交：c123aa5961602e747f02eaea128fc691a29c38a2
  - 在 prepare_test_cases 中为每个元素生成 uuid
- [x] Executor 类新增 `testcase_map` 成员
  - 提交：c123aa5961602e747f02eaea128fc691a29c38a2
  - 在 prepare_test_cases 中构建并设置到环境变量
- [x] 生成符合规范的上报 JSON 数据结构
  - 提交：c123aa5961602e747f02eaea128fc691a29c38a2
  - build_report_json 实现完整
  - 包含日志 URL 和环境变量传递
- [ ] 相关单元测试通过（待验证）

### UniAutosPython3 仓

- [x] 用例执行前，能够上报 `running` 状态到 libing 接口
  - 提交：5ed7e5b6a1e068f91b868eddf014a96c93afea23
  - Engine 和 BBTEngine 的 _runTest 方法均已实现
- [x] 用例执行结束后，能够上报全量状态（包含开始时间、结束时间、执行结果等）
  - 提交：5ed7e5b6a1e068f91b868eddf014a96c93afea23
  - Engine 和 BBTEngine 的 _runTest 方法均已实现
  - Engine 的 _runConfiguration 方法也已实现
- [x] 能够正确传递 pipeline_id、pipeline_run_id、job_id 参数
  - 提交：c123aa5961602e747f02eaea128fc691a29c38a2
  - 通过环境变量 PIPELINE_ID、PIPELINE_RUN_ID、JOB_RUN_ID 传递
  - 在 executor.py 的 __init__ 中调用 set_pipeline_info 设置
- [x] 不影响现有用例执行流程
  - 提交：5ed7e5b6a1e068f91b868eddf014a96c93afea23
  - 使用 try-except 条件导入，失败不影响执行
  - 上报异常被捕获，不阻塞执行

## 涉及仓库

| 仓库名 | 修改类型 | 说明 |
|--------|----------|------|
| openlibing-tep-executor | 主修改仓 | 实现上报基础设施 |
| UniAutosPython3 | 集成仓 | 集成上报功能到测试框架 |

## 修改文件清单

### openlibing-tep-executor 仓

| 文件路径 | 操作 | 说明 | 提交 |
|----------|------|------|------|
| `tepexecor_frame/cte/libing_api.py` | 新增 | libing 接口对接工具函数，包含完整实现 | c123aa5 |
| `tepexecor_frame/executor.py` | 修改 | 调用 set_pipeline_info 设置环境变量，prepare_test_cases 中生成 uuid 和 testcase_map，增加 TC_UUID 字段 | c123aa5 |
| `tepexecor_frame/uniautos.py` | 修改 | PYTHONPATH 设置包含 tepexecor_frame 父目录 | c123aa5 |
| `tepexecor_frame/cte/obs_utils.py` | 修改 | 辅助功能（可能涉及） | c123aa5 |
| `tepexecor_frame/cte/utils.py` | 修改 | 辅助功能（可能涉及） | c123aa5 |

### UniAutosPython3 仓

| 文件路径 | 操作 | 说明 | 提交 |
|----------|------|------|------|
| `src/Framework/Dev/lib/UniAutos/TestEngine/Engine.py` | 修改 | 导入 libing_api，添加 `_report_testcase_status` 静态方法，在 `_runTest` 和 `_runConfiguration` 中调用 | 5ed7e5b |
| `src/Framework/Dev/lib/UniAutos/TestEngine/BBTEngine.py` | 修改 | 导入 libing_api，继承 Engine 的 `_report_testcase_status` 方法，在 `_runTest` 中调用 | 5ed7e5b |

## 风险评估

1. **低风险**：上报功能为增量添加，不影响现有执行流程
2. **依赖风险**：libing_api 模块路径依赖 PYTHONPATH 正确设置 ✅ 已解决
3. **网络风险**：上报接口调用失败不应阻塞用例执行 ✅ 已解决（异常捕获）
4. **testcase_map 同步风险**：testcase_map 与 testcase_list 需保持同步 ✅ 已解决（同一循环构建）

## 不做什么

- ~~不实现完整的 libing 接口认证逻辑（API 先写成占位符 `test_example`）~~ **已实现完整接口调用**
- 不修改现有用例执行流程的核心逻辑 ✅ 已遵守

## 实现总结

### 已实现功能

1. **完整的 libing API 对接**：
   - 真实接口调用（非占位符）
   - 支持 hw_project_id 和 libing_appcode 参数
   - 完整的异常处理和日志记录

2. **环境变量传递机制**：
   - 主进程设置环境变量，子进程自动继承
   - 支持 pipeline_id、pipeline_run_id、job_run_id、hw_project_id、libing_appcode
   - 支持 testcase_map 通过 JSON 序列化传递

3. **日志文件上传**：
   - 支持将用例日志上传到 OBS
   - 自动构建日志 URL
   - 集成到上报 JSON 中

4. **测试框架集成**：
   - Engine 和 BBTEngine 均支持实时上报
   - 支持用例（Case）和配置（Configuration）两种类型
   - 条件导入确保向后兼容