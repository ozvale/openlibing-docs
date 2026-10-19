# 测试结果展示 Action

## 需求背景

在 GitCode CI/CD 工作流中，测试执行结果需要以清晰、可读的方式展示给用户。当前的测试报告主要以 JSON 格式存储，用户需要手动查看文件才能了解测试详情，缺乏直观的汇总展示。

为了提升用户体验，需要一个 GitCode Action 来自动解析测试结果 JSON 文件，生成格式化的 Markdown 表格，并输出到工作流步骤摘要（Step Summary）中，使用户能够直接在 GitCode 界面中查看测试结果。

## 目标

1. 提供一个可复用的 GitCode Action，用于解析测试结果 JSON 文件
2. 自动生成 Markdown 格式的测试结果汇总表格
3. 将汇总结果输出到 GitCode Step Summary，便于用户查看
4. 支持多文件输入，可同时处理多个测试任务的执行结果

## 验收标准

### 功能性验收

- [x] 能够解析符合约定格式的 JSON 文件
- [x] 能够提取测试用例的关键信息（编号、状态、耗时、结果 URL）
- [x] 能够生成格式化的 Markdown 表格
- [x] 能够正确统计测试用例总数、通过数、未通过数
- [x] 能够将结果输出到 GitCode Step Summary
- [x] 支持多文件输入（换行分隔）
- [x] 支持源任务（Source Task）前缀标注

### 安全性验收

- [x] 防止路径遍历攻击（检查 ".." 序列）
- [x] 限制文件路径范围（白名单目录）
- [x] 防止 Markdown 注入（转义特殊字符）
- [x] 防止 URL 协议注入（仅允许 http/https）

### 可用性验收

- [x] 提供清晰的错误提示
- [x] 支持绝对路径和相对路径
- [x] 失败的测试用例优先显示
- [x] 兼容 Windows 和 Linux 路径格式

### 容错性验收

- [x] 空路径输入不会导致流程中断，会跳过并记录 warning
- [x] 文件不存在不会导致流程中断，会跳过并记录 warning
- [x] 多文件输入时，单个文件失败不影响其他文件处理
- [x] 提供详细的 warning 日志帮助定位问题

## 输入输出规格

### 输入参数

| 参数名      | 类型   | 必填 | 描述                                                                                                   |
| ----------- | ------ | ---- | ------------------------------------------------------------------------------------------------------ |
| `json-file` | string | 是   | JSON 文件路径（支持多文件，换行分隔）<br>格式：`SourceTask:/path/to/file.json` 或 `/path/to/file.json` |

### 输出参数

| 参数名             | 类型   | 描述                                     |
| ------------------ | ------ | ---------------------------------------- |
| `total-cases`      | number | 测试用例总数                             |
| `passed-cases`     | number | 通过的测试用例数                         |
| `not-passed-cases` | number | 未通过的测试用例数（失败、跳过、错误等） |

## 输出示例

```markdown
## 测试结果汇总

**用例总数: 10, 通过用例: 8, 未通过用例: 2**

| 来源任务 | 用例名称    | 执行结果      | 耗时 | 用例结果                                |
| :------- | :---------- | :------------ | :--- | :-------------------------------------- |
| Task-A   | test_login  | **failed** ❌ | 1.5  | N/A                                     |
| Task-A   | test_logout | **failed** ❌ | 0.8  | N/A                                     |
| Task-B   | test_create | **passed** ✅ | 2.3  | [下载](https://example.com/result1.zip) |
| Task-B   | test_delete | **passed** ✅ | 1.1  | [下载](https://example.com/result2.zip) |
```

## 使用场景

1. **单测试任务场景**

   ```yaml
   - name: Display test results
     uses: ./.gitcode/actions/test-result-display
     with:
       json-file: /workspace/test-results.json
   ```

2. **多测试任务场景**
   ```yaml
   - name: Display test results
     uses: ./.gitcode/actions/test-result-display
     with:
       json-file: |
         Task-A:/workspace/results-a.json
         Task-B:/workspace/results-b.json
   ```

## 约束与限制

1. JSON 文件必须包含 `testCasesResult` 数组字段
2. 每个测试用例应包含 `number`、`state`、`beginTime`、`endTime`、`resultDownloadUrl` 字段
3. 绝对路径必须在白名单目录内（`/home`、`/tmp`、`/workspace`）
4. 文件扩展名必须为 `.json`
