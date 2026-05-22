# Design: config-list-format

## Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│        Config JSON 列表格式处理流程                            │
└───────────────────────────────────────────────────────────────┘

                    --config test.json
                           │
                           ▼
              ┌─────────────────────────────┐
              │   JSON 格式判断              │
              │                             │
              │  isinstance(data, list)?    │
              └─────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
      [字典格式]                        [列表格式]
           │                               │
           ▼                               ▼
  ┌─────────────────┐          ┌─────────────────────────┐
  │ 原有流程        │          │ 简洁优雅方案             │
  │                 │          │                         │
  │ test_paths合一  │          │ 第一个元素走原有流程     │
  │ (Issue #11)     │          │ ├─ testcase_list        │
  │                 │          │ ├─ userconfig           │
  │ testcase合并    │          │ ├─ env_config           │
  │ userconfig合并  │          │ └─ test_paths           │
  │ env_config合并  │          │                         │
  │                 │          │ 同时保存整个列表：       │
  │ max_workers=1   │          │ self.config_list =      │
  │ 或 parallelNum  │          │   config_json_data      │
  │                 │          │                         │
  │                 │          │ npu_parallel_num =      │
  │                 │          │   len(config_json_data) │
  └─────────────────┘          └─────────────────────────┘
           │                               │
           │                               │
           │                               ▼
           │                    ┌─────────────────────────┐
           │                    │ 传递 config_list        │
           │                    │                         │
           │                    │ executor → uniautos     │
           │                    │ uniautos → TestSet      │
           │                    └─────────────────────────┘
           │                               │
           ▼                               ▼
  ┌─────────────────┐          ┌─────────────────────────┐
  │ 单个 testSet    │          │ 多个独立 testSet        │
  │ 文件生成        │          │ 文件生成                │
  │                 │          │                         │
  │ testSet_        │          │ __find_testset_files    │
  │ Standard.uts    │          │ _include_cases()        │
  │                 │          │                         │
  │ (合并所有用例)  │          │ 遍历 config_list        │
  │                 │          │ ├─ 元素0: testSet_0.uts │
  │                 │          │ ├─ 元素1: testSet_1.uts │
  │                 │          │ ├─ 元素2: testSet_2.uts │
  │                 │          │ └─ ...                  │
  └─────────────────┘          └─────────────────────────┘
```

## Implementation Details

### 1. executor.py accept_para() - JSON 格式判断

在解析 JSON 后，立即判断类型：

```python
# 第 275 行，新增格式判断
with open(testcase_file_path, 'r', encoding="utf-8") as f:
    config_json_data = json.load(f)

# 新增：判断 config_json_data 类型
self.config_list = None  # 初始化
if isinstance(config_json_data, dict):
    # 字典格式：保持原有流程
    # ... 原有代码 ...
elif isinstance(config_json_data, list):
    # 列表格式：简洁优雅方案
    if len(config_json_data) == 0:
        raise Exception("Config list is empty")
    
    # 使用第一个元素走原有流程
    first_config = config_json_data[0]
    if not isinstance(first_config, dict):
        raise Exception("First config element must be dict")
    
    # 保存整个列表
    self.config_list = config_json_data
    
    # 设置并行数量
    npu_parallel_num = len(config_json_data)
    self.executor.set_max_workers(npu_parallel_num)
    
    # 使用第一个元素继续原有流程
    config_json_data = first_config
    # ... 继续原有代码 ...
else:
    raise Exception(f"Invalid config format: {type(config_json_data)}")
```

### 2. executor.py prepare() - 传递 config_list

修改 prepare() 方法，传递 config_list：

```python
# 第 581 行
def prepare(self):
    # 传递 config_list 到 uniautos.prepare()
    self.executor.prepare(
        self.data, 
        self.testcase_list, 
        self.env_config, 
        config_list=self.config_list  # 新增参数
    )
```

### 3. uniautos.py prepare() - 接收 config_list

修改 prepare() 方法签名和调用：

```python
# 第 92 行
def prepare(self, raw_task_info, test_cases, executor_info, config_list=None, args=None):
    # ... 原有代码 ...
    
    # 保存 config_list
    self._config_list = config_list
    
    # 第 132 行，传递到 TestSetGenParams
    test_set_files = TestSet(self.max_workers, config_list=config_list).gen(
        test_set_gen_params=TestSetGenParams(
            script_dirs=scripts_dirs,
            task_work_dir=self._task_work_dir,
            test_cases=self._test_cases,
            task_info=raw_task_info,
            product=product,
            test_set_dir=test_set_dir,
            kick_env=kick_env,
            roc_collect_log=roc_collect_log,
            roc_package_path=roc_package_path,
            roc_stage=roc_stage,
            lock_env_on_cte=lock_env_on_cte,
            collect_coverage_data=collect_coverage_data,
            config_list=config_list  # 新增字段
        )
    )
```

### 4. TestSetGenParams - 新增字段

修改 TestSetGenParams 数据类：

```python
# test_set.py 第 10-32 行
@dataclass
class TestSetGenParams:
    script_dirs: str
    task_work_dir: str
    test_cases: str
    task_info: dict = None
    product: str = None
    test_set_dir: str = None
    kick_env: bool = False
    roc_collect_log: str = None
    roc_package_path: str = None
    roc_stage: str = None
    lock_env_on_cte: str = None
    collect_coverage_data: str = None
    config_list: list = None  # 新增字段
```

### 5. TestSet.__init__() - 接收 config_list

修改 TestSet 初始化：

```python
# test_set.py 第 35-38 行
class TestSet(object):
    def __init__(self, max_workers, config_list=None):
        self.max_workers = max_workers
        self.config_list = config_list  # 新增属性
```

### 6. TestSet.__find_testset_files_include_cases() - 核心逻辑

修改核心方法，根据 config_list 组装 testSet 文件：

```python
# test_set.py 第 40-97 行
def __find_testset_files_include_cases(self, all_testset_files, test_cases, task_work_dir):
    """
    查找包含下发的测试用例的测试套，并拷贝到任务目录
    """
    if self.config_list:
        # 列表格式：每个元素独立处理
        return self.__find_testset_by_config_list(
            all_testset_files, self.config_list, task_work_dir
        )
    else:
        # 字典格式：原有逻辑
        return self.__find_testset_original(
            all_testset_files, test_cases, task_work_dir
        )

def __find_testset_by_config_list(self, all_testset_files, config_list, task_work_dir):
    """
    根据配置列表组装独立的 testSet 文件
    """
    valid_testset_files = []
    
    for config_idx, config_item in enumerate(config_list):
        # 提取当前元素的 testcase
        testcase_list = config_item.get("testcase", [])
        
        if not testcase_list:
            logger.warning(f"Config element {config_idx} has no testcase")
            continue
        
        # 查找包含这些 testcase 的 testSet 文件
        not_found_cases, testset_files_for_config = self.__find_testset_original(
            all_testset_files, testcase_list, task_work_dir
        )
        
        if not_found_cases:
            logger.error(f"Config {config_idx}: cases {not_found_cases} not found")
        
        # 为每个配置的 testSet 文件添加索引标识
        for testset_file in testset_files_for_config:
            # 重命名文件以标识配置索引
            base_name = os.path.basename(testset_file)
            new_name = f"config{config_idx}_{base_name}"
            new_path = os.path.join(task_work_dir, new_name)
            
            if testset_file != new_path:
                shutil.move(testset_file, new_path)
                valid_testset_files.append(new_path)
            else:
                valid_testset_files.append(testset_file)
    
    return [], valid_testset_files

def __find_testset_original(self, all_testset_files, test_cases, task_work_dir):
    """
    原有的查找逻辑（保持不变）
    """
    # ... 原有的 40-97 行代码 ...
```

## Configuration Example

### 字典格式（向后兼容）
```json
{
    "testcase": [
        {"number": "TC_001", "ScriptName": "test_script"}
    ],
    "userconfig": {
        "param1": "value1"
    },
    "testPaths": [
        "scripts/module_a/"
    ],
    "parallelNum": 1
}
```

### 列表格式（新增功能）
```json
[
    {
        "testcase": [
            {"number": "TC_001", "ScriptName": "script_a"}
        ],
        "userconfig": {"param1": "value1"},
        "testPaths": ["scripts/module_a/"]
    },
    {
        "testcase": [
            {"number": "TC_002", "ScriptName": "script_b"}
        ],
        "userconfig": {"param2": "value2"},
        "testPaths": ["scripts/module_b/"]
    },
    {
        "testcase": [
            {"number": "TC_003", "ScriptName": "script_c"}
        ],
        "userconfig": {"param3": "value3"},
        "testPaths": ["scripts/module_c/"]
    }
]
```

## Behavior Comparison

| Config 格式 | 处理流程 | testSet 文件 | 并行数量 |
|------------|---------|-------------|---------|
| 字典格式 | 原有流程 | testSet_Standard.uts | parallelNum 或 1 |
| 列表格式 | 第一个元素 + config_list 传递 | config0_*.uts, config1_*.uts, ... | len(config_list) |

## File Changes

| 文件 | 修改位置 | 改动说明 |
|-----|---------|---------|
| executor.py | `__init__()` | 新增 `self.config_list = None` |
| executor.py | `accept_para()` | 新增 JSON 格式判断，列表格式处理 |
| executor.py | `prepare()` | 新增 `config_list` 参数传递 |
| uniautos.py | `prepare()` | 新增 `config_list` 参数接收和传递 |
| test_set.py | `TestSetGenParams` | 新增 `config_list: list = None` |
| test_set.py | `TestSet.__init__()` | 新增 `config_list` 参数接收 |
| test_set.py | `__find_testset_files_include_cases()` | 新增 `config_list` 判断和分支处理 |
| test_set.py | 新增方法 | `__find_testset_by_config_list()` |

## Edge Cases Handling

1. **列表为空**: 抛出异常，提示用户
2. **列表元素不是字典**: 抛出异常，提示格式错误
3. **列表元素缺少 testcase**: 记录警告，跳过该元素
4. **字典格式**: 完全保持原有行为（向后兼容）
5. **CI 参数合并**: 列表格式时，CI 参数只合并到第一个元素

## Advantages

1. **最小改动**: 主要修改集中在 executor.py 和 test_set.py
2. **向后兼容**: 字典格式完全保持原有行为
3. **逻辑清晰**: 第一个元素确保变量初始化，config_list 在 testSet 中处理
4. **易于维护**: 不破坏现有调用链
5. **简洁优雅**: 避免复杂的重构和参数传递