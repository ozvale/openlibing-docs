# Tasks: Convert start.sh to GitCode Actions JavaScript Plugin

## 任务概览

| 阶段 | 任务 | 状态 | 负责人 |
|------|------|------|--------|
| Phase 1 | 插件定义与框架搭建 | ✅ 已完成 | AI |
| Phase 2 | 参数校验实现 | ✅ 已完成 | AI |
| Phase 3 | Git 认证与仓库克隆 | ✅ 已完成 | AI |
| Phase 4 | 依赖安装流程 | ✅ 已完成 | AI |
| Phase 5 | 调度器集成 | ✅ 已完成 | AI |
| Phase 6 | 日志收集与结果处理 | ✅ 已完成 | AI |
| Phase 7 | 文档与测试 | ✅ 已完成 | AI |

## 详细任务清单

### Phase 1: 插件定义与框架搭建

- [x] 创建 `.gitcode/actions/pytest-orch/` 目录结构
- [x] 编写 `action.yml` 插件定义文件
  - [x] 定义插件名称和描述
  - [x] 定义 19 个必选输入参数
  - [x] 定义 1 个可选输入参数
  - [x] 定义 4 个输出参数
  - [x] 声明运行时(Node.js 16)
- [x] 创建 `package.json` 依赖配置
  - [x] 添加 `@actions/core` 依赖
  - [x] 添加 `@actions/exec` 依赖
  - [x] 添加 `@actions/io` 依赖
  - [x] 添加 `@vercel/ncc` 开发依赖
- [x] 创建 `index.js` 主文件框架
  - [x] 导入依赖模块
  - [x] 创建 `run()` 异步主函数
  - [x] 实现错误处理和清理机制

### Phase 2: 参数校验实现

- [x] 实现 Git 凭证校验函数
  - [x] `validateGitUsername()` - 用户名校验
  - [x] `validateGitPassword()` - 密码校验
- [x] 实现 OBS 参数校验函数
  - [x] `validateObsAccessKey()` - AK/SK 校验
  - [x] `validateObsBucketName()` - 桶名校验
  - [x] `validateObsServer()` - 服务器名校验
  - [x] `validateObsBaseUrl()` - URL 校验
- [x] 实现通用校验函数
  - [x] `validatePositiveInteger()` - 正整数校验
  - [x] `validateIdentifier()` - 标识符校验
  - [x] `validateEnum()` - 枚举值校验
  - [x] `validateFilePath()` - 文件路径校验
  - [x] `validateBranchName()` - 分支名校验
  - [x] `validateRepoName()` - 仓名校验
  - [x] `validateDownloadUrl()` - 下载 URL 校验
  - [x] `validateWorkspaceName()` - 工作目录名校验
- [x] 实现 JSON 参数校验
  - [x] `validateJsonParam()` - JSON 校验和字段白名单
  - [x] `validateEnvDeviceResource()` - 设备资源配置校验
  - [x] `getJsonDepth()` - JSON 深度检查
  - [x] `fixJsonString()` - JSON 字符串修复
- [x] 实现安全辅助函数
  - [x] `assertSafePath()` - 路径前缀断言
  - [x] `sanitizeOutputValue()` - 输出值清理
  - [x] `safeRemove()` - 安全删除目录

### Phase 3: Git 认证与仓库克隆

- [x] 实现 Git 认证机制
  - [x] 创建临时 ASKPASS 脚本目录
  - [x] 生成 ASKPASS Shell 脚本(响应 Git 凭证请求)
  - [x] 设置脚本权限(700)
  - [x] 设置 `GIT_ASKPASS` 环境变量
- [x] 实现仓库克隆流程
  - [x] 克隆 executor 仓库到工作目录
  - [x] 克隆 testcase 仓库到 pytest-infra 目录
  - [x] 处理克隆失败和重试逻辑
- [x] 实现清理机制
  - [x] 在 `finally` 块中删除 ASKPASS 脚本
  - [x] 确保清理逻辑在异常时也能执行

### Phase 4: 依赖安装流程

- [x] 实现依赖下载流程
  - [x] 下载 pytest-testkit wheel 文件
  - [x] 下载 pytest-testcase-collector wheel 文件
  - [x] 校验下载 URL 格式
- [x] 实现依赖安装流程
  - [x] 使用 `exec.exec()` 执行 pip install 命令
  - [x] 捕获安装失败和错误消息
  - [x] 记录安装日志到 Actions 输出

### Phase 5: 调度器集成

- [x] 实现调度器调用流程
  - [x] 构建调度器命令行参数
  - [x] 设置环境变量(OBS 配置、调度器密钥)
  - [x] 执行 `python main.py` 命令
  - [x] 捕获退出码和输出日志
- [x] 实现参数传递
  - [x] 传递环境配置(env-model, env-device-resource)
  - [x] 传递测试配置(testcase-config-file)
  - [x] 传递平台配置(platform, env-deploy-model)
- [x] 实现错误处理
  - [x] 捕获调度器执行失败
  - [x] 提供清晰错误消息
  - [x] 记录失败日志

### Phase 6: 日志收集与结果处理

- [x] 实现日志收集
  - [x] 收集 executor 执行日志
  - [x] 收集环境日志文件
  - [x] 归档日志到指定目录
- [x] 实现 OBS 上传
  - [x] 调用 OBS SDK 上传日志文件
  - [x] 生成 OBS 访问 URL
  - [x] 处理上传失败
- [x] 实现输出参数设置
  - [x] 设置 `pipeline-id` 输出
  - [x] 设置 `job-run-id` 输出
  - [x] 设置 `testcase-obs-url` 输出
  - [x] 设置 `testcase-file` 输出
  - [x] 设置 `env-log-file` 输出

### Phase 7: 文档与测试

- [x] 更新 `.gitignore`
  - [x] 排除 `node_modules/` 目录
  - [x] 排除 Python `dist/` 目录
  - [x] 保留 `.gitcode/actions/*/dist/` (使用 `!` 前缀)
- [x] 编写使用文档
  - [x] 在 README.md 中添加插件使用指南
  - [x] 添加参数说明示例
  - [x] 添加从 start.sh 迁移的说明
- [x] 编译和打包
  - [x] 运行 `npm run build` 生成 `dist/index.js`
  - [x] 测试插件在 GitCode Actions 中的运行

## 验证清单

### 功能验证

- [x] 插件能够在 GitCode Actions 中成功运行
- [x] 所有 20 个参数能够正确传递给 Python 调度器
- [x] Git 仓库能够成功克隆
- [x] Python 调度器能够成功执行
- [x] 日志能够正确收集和上传
- [x] 输出参数能够正确返回

### 安全验证

- [x] 所有输入参数经过校验
- [x] JSON 参数包含字段白名单限制
- [x] 路径操作包含安全断言
- [x] Git 凭证通过安全机制传递
- [x] 敏感信息不会在日志中泄露

### 文档验证

- [x] README 包含使用指南
- [x] README 包含迁移说明
- [x] action.yml 包含参数描述

## 提交记录

```
commit 65884d7c7100c9338d99bbc5df4c935c5bc7ecff
Author: z30004965 <zhengting13@huawei.com>
Date:   Mon Jul 13 10:20:52 2026 +0800

feat(pytest-executor): convert start.sh to GitCode Actions JavaScript plugin

Add GitCode Actions plugin support for pytest-executor, providing a standard
CI/CD integration alternative to the original Shell script.

Changes:
- Add action.yml: define 19 required inputs + 1 optional input (image-label)
- Add index.js: implement core logic using @actions/core/exec/io
- Add package.json: define Node.js dependencies
- Update README.md: add plugin usage guide and migration instructions
- Update .gitignore: exclude pytest-executor/dist/ and node_modules/
- Update ssh.py: minor adjustments for plugin integration

Refs #23

Co-authored-by: Trae <noreply@trae.ai>
Generated-by: claude-sonnet-4-6
```

## 关联 Issue

- GitCode Issue: [openlibing/openlibing-pytest-executor#23](https://gitcode.com/openlibing/openlibing-pytest-executor/issues/23)

## 后续优化建议

1. **性能优化**
   - [ ] 添加仓库克隆缓存机制
   - [ ] 实现依赖预安装检查

2. **功能增强**
   - [ ] 支持自定义 Python 版本
   - [ ] 支持多测试仓库并行执行
   - [ ] 添加执行超时配置

3. **安全增强**
   - [ ] 实现参数签名验证
   - [ ] 添加运行时权限隔离

4. **可观测性**
   - [ ] 添加详细执行时间统计
   - [ ] 集成 GitCode Actions 审计日志