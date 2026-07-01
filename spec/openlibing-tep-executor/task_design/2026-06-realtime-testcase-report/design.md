# Design: 实时用例上报功能 — 技术设计

## 总体架构

### 架构概述

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              整体架构                                        │
└─────────────────────────────────────────────────────────────────────────────┘

openlibing-tep-executor                       UniAutosPython3
┌─────────────────────────┐                  ┌─────────────────────────────────┐
│ executor.py             │                  │ Engine.py                       │
│  - __init__:            │──环境变量──▶    │  - _report_testcase_status()    │
│    set_pipeline_info()  │  (主进程设置)    │    (静态方法)                   │
│    set_obs_log_config() │                  │  - _runTest()                   │
│    set_testcase_map()   │                  │    - 上报 running               │
│  - prepare_test_cases() │                  │    - 执行用例                   │
│    生成 uuid            │                  │    - 上报全量状态               │
│    构建 testcase_map    │                  │                                 │
└─────────────────────────┘                  │ BBTEngine.py                    │
│                                            │  - _runTest()                   │
│ libing_api.py (新增)       │                  │    - 继承父类方法               │
│  - set_pipeline_info()    │                  │    - 上报 running               │
│  - get_pipeline_info()    │                  │    - 执行用例                   │
│  - build_report_json()    │                  │    - 上报全量状态               │
│  - report_testcase_status()│                  └─────────────────────────────────┘
│  - upload_testcase_result()│
│  - set_testcase_map()     │
│  - set_obs_log_config()   │
│  - _upload_case_log_file()│
└────────────────────────────┘
```

### 数据流（实际实现）

```
1. Executor 初始化 (__init__)
   └─▶ 解析命令行参数（hw_project_id, libing_secret）
   └─▶ 调用 set_pipeline_info() 设置环境变量：
       - PIPELINE_ID
       - PIPELINE_RUN_ID
       - JOB_RUN_ID
       - HW_PROJECT_ID
       - LIBING_APPCODE
   └─▶ 调用 set_obs_log_config() 设置 OBS 日志配置：
       - CASE_LOG_DIR
       - BASE_URL
       - LOG_BASE_URL
       - OBS_AK, OBS_SK, OBS_SERVER, OBS_BUCKET_NAME
       - TASK_PROJECT_ID

2. Executor prepare_test_cases()
   └─▶ 初始化 testcase_map = dict()
   └─▶ 循环 testcase_list：
       - 为每个元素生成 uuid (str(uuid.uuid4()))
       - 初始化字段（TC_RESULT, TC_BEGIN_TIME 等）
       - 构建 testcase_map (number -> tc)
   └─▶ 调用 set_testcase_map() 将 testcase_map 序列化为 JSON 存入环境变量

3. UniAutos 执行 (run_parallel / run_together)
   └─▶ 设置 PYTHONPATH 包含 tepexecor_frame 父目录
   └─▶ 启动子进程（自动继承主进程环境变量）

4. Engine 用例执行 (_runTest / _runConfiguration)
   └─▶ 条件导入 libing_api (LIBING_API_AVAILABLE 标志)
   └─▶ 执行前：
       - 调用 _report_testcase_status(testCase, "running")
       - 内部调用 report_testcase_status(testCase, "running")
         -> build_report_json(testCase, "running")
         -> upload_testcase_result(data)
   └─▶ 执行用例
   └─▶ 执行后：
       - 移动日志文件到 cases_log 目录
       - 获取日志 URL
       - 上传日志文件到 OBS
       - 调用 _report_testcase_status(testCase, testCase.caseStatus)
       - 内部调用 report_testcase_status(testCase, mapped_status)
         -> build_report_json(testCase, mapped_status)（包含日志 URL）
         -> upload_testcase_result(data)
```

## 关键设计决策

### 决策 1：testcase_map 设计

**问题**：如何快速查询和更新用例状态？

**决策**：采用 dict 结构，key 为 testcase 的 number 字段，value 为完整的 testcase dict 对象。

**实际实现**：
- 在 `prepare_test_cases` 方法中初始化并构建
- 通过 `set_testcase_map()` 函数将 testcase_map 序列化为 JSON 字符串存入环境变量
- 子进程通过 `get_testcase_map()` 函数从环境变量反序列化获取
- 用例上报时从 testcase_map 中获取基础数据，然后用 test_case 对象刷新相关字段

理由：
- number 是用例唯一标识，便于快速查询和更新
- dict 结构查询效率 O(1)，适合实时更新场景
- 通过环境变量传递，支持跨进程访问
- 环境变量自动被子进程继承，无需在 uniautos.py 中额外传递

### 决策 2：id 字段生成时机

**问题**：在何处为 testcase 生成唯一标识？

**决策**：在 `prepare_test_cases` 方法中为每个元素生成 uuid。

**实际实现**：
- 字段名为 `TC_UUID`（而非 `id`）
- 使用 `str(uuid.uuid4())` 生成唯一标识
- 在 prepare_test_cases 的循环中与 testcase_map 构建同时完成

理由：
- 职责单一 - 该方法专门用于初始化用例执行所需字段
- 与现有逻辑一致 - 已初始化 TC_RESULT、TC_BEGIN_TIME 等字段
- 更好的代码组织 - uuid 生成与其他字段初始化放在一起
- 确保所有执行前初始化集中在一个方法中

### 决策 3：参数传递方式（实际实现调整）

**问题**：如何将 pipeline_id、pipeline_run_id、job_id 从 executor 传递到 UniAutosPython3？

**设计决策**：采用 **环境变量** 方案，在 uniautos.py 的 `run_together` 方法中传递。

**实际实现**（优化后）：
- **在 executor.py 的 `__init__` 方法中调用 `set_pipeline_info()` 设置环境变量**
- 主进程设置，子进程自动继承（无需在 uniautos.py 中额外传递）
- 支持更多参数：hw_project_id、libing_appcode
- 通过 `get_pipeline_info()` 函数统一获取

理由：
1. **修改范围更小** - 仅需在 executor.py 中添加调用，无需修改 uniautos.py 的环境变量传递逻辑
2. **更符合进程模型** - 主进程设置环境变量，子进程自动继承，更符合 os.environ 的工作原理
3. **参数更完整** - 支持 hw_project_id、libing_appcode 等认证参数
4. **统一管理** - 所有 pipeline 信息通过 libing_api.py 的函数统一管理

### 决策 4：上报时机

**问题**：在哪些时机上报用例状态？

**分析**：UniAutosPython3 有多个 Engine 类：

| Engine 类 | 继承关系 | `_runTest` 方法来源 | 是否需要修改 |
|-----------|----------|---------------------|--------------|
| Engine | 基类 | 自己定义 | ✅ 是 |
| RatsEngine | Engine | 继承父类 | ❌ 否（使用父类） |
| BBTEngine | Engine | 自己定义 | ✅ 是 |
| BBTRatsEngine | RatsEngine | 继承父链 | ❌ 否（使用父链） |

Engine.py 中的执行方法：

| 方法 | 执行类型 | 是否需要上报 |
|------|----------|--------------|
| `_runTest` | 串行执行 Case | ✅ 是 |
| `_runTestParallel` | 并发执行 Case | ❌ 否（内部调用 `_runTest`） |
| `_runConfiguration` | 执行 Configuration | ✅ 是 |
| `runTestsInParallel` | 并发执行入口 | ❌ 否（调用 `_runTestParallel`） |

**决策**：
1. **Engine.py - Case 执行**：在 `_runTest` 方法中上报（覆盖串行和并发执行）
   - 执行前：上报 `running` 状态
   - 执行后：上报全量状态
2. **Engine.py - Configuration 执行**：在 `_runConfiguration` 方法中上报
   - 执行前：上报 `running` 状态
   - 执行后：上报全量状态（CONFIGURED/DE_CONFIGURED）
3. **BBTEngine.py - BBT Case 执行**：在 `_runTest` 方法中上报
   - BBTEngine 有独立的 `_runTest` 方法，需单独添加上报逻辑

**实际实现**：
- Engine.py：添加静态方法 `_report_testcase_status`，直接调用 `report_testcase_status`
- BBTEngine.py：继承 Engine 的 `_report_testcase_status` 方法，无需重新定义
- 实现更简洁，复用父类方法

### 决策 5：异常处理

**问题**：上报失败是否应阻塞用例执行？

**决策**：上报失败 **不阻塞** 用例执行，捕获异常后仅记录日志。

**实际实现**：
- libing_api.py 的 `report_testcase_status` 函数内部捕获所有异常
- UniAutosPython3 使用 `LIBING_API_AVAILABLE` 标志，导入失败时跳过上报
- 上报失败记录日志：`tep_executor_logger.info(f"Failed to report testcase status: {e}")`

理由：
1. 上报功能为辅助功能，不应影响主流程
2. 网络问题可能导致上报失败，不应中断测试执行

### 决策 6：PYTHONPATH 设置方式

**决策**：参考 `uniautos.py` 中 `run_parallel` 和 `run_together` 函数的实现，使用 os 环境变量设置。

**实际实现**：
```python
# uniautos.py 中，run_parallel 和 run_together 方法
extra_dirs = [os.path.dirname(self._plugin_base_dir)]  # tepexecor_frame 父目录
tag = ";" if utils.is_windows() else ":"
env_path = tag.join(
    [os.path.join(self._framework_dir, 'src', 'Framework', 'Dev', 'lib'),
     self._scripts_dir, *extra_dirs]
)
```

确保 `tepexecor_frame.cte.libing_api` 模块可直接 import。

### 决策 7：日志文件上传（新增）

**问题**：如何将用例日志上传到 OBS 并集成到上报 JSON？

**决策**：
- 在 executor.py 中调用 `set_obs_log_config()` 设置 OBS 配置
- 在 `build_report_json()` 函数中，对于非 running 状态：
  - 移动日志文件到 cases_log 目录
  - 获取日志 URL
  - 上传日志文件到 OBS
  - 将日志 URL 加入上报 JSON

**实际实现**：
- 使用 ObsLogConfig 数据类统一管理 OBS 配置参数
- 通过环境变量传递配置，子进程可直接获取
- `_upload_case_log_file()` 函数封装上传逻辑
- 日志 URL 通过 `utils.get_case_log_urls()` 获取

## 详细设计

### Part 1: openlibing-tep-executor 仓修改

#### 1.1 executor.py 参数设置（实际实现）

在 `__init__` 方法中，解析命令行参数后调用：

```python
# executor.py
parser.add_argument("--hw_project_id", required=False, help="HW项目ID（来源于CI）")
parser.add_argument("--libing_secret", required=False, help="Libing API凭证")

hw_project_id = args.hw_project_id if args.hw_project_id else None

set_pipeline_info(
    self.pipeline_id,
    self.pipeline_run_id,
    self.job_run_id,
    hw_project_id=hw_project_id,
    libing_appcode=args.libing_secret,
)
```

在 OBS 配置解析后调用：

```python
# 设置 OBS 日志配置
obs_log_config = ObsLogConfig(
    case_log_dir=self.cases_log_path,
    base_url=self.obs.get("base_url", ""),
    ak=self.obs.get("ak", ""),
    sk=self.obs.get("sk", ""),
    server=self.obs.get("server", ""),
    bucket_name=self.obs.get("bucket_name", ""),
    task_project_id=self.task_project_id
)
set_obs_log_config(obs_log_config)
```

#### 1.2 uuid 生成与 testcase_map 构建（实际实现）

在 `prepare_test_cases` 方法中：

```python
def prepare_test_cases(self):
    error_msg = u''
    self.testcase_map = dict()
    for tc in self.testcase_list:
        tc[TC_UUID] = str(uuid.uuid4())  # 新增：执行记录唯一标识
        tc[TC_RESULT] = ''
        tc[TC_BEGIN_TIME] = ''
        tc[TC_END_TIME] = ''
        tc[TC_ERROR_REASON] = error_msg
        tc[TC_FAILURE_CAUSE] = error_msg
        tc[TC_ERROR_INFO] = error_msg
        number = tc.get("number", "")
        if number:
            self.testcase_map[number] = tc
    # 将 testcase_map 存入环境变量，供子进程使用
    set_testcase_map(self.testcase_map)
```

#### 1.3 libing_api.py 结构（实际实现）

```python
"""libing 接口对接工具"""
import os
import json
import datetime
import requests
from dataclasses import dataclass
from typing import Dict, Any
from tepexecor_frame.cte.log import tep_executor_logger

@dataclass
class ObsLogConfig:
    """OBS日志配置参数"""
    case_log_dir: str
    base_url: str
    ak: str
    sk: str
    server: str
    bucket_name: str
    task_project_id: str

LIBING_API_URL = ("https://174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2."
                  "huaweicloudapis.com/openlibing-cicd/project/pipeline/test-case/report")

# 环境变量 key 定义
PIPELINE_ID_ENV_KEY = "PIPELINE_ID"
PIPELINE_RUN_ID_ENV_KEY = "PIPELINE_RUN_ID"
JOB_RUN_ID_ENV_KEY = "JOB_RUN_ID"
HW_PROJECT_ID_ENV_KEY = "HW_PROJECT_ID"
LIBING_APPCODE_ENV_KEY = "LIBING_APPCODE"
TESTCASE_MAP_ENV_KEY = "TESTCASE_MAP"
CASE_LOG_DIR_ENV_KEY = "CASE_LOG_DIR"
BASE_URL_ENV_KEY = "BASE_URL"
LOG_BASE_URL_ENV_KEY = "LOG_BASE_URL"
OBS_AK_ENV_KEY = "OBS_AK"
OBS_SK_ENV_KEY = "OBS_SK"
OBS_SERVER_ENV_KEY = "OBS_SERVER"
OBS_BUCKET_NAME_ENV_KEY = "OBS_BUCKET_NAME"
TASK_PROJECT_ID_ENV_KEY = "TASK_PROJECT_ID"

def set_pipeline_info(pipeline_id: str, pipeline_run_id: str, job_run_id: str,
                      hw_project_id: str = None, libing_appcode: str = None):
    """设置 pipeline 信息，用于用例实时上报"""

def get_pipeline_info() -> tuple:
    """获取 pipeline 信息"""
    return (pipeline_id, pipeline_run_id, job_run_id, hw_project_id, libing_appcode)

def set_testcase_map(testcase_map: Dict[str, Any]):
    """设置 testcase_map，用于用例信息传递"""

def get_testcase_map() -> Dict[str, Any]:
    """获取 testcase_map"""

def set_obs_log_config(config: ObsLogConfig):
    """设置 OBS 日志配置"""

def upload_testcase_result(data: Dict[str, Any]) -> bool:
    """上报用例结果到 libing（真实接口调用）"""

def build_report_json(test_case, status: str) -> Dict[str, Any]:
    """构建上报 JSON 数据结构"""

def report_testcase_status(test_case, status: str) -> bool:
    """上报用例状态到 libing（封装函数）"""

def _upload_case_log_file(src_file_path: str, obs_object_key: str) -> bool:
    """上传单个用例日志文件到 OBS"""

def _convert_time_to_timestamp(time_str) -> int:
    """将时间字符串转换为毫秒级时间戳"""

def _build_obs_url(base_url: str, task_project_id: str) -> str:
    """构建OBS URL路径"""
```

**关键特性**：
- **真实接口调用**：使用 `requests.post()` 调用 libing API
- **认证支持**：通过 `X-Apig-Appcode` header 进行认证
- **日志上传**：支持将用例日志上传到 OBS
- **环境变量管理**：统一管理所有环境变量 key
- **异常处理**：完整的异常捕获和日志记录
- **时间转换**：支持多种时间格式转换为毫秒级时间戳

#### 1.4 uniautos.py PYTHONPATH 设置（实际实现）

修改 `run_parallel` 和 `run_together` 方法：

```python
# 添加 tepexecor_frame 父目录，用于导入 cte/libing_api 模块
extra_dirs = [os.path.dirname(self._plugin_base_dir)]
tag = ";" if utils.is_windows() else ":"
env_path = tag.join(
    [os.path.join(self._framework_dir, 'src', 'Framework', 'Dev', 'lib'),
     self._scripts_dir, *extra_dirs]
)
```

### Part 2: UniAutosPython3 仓修改

#### 2.1 Engine.py 导入模块（实际实现）

```python
# 条件导入 libing_api 模块，用于用例实时上报
try:
    from tepexecor_frame.cte.libing_api import report_testcase_status
    LIBING_API_AVAILABLE = True
except ImportError:
    LIBING_API_AVAILABLE = False
```

#### 2.2 Engine.py 上报方法（实际实现）

```python
@staticmethod
def _report_testcase_status(testCase, status):
    """上报用例状态到 libing
    
    Args:
        testCase: 测试用例对象
        status: 用例状态
    """
    report_testcase_status(testCase, status)
```

#### 2.3 Engine.py 用例执行上报（实际实现）

在 `_runTest` 方法中添加：

```python
def _runTest(self, testCase, tcLogFile):
    # ... 现有代码 ...
    
    testCase.setStartTime(_start.strftime('%Y-%m-%d %H:%M:%S'))
    testCase.setCaseStatus(TEST_STATUS.RUNNING)
    
    # 上报 running 状态到 libing
    if LIBING_API_AVAILABLE:
        self._report_testcase_status(testCase, "running")
    
    # ... 执行用例 ...
    
    testCase.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
    
    # 上报全量状态到 libing
    if LIBING_API_AVAILABLE:
        self._report_testcase_status(testCase, testCase.caseStatus)
```

#### 2.4 Engine.py Configuration 上报（实际实现）

在 `_runConfiguration` 方法中添加：

```python
def _runConfiguration(self, configuration, tcLogFile):
    # ... 现有代码 ...
    
    # 上报 running 状态到 libing
    if LIBING_API_AVAILABLE:
        self._report_testcase_status(configuration, "running")
    
    # ... 执行逻辑 ...
    
    configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
    
    # 上报全量状态到 libing
    if LIBING_API_AVAILABLE:
        self._report_testcase_status(configuration, configuration.caseStatus)
```

#### 2.5 BBTEngine.py 修改（实际实现）

```python
# 条件导入 libing_api 模块，用于用例实时上报
try:
    from tepexecor_frame.cte.libing_api import report_testcase_status
    LIBING_API_AVAILABLE = True
except ImportError:
    LIBING_API_AVAILABLE = False

class BBTEngine(Engine):
    # 继承 Engine 的 _report_testcase_status 静态方法
    # 在 _runTest 方法中添加上报调用（与 Engine._runTest 相同）
```

### 状态映射

libing_api.py 内部的状态映射：

| UniAutos 状态 | libing 状态 |
|---------------|-------------|
| running | running |
| pass | passed |
| fail | failed |
| investigat | investigated |
| error | error |
| block | blocked |

映射逻辑：
```python
status_map = {
    "pass": "passed",
    "fail": "failed",
    "investigat": "investigated",
    "error": "error",
    "block": "blocked",
}
mapped_status = status_map.get(status.lower(), status)
```

## 影响范围

### openlibing-tep-executor 仓

| 文件 | 操作 | 说明 | 提交 |
|------|------|------|------|
| `tepexecor_frame/executor.py` | 修改 | 调用 set_pipeline_info、set_obs_log_config、set_testcase_map，prepare_test_cases 中生成 uuid 和 testcase_map，增加 TC_UUID 字段 | c123aa5 |
| `tepexecor_frame/uniautos.py` | 修改 | PYTHONPATH 设置包含 tepexecor_frame 父目录 | c123aa5 |
| `tepexecor_frame/cte/libing_api.py` | 新增 | libing 接口对接工具函数，完整实现（真实接口、日志上传） | c123aa5 |
| `tepexecor_frame/cte/obs_utils.py` | 修改 | 辅助功能（可能涉及） | c123aa5 |
| `tepexecor_frame/cte/utils.py` | 修改 | 辅助功能（可能涉及） | c123aa5 |

### UniAutosPython3 仓

| 文件 | 操作 | 说明 | 提交 |
|------|------|------|------|
| `Engine.py` | 修改 | 导入 libing_api，添加 `_report_testcase_status` 静态方法，在 `_runTest` 和 `_runConfiguration` 中调用 | 5ed7e5b |
| `BBTEngine.py` | 修改 | 导入 libing_api，继承 Engine 的 `_report_testcase_status` 方法，在 `_runTest` 中调用 | 5ed7e5b |

### 不影响

- 现有用例执行流程
- 现有日志记录机制
- 现有状态管理逻辑

## 风险 & 缓解

| 风险 | 缓解措施 | 状态 |
|------|---------|------|
| testcase_map 与 testcase_list 不同步 | 在每次修改 testcase_list 时同步更新 testcase_map | ✅ 已缓解（同一循环构建） |
| uuid 生成性能开销 | uuid.uuid4() 性能足够，单次任务用例数量通常 < 1000 | ✅ 已评估（无问题） |
| PYTHONPATH 设置影响其他模块 | 仅在必要时设置，不全局修改 | ✅ 已缓解 |
| 网络上报失败 | 捕获异常，不阻塞用例执行 | ✅ 已缓解（完整异常处理） |
| libing_api 模块导入失败 | 使用条件导入，设置可用性标志 | ✅ 已缓解 |
| 环境变量传递失败 | 主进程设置，子进程自动继承 | ✅ 已缓解 |

## 测试策略

### openlibing-tep-executor 仓

1. **单元测试**：验证 uuid 生成正确性
2. **单元测试**：验证 testcase_map 构建正确性
3. **单元测试**：验证 JSON 数据结构符合规范
4. **集成测试**：验证环境变量传递正确性
5. **集成测试**：验证 OBS 日志上传功能

### UniAutosPython3 仓

1. **单元测试**：验证 `_report_testcase_status` 方法的调用正确性
2. **集成测试**：验证环境变量传递链路正确性
3. **异常测试**：验证上报失败不影响用例执行
4. **异常测试**：验证导入失败不影响用例执行

### 跨仓集成测试

1. **端到端测试**：验证完整上报流程正常工作
2. **状态映射测试**：验证状态转换正确性
3. **日志上传测试**：验证日志文件上传和 URL 正确性
4. **性能测试**：验证上报不影响用例执行性能