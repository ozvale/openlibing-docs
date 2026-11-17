# design：pre-commit-action 免凭证接入（PR #30）

需求：PR 增量检查优先复用 checkout（`fetch-depth: 0`）已生成的基线 ref `origin/<baseRef>`；`gc_token` 保留为可选兼容输入并标注已废弃，仅在基线 ref 缺失时用于认证 fetch。

## 1. 方案设计

### 1.1 现状问题

`buildAutoArgs()` 在 PR 事件下的既有链路：

1. `getInput('gc_token')` 读取调用方传入的 Token；
2. `createGitAskpass(token)` 在系统临时目录写 GIT_ASKPASS 脚本，Token 经 `PRE_COMMIT_GC_TOKEN` 环境变量传给子进程；
3. `execFile('git', ['fetch', 'origin', baseRef], { env })` 执行认证 fetch；
4. `finally` 中 `removeGitAskpass()` 清理脚本；
5. 固定返回 `--from-ref FETCH_HEAD --to-ref HEAD`。

问题：下游每个接入仓都要维护并传入高权限 Token，凭证暴露面随接入仓数量线性放大；插件内部维护纯凭证搬运代码，与「执行 pre-commit 钩子」的核心职责无关；checkout 在 `fetch-depth: 0` 时已生成远端基线 ref，插件重复 fetch 属于冗余网络操作。注意：凭证是否可复用取决于执行机类型——GitCode 托管 checkout 默认不持久化凭证，自建 runner 的 checkout 可能写入 `.git/config`。

### 1.2 方案对比

| 方案                                           | 说明                                                                    | 结论                                                                                 |
| ---------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| A. 保留 `gc_token` 为唯一路径                  | 维持现状，插件总是自行认证 fetch                                        | 不采纳：凭证暴露面无法收敛，推荐路径仍要求下游维护 Token                             |
| B. 直接删除 Token                              | 改为完全依赖 checkout 持久化凭证做回退 fetch                            | 不采纳：托管 checkout 默认不持久化凭证，未配 `fetch-depth: 0` 的存量调用方会直接断链 |
| C. 复用基线 ref + 保留 `gc_token` 兼容（选定） | 命中 `origin/<baseRef>` 时零 fetch 零凭证；缺失时按有无 `gc_token` 分流 | 采纳：新接入免凭证，存量行为不变，可渐进下线 Token                                   |

### 1.3 总体方案

- 插件侧：新增 `resolveBaseRef(baseRef)` 实现三级解析——优先 `origin/<baseRef>`；缺失且传入 `gc_token` 时走原 askpass 认证 fetch；缺失且未传 `gc_token` 时无凭证 fetch，失败 fail-closed。`gc_token` 改为可选并标注已废弃。
- 调用方侧（本次不改）：推荐 PR 场景 checkout 配置 `fetch-depth: 0`。该约束以 README 推荐配置形式声明，`openlibing-cicd` 等调用的 workflow 统一整改后续单独进行。
- 不在本 PR 范围内：不打 tag、不改任何 `.gitcode/workflows/` 文件、不改非 PR 事件的 `--all-files` 行为、不删除 `gc_token` 输入（下线待下游迁移完成后另起变更）。

## 2. 实现逻辑设计

### 2.1 主流程（PR 事件）

```
ATOMGIT_EVENT_NAME ∈ {mr, pull_request, note} 且 ATOMGIT_BASE_REF 非空
  └─ resolveBaseRef(baseRef)
       ├─ git rev-parse --verify --quiet origin/<baseRef> 有输出
       │    ├─ 返回 origin/<baseRef>（零 fetch、零凭证）
       │    └─ warnIfShallowClone() 浅历史仅提示
       └─ 无输出
            ├─ 打印 WARN + 建议 fetch-depth: 0
            ├─ 传入 gc_token？
            │    ├─ 是：[DEPRECATED] + askpass 认证 fetch
            │    │      ├─ 成功 → 返回 FETCH_HEAD
            │    │      └─ 失败 → ERROR + exit(1)
            │    └─ 否：无凭证 fetch
            │           ├─ 成功 → 返回 FETCH_HEAD
            │           └─ 失败 → 修复指引 + exit(1)
            └─ warnIfShallowClone()
  └─ 返回 { type: 'args', args: '--from-ref <fromRef> --to-ref HEAD' }
```

非 PR 事件（push / workflow_dispatch / schedule）：保持 `--all-files` 全量检查，逻辑不变。

### 2.2 关键实现点

| 位置                                    | 实现                                                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `resolveBaseRef(baseRef)`               | `execCapture` 查本地 ref，命中即返回；未命中按有无 `gc_token` 分流到认证 fetch 与无凭证 fetch，失败均 fail-closed |
| `buildAutoArgs()`                       | 调用 `resolveBaseRef()`，`--from-ref` 由固定 `FETCH_HEAD` 改为解析结果                                            |
| `createGitAskpass` / `removeGitAskpass` | 保留，仅服务 `gc_token` 兼容路径：脚本写系统临时目录（0700），Token 经环境变量传递，`finally` 立即清理            |
| `execFile(cmd, args, options)`          | 保留 `options.env` 覆盖能力，仅 askpass 兼容路径使用                                                              |
| `warnIfShallowClone()`                  | 新增：`git rev-parse --is-shallow-repository` 为 `true` 时打印提示，不阻断                                        |
| `printBaseRefFixHint(baseRef)`          | 新增：基线 ref 缺失且无凭证 fetch 失败时输出可照抄的 `fetch-depth: 0` 修复指引                                    |
| 日志                                    | `baseRef`、`baseSha`、异常信息统一经 `sanitizeLogValue()` 折叠换行与控制字符                                      |
| 导出                                    | 导出 `resolveBaseRef`，供单测直接调用                                                                             |

### 2.3 边界与异常处理

- `ATOMGIT_BASE_REF` 为空：不进入增量分支，按非 PR 事件全量检查（与原行为一致）。
- `baseRef` 含异常字符：`rev-parse` 失败即视为未命中，落入回退 fetch；`execFile` 数组传参不经过 shell，消除 shell 注入面；ref 合法性由 git 命令自身校验。
- 回退 fetch 失败：显式 `process.exit(1)`，不允许在基线缺失时静默通过（否则增量范围错误等于门禁失效）。
- 浅克隆（未配 `fetch-depth: 0`）：`origin/<baseRef>` 通常不存在，走回退路径并在日志给出明确配置指引。
- 中间态（`origin/<baseRef>` 存在但历史仍为浅）：命中后由 `warnIfShallowClone()` 提示增量口径可能退化，不阻断执行。
- 托管 checkout 无持久化凭证：未传 `gc_token` 时无凭证 fetch 会失败并 fail-closed，需按指引补 `fetch-depth: 0`；该场景不等价于改造前的隐式成功。

## 3. 类设计

本插件为 CommonJS 纯函数模块，无类与实例状态。

| 函数                                | 签名                           | 职责                                                          | 变更             |
| ----------------------------------- | ------------------------------ | ------------------------------------------------------------- | ---------------- |
| `resolveBaseRef`                    | `(baseRef: string) => string`  | 三级解析增量基线 ref，返回 `origin/<baseRef>` 或 `FETCH_HEAD` | 新增             |
| `buildAutoArgs`                     | `() => {type, args}`           | 根据事件类型决定 `--all-files` 或 `--from-ref/--to-ref`       | 修改             |
| `execFile`                          | `(cmd, args, options) => void` | 命令执行封装，保留 `env` 覆盖                                 | 不变             |
| `createGitAskpass`                  | `(token) => string \| null`    | 生成 GIT_ASKPASS 脚本                                         | 保留（兼容路径） |
| `removeGitAskpass`                  | `(scriptPath) => void`         | 清理 GIT_ASKPASS 脚本                                         | 保留（兼容路径） |
| `warnIfShallowClone`                | `() => void`                   | 浅克隆自检与提示                                              | 新增             |
| `printBaseRefFixHint`               | `(baseRef: string) => void`    | 基线解析失败时的修复指引                                      | 新增             |
| `sanitizeLogValue` / `sanitizePath` | `(value: string) => string`    | 日志脱敏与路径折叠                                            | 复用             |

模块依赖：保留 `os` 依赖（兼容路径仍需 `os.tmpdir()` 生成 askpass 脚本）。

## 4. 数据模型设计

无数据库、无持久化存储、无 schema 变更。运行期数据契约如下：

| 数据           | 形态                                                         | 说明                                                                                                 |
| -------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| action 输入    | `action.yml` inputs                                          | `gc_token` 改为可选并标注已废弃；`extra_args` / `report-dir` / `sarif-file` / `sarif-files` 保持不变 |
| 运行期环境变量 | `ATOMGIT_EVENT_NAME`、`ATOMGIT_BASE_REF`、`ATOMGIT_HEAD_REF` | 只读，用于自动判定检查模式                                                                           |
| 增量参数       | `{ type: 'args', args: string }`                             | `args` 为 `--from-ref <ref> --to-ref HEAD`                                                           |
| 临时文件       | `os.tmpdir()/gc-askpass-<pid>.sh`                            | 仅在 `gc_token` 兼容路径生成（权限 0700），`finally` 中立即删除；推荐路径不产生任何凭证文件          |

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

| 参数         | 变更                 | 必填 | 默认值                     | 说明                                                              |
| ------------ | -------------------- | ---- | -------------------------- | ----------------------------------------------------------------- |
| `gc_token`   | **改为可选，已废弃** | 否   | 空                         | 仅基线 ref 缺失时用于兼容认证 fetch；推荐 `fetch-depth: 0` 后删除 |
| `extra_args` | 不变                 | 否   | 空                         | 为空时自动判定增量/全量                                           |
| `report-dir` | 不变                 | 否   | `/tmp/pre-commit-reports/` | SARIF 报告约定目录                                                |
| `sarif-file` | 不变                 | 否   | 空                         | 显式报告路径，优先于 `report-dir`                                 |

### 6.2 输出契约

输出项与语义均不变：`sarif-files`（多值报告路径）、`result`（检查结果）、`checked_files`（受检文件清单）。

### 6.3 调用契约（行为约定）

- PR 事件：`origin/<baseRef>` 命中时 `--from-ref origin/<baseRef> --to-ref HEAD`；未命中且 fetch 成功时 `--from-ref FETCH_HEAD --to-ref HEAD`。
- 非 PR 事件：`--all-files`。
- PR 事件下**推荐**调用方 checkout 配置 `fetch-depth: 0`；未配置时插件走回退 fetch：传 `gc_token` 用认证 fetch，未传则无凭证 fetch（GitCode 托管 checkout 默认不持久化凭证，失败即报错退出）。

## 7. 安全设计

- **鉴权**：推荐路径不注入任何凭证（复用 checkout 生成的 `origin/<baseRef>`）；兼容路径沿用原有 `gc_token` + GIT_ASKPASS 机制，插件不扩展新的鉴权通道。
- **敏感信息**：`gc_token` 仅经环境变量 `PRE_COMMIT_GC_TOKEN` 传给 askpass 子进程，不出现在命令行参数、不写入被检仓 `.git/config`；askpass 脚本权限 0700 且 `finally` 中立即删除。Token 不打印；日志中的 `baseRef`、`baseSha`、异常信息统一经 `sanitizeLogValue()` 处理，避免日志注入。本插件不涉及数据库存储与文件下载能力。
- **硬编码**：无 appkey / token / cookie 硬编码；镜像源等公网地址沿用既有的环境变量注入模式。
- **审计日志**：按级别记录基线来源（`[INFO] 使用已检出的基线 ref origin/<baseRef>`）、兼容路径（`[DEPRECATED] gc_token 输入已废弃`）、回退原因（`[WARN] 未找到基线 ref ...`）、失败指引（`[ERROR] ... 请确认 checkout 已配置 fetch-depth: 0`），基线选择过程可追溯。
- **注入防护**：`execFile` 以数组传参，`baseRef` 不经过 shell 解析，无 shell 注入面。
- **失败语义**：回退 fetch 失败即 `process.exit(1)`，fail-closed，不静默降级为全量或放行。

## 附：验证方式与风险对策

### 验证

- 单测：`npm test` 7 个用例，`test/resolve-base-ref.test.js` 覆盖「命中 `origin/<baseRef>`」「回退无凭证 fetch 成功」「回退 fetch 失败退出」「浅克隆提示」「`gc_token` 兼容路径」五条路径（本地 bare 仓模拟 origin，离线可跑）。
- 静态检查：`npx eslint index.js test/`、`npx prettier@3.9.5 --check`。
- 产物一致性：`npm run package` 重建 `dist/index.js`，与源码同步提交。
- 端到端：业务 PR #30 的 7 条检查全部通过；测试仓 `openlibing-test/openlibing-cicd-test` PR 事件不传 `gc_token` 时日志命中 `origin/main`、无凭证报错，门禁通过。

### 风险对策

| 风险                                               | 对策                                                                                                               |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 调用方未配 `fetch-depth: 0` 且凭证不可用           | 回退失败时明确报错退出并给出配置指引，不静默降级                                                                   |
| 下游仍传 `gc_token`                                | 保留为可选兼容输入，行为与改造前一致（多一条 `[DEPRECATED]` 日志）；PR 描述提供迁移说明，workflow 统一整改后续进行 |
| 浅克隆下 `origin/<baseRef>` 指针存在但父级历史缺失 | 命中后由 `warnIfShallowClone()` 提示；README 与报错信息均推荐 `fetch-depth: 0`                                     |
| 直接删除 `gc_token` 导致存量断链                   | 本次不删除输入；下线需「发布新版本 → 下游迁移 → 再删除」分步执行                                                   |
