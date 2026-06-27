# upload_to_openlibing 插件规范文档

## 需求背景

OpenLibing 平台需要将测试元数据和结果文件上传到 OBS 存储桶，用于测试报告归档、结果追踪和历史数据分析。

## 功能描述
提供一个公共插件，支持将测试相关结果过性文档上传到 OBS 存储桶，供问题追溯和看板运营使用。

### 核心功能

`upload_to_openlibing` 插件提供将测试文件上传到 OpenLibing OBS 存储桶的能力，支持以下特性：

1. **多种上传模式**
   - 流水线参数模式：归档为 `testcase-metadata/{pipeline_id}/{pipeline_run_id}/{job_id}/{filename}`
   - Label 模式：归档为 `/{label}/{filename}`
   - Label + Archive Path 模式：归档为 `/{label}/{archive_path}/{filename}`

2. **多种调用方式**
   - Shell 命令行调用
   - Python 模块调用

3. **灵活的参数配置**
   - 支持标准 JSON 和简化格式的 secret 参数
   - 支持环境变量传递 secret
   - 支持自定义上传 URL

4. **完善的错误处理**
   - 文件不存在时自动跳过
   - 详细的日志记录
   - HTTP 错误自动抛出异常

### 不做什么

- 不涉及文件内容处理或转换
- 不提供文件下载功能
- 不支持批量并发上传优化

## 验收标准

### 功能验收

- [x] **文件上传功能**：支持上传单个或多个文件到 OpenLibing OBS 存储桶
- [x] **流水线参数模式**：传入 `--pipeline-id`/`--pipeline-run-id`/`--job-id` 时，正确归档到 `testcase-metadata/{pipeline_id}/{pipeline_run_id}/{job_id}/{filename}`
- [x] **Label 模式**：传入 `--label` 时，正确归档到 `/{label}/{filename}`
- [x] **Label + Archive Path 模式**：同时传入 `--label` 和 `--archive-path` 时，正确归档到 `/{label}/{archive_path}/{filename}`
- [x] **CLI 调用**：支持通过命令行参数传递所有配置项
- [x] **Python 模块调用**：支持通过 `import upload_to_openlibing` 导入并调用 `upload_data_to_openlibing()` 函数
- [x] **Secret 参数解析**：支持标准 JSON 格式 `{"key": "value"}` 和简化格式 `{key: value}`
- [x] **环境变量支持**：未传入 `--openlibing-secret` 时，自动从 `OPENLIBING_SECRET` 环境变量读取
- [x] **文件不存在处理**：文件不存在时跳过并记录警告日志，不中断整体上传流程

### 错误处理验收

- [x] **参数校验**：`--archive-path` 必须配合 `--label` 使用，否则报错退出
- [x] **必填参数校验**：必须提供 `--label` 或流水线参数，否则报错退出
- [x] **Secret 校验**：未提供 secret 时报错退出
- [x] **HTTP 错误处理**：上传失败时抛出异常并记录详细错误日志

### 测试验收

- [x] **单元测试覆盖率**：核心功能单元测试覆盖率 100%
- [x] **JSON 参数解析测试**：覆盖标准格式和简化格式的解析
- [x] **上传逻辑测试**：覆盖正常上传和异常场景
- [x] **CLI 参数校验测试**：覆盖各种参数组合的校验逻辑

## 影响范围

- **文档位置**：`openlibing-docs/spec/openlibing-pytest-executor/task_design/upload_to_openlibing-spec/`
- **相关代码**：`openlibing-pytest-executor/plugins/upload_to_openlibing/`