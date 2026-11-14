# design：pre-commit-action 免凭证接入（PR #29）

需求：移除 `gc_token` 输入，PR 增量检查复用 checkout 已检出的基线 ref，插件不再接收、传递、落盘任何 Git 凭证。

## 1. 方案设计

### 1.1 现状问题

`buildAutoArgs()` 在 PR 事件下的既有链路：

1. `getInput('gc_token')` 读取调用方传入的 Token；
2. `createGitAskpass(token)` 在系统临时目录写 GIT_ASKPASS 脚本，Token 经 `PRE_COMMIT_GC_TOKEN` 环境变量传给子进程；
3. `execFile('git', ['fetch', 'origin', baseRef], { env })` 执行认证 fetch；
4. `finally` 中 `removeGitAskpass()` 清理脚本；
5. 固定返回 `--from-ref FETCH_HEAD --to-ref HEAD`。

问题：下游每个接入仓都要维护并传入高权限 Token，凭证暴露面随接入仓数量线性放大；插件内部维护纯凭证搬运代码，与「执行 pre-commit 钩子」的核心职责无关；checkout 步骤本身已按 `fetch-depth` 生成远端基线 ref，插件重复 fetch 属于冗余网络操作。

### 1.2 方案对比

| 方案                              | 说明                                                                      | 结论                                                         |
| --------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------ |
| A. 保留 `gc_token`                | 维持现状，插件自行认证 fetch                                              | 不采纳：凭证暴露面无法收敛                                   |
| B. 仅删 Token，保留插件内 fetch   | 改为依赖 checkout 持久化凭证                                              | 不采纳：GitCode 托管 checkout 不持久化凭证，回退路径必然失败 |
| C. 复用 checkout 基线 ref（选定） | checkout 配 `fetch-depth: 0` 生成 `origin/<baseRef>`，插件零 fetch 零凭证 | 采纳：与测试仓验证结果一致                                   |

### 1.3 总体方案

- 插件侧：删除 `gc_token` 输入及全部凭证搬运代码，新增 `resolveBaseRef(baseRef)`，优先直接使用 `origin/<baseRef>` 作为 `--from-ref`。
- 调用方侧（本次不改）：PR 场景 checkout 必须配置 `fetch-depth: 0`。该约束以 README 硬前提形式声明，`openlibing-cicd` 等调用的 workflow 统一整改后续单独进行。
- 不在本 PR 范围内：不打 tag、不改任何 `.gitcode/workflows/` 文件、不改非 PR 事件的 `--all-files` 行为。

## 2. 实现逻辑设计

### 2.1 主流程（PR 事件）

```
ATOMGIT_EVENT_NAME ∈ {mr, pull_request, note} 且 ATOMGIT_BASE_REF 非空
  └─ resolveBaseRef(baseRef)
       ├─ git rev-parse --verify --quiet origin/<baseRef> 有输出
       │    └─ 返回 origin/<baseRef>，插件零 fetch、零凭证
       └─ 无输出
            ├─ 打印 WARN + 建议 fetch-depth: 0
            ├─ git fetch origin <baseRef>（复用 checkout 持久化凭证）
            │    ├─ 成功 → 返回 FETCH_HEAD
            │    └─ 失败 → 打印 ERROR + 配置指引 → process.exit(1)
  └─ 返回 { type: 'args', args: '--from-ref <fromRef> --to-ref HEAD' }
```

非 PR 事件（push / workflow_dispatch / schedule）：保持 `--all-files` 全量检查，逻辑不变。

### 2.2 关键实现点

| 位置                           | 实现                                                                                                                          |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `resolveBaseRef(baseRef)`      | 以 `execCapture` 执行本地 ref 查询，命中即返回；未命中走 `execFile` 回退 fetch；回退失败 fail-closed 退出                     |
| `buildAutoArgs()`              | 用 `resolveBaseRef()` 替换原 `createGitAskpass` + `execFile(... {env})` 代码块，`--from-ref` 由固定 `FETCH_HEAD` 改为解析结果 |
| `execFile(cmd, args, options)` | 删除 `options.env` 覆盖能力（唯一调用点已移除），避免再次出现凭证经 env 透传的路径                                            |
| 日志                           | `baseRef`、`baseSha`、异常信息统一经 `sanitizeLogValue()` 折叠换行与控制字符                                                  |
| 导出                           | 新增导出 `resolveBaseRef`，供单测直接调用                                                                                     |

### 2.3 边界与异常处理

- `ATOMGIT_BASE_REF` 为空：不进入增量分支，按非 PR 事件全量检查（与原行为一致）。
- `baseRef` 含异常字符：`rev-parse` 失败即视为未命中，落入回退 fetch；`execFile` 数组传参不经过 shell，无命令注入面。
- 回退 fetch 失败：显式 `process.exit(1)`，不允许在基线缺失时静默通过（否则增量范围错误等于门禁失效）。
- 浅克隆（未配 `fetch-depth: 0`）：`origin/<baseRef>` 不存在，走回退路径并在日志给出明确配置指引。

## 3. 类设计

本插件为 CommonJS 纯函数模块，无类与实例状态。

| 函数                                | 签名                           | 职责                                                            | 变更                  |
| ----------------------------------- | ------------------------------ | --------------------------------------------------------------- | --------------------- |
| `resolveBaseRef`                    | `(baseRef: string) => string`  | 解析可用的增量基线 ref，返回 `origin/<baseRef>` 或 `FETCH_HEAD` | 新增                  |
| `buildAutoArgs`                     | `() => {type, args}`           | 根据事件类型决定 `--all-files` 或 `--from-ref/--to-ref`         | 修改                  |
| `execFile`                          | `(cmd, args, options) => void` | 命令执行封装                                                    | 修改：移除 `env` 覆盖 |
| `createGitAskpass`                  | `(token) => string \| null`    | 生成 GIT_ASKPASS 脚本                                           | 删除                  |
| `removeGitAskpass`                  | `(scriptPath) => void`         | 清理 GIT_ASKPASS 脚本                                           | 删除                  |
| `sanitizeLogValue` / `sanitizePath` | `(value: string) => string`    | 日志脱敏与路径折叠                                              | 复用                  |

模块依赖变化：移除 `os` 依赖（不再需要 `os.tmpdir()`）。

## 4. 数据模型设计

无数据库、无持久化存储、无 schema 变更。运行期数据契约如下：

| 数据           | 形态                                                         | 说明                                                                                                                              |
| -------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| action 输入    | `action.yml` inputs                                          | 删除 `gc_token`；`extra_args` / `report-dir` / `sarif-file` / `sarif-files` / `result` / `checked_files` / `sarif-files` 保持不变 |
| 运行期环境变量 | `ATOMGIT_EVENT_NAME`、`ATOMGIT_BASE_REF`、`ATOMGIT_HEAD_REF` | 只读，用于自动判定检查模式                                                                                                        |
| 增量参数       | `{ type: 'args', args: string }`                             | `args` 为 `--from-ref <ref> --to-ref HEAD`                                                                                        |
| 临时文件       | 无                                                           | 原 GIT_ASKPASS 脚本（`os.tmpdir()/gc-askpass-<pid>.sh`）不再生成，临时凭证残留风险归零                                            |

## 5. 性能设计

本次无新页面、无新接口，不涉及数据库表索引、冗余字段、SQL 优化、缓存、分布式并行、异步处理、算法优化。对 CI 门禁链路的性能影响：

- **正常路径（推荐配置）**：省去一次 `git fetch origin <baseRef>` 网络往返，PR 门禁耗时下降；`resolveBaseRef` 仅执行一次本地 ref 查询，毫秒级开销。
- **回退路径**：与原实现等价的 fetch 开销，无性能回退。
- **全量事件**：`--all-files` 路径未改动。
- **前置条件性能影响**：`fetch-depth: 0` 会增加 checkout 阶段的拉取量，属于用一次性检出成本换取增量基线准确性，与 `git diff origin/main...HEAD` 的 merge-base 计算正确性强相关。
- **结论**：无额外缓存、并行或异步设计需求，不引入新资源开销。

## 6. API 接口设计

无 HTTP/RPC 接口。对外契约即 action 的 inputs/outputs。

### 6.1 输入契约

| 参数            | 变更     | 必填 | 默认值                     | 说明                                                              |
| --------------- | -------- | ---- | -------------------------- | ----------------------------------------------------------------- |
| `gc_token`      | **删除** | -    | -                          | 不再接收任何 Git 凭证；下游残留传参按未知输入提示忽略，不阻断运行 |
| `extra_args`    | 不变     | 否   | 空                         | 为空时自动判定增量/全量                                           |
| `report-dir`    | 不变     | 否   | `/tmp/pre-commit-reports/` | SARIF 报告约定目录                                                |
| `sarif-file`    | 不变     | 否   | 空                         | 显式报告路径，优先于 `report-dir`                                 |
| `sarif-files`   | 不变     | 否   | 空                         | 多值报告路径                                                      |
| `result`        | 不变     | 否   | 空                         | 检查结果输出                                                      |
| `checked_files` | 不变     | 否   | 空                         | 受检文件清单输出                                                  |

### 6.2 输出契约

输出项与语义均不变。

### 6.3 调用契约（行为约定）

- PR 事件：`--from-ref origin/<baseRef> --to-ref HEAD`。
- 非 PR 事件：`--all-files`。
- PR 事件下调用方 checkout **必须**配置 `fetch-depth: 0`；未配置时插件回退 fetch，GitCode 托管 checkout 不持久化凭证的场合会明确报错退出。

## 7. 安全设计

- **鉴权**：继承 checkout 步骤既有的仓库凭证，插件不新增、不接管任何鉴权逻辑；删除 `gc_token` 后，插件侧不存在任何 Token 输入通道。
- **敏感信息**：插件不再接收 Token，`GIT_ASKPASS` 临时脚本与 `PRE_COMMIT_GC_TOKEN` 环境变量传递链路整体删除，Token 不打印、不落盘、不写 `.git/config`；日志中的 `baseRef`、`baseSha`、异常信息统一经 `sanitizeLogValue()` 处理，避免日志注入。本插件不涉及数据库存储与文件下载能力。
- **硬编码**：无 appkey / token / cookie 硬编码；镜像源等公网地址沿用既有的环境变量注入模式。
- **审计日志**：按级别记录基线来源（`[INFO] 使用已检出的基线 ref origin/<baseRef>`）、回退原因（`[WARN] 未找到基线 ref ...`）、失败指引（`[ERROR] ... 请确认 checkout 已配置 fetch-depth: 0`），基线选择过程可追溯。
- **注入防护**：`execFile` 以数组传参，`baseRef` 不经过 shell 解析，无命令注入面。
- **失败语义**：回退 fetch 失败即 `process.exit(1)`，fail-closed，不静默降级为全量或放行。

## 附：验证方式与风险对策

### 验证

- 单测：`npm test`，`test/resolve-base-ref.test.js` 覆盖「命中 `origin/<baseRef>`」「回退 fetch 成功」「回退失败退出」三条路径（本地 bare 仓模拟 origin，离线可跑）。
- 静态检查：`npx eslint index.js test/`、`npx prettier@3.9.5 --check`。
- 产物一致性：`npm run package` 重建 `dist/index.js`，与源码同步提交。
- 端到端：测试仓 `openlibing-test/openlibing-cicd-test` PR #286 已验证不传 `gc_token` 时日志命中 `origin/main`、无 fetch、门禁通过；codearts-hosted 与 SGRunner 自建 euler 执行机矩阵均通过。

### 风险对策

| 风险                                               | 对策                                                                   |
| -------------------------------------------------- | ---------------------------------------------------------------------- |
| 调用方未配 `fetch-depth: 0` 且凭证不可用           | 回退失败时明确报错退出并给出配置指引，不静默降级                       |
| 下游仍传 `gc_token`                                | 平台按未知输入提示忽略；PR 描述提供迁移说明，workflow 统一整改后续进行 |
| 浅克隆下 `origin/<baseRef>` 指针存在但父级历史缺失 | README 与报错信息均要求 `fetch-depth: 0`；由 checkout 保证祖先链完整   |
