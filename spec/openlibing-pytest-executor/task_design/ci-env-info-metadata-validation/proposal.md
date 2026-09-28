# ci-env-info-metadata-validation

## 需求背景

pytest 用例在执行时无法感知自己跑在哪一次 CI 运行里。调度框架只知道 `pipeline_id` /
`pipeline_run_id` / `job_run_id` 这类内部 ID（`Config.job_info`），而 CI 平台通过 runner
环境变量暴露的是人类可读的上下文：仓库名、工作流名、job 名、运行序号、step 名。

缺少这份信息的直接后果：

- 用例内部无法按 CI 上下文做归因，日志和上报结果里看不出这条用例属于哪条流水线的哪一步；
- 排查一次夜间跑的失败时，需要人工在 CI 控制台和执行日志之间来回比对 ID；
- 用例若想引用 CI 元数据，只能各自去猜 runner 的环境变量名，而 `local` 执行模式下用例
  进程运行在远端测试机上，根本不继承调度机的环境，猜也猜不到。

因此需要一条从 CI runner 到用例进程的稳定通道，并且这条通道要覆盖
`runner` / `remote` / `local` 三种执行模式。

## 功能描述

**做什么**

1. 调度插件 `pytest-orch` 采集 5 个 runner 环境变量，按固定字段名组装成分组 JSON：

   | 来源环境变量         | 目标字段        |
   | -------------------- | --------------- |
   | `ATOMGIT_REPOSITORY` | `project_name`  |
   | `ATOMGIT_WORKFLOW`   | `workflow_name` |
   | `ATOMGIT_JOB`        | `job_name`      |
   | `ATOMGIT_RUN_NUMBER` | `run_number`    |
   | `ATOMGIT_ACTION`     | `step_name`     |

2. 插件通过 `--ci_env_info` 命令行参数把 JSON 透传给调度框架 `main.py`。
3. 调度框架在 `Config` 上以 `{"ci_env_info": {...}}` 分组保存，并对入参做
   结构校验、字段白名单过滤、值清洗（控制字符剔除、标量转字符串、超长截断、五键补齐）。
4. 执行用例时，分组内容序列化为**一个**名为 `ci_env_info` 的环境变量注入用例进程，
   三种执行模式行为一致。
5. 用例侧统一读取方式：

   ```python
   import json
   import os

   info = json.loads(os.environ.get("ci_env_info", "{}"))
   info["project_name"]  # 白名单 5 个字段恒定存在，缺失为空串
   ```

**不做什么**

- 不改动既有 `Config.job_info` / `job_unique_id` 的语义与采集方式，二者并存；
- 不把 CI 元数据接入测试结果上报体，上报字段映射不在本次范围；
- 不在 CI 控制台新增展示面板（插件侧只做参数回显，便于排查）；
- 不承诺字段值的业务合法性校验（例如不校验 `run_number` 是否为数字），
  清洗只保证「能安全进入环境变量和远端 shell」。

## 验收标准

- [x] 插件能把 5 个 `ATOMGIT_*` 变量组装为 `{"ci_env_info": {...}}` 并通过
      `--ci_env_info` 传给 `main.py`；任一变量未设置时对应字段为 `""`
- [x] `main.py` 接受 `--ci_env_info`，缺省、空串、非法 JSON 均不导致调度失败
- [x] `Config.validate_ci_env_info` 对任意输入返回
      `{"ci_env_info": {...}}`，且分组内白名单 5 个字段恒在、值恒为字符串
- [x] 非法输入（分组非字典、含未支持字段、值非标量、含控制字符、超长）
      降级为安全值并输出告警，告警不回显原始值内容
- [x] `runner` / `remote` 模式通过子进程环境字典注入；`local` 模式通过
      远端 shell 的 `export` 注入，且值经 `shlex.quote` 转义
- [x] 用例侧 `json.loads(os.environ["ci_env_info"])` 在三种模式下都能拿到 5 个字段
- [x] 非 ASCII 值经 `ensure_ascii` 输出为纯 ASCII JSON，经 SSH 链路不产生乱码
- [x] 新增单元测试覆盖校验器、CLI 解析、执行器注入三层，全量测试通过
- [ ] 值清洗的字符白名单收窄（Unicode 孤立代理、Cf 格式字符两类缺口）
      —— 已实测确认存在，修复未获授权，见 design.md「已识别但未修复的缺口」

## 影响范围

**业务仓 `openlibing-pytest-executor`**

| 文件                                                | 影响                                                                                      |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `pytest-executor/main.py`                           | 新增 `--ci_env_info` CLI 参数与 `_parse_ci_env_info`，接入 `_init_config`                 |
| `pytest-executor/src/scheduler/scheduler_config.py` | 新增 `ci_env_info` 配置项、白名单/长度常量、`validate_ci_env_info`、`_clean_ci_env_value` |
| `pytest-executor/src/executor/pytest_executor.py`   | 新增 `_ci_env_vars`、`_ci_env_exports`，接入三种执行模式                                  |
| `pytest-executor/tests/test_ci_env_info.py`         | 新增测试文件                                                                              |

**业务仓 `test-action`**

| 文件                        | 影响                                                                       |
| --------------------------- | -------------------------------------------------------------------------- |
| `pytest-orch/index.js`      | 新增 `buildCiEnvInfo()`、参数透传与日志回显                                |
| `pytest-orch/dist/index.js` | `index.js` 经 ncc 重新打包的产物（`action.yml` 的 `runs.main` 指向此文件） |

**用例侧（下游消费方）**

`ci_env_info` 环境变量的 JSON 值现在**恒定包含 5 个键**。原先若写过
`json.loads(...) == 传入的 dict` 这类断言，需要调整为按键访问。
