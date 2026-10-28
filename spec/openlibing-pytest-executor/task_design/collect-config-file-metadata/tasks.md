# 支持可选 collect_config_file 用于元数据收集 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 新增 CLI 参数与 Config 属性
  - main.py 新增 `--collect_config_file` 参数（default=None）
  - `_init_config` 中 `Config.set("collect_config_file", args.collect_config_file)`
  - scheduler_config.py 新增 `collect_config_file = None` 类属性

- [x] Task 2: metadata_collect 分支逻辑
  - 读取 `Config.collect_config_file`，拼接 `test_dir / collect_config_file`
  - 文件存在时 `config_path = candidate_path`，`test_paths = []`
  - 文件不存在时 warning 并回退默认流程
  - `config_path` 非空时追加 `["-c", str(config_path), f"--rootdir={target_dir_str}"]`
  - 否则追加 `["-c", os.devnull]`

- [x] Task 3: start.sh 透传
  - 使用 `${collect_config_file:+--collect_config_file "${collect_config_file}"}` 透传

- [x] Task 4: 补充单元测试
  - TestGetTestPaths：验证 `_get_test_paths()` 行为不变
  - TestMetadataCollectConfig：默认流程 / 存在配置 / 缺失配置三分支
  - TestCollectConfigFileArg：CLI 解析默认 None 与显式传值

## 关键约束

- 保持完全向后兼容，未传入参数时行为与原版本一致
- `_get_test_paths()` 不受 `collect_config_file` 影响
- 路径相对 `testcase_dir`，由 Collector 内部拼接绝对路径并校验
- 文件不存在时回退默认流程，不抛异常

## 涉及文件

| 文件                                                   | 操作 | 说明                                  |
| ------------------------------------------------------ | ---- | ------------------------------------- |
| pytest-executor/main.py                                | 修改 | 新增 CLI 参数与 Config 写入（+10 行） |
| pytest-executor/src/scheduler/scheduler_config.py      | 修改 | Config 新增属性（+2 行）              |
| pytest-executor/src/case_collector/pytest_collector.py | 修改 | metadata_collect 分支逻辑（+30 行）   |
| pytest-executor/start.sh                               | 修改 | 透传 collect_config_file（+1 行）     |
| pytest-executor/tests/test_pytest_collector.py         | 修改 | 新增三类测试（+210 行）               |

## 验证方式

- 默认流程测试：未传入时命令包含 `-c os.devnull` 与 `.`
- 配置存在测试：传入存在文件时命令包含 `-c <path>` + `--rootdir=<testcase_dir>`，不含 test_paths
- 配置缺失测试：传入不存在文件时回退默认流程并输出 warning
- CLI 解析测试：默认 None，显式传值正确解析
