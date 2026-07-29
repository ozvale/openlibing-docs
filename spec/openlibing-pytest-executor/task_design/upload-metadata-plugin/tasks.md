# upload-metadata-plugin — 实现任务

## 进度: 6/6 complete

- [x] Task 1: 创建 GitCode Actions 插件元数据文件
  - 文件：`.gitcode/actions/openlibing-upload-reports/action.yml`
  - 内容：定义输入参数（files、openlibing-secret、pipeline-id、label 等）、输出参数（success、status-code、response-text）、运行时（node16）

- [x] Task 2: 实现插件主逻辑
  - 文件：`.gitcode/actions/openlibing-upload-reports/index.js`
  - 功能：
    - 参数获取与验证
    - 文件路径安全验证
    - JSON 参数解析与白名单验证
    - Label 和 archive-path 验证
    - 文件上传（axios + form-data）
    - 错误处理与输出

- [x] Task 3: 配置依赖管理
  - 文件：
    - `.gitcode/actions/openlibing-upload-reports/package.json`
    - `.gitcode/actions/openlibing-upload-reports/package-lock.json`
  - 依赖：
    - @actions/core@^1.10.0
    - axios@^1.6.0
    - form-data@^4.0.0
    - mime-types@^2.1.35

- [x] Task 4: 实现安全验证函数
  - 函数：
    - `validateFilePath()`：防止路径遍历攻击，限制目录访问范围
    - `processJsonParam()`：JSON 参数解析与字段白名单验证
    - `validateLabel()`：Label 正则验证
    - `validateArchivePath()`：archive-path 验证

- [x] Task 5: 实现文件上传函数
  - 函数：`uploadFiles()`
  - 功能：
    - 构建 HTTP 请求（headers + FormData）
    - 支持 Pipeline 模式和 Label 模式
    - 处理文件不存在的情况（跳过并警告）
    - 返回 HTTP 响应状态和数据

- [x] Task 6: 更新 workflow 示例
  - 文件：`.github/workflows/Nightly-CI-example.yml`
  - 修改：使用新的 `openlibing-upload-reports` 插件替换旧的上传逻辑

## 技术要点

### 安全验证

```javascript
// 文件路径验证
const ALLOWED_PREFIXES = ['/home', '/tmp'];
if (path.isAbsolute(trimmedPath)) {
  const isAllowed = ALLOWED_PREFIXES.some(prefix =>
    resolvedPath.startsWith(path.resolve(prefix))
  );
  if (!isAllowed) throw new Error('...');
}

// JSON 参数白名单
const ALLOWED_FIELDS = ['apig_code', 'apig_key', 'apig_secret'];
const unknownFields = Object.keys(parsed).filter(k => !ALLOWED_FIELDS.includes(k));
if (unknownFields.length > 0) throw new Error('...');
```

### 双模式实现

```javascript
const isLabelMode = Boolean(label);

if (isLabelMode) {
  // Label 模式：忽略 Pipeline 参数
  pipelineId = null;
  pipelineRunId = null;
  jobId = null;
} else {
  // Pipeline 模式：从输入或环境变量获取
  pipelineId = core.getInput('pipeline-id') || process.env.ATOMGIT_WORKFLOW_ID;
  // ...
}
```

### FormData 构建

```javascript
const formData = new FormData();

// Pipeline 模式参数
if (pipelineId) formData.append('pipelineId', pipelineId);

// Label 模式参数
const archiveConfig = {};
if (label) archiveConfig.label = label;
if (archivePath) archiveConfig.archivePath = archivePath;
if (Object.keys(archiveConfig).length > 0) {
  formData.append('archiveConfig', JSON.stringify(archiveConfig));
}

// 文件流
formData.append('files', fs.createReadStream(validatedPath), {
  filename: fileName,
  contentType: mimeType,
});
```

## 验证清单

- [x] Pipeline 模式功能正常
- [x] Label 模式功能正常
- [x] 安全验证有效（路径遍历、注入攻击）
- [x] 错误处理完善（文件不存在、网络失败）
- [x] 依赖安装成功
- [x] Workflow 示例更新正确