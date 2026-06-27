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
| `keyword=value` | 等号/冒号格式（支持空格分隔） | `token=abc123`, `password = secret123` |
| `keyword: value (space)` | 冒号格式（值包含空格） | `Authorization: Bearer eyJhbG...` |

### 3. Ansible 文件写入安全改进

| 问题 | 修复方案 |
|------|---------|
| `os.system` 通过 shell 传递密码 | 使用 Python `open()` 函数直接写入 |
| 文件权限未限制（TOCTOU 竞态风险） | 使用 `os.open()` + `os.O_CREAT | os.O_WRONLY | os.O_EXCL` 原子创建，配合 `os.fchmod()` 在文件描述符级别设置权限，避免竞态窗口 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `tepexecor_frame/cte/utils.py` | 新增/修改 | 核心脱敏函数实现 |
| `tepexecor_frame/unified.py` | 修改 | Ansible 文件安全写入 |
| `tepexecor_frame/test_set.py` | 修改 | kwargs 日志脱敏调用 |
| `tests/test_sanitize_sensitive_data.py` | 新增 | 单元测试（44 个用例：21 原始 + 23 正则模式） |

## 核心代码结构

```python
# utils.py

def _sanitize_sensitive_data_str(data_str, sensitive_keywords):
    """字符串类型正则匹配脱敏"""
    for keyword in sensitive_keywords:
        if keyword in data_str.lower():
            kw = keyword.split('=')[0]
            patterns = [
                # 模式1: JSON 格式 "keyword": "value"
                (r'"' + re.escape(kw) + r'"\s*:\s*"[^"]*"', r'"' + kw + '": "***"'),
                # 模式2: keyword=value (值不含空格)
                (r'(' + re.escape(kw) + r'\s*[:=]\s*)[^\s,\'"\\}\]]+', r'\1***'),
                # 模式3: keyword: value (值包含空格)
                (r'(' + re.escape(kw) + r'\s*[:=]\s*)(.+?)(?=\s+[\w-]+[:=]|\s*$|\s*[,\'\"\\}\]])', r'\1***')
            ]
            for pattern, replacement in patterns:
                data_str = re.sub(pattern, replacement, data_str, flags=re.IGNORECASE)
    return data_str

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

```python
# unified.py - Ansible 文件安全写入（推荐实现）

def write_ansible_yml(write_ansible_yml_params: WriteAnsibleYmlParams):
    """write ansible linux.yml - 使用原子操作避免 TOCTOU 竞态"""
    host, number, username, password, os_type, port = astuple(write_ansible_yml_params)
    yml_path = os.path.join(ANSIBLE_GROUP_VARS_DIR, f'{os_type}{number}.yml')
    
    # 使用 os.open() 原子创建，O_EXCL 确保文件不存在时才创建
    fd = os.open(yml_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(f"ansible_ssh_user: {username}\nansible_ssh_pass: {password}\nansible_ssh_port: {port}")
    except:
        os.close(fd)
        os.remove(yml_path)
        raise
```

## 敏感关键字列表

```python
sensitive_keywords = [
    'password', 'passwd', 'pwd', 'secret', 'token',
    'api_key', 'access_key', 'private_key', 'credential',
    'authorization', 'apig_key', 'apig_secret'
]
```

**设计说明**：关键字列表中不包含 `ak=` 和 `sk=` 这类带等号的部分匹配关键字。因为当前正则模式要求关键字后跟 `:` 或 `=`，如果使用 `ak` 作为关键字，会误匹配 `access_key=xxx` 中的 `ak` 子串，导致非预期的脱敏。建议使用完整键名（如 `access_key`）而非缩写（如 `ak`）以避免语义冲突。

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
| 正则匹配遗漏边界场景 | 44 个单元测试覆盖各种边界情况（含 23 个正则模式精确测试） |
| 性能影响（大量数据脱敏） | 设置 `max_length=100` 限制输出长度 |
| 调试日志过多 | 使用 `tep_executor_logger.debug` 级别，生产环境可过滤 |
| TOCTOU 竞态（文件权限设置） | 使用 `os.open()` 原子创建 + `os.O_CREAT | os.O_EXCL`，权限在创建时即设定 |

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