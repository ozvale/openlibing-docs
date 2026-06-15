# Logger Fixture Header/Footer 注入能力 - 需求提案

## 1. 需求背景

在昇腾 CANN 测试场景中，单个测试用例会批量验证多个算子。目前框架仅支持上传和展示基础日志文件（如 HTML 格式），**缺乏对算子执行结果的集成和展示**，导致：
- 测试结果数据维度不完整
- 用户无法直观查阅算子测试结果

## 2. 需求目标

为 pytest 插件的 `logger` fixture 增加 `set_header()` 和 `set_footer()` 方法，支持在 HTML 日志的指定位置注入自定义内容（算子测试结果），提升测试报告的信息完整性。

## 3. 功能需求

### 3.1 新增方法定义

| 方法名 | 参数 | 返回值 | 功能描述 |
|--------|------|--------|----------|
| `set_header()` | `html_content: str` - 要注入的 HTML 内容<br>`append: bool = False` - 是否追加（默认覆盖） | `None` | 在 HTML 日志头部（header 统计信息之后、详细信息表格之前）注入内容 |
| `set_footer()` | `html_content: str` - 要注入的 HTML 内容<br>`append: bool = False` - 是否追加（默认覆盖） | `None` | 在 HTML 日志尾部（详细信息表格之后）注入内容 |

### 3.2 核心特性

| 特性 | 描述 | 溯源 |
|------|------|------|
| 线程隔离 | 每个测试用例注入的内容互不影响 | 需求确认 #4 |
| 覆盖/追加模式 | 通过 `append` 参数控制，默认覆盖 | 需求确认 #2 |
| 安全校验 | 对注入内容进行安全校验，但不限制格式 | 需求确认 #3 |
| 容错机制 | 注入内容异常时不影响原有 HTML 内容 | 需求确认 #3、#5 |

## 4. 验收标准

### 4.1 功能验收

1. ✅ 测试用例可调用 `logger.set_header(html_content)` 注入头部内容
2. ✅ 测试用例可调用 `logger.set_footer(html_content)` 注入尾部内容
3. ✅ 默认模式下，多次调用后一次覆盖前一次
4. ✅ `append=True` 时，多次调用的内容追加合并
5. ✅ 不同线程（测试用例）的注入内容相互隔离
6. ✅ 注入内容异常（如格式错误）时，不影响原有 HTML 报告生成

### 4.2 接口验收

```python
# 基础用法 - 覆盖模式（默认）
logger.set_header("<div>头部内容</div>")
logger.set_footer("<div>算子测试结果</div>")

# 追加模式
logger.set_header("<div>追加头部</div>", append=True)
logger.set_footer("<div>追加内容</div>", append=True)
```

### 4.3 输出验收

生成的 HTML 报告结构：
```html
<!-- header 统计信息 -->
<div class="header">...</div>

<!-- set_header 注入的内容 -->
<div>头部内容</div>

<!-- 详细信息表格 -->
<table>...</table>

<!-- set_footer 注入的内容 -->
<div>算子测试结果</div>
```

## 5. 非功能需求

| 需求类型 | 描述 |
|----------|------|
| 性能 | 不显著增加测试执行耗时 |
| 兼容性 | 不影响现有测试用例运行 |
| 可维护性 | 代码符合现有项目规范 |

## 6. 关联 Issue

- Issue #12: 【蓝区测试】pytest插件的logger fixture支持注入算子测试结果

## 7. 预计交付时间

2026-06-15
