# upload_to_openlibing 插件 — 技术设计

## 方案概述

基于 Python `requests` 库实现 HTTP POST 请求，将文件上传到 OpenLibing API 端点，支持多种归档模式和灵活的参数配置。

## 架构决策

### 1. 模块结构设计

采用单文件模块设计，包含以下核心组件：

| 组件 | 职责 |
|------|------|
| `_process_json_param()` | 处理 JSON 参数，支持标准 JSON 和简化格式 |
| `upload_data_to_openlibing()` | 核心上传函数，处理文件上传逻辑 |
| `main()` | CLI 入口，参数解析和调用 |

**决策原因**：
- 单文件设计便于部署和维护
- 功能内聚，职责清晰
- 符合插件化架构要求

### 2. 归档路径策略

采用优先级策略确定归档路径：

```
archive_path > pipeline_params > label
```

**决策原因**：
- `archive_path` 提供最高自定义能力
- `pipeline_params` 是流水线集成场景的标准路径
- `label` 是简单场景的默认路径

### 3. 错误处理策略

采用分层错误处理：

| 层级 | 处理方式 |
|------|----------|
| 文件级别 | 跳过不存在的文件，记录警告日志 |
| HTTP 层级 | 抛出 `HTTPError` 异常，包含详细错误信息 |
| 应用层级 | 记录错误日志并退出（exit code 1） |

**决策原因**：
- 文件级别容错，避免单个文件失败影响整体
- HTTP 层级严格，确保上传成功
- 应用层级友好，提供清晰的错误提示

### 4. 认证机制

使用 HTTP Headers 传递认证信息：

```python
headers = {
    "X-Apig-Appcode": openlibing_secret.get("apig_code", ""),
    "AppKey": openlibing_secret.get("apig_key", ""),
    "AppSecret": openlibing_secret.get("apig_secret", ""),
}
```

**决策原因**：
- 符合 OpenLibing API 规范
- 支持多租户认证
- 便于审计追踪

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `plugins/upload_to_openlibing/upload_to_openlibing.py` | 已存在 | 核心实现文件 |
| `plugins/upload_to_openlibing/__init__.py` | 已存在 | 包初始化文件 |
| `plugins/upload_to_openlibing/tests/test_upload_to_openlibing.py` | 已存在 | 单元测试文件 |
| `plugins/upload_to_openlibing/requirements.txt` | 已存在 | 依赖声明文件 |

## 数据流

```
用户输入
  ↓
参数解析 (argparse)
  ↓
参数校验 (label/pipeline_params 至少一个)
  ↓
Secret 解析 (_process_json_param)
  ↓
文件收集与验证
  ↓
HTTP POST 请求 (requests.post)
  ↓
响应处理 (raise_for_status)
  ↓
日志记录与结果返回
```

## 接口设计

### CLI 接口

```bash
python upload_to_openlibing.py \
    --files <file1> <file2> ... \
    [--pipeline-id <id>] \
    [--pipeline-run-id <id>] \
    [--job-id <id>] \
    [--label <label>] \
    [--archive-path <path>] \
    [--openlibing-secret <json>] \
    [--url <url>]
```

### Python 模块接口

```python
from upload_to_openlibing import upload_data_to_openlibing

response = upload_data_to_openlibing(
    file_paths=[Path("/path/to/file1.xml"), Path("/path/to/file2.xml")],
    openlibing_secret={"apig_code": "xxx", "apig_key": "xxx", "apig_secret": "xxx"},
    pipeline_id="pipeline-123",  # 可选
    pipeline_run_id="run-456",   # 可选
    job_id="job-789",            # 可选
    label="performance",         # 可选
    archive_path="2026/06",      # 可选
    url="https://...",           # 可选
)
```

## 测试策略

### 单元测试覆盖

| 测试类 | 覆盖范围 |
|--------|----------|
| `TestProcessJsonParam` | JSON 参数解析 |
| `TestUploadDataToOpenlibing` | 核心上传逻辑 |
| `TestCliArgValidation` | CLI 参数校验 |
| `TestIntegration` | 集成测试（需真实 secret） |

### Mock 策略

- 使用 `unittest.mock.patch` mock `requests.post`
- 使用 `tempfile.NamedTemporaryFile` 创建临时测试文件
- 使用 `pytest.raises` 验证异常抛出

## 安全考虑

1. **Secret 管理**
   - 支持环境变量传递，避免硬编码
   - 不在日志中输出完整 secret
   - 支持简化 JSON 格式，降低配置复杂度

2. **HTTPS 验证**
   - 默认 `verify=False`（因内网环境）
   - 生产环境建议启用证书验证

3. **文件访问**
   - 检查文件存在性，避免路径遍历
   - 使用 `Path` 对象处理路径，提高安全性

## 风险 & 缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API 端点变更 | 上传失败 | 支持自定义 URL 参数 |
| 网络超时 | 用户体验差 | 建议调用方添加重试逻辑 |
| 大文件上传 | 内存占用高 | 建议限制单文件大小 |
| Secret 泄露 | 安全风险 | 使用环境变量，不在代码中硬编码 |

## 性能考虑

- 文件逐个打开和上传，避免内存爆炸
- 使用 `finally` 块确保文件句柄正确关闭

## 可扩展性

1. **支持新的归档模式**
   - 可扩展参数校验逻辑
   - 可扩展归档路径生成算法

2. **支持新的认证方式**
   - 可扩展 headers 生成逻辑
   - 可支持 OAuth 等其他认证方式

3. **支持新的文件类型**
   - 自动 MIME 类型检测（`mimetypes.guess_type`）
   - 可扩展文件处理逻辑

## 跨仓影响

无跨仓影响，插件独立运行，仅依赖 `requests` 库。