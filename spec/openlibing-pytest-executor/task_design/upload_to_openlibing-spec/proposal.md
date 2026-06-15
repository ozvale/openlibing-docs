# upload_to_openlibing 插件规范文档

## 需求背景

OpenLibing 平台需要将测试元数据和结果文件上传到 OBS 存储桶，用于测试报告归档、结果追踪和历史数据分析。现有插件 `upload_to_openlibing.py` 已实现完整功能，但缺乏规范的文档说明，不利于团队协作和新人上手。

## 功能描述

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

- [x] proposal.md 描述清晰需求背景和功能范围
- [x] design.md 包含技术架构和关键决策
- [x] tasks.md 列出完整的实现任务清单
- [x] 文档格式符合 OpenLibing 规范要求

## 影响范围

- **文档位置**：`openlibing-docs/spec/openlibing-pytest-executor/task_design/upload_to_openlibing-spec/`
- **相关代码**：`openlibing-pytest-executor/plugins/upload_to_openlibing/`
- **测试覆盖**：25 个单元测试用例，覆盖率 100%