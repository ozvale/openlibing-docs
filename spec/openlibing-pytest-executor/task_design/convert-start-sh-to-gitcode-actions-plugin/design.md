# Design: Convert start.sh to GitCode Actions JavaScript Plugin

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                  GitCode Actions Workflow                    │
│              (CI/CD Pipeline Trigger)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              pytest-orch Action (Node.js)                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 0: 参数获取与校验                                    ││
│  │  - 19 必选 + 1 可选参数                                   ││
│  │  - 类型/长度/格式/白名单校验                               ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 1-2: 环境准备                                       ││
│  │  - 创建工作目录                                           ││
│  │  - 清理旧文件                                             ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 3: Git 认证                                          ││
│  │  - GIT_ASKPASS 机制                                       ││
│  │  - 克隆 executor + testcase 仓库                          ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 4-5: 依赖安装                                        ││
│  │  - pip install pytest-testkit                            ││
│  │  - pip install pytest-testcase-collector                 ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 6-8: Python 调度器执行                               ││
│  │  - 环境申请                                               ││
│  │  - 测试执行                                               ││
│  │  - 环境释放                                               ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Step 9: 结果处理                                          ││
│  │  - 日志归档                                               ││
│  │  - 上传 OBS                                               ││
│  │  - 设置输出参数                                           ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Python Scheduler (pytest-executor)              │
│  - 环境管理 (k8s/hidevlab)                                  │
│  - 用例收集 (pytest/unittest)                                │
│  - 测试执行                                                   │
│  - 结果上传                                                   │
└─────────────────────────────────────────────────────────────┘
```

### 插件目录结构

```
.gitcode/actions/pytest-orch/
├── action.yml           # 插件定义(元数据、输入输出参数)
├── index.js             # 核心实现(约 1255 行)
├── package.json         # Node.js 依赖配置
├── package-lock.json    # 依赖版本锁定
└── dist/                # 编译产物(由 ncc 生成)
    └── index.js
```

## 核心设计决策

### 1. 参数校验策略

**决策**: 对所有输入参数实施严格校验,包含类型、长度、格式和白名单检查。

**原因**:
- 防止命令注入和路径穿越攻击
- 提供早期错误发现和清晰错误消息
- 符合 GitCode Actions 安全最佳实践

**实现**:
- 每个参数类型有专用校验函数(如 `validateObsAccessKey`、`validateJsonParam`)
- JSON 参数校验包含字段白名单(如 `scheduler-secret` 只允许特定字段)
- 路径参数校验限制在安全目录范围内(`/home`、`/tmp`、`/workspace`)

### 2. Git 认证机制

**决策**: 使用 `GIT_ASKPASS` 环境变量机制传递凭证。

**原因**:
- 避免在命令行参数中暴露密码
- Git 原生支持的凭证传递方式
- 兼容所有 Git 操作(clone/fetch/pull)

**实现**:
- 临时创建 ASKPASS 脚本文件(权限 700)
- 脚本响应 Git 的凭证请求
- 执行完成后清理临时文件

### 3. 环境变量传递

**决策**: 通过环境变量向 Python 调度器传递配置。

**原因**:
- Python 代码无需解析复杂的 CLI 参数
- 与 GitCode Actions 环境变量机制一致
- 避免命令行参数长度限制

**实现**:
- 核心配置通过 `process.env` 设置
- 敏感信息(OBS AK/SK)通过环境变量传递
- Job/Run ID 等上下文信息从 Actions 运行时环境获取

### 4. 构建与打包

**决策**: 使用 `@vercel/ncc` 将所有依赖打包为单文件。

**原因**:
- GitCode Actions 要求插件为自包含单文件
- 简化部署和分发
- 支持 `dist/` 目录排除策略

**实现**:
- `npm run build` 触发 ncc 打包
- 生成 `dist/index.js` 包含所有依赖
- `.gitignore` 排除源码和 node_modules,但保留 `dist/`

## 参数设计

### 输入参数(共 20 个)

| 参数名 | 类型 | 必选 | 校验规则 | 用途 |
|--------|------|------|----------|------|
| git-username | string | 是 | 1-256 字符,字母数字下划线中划线 | GitCode 用户名 |
| git-password | string | 是 | 1-256 字符,非空 | GitCode 密码或 Token |
| workspace | string | 否 | 默认 "workspace",1-64 字符 | 工作目录名 |
| testcase-config-file | string | 否 | 路径安全校验 | 测试配置文件路径 |
| log-conf | string | 否 | JSON 字符串或文件路径 | 日志配置 |
| scheduler-secret | JSON | 是 | 最大 10KB,最大深度 10,字段白名单 | 调度器密钥 |
| obs-ak | string | 是 | 字母数字+/组成,最大 256 字符 | OBS AK |
| obs-sk | string | 是 | 字母数字+/组成,最大 256 字符 | OBS SK |
| obs-bucket-name | string | 是 | 3-63 字符,小写字母数字中划线 | OBS 桶名 |
| obs-server | string | 是 | 字母数字点中划线,最大 253 字符 | OBS 服务器 |
| obs-base-url | string | 否 | HTTP/HTTPS URL,最大 2048 字符 | OBS 基础 URL |
| executor-branch | string | 否 | 默认 "master",分支名格式 | Executor 仓库分支 |
| executor-repo | string | 否 | 默认 openlibing 仓库 | Executor 仓库地址 |
| testcase-repo | string | 是 | owner/repo 格式 | 测试用例仓库 |
| case-branch | string | 否 | 默认 "main" | 测试用例分支 |
| max-workers | string | 否 | 默认 "2",正整数 | 最大并发数 |
| pytest-testkit-url | string | 否 | 默认 Release URL | testkit 下载地址 |
| testcase-collector-url | string | 否 | 默认 Release URL | collector 下载地址 |
| image-label | string | 否 | 标识符格式 | 镜像标签 |
| archive-log-dir | string | 否 | 路径安全校验 | 归档日志目录 |
| env-model | string | 否 | 标识符格式 | 环境模型 |
| env-device-resource | JSON | 否 | 最大 10KB,最大深度 10 | 设备资源配置 |
| env-deploy-model | string | 否 | 默认 "Dislocated",枚举值 | 部署模式 |
| platform | string | 否 | 默认 "codearts" | 平台前缀 |

### 输出参数(共 4 个)

| 参数名 | 描述 | 格式 |
|--------|------|------|
| pipeline-id | 流水线 ID | 从环境变量获取 |
| job-run-id | 任务运行 ID | 格式: `{id}_{step}` |
| testcase-obs-url | 测试用例 OBS URL | 完整 HTTP URL |
| testcase-file | 测试用例文件路径 | 绝对路径 |
| env-log-file | 环境日志文件路径 | 绝对路径 |

## 执行流程

### 流程图

```
开始
  │
  ├─ Step 0: 获取输入参数
  │   ├─ 从 Actions 上下文获取参数
  │   ├─ 执行参数校验
  │   └─ 构建内部变量
  │
  ├─ Step 0.5: 构建安全基础路径
  │   └─ 路径: /tmp/pytest-orch/{workspace}
  │
  ├─ Step 1: 构建路径和 URL
  │   ├─ 工作目录: executor-log, pytest-testkit, testcase-collector
  │   └─ 仓库 URL: executor-repo, testcase-repo
  │
  ├─ Step 2: 清理工作空间
  │   ├─ 检查目录是否存在
  │   ├─ 安全删除(校验路径前缀)
  │   └─ 创建新目录结构
  │
  ├─ Step 3: 设置 Git 认证
  │   ├─ 创建 ASKPASS 脚本
  │   ├─ 设置 GIT_ASKPASS 环境变量
  │   └─ 克隆 executor 仓库
  │
  ├─ Step 4: 克隆测试用例仓库
  │   └─ 克隆到 pytest-infra 目录
  │
  ├─ Step 5: 安装 pytest-testkit
  │   ├─ 下载 wheel 文件
  │   └─ pip install
  │
  ├─ Step 6: 安装 testcase-collector
  │   ├─ 下载 wheel 文件
  │   └─ pip install
  │
  ├─ Step 7: 执行调度器
  │   ├─ 设置环境变量
  │   ├─ 调用 python main.py
  │   └─ 捕获退出码
  │
  ├─ Step 8: 日志收集和上传
  │   ├─ 收集日志文件
  │   └─ 上传到 OBS
  │
  ├─ Step 9: 设置输出参数
  │   └─ core.setOutput()
  │
  └─ 清理临时文件
      └─ 删除 ASKPASS 脚本
```

## 安全设计

### 输入校验

1. **类型校验**: 所有参数必须符合声明类型
2. **长度校验**: 字符串参数限制最大长度
3. **格式校验**: 使用正则表达式匹配预期格式
4. **白名单校验**: JSON 参数限制允许的字段名

### 路径安全

```javascript
// 路径前缀断言
function assertSafePath(dir) {
  const allowedPrefixes = ['/tmp/', '/home/', '/workspace/'];
  if (!allowedPrefixes.some(prefix => dir.startsWith(prefix))) {
    throw new Error(`Unsafe path: ${dir}`);
  }
}
```

### 命令注入防护

- 所有参数经过校验后才用于命令构造
- 使用 `@actions/exec` 的 `exec` 函数,自动处理参数转义
- 禁止直接拼接 Shell 命令字符串

### 凭证安全

- Git 密码通过 ASKPASS 脚本传递,不在日志中显示
- OBS 密钥通过环境变量传递,不在日志中显示
- 敏感环境变量使用 `core.setSecret()` 标记

## 影响范围

### 新增文件

- `.gitcode/actions/pytest-orch/action.yml` (102 行)
- `.gitcode/actions/pytest-orch/index.js` (1255 行)
- `.gitcode/actions/pytest-orch/package.json` (26 行)
- `.gitcode/actions/pytest-orch/package-lock.json` (145 行)

### 修改文件

- `.gitignore` (+7 行): 排除 node_modules,但保留 `.gitcode/actions/*/dist/`

### 向后兼容

- 原有 `start.sh` Shell 脚本保留,不受影响
- 新增 GitCode Actions 插件作为可选集成方式
- 用户可根据需求选择 Shell 脚本或 Actions 插件

## 测试策略

### 单元测试

- 参数校验函数测试(各校验函数的边界条件)
- 路径安全断言测试
- JSON 校验和白名单测试

### 集成测试

- 完整 Actions 流程测试(在测试仓库中运行)
- Git 克隆流程测试
- Python 调度器调用测试

### 安全测试

- 命令注入测试(尝试注入恶意参数)
- 路径穿越测试(尝试访问非授权目录)
- 参数篡改测试(测试边界值和异常格式)

## 部署说明

### 构建步骤

```bash
cd .gitcode/actions/pytest-orch
npm install
npm run build
```

### 使用方式

```yaml
- name: Run pytest executor
  uses: openlibing/openlibing-pytest-executor/.gitcode/actions/pytest-orch@master
  with:
    git-username: ${{ secrets.GIT_USERNAME }}
    git-password: ${{ secrets.GIT_PASSWORD }}
    scheduler-secret: ${{ secrets.SCHEDULER_SECRET }}
    obs-ak: ${{ secrets.OBS_AK }}
    obs-sk: ${{ secrets.OBS_SK }}
    obs-bucket-name: 'test-bucket'
    obs-server: 'obs.example.com'
    obs-base-url: 'https://obs.example.com'
    testcase-repo: 'owner/test-repo'
```

## 参考资源

- [GitCode Actions 官方文档](https://gitcode.com/docs/actions)
- [@actions/core 文档](https://github.com/actions/toolkit/tree/main/packages/core)
- [@actions/exec 文档](https://github.com/actions/toolkit/tree/main/packages/exec)
- [GitHub Actions 安全最佳实践](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/)