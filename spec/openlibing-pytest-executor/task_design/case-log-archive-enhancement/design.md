# 用例日志归档增强 - 技术设计

## 方案概述

本方案通过改造 pytest-testkit 的日志目录结构和 pytest-executor 的报告处理流程，实现算子执行结果等结构化数据的自动归档和上传。

## 架构决策

### 决策 1：目录结构设计

**选择**：`logs/TestCases/日期/用例名_时间/文件`

**原因**：
- 日期层级便于按天管理和清理历史日志
- 用例名+时间戳确保目录唯一性，避免同名用例冲突
- 与现有 OBS 上传路径结构兼容

**替代方案**：`logs/TestCases/用例名/日期_时间/文件`
- 未选原因：不利于按日期批量清理，且用例名可能包含特殊字符

### 决策 2：zip 文件存放位置

**选择**：zip 文件与用例子目录同级，放在日期目录下

```
logs/TestCases/2026-06-02/
├── test_npu_info_11-38-05/          # 用例子目录
│   ├── testcase_id1.html
│   └── operator_results.xlsx
└── testcase_id1_log.zip              # 打包文件
```

**原因**：
- 保持 OBS 上传路径简洁
- 避免 zip 文件嵌套在子目录中导致路径过长
- 与 HTML 文件的 URL 生成逻辑保持一致

### 决策 3：logger.path 实现方式

**选择**：通过线程本地存储 `_local.case_log_path` 存储路径

**原因**：
- pytest 用例执行是单线程的，线程隔离足够
- 与现有 logger 实现方式保持一致（使用 `_local` 存储线程本地数据）
- 无需修改用例代码，通过 `logger.path` 属性即可获取

## 关键设计要点

### 1. 目录创建时序

```
pytest_runtest_setup (plugin.py)
    └── switch_to_case_log (log_factory.py)
        └── 创建用例目录并设置 _local.case_log_path
                └── 用例执行期间可通过 logger.path 获取路径
                    └── generate_html_report
                        └── HTML 生成在用例目录中
```

### 2. 打包触发时机

```
xml_processor.convert_case_name_for_results_and_log
    └── _replace_log_case_name
        └── 重命名 HTML 文件后
            └── _package_case_logs
                └── 扫描用例目录，打包除插件生成的 HTML 之外的所有文件（如有）
```

**打包逻辑说明**：
- 排除文件：仅排除 pytest-testkit 插件生成的 HTML 文件（文件名格式：`{case_name}.html`）
- 包含文件：用例自身生成的所有其他文件（包括用例自己创建的 HTML 文件、csv、xlsx、txt 等）
- 可选打包：如果用例目录下除插件生成的 HTML 外没有其他文件，则不生成 zip 文件

### 3. URL 生成规则

| 文件类型 | URL 格式 | 示例 |
|---------|---------|------|
| HTML 日志 | `{base_url}/{task_id}/{case_name}.html` | `.../task-001/test_case@env1.html` |
| 环境日志 zip | `{base_url}/{task_id}/{case_name}_log.zip` | `.../task-001/test_case@env1_log.zip` |

**envDownloadUrl 设置规则**：
- 仅当用例目录下存在需要打包的文件时，才在 `result_json_list` 中设置 `envDownloadUrl` 属性
- 如果没有需要打包的文件，`envDownloadUrl` 属性不出现（不设置为 null 或空字符串）

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `pytest-testkit/pytest_testkit/lib/common/log/log_factory.py` | 修改 | 新增目录层级，添加 logger.path 属性 |
| `pytest-executor/pytest_executor/src/report/xml_processor.py` | 修改 | 适配新目录扫描，新增打包方法 |
| `pytest-executor/pytest_executor/src/report/report_uploader.py` | 修改 | 生成 envDownloadUrl |

## 接口变更

### 新增属性

```python
# InfraLogger 类新增属性
@property
def path(self) -> Optional[str]:
    """返回当前用例的日志归档目录路径"""
    return getattr(_local, 'case_log_path', None)
```

### 新增方法

```python
# XmlProcessor 类新增方法
def _package_case_logs(self, case_dir: Path, case_name: str, env_case_info: Dict) -> Optional[Path]:
    """打包用例目录下的非 HTML 文件"""
```

## 风险 & 缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 目录层级变深导致路径过长 | 高（Windows 限制 260 字符） | 使用 `os.makedirs` 的 `exist_ok=True`，路径超过限制时记录警告 |
| zip 文件过大影响上传 | 中 | 不限制 zip 大小，依赖 OBS 上传能力；如需要可后续添加分卷功能 |
| 多线程用例执行时 logger.path 混乱 | 低 | 使用线程本地存储 `_local`，每个线程独立 |
| 旧版本兼容性问题 | 中 | 本次变更只影响新执行的测试，历史数据不受影响 |

## 测试策略

1. **单元测试**：
   - 验证目录结构生成正确
   - 验证 logger.path 返回正确路径
   - 验证打包功能正确处理各种文件类型

2. **集成测试**：
   - 完整执行流程验证
   - 多环境执行场景验证
   - OBS 上传和下载验证

## 性能考虑

- 目录创建：`os.makedirs` 使用 `exist_ok=True` 避免重复检查
- 文件打包：使用 `zipfile.ZIP_DEFLATED` 压缩，减少上传大小
- 目录扫描：使用 `pathlib.Path.glob` 递归扫描，避免深度递归
