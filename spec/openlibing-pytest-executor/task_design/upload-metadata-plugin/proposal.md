# upload-metadata-plugin

## 需求背景

OpenLibing 平台在执行 CI/CD 流水线时，需要将测试元数据和结果文件上传到 OBS 对象存储桶进行持久化存储。此前缺少一个标准化的 GitCode Actions 插件来处理这一上传流程，导致：

1. 各项目需要重复编写上传逻辑
2. 缺乏统一的安全验证机制
3. 文件路径和参数管理混乱

因此需要开发一个可复用的 GitCode Actions 插件，为所有项目提供标准化的元数据上传能力。

## 功能描述

### 核心功能

开发 `openlibing-upload-reports` GitCode Actions 插件，实现：

1. **文件上传**：支持将多个文件上传到 OpenLibing OBS 桶
2. **双模式支持**：
   - Pipeline 模式：基于 pipeline-id、pipeline-run-id、job-id 定位文件存储路径
   - Label 模式：基于 label 和可选的 archive-path 定位文件存储路径
3. **安全验证**：
   - 文件路径验证（防止路径遍历攻击）
   - JSON 参数验证（字段白名单）
   - Label 和 archive-path 验证（防止注入）
   - 限制允许访问的目录范围

### 不做什么

- 不提供文件压缩、加密功能
- 不支持断点续传
- 不提供上传进度的实时反馈
- 不处理文件去重

## 验收标准

- [ ] 能够通过 GitCode Actions 配置文件调用该插件
- [ ] 支持 Pipeline 模式上传（需要 pipeline-id、pipeline-run-id、job-id）
- [ ] 支持 Label 模式上传（需要 label，可选 archive-path）
- [ ] 能够正确验证文件路径，拒绝路径遍历攻击
- [ ] 能够正确解析 JSON 参数，只允许白名单字段
- [ ] 能够正确验证 label 和 archive-path 参数
- [ ] 上传成功后返回 success=true 和正确的 HTTP 状态码
- [ ] 上传失败时返回 success=false 和错误信息
- [ ] 支持 space-separated 的多文件上传
- [ ] 正确处理文件不存在的情况（跳过并警告）

## 影响范围

### 受影响的模块/文件

- 新增：`.gitcode/actions/openlibing-upload-reports/` 目录
  - `action.yml`：GitCode Actions 元数据定义
  - `index.js`：插件主逻辑（388 行）
  - `package.json`：依赖管理
  - `package-lock.json`：依赖锁定文件
- 更新：`.github/workflows/Nightly-CI-example.yml`（使用新插件替换旧的上传逻辑）

### 跨仓影响

无跨仓影响，所有改动都在 `openlibing-pytest-executor` 仓库内。

### 依赖变化

新增依赖：
- `@actions/core@^1.10.0`：GitCode Actions SDK
- `axios@^1.6.0`：HTTP 客户端
- `form-data@^4.0.0`：FormData 实现
- `mime-types@^2.1.35`：MIME 类型检测

开发依赖：
- `@vercel/ncc@^0.38.1`：打包工具

### 外部接口

调用 OpenLibing API：
- 端点：`https://apig.openlibing.com/openlibing-sync/sync/testcase/metadata/upload`
- 方法：POST（multipart/form-data）
- 认证：X-Apig-Appcode、AppKey、AppSecret 头部