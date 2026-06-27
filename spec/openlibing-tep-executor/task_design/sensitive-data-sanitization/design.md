# sensitive-data-sanitization — 技术设计

## 方案概述

通过实现敏感数据脱敏函数 `_sanitize_sensitive_data`，在日志打印前自动检测并替换敏感关键字对应的值为 `"***"`。采用递归结构处理嵌套数据类型，支持 JSON 格式解析和正则匹配两种处理方式。

## 架构决策

### 1. 脱敏函数设计

| 决策 | 原因 |
|------|------|
| 递归处理嵌套结构 | 支持多层 dict/list/tuple/set 嵌套 |
| JSON 优先解析 | JSON 格式字符串使用结构化处理更准确 |
| 正则兜底处理 | 非 JSON 字符串使用正则匹配关键字 |
| 辅助函数分离 | `_sanitize_sensitive_data_str` 职责单一，便于调试 |

### 2. 正则表达式设计

| 模式 | 匹配场景 | 示例 |
|------|---------|------|
| `"keyword": "value"` | JSON 格式（带引号） | `"password": "secret123"` |
| `keyword=value` | 等号格式（无空格分隔） | `token=abc123` |
| `keyword: value (space)` | 冒号格式（值包含空格） | `Authorization: Bearer eyJhbG...` |

### 3. Ansible 文件写入安全改进

| 问题 | 修复方案 |
|------|---------|
| `os.system` 通过 shell 传递密码 | 使用 Python `open()` 函数直接写入 |
| 文件权限未限制 | 添加 `os.chmod(yml_file, 0o600)` 限制读取权限 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `tepexecor_frame/cte/utils.py` | 新增/修改 | 核心脱敏函数实现 |
| `tepexecor_frame/unified.py` | 修改 | Ansible 文件安全写入 |
| `tepexecor_frame/test_set.py` | 修改 | kwargs 日志脱敏调用 |
| `tests/test_sanitize_sensitive_data.py` | 新增 | 单元测试（21 个用例） |

## 核心代码结构

```python
# utils.py

def _sanitize_sensitive_data_str(data_str, sensitive_keywords):
    """字符串类型正则匹配脱敏"""
    # 模式1: JSON 格式 "keyword": "value"
    # 模式2: keyword=value (无空格分隔)
    # 模式3: keyword: value (值包含空格)

def _sanitize_sensitive_data(data, max_length=100):
    """多类型脱敏入口"""
    if isinstance(data, dict):
        # 递归处理 dict，key 或 value 匹配敏感关键字时替换为 "***"
    elif isinstance(data, list):
        # 递归处理 list，元素匹配敏感关键字时替换为 "***"
    elif isinstance(data, str):
        # JSON 格式尝试解析后递归，否则调用 _sanitize_sensitive_data_str
    elif isinstance(data, (tuple, set, frozenset)):
        # 递归处理集合类型
    else:
        # 其他类型转 str 后正则处理
```

## 敏感关键字列表

```python
sensitive_keywords = [
    'password', 'passwd', 'pwd', 'secret', 'token',
    'api_key', 'access_key', 'private_key', 'credential',
    'authorization', 'ak=', 'sk=', 'apig_key', 'apig_secret'
]
```

## 调试日志

为方便排查脱敏失败情况，在核心递归分支和正则匹配处添加 `tep_executor_logger` 日志：

| 日志标签 | 记录内容 |
|---------|---------|
| `[SANITIZE]` | 函数入口、数据类型、None 值处理 |
| `[SANITIZE-DICT]` | key 匹配、嵌套递归、完成统计 |
| `[SANITIZE-LIST]` | index 处理、嵌套递归、完成统计 |
| `[SANITIZE-STR]` | 字符串长度、JSON 检测、正则匹配计数 |
| `[SANITIZE-TUPLE/SET]` | 嵌套递归、完成统计 |
| `[SANITIZE-OTHER]` | 其他类型处理 |

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| 正则匹配遗漏边界场景 | 21 个单元测试覆盖各种边界情况 |
| 性能影响（大量数据脱敏） | 设置 `max_length=100` 限制输出长度 |
| 调试日志过多 | 使用 `tep_executor_logger.debug` 级别，生产环境可过滤 |

## 测试策略

### 单元测试覆盖场景

| 场景 | 测试用例 |
|------|---------|
| 基础类型 | None、dict、list、str、tuple、set |
| JSON 格式 | `"password": "value"` |
| Authorization | `Bearer <token>` |
| 等号格式 | `token=value` |
| 混合格式 | `password=abc, token=xyz` |
| 嵌套结构 | `{'data': {'token': 'nested'}}` |
| 边界情况 | 空字符串、int/float/bool、无敏感关键字 |
| 多行字符串 | `password=abc\ntoken=xyz` |

## 跨仓影响

本次修改仅影响 `openlibing-tep-executor` 仓库，无跨仓接口变化。