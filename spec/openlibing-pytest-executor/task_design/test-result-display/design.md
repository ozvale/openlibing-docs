# 测试结果展示 Action - 技术设计

## 架构概览

本 Action 是一个 GitCode Action，采用 Node.js 16 实现，遵循 GitCode Actions 标准接口规范。核心流程如下：

```
输入参数 → 文件路径解析 → JSON 解析 → 数据转换 → Markdown 生成 → 输出
```

## 模块设计

### 1. 核心模块（index.js）

#### 1.1 文件路径验证模块

**函数**: `validateJsonFilePath(jsonFilePath)`

**职责**:

- 验证路径安全性（防止路径遍历攻击）
- 验证文件扩展名（仅允许 .json）
- 对绝对路径进行白名单验证

**注意**: 空路径检查和文件存在性检查已移至 `run()` 主函数中处理，便于实现更友好的容错策略。

**安全策略**:

- 白名单目录：`/home`、`/tmp`、`/workspace`
- 禁止路径遍历：拒绝包含 ".." 的路径
- 扩展名检查：确保文件类型正确

**路径处理逻辑**:

```javascript
// 绝对路径：验证白名单
if (path.isAbsolute(trimmedPath)) {
  // 检查白名单目录
  // 不再检查文件存在（由 run() 处理）
}

// 相对路径：基于 cwd 解析
else {
  const resolvedPath = path.resolve(cwd, trimmedPath);
  // 不再检查文件存在（由 run() 处理）
}
```

#### 1.2 JSON 解析模块

**函数**: `parseTestResults(jsonFilePath, sourceTask)`

**职责**:

- 调用文件路径验证
- 读取并解析 JSON 文件
- 验证 JSON 结构（必须包含 `testCasesResult` 数组）
- 提取测试用例关键字段
- 计算执行时长

**数据转换**:

```javascript
// 输入 JSON 结构
{
  "testCasesResult": [
    {
      "number": "test_001",
      "state": "passed",
      "beginTime": 1625097600000,
      "endTime": 1625097605000,
      "resultDownloadUrl": "https://example.com/result.zip"
    }
  ]
}

// 输出数据结构
{
  "number": "test_001",
  "state": "passed",
  "duration": "5.0",  // 秒，保留一位小数
  "resultUrl": "https://example.com/result.zip",
  "sourceTask": "Task-A"
}
```

#### 1.3 Markdown 生成模块

**函数**: `generateMarkdownTable(testResults)`

**职责**:

- 生成 Markdown 表格标题
- 计算测试统计信息
- 排序测试结果（失败用例优先）
- 生成表格行
- 处理 URL 链接生成

**Markdown 转义策略**:

**函数**: `escapeMarkdownTable(text)`

转义字符优先级（按顺序）：

1. `\` → `\\`（反斜杠必须第一个转义，避免双重转义）
2. `|` → `\|`
3. `*` → `\*`
4. `_` → `\_`
5. `` ` `` → `` \` ``
6. `#` → `\#`
7. `<` → `&lt;`（HTML 实体）
8. `>` → `&gt;`（HTML 实体）
9. `[` → `\[`
10. `]` → `\]`
11. `~` → `\~`

**URL 处理策略**:

- 仅允许 http/https 协议
- 括号进行 URL 编码：`)` → `%29`，`(` → `%28`
- 无效 URL 显示为 "N/A"

#### 1.4 输入解析模块

**函数**: `parseJsonFileInput(input)`

**职责**:

- 解析换行分隔的输入
- 支持源任务前缀格式：`SourceTask:/path/to/file.json`
- 兼容 Windows 路径（C:\、D:/）
- 兼容纯文件路径格式

**解析逻辑**:

```
输入: "Task-A:/path/a.json\n/path/b.json"

处理:
1. 第一行包含 ":" 且非 Windows 路径 → 提取 "Task-A" 和 "/path/a.json"
2. 第二行无 ":" 或为 Windows 路径 → 整行作为文件路径，源任务为空

输出:
[
  { sourceTask: "Task-A", jsonFile: "/path/a.json" },
  { sourceTask: "", jsonFile: "/path/b.json" }
]
```

#### 1.5 统计模块

**函数**: `countStatistics(testResults)`

**职责**:

- 统计总用例数
- 统计通过用例数
- 统计未通过用例数

**计算公式**:

```javascript
total = testResults.length;
passed = testResults.filter((r) => r.state === "passed").length;
notPassed = total - passed;
```

### 2. Action 元数据（action.yml）

定义 Action 的输入输出接口：

```yaml
inputs:
  json-file:
    description: "Path(s) to JSON file(s) containing test case execution results"
    required: true

outputs:
  total-cases:
    description: "Total number of test cases"
  passed-cases:
    description: "Number of passed test cases"
  not-passed-cases:
    description: "Number of test cases that did not pass"
```

### 3. 依赖管理

**生产依赖**:

- `@actions/core@^1.10.0`: GitCode Actions 核心库，提供输入输出、日志、失败等 API

**开发依赖**:

- `@vercel/ncc@^0.38.0`: 将 Node.js 项目打包为单文件，用于 Action 分发

## 安全设计

### 1. 输入验证

**路径验证**:

- 防止路径遍历：拒绝包含 ".." 的路径
- 白名单目录限制：仅允许 `/home`、`/tmp`、`/workspace`
- 扩展名检查：仅允许 `.json` 文件

**JSON 结构验证**:

- 检查必需字段：`testCasesResult` 数组
- 类型检查：确保 `testCasesResult` 是数组

### 2. 输出编码

**Markdown 转义**:

- 所有用户可控数据都经过转义
- 使用 HTML 实体编码 `<` 和 `>` 防止 HTML 注入

**URL 验证**:

- 使用 `URL` 构造器验证 URL 格式
- 仅允许 http/https 协议
- 括号进行 URL 编码防止 Markdown 链接语法破坏

### 3. 错误处理

**容错策略**（最新优化）:

- **跳过无效文件并继续**：遇到空路径或文件不存在时，记录 warning 并跳过，而不是中断整个流程
- **多文件场景友好**：在处理多个 JSON 文件时，单个文件失败不影响其他文件的处理
- **详细的 warning 日志**：通过 `core.warning()` 输出详细日志，帮助用户定位问题

**错误分类处理**:

| 错误类型      | 处理策略           | 输出方式           |
| ------------- | ------------------ | ------------------ |
| 空路径        | 跳过并记录 warning | `core.warning()`   |
| 文件不存在    | 跳过并记录 warning | `core.warning()`   |
| 路径遍历攻击  | 中断并报告错误     | `core.setFailed()` |
| JSON 格式错误 | 中断并报告错误     | `core.setFailed()` |
| 缺失必需字段  | 中断并报告错误     | `core.setFailed()` |

**实现位置**:

- 文件存在性检查：在 `run()` 主函数中，处理每个文件前检查
- 安全和格式验证：在 `validateJsonFilePath()` 中检查，失败时抛出异常

**错误处理流程**:

```javascript
// run() 函数中的容错逻辑
for (const item of jsonFiles) {
  // 1. 检查空路径 - 跳过
  if (!item.jsonFile || item.jsonFile.trim() === "") {
    core.warning(`Skipping entry with empty jsonFile path`);
    continue;
  }

  // 2. 检查文件存在性 - 跳过
  if (!fs.existsSync(item.jsonFile)) {
    core.warning(`JSON file not found, skipping: ${item.jsonFile}`);
    continue;
  }

  // 3. 尝试解析文件 - 可能抛出异常
  try {
    const results = parseTestResults(item.jsonFile, item.sourceTask || "");
    allTestResults = allTestResults.concat(results);
  } catch (error) {
    // JSON 格式错误、安全问题等 - 中断流程
    core.setFailed(error.message);
    return;
  }
}
```

## 部署架构

### 文件结构

```
.gitcode/actions/test-result-display/
├── action.yml           # Action 元数据
├── index.js            # 源代码
├── dist/index.js       # 打包后的代码（实际执行）
├── package.json        # 依赖声明
└── package-lock.json   # 依赖锁定
```

### 构建流程

```bash
npm install
npm run build  # 使用 ncc 打包到 dist/index.js
```

### 运行环境

- Node.js 16+（GitCode Actions 默认支持）
- 访问 GitCode Step Summary 环境：`$ATOMGIT_STEP_SUMMARY`

## 性能考虑

1. **文件读取**: 同步读取（`fs.readFileSync`），适合小文件（< 10MB）
2. **内存占用**: 单个测试结果对象约 200 bytes，1000 个用例约 200KB
3. **输出方式**: 追加写入（`fs.appendFileSync`），支持多 Action 输出到同一 Summary

## 扩展性

### 支持新字段

如需支持新的测试用例字段，修改 `parseTestResults` 函数：

```javascript
return {
  number: testCase.number || "N/A",
  state: testCase.state || "unknown",
  duration: durationSeconds.toFixed(1),
  resultUrl: testCase.resultDownloadUrl || "",
  sourceTask: sourceTask,
  // 新增字段
  error: testCase.errorMessage || "",
};
```

### 支持新统计维度

如需支持新的统计维度，修改 `countStatistics` 和 `generateMarkdownTable`：

```javascript
// 新增统计
const skipped = testResults.filter((r) => r.state === "skipped").length;

// 更新 Markdown 输出
markdown += `**用例总数: ${total}, 通过: ${passed}, 跳过: ${skipped}, 失败: ${failed}**\n`;
```

## 测试策略

### 单元测试覆盖

- 文件路径验证（正常、异常、边界）
- JSON 解析（格式正确、格式错误、缺失字段）
- Markdown 转义（特殊字符、空值）
- 输入解析（单文件、多文件、源任务前缀、Windows 路径）

### 集成测试

- 完整工作流测试：输入 → 输出
- 多文件场景测试
- 错误处理测试

## 影响范围

### 新增文件

- `.gitcode/actions/test-result-display/` 目录及所有文件

### 依赖影响

- 无外部依赖变更
- 新增 `@actions/core` 依赖（仅在 Action 内部使用）

### 运行时影响

- 在 GitCode CI 工作流中作为步骤执行
- 需要读取测试结果 JSON 文件权限
- 需要写入 Step Summary 权限（由 GitCode 平台提供）
