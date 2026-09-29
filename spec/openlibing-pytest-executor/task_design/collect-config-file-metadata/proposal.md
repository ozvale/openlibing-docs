# Proposal: 支持可选 collect_config_file 用于元数据收集

## 背景

pytest-executor 在测试用例元数据收集阶段（`metadata_collect`）通过调用 pytest 的 `--collect-only` 模式收集用例元信息。原有流程使用 `-c os.devnull` 作为空配置，并通过命令行显式追加 test_paths（来自 `testcase_config_file` 或 `pytest.ini`）。

在某些场景下，用户希望在元数据收集阶段使用一份独立的 pytest 配置文件（其中可自定义 testpaths、markers 等），而与执行阶段使用的配置解耦。原有链路不支持指定独立的收集配置文件。

- Commit: 0ac0a1d142c6f9485077a08f415a29d89c1660d4
- 仓库分支: tzing_dev

## 问题分析

原有 `metadata_collect` 流程的约束：

1. **固定使用空配置**：`-c os.devnull` 使 pytest 不读取任何 ini 配置，所有 testpaths 必须由命令行显式传入。
2. **testpaths 单一来源**：test_paths 由 `_get_test_paths()` 从 `testcase_config_file` / `pytest.ini` 解析，无法在收集阶段使用另一份配置。
3. **缺少配置隔离**：收集阶段与执行阶段共用同一份 testpaths 配置，无法分别定制。

当用户希望在收集阶段扫描与执行阶段不同的测试目录子集时，原有方案无法满足。

## 需求范围

新增可选参数 `--collect_config_file`，指定元数据收集阶段使用的 pytest 配置文件（路径相对 `testcase_dir`）。

### 功能目标

- 未传入参数时，走原有流程（`-c os.devnull` + 显式 test_paths），完全向后兼容。
- 传入且文件存在时，使用该文件作为 `-c` 配置，由 pytest 自行读取其中的 testpaths，不再显式追加命令行测试路径。
- 传入但文件不存在时，记录警告并回退到默认空配置流程。

### 非目标

- 不修改执行阶段的配置加载逻辑。
- 不修改 `_get_test_paths()` 的既有行为（该函数仍只读取 `testcase_config_file` / `pytest.ini`，不受 `collect_config_file` 影响）。

## 验收标准

1. 新增 CLI 参数 `--collect_config_file`，默认 `None`，可选传入。
2. 未传入时，`metadata_collect` 生成的 pytest 命令包含 `-c os.devnull` 及显式 test_paths（与原行为一致）。
3. 传入且文件存在时，pytest 命令包含 `-c <config_path>` 与 `--rootdir=<testcase_dir>`，且不追加 test_paths。
4. 传入但文件不存在时，回退到默认空配置流程并输出 warning 日志。
5. `_get_test_paths()` 不受 `collect_config_file` 影响。
6. `start.sh` 透传 `collect_config_file` 环境变量（仅在非空时透传）。
7. 相关单元测试覆盖以上分支并通过。
