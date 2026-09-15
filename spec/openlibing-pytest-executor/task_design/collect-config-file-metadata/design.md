# Design: 支持可选 collect_config_file 用于元数据收集

## 技术方案

### 方案概述

在 pytest-executor 的元数据收集链路上新增一个可选配置入口 `--collect_config_file`，通过 `Config` 类属性承载，由 `PytestCollector.metadata_collect` 读取并据此切换 `-c` 目标与 test_paths 处理逻辑。复用 pytest 原生 `-c` + testpaths 机制，无需自研路径解析。

### 传递链路

```text
CLI (--collect_config_file)
    ↓
main.parse_args() / main._init_config()
    ↓
Config.collect_config_file
    ↓
PytestCollector.metadata_collect() 读取并切换 -c / test_paths
    ↓
start.sh 透传环境变量
```

### 实现细节

#### 1. CLI 参数与 Config 属性

`main.py` 新增参数：

```python
parser.add_argument(
    "--collect_config_file",
    required=False,
    default=None,
    help=(
        "Optional pytest config file (relative to testcase_dir) used for "
        "test case metadata collection; defaults to the original flow when omitted"
    ),
)
```

`_init_config` 中写入 Config：

```python
Config.set("collect_config_file", args.collect_config_file)
```

`scheduler_config.py` 新增类属性：

```python
class Config:
    # 元数据收集专用配置文件, 未传入时走原有流程(testcase_config_file/pytest.ini)
    collect_config_file = None
```

#### 2. metadata_collect 分支逻辑

```text
读取 Config.collect_config_file
    ↓
collect_config_file 非空?
  ├─ 是 → 拼接 candidate_path = test_dir / collect_config_file
  │       ├─ 存在 → config_path = candidate_path; test_paths = []
  │       └─ 不存在 → 警告; config_path = None; 走默认流程
  └─ 否 → config_path = None; test_paths = _get_test_paths()（空则回退 "."）
    ↓
组装 pytest_args（公共参数：--job-id、--collect-only、-W、-qq）
    ↓
config_path 非空?
  ├─ 是 → pytest_args += ["-c", str(config_path), f"--rootdir={target_dir_str}"]
  └─ 否 → pytest_args += ["-c", os.devnull]
    ↓
pytest_args += test_paths
```

关键决策：

- **路径校验**：`candidate_path = self.test_dir / collect_config_file`，使用 `Path.exists()` 判定，不存在时 `logger.warning` 并回退，保证健壮性。
- **test_paths 切换**：使用 `config_path` 时置空 `test_paths`，交由 pytest 读取 `-c` 配置文件中的 testpaths，避免双源冲突。
- **--rootdir 显式设定**为 `target_dir_str`，确保 pytest 以 `testcase_dir` 作为根目录解析配置中的相对 testpaths。

#### 3. start.sh 透传

使用 shell 参数展开实现仅在环境变量非空时透传，与 `testcase_config_file` 方式一致：

```bash
${collect_config_file:+--collect_config_file "${collect_config_file}"}
```

### 边缘情况处理

| 场景                           | 处理方式                                                       |
| ------------------------------ | -------------------------------------------------------------- |
| 未传入 `--collect_config_file` | 走原有流程，`-c os.devnull` + 显式 test_paths                  |
| 传入且文件存在                 | 使用该文件作为 `-c`，`--rootdir=testcase_dir`，test_paths 置空 |
| 传入但文件不存在               | warning 日志，回退到默认空配置流程                             |
| `_get_test_paths()` 返回空     | 默认流程下回退为 `["."]`                                       |

### 向后兼容性

1. 参数默认 `None`，未传入时行为与原版本完全一致。
2. `_get_test_paths()` 未修改，仍只读取 `testcase_config_file` / `pytest.ini`，不受 `collect_config_file` 影响。
3. `metadata_collect` 方法签名未变，仅内部分支行为扩展。

## 文件修改清单

| 文件                                                   | 修改内容                                                    | 行数估算 |
| ------------------------------------------------------ | ----------------------------------------------------------- | -------- |
| pytest-executor/main.py                                | 新增 `--collect_config_file` CLI 参数与 `_init_config` 写入 | +10      |
| pytest-executor/src/scheduler/scheduler_config.py      | Config 新增 `collect_config_file` 属性                      | +2       |
| pytest-executor/src/case_collector/pytest_collector.py | `metadata_collect` 分支逻辑                                 | +30      |
| pytest-executor/start.sh                               | 透传 `collect_config_file`                                  | +1       |
| pytest-executor/tests/test_pytest_collector.py         | 新增三类测试                                                | +210     |

## 测试策略

### 单元测试

1. **TestGetTestPaths**：验证 `_get_test_paths()` 行为不变（读取 `testcase_config_file` / `pytest.ini`，忽略 `collect_config_file`）。
2. **TestMetadataCollectConfig**：
   - 默认流程使用 `-c os.devnull` 并包含 `.`。
   - 传入存在的 `collect_config_file` 时使用 `-c <path>` + `--rootdir`，不含 test_paths。
   - 传入不存在的文件时回退默认流程。
3. **TestCollectConfigFileArg**：CLI 解析默认 `None` 与显式传值。

### 验证方式

通过 `monkeypatch` 替换 `subprocess.run` 捕获 pytest 参数，断言 `-c` 目标、`--rootdir` 与 test_paths 的组合符合预期。
