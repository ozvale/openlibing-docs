# Logger Fixture Header/Footer 注入能力 - 技术设计

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        测试用例层                               │
│                    def test_example(logger):                    │
│                         logger.set_header(html_content)         │
│                         logger.set_footer(html_content)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Fixture 层                              │
│               @pytest.fixture(name="logger")                    │
│               def infra_logger(request):                        │
│                    return InfraLogger(...)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      InfraLogger 类                            │
│                    - set_header(html_content, append)           │
│                    - set_footer(html_content, append)           │
│                    - 线程本地存储 header/footer 内容             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MemoryBufferHandler                          │
│               按线程缓冲日志，测试结束时生成 HTML                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    generate_html_report()                       │
│               读取线程本地 header/footer 内容并插入 HTML         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计要点

| 设计点 | 方案 | 说明 |
|--------|------|------|
| 线程隔离 | `threading.local()` | 每个线程独立存储 header/footer 内容 |
| 存储机制 | 字典结构 `{thread_id: {header, footer}}` | 支持多线程并行测试 |
| 注入时机 | HTML 报告生成阶段 | 在 `close_handler_for_thread()` 中处理 |
| 安全校验 | 标签白名单过滤 | 防止 XSS 攻击 |

## 2. 关键类/方法设计

### 2.1 InfraLogger 类扩展

**文件路径**: `pytest-testkit/pytest_testkit/lib/common/log/log_factory.py`

**新增方法**:

| 方法名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| `set_header()` | 设置 HTML 日志头部注入内容（header 统计信息之后、表格之前） | `html_content: str` - HTML 内容<br>`append: bool = False` - 是否追加 | `None` |
| `set_footer()` | 设置 HTML 日志尾部注入内容（表格之后） | `html_content: str` - HTML 内容<br>`append: bool = False` - 是否追加 | `None` |

**方法实现逻辑 - set_header**:

```python
def set_header(self, html_content: str, append: bool = False) -> None:
    """
    设置 HTML 日志头部注入内容（header 统计信息之后、表格之前）
    
    Args:
        html_content: 要注入的 HTML 内容
        append: 是否追加到现有内容之后，默认覆盖
    """
    # 1. 获取当前线程 ID
    thread_id = threading.current_thread().ident
    
    # 2. 获取或初始化线程本地存储
    if not hasattr(self._local, 'headers'):
        self._local.headers = {}
    
    # 3. 安全校验
    safe_content = self._sanitize_html(html_content)
    
    # 4. 覆盖或追加
    if append and thread_id in self._local.headers:
        self._local.headers[thread_id] += safe_content
    else:
        self._local.headers[thread_id] = safe_content
```

**方法实现逻辑 - set_footer**:

```python
def set_footer(self, html_content: str, append: bool = False) -> None:
    """
    设置 HTML 日志尾部注入内容（表格之后）
    
    Args:
        html_content: 要注入的 HTML 内容
        append: 是否追加到现有内容之后，默认覆盖
    """
    # 1. 获取当前线程 ID
    thread_id = threading.current_thread().ident
    
    # 2. 获取或初始化线程本地存储
    if not hasattr(self._local, 'footers'):
        self._local.footers = {}
    
    # 3. 安全校验
    safe_content = self._sanitize_html(html_content)
    
    # 4. 覆盖或追加
    if append and thread_id in self._local.footers:
        self._local.footers[thread_id] += safe_content
    else:
        self._local.footers[thread_id] = safe_content
```

### 2.2 安全校验方法

**新增方法**: `_sanitize_html()`

```python
def _sanitize_html(self, html_content: str) -> str:
    """
    HTML 内容安全校验
    
    仅过滤最危险的内容，保留常用标签和属性：
    1. 过滤最危险标签（script, iframe, embed, object）
    2. 过滤最危险事件属性（onclick, onload, onerror, onunload）
    3. 过滤 javascript: 和 vbscript: 伪协议
    4. 保留常用标签（div, table, tr, td, span, p, h1-h6, form, input 等）
    5. 清理标签内多余的空格（移除属性后自动清理，如 <div   > -> <div>）
    
    Returns:
        安全的 HTML 内容
    """
    # 实现安全过滤逻辑
    pass
```

### 2.3 HTML 报告生成修改

**修改方法**: `generate_html_report()`

在生成 HTML 时，读取线程本地的 header 和 footer 内容并插入到指定位置：

```python
def generate_html_report(thread_id: int) -> str:
    # ... 现有逻辑 ...
    
    # 读取 header 和 footer 内容
    header_content = ""
    footer_content = ""
    if hasattr(_local, 'headers') and thread_id in _local.headers:
        header_content = _local.headers.get(thread_id, "")
    if hasattr(_local, 'footers') and thread_id in _local.footers:
        footer_content = _local.footers.get(thread_id, "")
    
    # 构建 HTML
    html = f"""
    <html>
    <head>...</head>
    <body>
        <!-- 统计信息 -->
        <div class="header">...</div>
        
        <!-- Header 注入内容（header 统计信息之后、Total Entries 之前） -->
        {header_content}
        
        <p><strong>Total Entries:</strong> xxx</p>
        
        <!-- 详细信息表格 -->
        <table>...</table>
        
        <!-- Footer 注入内容（表格之后） -->
        {footer_content}
    </body>
    </html>
    """
    
    return html
```

## 3. 数据结构设计

### 3.1 线程本地存储结构

```python
# threading.local() 存储结构
_local = threading.local()

# _local.footers 结构
{
    12345: "<div>算子测试结果1</div>",  # thread_id: footer_content
    12346: "<div>算子测试结果2</div>",
    ...
}
```

### 3.2 安全标签白名单

| 标签类别 | 允许标签 |
|----------|----------|
| 容器标签 | `div`, `span`, `p`, `div`, `section`, `article` |
| 表格标签 | `table`, `thead`, `tbody`, `tr`, `td`, `th` |
| 标题标签 | `h1`, `h2`, `h3`, `h4`, `h5`, `h6` |
| 列表标签 | `ul`, `ol`, `li` |
| 样式标签 | `style`, `class`（仅允许特定值） |
| 其他 | `br`, `hr`, `strong`, `em`, `a`（限制 href 协议） |

## 4. API 设计

### 4.1 对外接口

```python
class InfraLogger:
    def set_footer(self, html_content: str, append: bool = False) -> None:
        """
        在 HTML 日志尾部注入内容
        
        Args:
            html_content: 要注入的 HTML 内容片段
            append: 是否追加模式，默认 False（覆盖）
        
        Example:
            # 基础用法 - 覆盖模式
            logger.set_footer("<div>算子测试结果</div>")
            
            # 追加模式
            logger.set_footer("<div>追加内容</div>", append=True)
        """
```

### 4.2 内部接口

| 方法 | 功能 | 调用时机 |
|------|------|----------|
| `_sanitize_html()` | HTML 安全过滤 | `set_footer()` 调用时 |
| `_get_footer_content()` | 获取线程的 footer 内容 | HTML 报告生成时 |
| `_clear_footer_content()` | 清理线程的 footer 内容 | 测试结束时 |

## 5. 部署与集成方案

### 5.1 依赖与环境

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.8+ | 项目基础依赖 |
| pytest | 6.0+ | 测试框架 |
| threading | 内置模块 | 线程隔离 |

### 5.2 集成方式

1. **修改文件**: `pytest-testkit/pytest_testkit/lib/common/log/log_factory.py`
   - 在 `InfraLogger` 类中添加 `set_footer()` 方法
   - 添加 `_sanitize_html()` 安全校验方法
   - 修改 `generate_html_report()` 方法

2. **无需配置变更**: 该功能为向后兼容扩展，不影响现有配置

## 6. 安全性考虑

### 6.1 XSS 防护

| 风险点 | 防护措施 |
|--------|----------|
| 脚本注入 | 过滤 `<script>`, `javascript:` 等危险标签和属性 |
| iframe 攻击 | 过滤 `<iframe>` 标签 |
| 事件处理器 | 过滤 `onclick`, `onload`, `onerror` 等事件属性 |
| 样式注入 | 限制 style 属性的取值范围 |

### 6.2 容错机制

| 异常场景 | 处理方式 |
|----------|----------|
| HTML 格式错误 | 记录警告日志，继续生成报告，注入内容可能显示异常但不影响原有内容 |
| 空内容注入 | 忽略，不写入报告 |
| 超大内容注入 | 限制最大长度（如 10MB），超出部分截断 |

## 7. 影响范围

### 7.1 修改的文件

| 文件 | 修改类型 | 影响 |
|------|----------|------|
| `log_factory.py` | 修改 + 新增 | 添加 `set_footer()` 方法和安全校验逻辑 |

### 7.2 新增的文件

| 文件 | 用途 |
|------|------|
| 无 | 无需新增文件 |

### 7.3 向后兼容性

- ✅ 原有 API 保持不变
- ✅ 不影响现有测试用例运行
- ✅ 新方法为可选功能，按需使用

## 8. 测试策略

### 8.1 单元测试

| 测试场景 | 测试用例 |
|----------|----------|
| 基础功能 | 调用 `set_footer()` 后，HTML 报告尾部包含注入内容 |
| 覆盖模式 | 多次调用 `set_footer()`，最终只有最后一次内容 |
| 追加模式 | `append=True` 时，多次调用内容合并 |
| 线程隔离 | 多线程并行调用，各自内容正确隔离 |
| 安全校验 | 注入危险内容（如 `<script>`）被过滤 |
| 容错机制 | 注入无效 HTML，原有报告不受影响 |

### 8.2 集成测试

| 测试场景 | 测试方法 |
|----------|----------|
| 完整流程 | 运行实际测试用例，验证 footer 注入功能正常工作 |
| 性能测试 | 验证大量测试用例并行执行时的性能 |
