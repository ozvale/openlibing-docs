# Logger Fixture Header/Footer 注入能力 - 任务清单

## 任务总览

| 任务编号 | 任务描述 | 状态 | 备注 |
|---------|---------|------|------|
| T-01 | InfraLogger 类扩展：添加 set_header 和 set_footer 方法 | DONE | |
| T-02 | InfraLogger 类扩展：添加 _sanitize_html 安全校验方法 | DONE | |
| T-03 | LogFactory 类修改：generate_html_report 方法支持注入内容 | DONE | |
| T-04 | LogFactory 类修改：close_handler_for_thread 传递 thread_id | DONE | |
| T-05 | 单元测试：test_log_factory.py 添加测试用例 | DONE | |
| T-06 | 集成测试：test_log_factory_integration.py 使用 logger fixture | DONE | |
| T-07 | 验证测试：运行测试确保功能正常 | PENDING | |

## 任务详情

### T-01: InfraLogger 类扩展 - set_header/set_footer 方法

**文件**: `pytest_testkit/lib/common/log/log_factory.py`

**实现内容**:
- `set_header(html_content: str, append: bool = False)` 方法
- `set_footer(html_content: str, append: bool = False)` 方法
- 使用 `threading.current_thread().ident` 获取线程 ID
- 使用线程本地存储 `_local` 保存 header/footer 内容
- 支持覆盖模式和追加模式

**完成标准**:
- [x] `set_header` 方法正确实现
- [x] `set_footer` 方法正确实现
- [x] 覆盖模式正常工作
- [x] 追加模式正常工作
- [x] 线程隔离正常

### T-02: 安全校验 - _sanitize_html 方法

**文件**: `pytest_testkit/lib/common/log/log_factory.py`

**实现内容**:
- 过滤危险标签：`<script>`, `<iframe>`, `<embed>`, `<object>`
- 过滤危险属性：`onclick`, `onload`, `onerror`, `onunload`, `onmouseover`, `onblur`, `onfocus`, `onchange`
- 过滤危险协议：`javascript:`, `vbscript:`
- 清理标签内多余的空格

**完成标准**:
- [x] 危险标签被完全移除
- [x] 危险属性被完全移除
- [x] 危险协议被移除
- [x] 常用标签（div, table, form 等）被保留
- [x] 空格清理正常工作

### T-03: LogFactory.generate_html_report 方法修改

**文件**: `pytest_testkit/lib/common/log/log_factory.py`

**实现内容**:
- 添加 `thread_id` 参数
- 从线程本地存储读取 header 和 footer 内容
- 在 HTML 模板的指定位置注入内容
- 注入位置：
  - header: 统计信息之后、Total Entries 之前
  - footer: 详细信息表格之后

**完成标准**:
- [x] 添加 thread_id 参数
- [x] 正确读取线程本地存储
- [x] header 内容在正确位置注入
- [x] footer 内容在正确位置注入

### T-04: close_handler_for_thread 传递 thread_id

**文件**: `pytest_testkit/lib/common/log/log_factory.py`

**实现内容**:
- 修改 `close_handler_for_thread` 方法
- 将 `thread_id` 传递给 `generate_html_report`

**完成标准**:
- [x] thread_id 正确传递

### T-05: 单元测试

**文件**: `pytest_testkit/tests/test_log_factory.py`

**测试用例**:
- [x] `test_set_header_basic` - 基本 header 设置功能
- [x] `test_set_footer_basic` - 基本 footer 设置功能
- [x] `test_set_header_footer_combined` - header 和 footer 同时设置
- [x] `test_header_footer_override_mode` - 覆盖模式测试
- [x] `test_header_footer_append_mode` - 追加模式测试
- [x] `test_header_footer_thread_isolation` - 线程隔离测试
- [x] `test_concurrent_header_footer` - 并发测试
- [x] `test_large_content_injection` - 大内容注入测试
- [x] `test_sanitize_html_removes_script_tags` - script 标签过滤
- [x] `test_sanitize_html_removes_iframe_tags` - iframe 标签过滤
- [x] `test_sanitize_html_removes_event_attributes` - 事件属性过滤
- [x] `test_sanitize_html_removes_javascript_protocol` - javascript 协议过滤
- [x] `test_sanitize_html_preserves_safe_tags` - 安全标签保留
- [x] `test_sanitize_html_removes_extra_spaces` - 空格清理

### T-06: 集成测试

**文件**: `pytest_testkit/tests/test_log_factory_integration.py`

**测试用例**:
- [x] `test_header_footer_injection` - 使用 logger fixture 设置 header/footer
- [x] `test_header_footer_append_mode` - 追加模式
- [x] `test_header_footer_with_safe_content` - 安全的 HTML 内容注入
- [x] `test_dangerous_content_filtered` - 危险内容过滤
- [x] `test_empty_and_none_content` - 空内容和 None 处理

### T-07: 验证测试

**执行命令**:
```bash
cd pytest-testkit
python -m pytest tests/test_log_factory.py tests/test_log_factory_integration.py -v
```

**完成标准**:
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] HTML 报告包含注入的 header 和 footer 内容
