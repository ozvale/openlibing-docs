# UT 测试覆盖率插件支持 GitHub · 设计文档

> FE 需求名称：【openLiBing-coderepo】UT测试覆盖率插件支持GitHub
> 关联 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/280

## 1. 方案设计

### 1.1 总体方案

采用**单份代码、运行时识别平台**，不维护 GitHub 专用分支。平台判定一次完成，后续只读取对应平台的变量：

```js
// GitHub 仅在 GITHUB_ACTIONS=true 且不存在 GitCode 关键上下文时成立；
// 兼容层 runner 若同时注入两平台变量，以 GitCode 为准，避免存量上报回归。
const isGithub = detectPlatform(process.env) === "github";
```

平台判定采用 `GITHUB_ACTIONS=true && 不存在 ATOMGIT_* 关键变量` 的组合条件：

- GitHub Actions 注入 `GITHUB_ACTIONS=true`，且不注入 `ATOMGIT_RUN_ID` / `ATOMGIT_REPOSITORY` / `ATOMGIT_REPOSITORY_URL`；
- GitCode Actions 注入上述 `ATOMGIT_*` 关键上下文；若兼容层 runner 额外注入 `GITHUB_ACTIONS=true`，组合条件仍判定为 GitCode；
- 依据 1：项目 GitHub 接入指南（`github-plugin-onboarding`）与已交付的 `code-metrics-action` GitHub 适配均以 `GITHUB_ACTIONS` 判定并在 GitCode 侧完成回归；
- 依据 2：组合条件作为防御性兜底，避免单变量误判导致存量 GitCode 上报同时切换 OBS 桶与 OIDC 提供商；
- `detectPlatform` 在 `src/util/platform.js` 统一实现，`index.js` 与 `ObsUploader.js` 共用，单测覆盖双标志冲突场景。

### 1.2 上下文映射

| 语义        | GitHub                                                                                                 | GitCode（保持现状）                              |
| ----------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| 平台判定    | `GITHUB_ACTIONS=true` 且无 `ATOMGIT_*` 关键变量                                                        | 无该标志，或存在 `ATOMGIT_*` 关键变量            |
| 仓库地址    | `GITHUB_SERVER_URL` + `/` + `GITHUB_REPOSITORY`                                                        | `ATOMGIT_REPOSITORY_URL`（去 `.git`）            |
| 当前分支    | `GITHUB_REF_NAME`                                                                                      | `ATOMGIT_REF_NAME`                               |
| PR 目标分支 | `GITHUB_BASE_REF`（`pull_request` / `pull_request_target`）                                            | `ATOMGIT_HEAD_REF`（MR，保持既有行为）           |
| 运行 ID     | `GITHUB_RUN_ID`                                                                                        | `ATOMGIT_RUN_ID`                                 |
| 提交 SHA    | PR 事件取 `GITHUB_EVENT_PATH` 的 `pull_request.base.sha`；其余取 `GITHUB_SHA`（缺失回退 `GITHUB_SHA`） | `ATOMGIT_SHA`                                    |
| 仓库名      | `GITHUB_REPOSITORY` 最后一段                                                                           | `ATOMGIT_REPOSITORY` / `GIT_REPOSITORY` 最后一段 |
| 工作区      | `GITHUB_WORKSPACE`                                                                                     | `WORKSPACE`                                      |

GitHub PR 事件统一下报到**目标分支**：`branchName=GITHUB_BASE_REF`，`commitId=pull_request.base.sha`（从 `GITHUB_EVENT_PATH` 解析），两者同属目标分支。`pull_request` 事件的 `GITHUB_SHA` 是 PR 合并提交（`refs/pull/N/merge`），不属于目标分支，因此不作为 PR 场景的 `commitId`；事件文件缺失或解析失败时回退 `GITHUB_SHA` 并打印告警。GitCode 保持既有 `ATOMGIT_HEAD_REF` / `ATOMGIT_SHA` 行为。

### 1.3 OIDC 认证

| 项         | 方案                                                                                                                                               |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDK 版本   | `@openlibing/huaweicloud-oidc-client` 由 `0.0.5` 升级到 `0.0.7`                                                                                    |
| 身份提供商 | SDK 按 `GITHUB_ACTIONS` 自动选择 `GitHubActions` / `GitCodeActions`                                                                                |
| 信任委托   | SDK 按 `GITHUB_ACTIONS` 自动选择 `github-actions` / `gitcode-actions`                                                                              |
| 插件侧配置 | 正常不手写 `configure`；仅当检测到 `GITHUB_ACTIONS=true` 但存在 `ATOMGIT_*`（兼容 runner 冲突）时，显式覆盖为 `GitCodeActions` / `gitcode-actions` |
| 凭据形态   | OIDC ID Token → STS 临时 AK/SK/SecurityToken，不落长期密钥                                                                                         |

### 1.4 OBS 桶隔离

| 平台    | 桶                          | 读地址                                                                   |
| ------- | --------------------------- | ------------------------------------------------------------------------ |
| GitHub  | `openlibing-github-action`  | `https://openlibing-github-action.obs.cn-southwest-2.myhuaweicloud.com`  |
| GitCode | `openlibing-gitcode-action` | `https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com` |

对象 key 结构保持完全一致：

```text
ut-coverage-action/{repoName}/{yyyyMMdd}.{HH}/{pipelineRunId|manual}/ut-coverage.json
```

### 1.5 兼容性策略

- GitCode 场景只读取 `ATOMGIT_*`，OBS 桶、上报报文与既有工作流行为不变；
- `action.yml` 保持 `runs.using: node16`：GitCode runner 仅支持 node16；GitHub 会将 node16 动作强制按 node20 运行（已知告警，纳入后续升级跟踪）；
- `report_path` / `region` / `env_type` 输入参数不变；
- 上报报文（`gitUrl` / `branchName` / `pipelineRunId` / `commitId` / `obsUrl`）结构不变；
- GitHub 生效前置：华为云 IAM 已注册 `GitHubActions` 提供商与 `github-actions` 委托；Workflow 声明 `permissions: id-token: write`。

## 2. 实现逻辑设计

### 2.1 upload-ut-action 主流程

1. `run()` 调用 `resolvePlatformContext(process.env)` 一次性解析平台上下文（仓库、分支、运行 ID、提交 SHA、仓库名、工作区）；
2. 解析输入参数；
3. 扫描 `report_path` 并解析覆盖率报告，组装标准 JSON；
4. `ObsUploader.uploadAndNotify` 执行 OIDC 换证 → OBS 上传 → APIG 回调；
5. `setOutput('result', ...)` 写 step 输出（GitHub 优先 `GITHUB_OUTPUT`，GitCode 使用 `STEP_OUTPUT`）。

### 2.2 平台上下文解析

新增纯函数 `resolvePlatformContext(env)`，返回统一结构：

```js
{
  isGithub,
  gitUrl, // 不含 .git
  branchName, // PR 为目标分支
  pipelineRunId,
  commitId, // PR 为目标分支 base.sha
  repoName,
  workspace,
}
```

- 平台判定：调用 `detectPlatform(env)`，仅 `GITHUB_ACTIONS=true` 且无 `ATOMGIT_*` 关键变量时按 GitHub 处理；
- GitHub 分支：`pull_request` / `pull_request_target` 取 `GITHUB_BASE_REF`，其余取 `GITHUB_REF_NAME`；
- GitHub 提交：PR 事件从 `GITHUB_EVENT_PATH` 解析 `pull_request.base.sha`，与目标分支自洽；缺失时回退 `GITHUB_SHA` 并告警；
- GitCode 分支：沿用现有逻辑（MR 取 `ATOMGIT_HEAD_REF`，其余取 `ATOMGIT_REF_NAME`）；
- 缺失关键字段时保持原有兜底（仓库名 `unknown-repo`、运行 ID 空 → OBS key 使用 `manual`）。

### 2.3 OBS 桶与上传

- `ObsUploader` 新增 `selectObsBucket(isGithub)` 纯函数，模块加载时按 `detectPlatform()` 选定 `OBS_BUCKET` 与 `OBS_READ_ENDPOINT`；
- 兼容 runner 同时注入两平台变量时按 GitCode 选择桶，并显式 `configure` 覆盖 SDK 的 OIDC 提供商为 `GitCodeActions` / `gitcode-actions`；
- `uploadJson` 使用选定的桶上传，ACL 与重试策略不变；
- 上传成功后回调 `POST /action-api/ut/coverage/report`，请求体不变；
- 回调失败仅告警、不阻断（OBS 数据已留存），与现有行为一致。

### 2.4 step 输出兼容

`setOutput` 目标文件按 `GITHUB_OUTPUT` → `STEP_OUTPUT` 顺序选择；两者都不存在时仅告警。写入格式仍为 `key=value` 单行追加。

### 2.5 openlibing-coderepo 下载白名单

`ObsBucketServiceImpl.downloadToTempFile`：

1. 解析 `obsUrl`，host 首个 label 为桶名，path 为首个 `/` 之后的内容为 objectKey；
2. 桶名校验由单桶等值判断改为 `ALLOWED_METRICS_OBS_BUCKETS.contains(bucketName)`；
3. 对象前缀仍只允许 `code-metrics-action/`、`ut-coverage-action/`；
4. 其余大小上限、流式复制、临时文件清理逻辑不变。

### 2.6 异常与降级

| 场景                                | 处理                                                                    |
| ----------------------------------- | ----------------------------------------------------------------------- |
| 双平台标志同时存在                  | 按 GitCode 处理并告警，桶与 OIDC 提供商均保持 GitCode，避免存量上报回归 |
| GitHub 上下文缺失（如本地直接运行） | 字段为空，仓库名兜底 `unknown-repo`，日志明确打印平台与上下文           |
| GitHub PR 事件文件缺失              | `commitId` 回退 `GITHUB_SHA` 并告警，分支仍取 `GITHUB_BASE_REF`         |
| GitHub OIDC 换证失败                | 直接失败并返回 SDK 错误信息，不重试掩盖配置问题                         |
| OBS 上传失败                        | 指数退避重试 3 次后失败，step 输出 `result=failed`                      |
| APIG 回调失败                       | 告警降级，OBS 已上传数据可由平台补导入                                  |
| 后端白名单未放行 GitHub 桶          | 回调返回明确业务失败并落失败记录，不会静默成功                          |
| 未识别到报告                        | 保持现状：告警并以成功结束                                              |

## 3. 类设计

| 文件                                                    | 职责                                       | 本次变化                                                                                                                                |
| ------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `upload-ut-action/index.js`                             | 入口：输入解析、上下文解析、扫描调度、输出 | 新增 `resolvePlatformContext` / `resolveGithubCommitId`；删除分散的 `resolveBranch` / `resolveGitUrl`；`setOutput` 兼容 `GITHUB_OUTPUT` |
| `upload-ut-action/src/util/platform.js`                 | 平台判定                                   | 新增 `detectPlatform`，`GITHUB_ACTIONS=true` 且无 `ATOMGIT_*` 关键变量时判定 GitHub，双标志冲突时按 GitCode                             |
| `upload-ut-action/src/obs/ObsUploader.js`               | OIDC 换证、OBS 上传、APIG 回调             | 新增 `selectObsBucket`，桶与读地址按 `detectPlatform` 选择；双标志冲突时覆盖 SDK OIDC 提供商为 GitCode                                  |
| `upload-ut-action/package.json` + `package-lock.json`   | 依赖与版本                                 | OIDC SDK 升级 `0.0.7`；版本号与 `action.yml` 对齐                                                                                       |
| `upload-ut-action/action.yml`                           | Action 元数据                              | 描述补充双平台；版本随打包自增                                                                                                          |
| `upload-ut-action/README.md`                            | 用户文档                                   | 补充 GitHub 使用方式、`id-token: write`                                                                                                 |
| `upload-ut-action/test/platform-context.test.js`        | 单测                                       | 新增双平台上下文解析用例                                                                                                                |
| `upload-ut-action/test/obs-uploader.test.js`            | 单测                                       | 新增 `selectObsBucket` 用例                                                                                                             |
| `upload-ut-action/.gitleaks.toml`                       | gitleaks 误报白名单                        | 新增 `^dist/`：ncc 产物内联第三方依赖会带入示例密钥/许可证邮箱误报，源码文件仍独立扫描                                                  |
| `upload-ut-action/dist/index.js`                        | ncc 打包产物                               | 由源码重新构建                                                                                                                          |
| `openlibing-coderepo/.../ObsBucketServiceImpl.java`     | OBS 下载白名单                             | 单桶 → 双桶集合                                                                                                                         |
| `openlibing-coderepo/.../ObsBucketService.java`         | 接口契约注释                               | 注释同步双桶                                                                                                                            |
| `openlibing-coderepo/.../ObsBucketServiceImplTest.java` | 单测                                       | 新增 GitHub 桶下载成功用例                                                                                                              |

## 4. 数据模型设计

### 4.1 数据库

无 DDL、无字段、无索引变更。

### 4.2 上报报文

`ut-coverage.json` 与回调请求体结构不变：

| 字段            | 说明                                                                    |
| --------------- | ----------------------------------------------------------------------- |
| `gitUrl`        | 仓库地址（不含 `.git`；GitHub 为 `https://github.com/{owner}/{repo}`）  |
| `branchName`    | 分支（PR 为目标分支 `GITHUB_BASE_REF`）                                 |
| `pipelineRunId` | 运行 ID（GitHub 为 `GITHUB_RUN_ID`）                                    |
| `commitId`      | 提交 SHA；GitHub PR 事件为 `pull_request.base.sha`，其余为 `GITHUB_SHA` |
| `lineCoverage`  | 行覆盖率（唯一必填指标）                                                |
| `fileDetails`   | 文件级行覆盖率明细                                                      |

### 4.3 OBS 对象模型

| 平台    | 桶                          | 对象 key                                                                           |
| ------- | --------------------------- | ---------------------------------------------------------------------------------- |
| GitCode | `openlibing-gitcode-action` | `ut-coverage-action/{repoName}/{yyyyMMdd}.{HH}/{runId \| manual}/ut-coverage.json` |
| GitHub  | `openlibing-github-action`  | 同上（结构完全一致）                                                               |

## 5. 性能设计

- 平台上下文解析以内存变量读取为主；仅 GitHub PR 事件额外读取一次 `GITHUB_EVENT_PATH` 事件 JSON（本地小文件），无网络调用；
- OIDC 换证仍为单次调用（SDK 内部缓存/并发去重），OBS 上传与回调次数不变；
- SDK 0.0.7 新增 `undici` 依赖，由 ncc 内联到 `dist/index.js`；运行时优先由插件注入的 fetch polyfill 提供全局 `fetch`，node18+ 环境直接使用原生 fetch；
- 后端桶名校验由一次等值判断变为最多两次集合比较，耗时可忽略，不新增 OBS 请求或数据库查询。

## 6. API 接口设计

无新增或修改的 HTTP 接口。

| 接口                                  | 变更                                           |
| ------------------------------------- | ---------------------------------------------- |
| `POST /action-api/ut/coverage/report` | 请求/响应结构不变；`obsUrl` 允许 GitHub 平台桶 |
| OBS 上传                              | 桶按平台选择；对象 key 规则不变                |

## 7. 安全设计

1. **免密优先**：GitHub 侧使用 OIDC 临时凭证，仓库不落任何长期 AK/SK；Workflow 必须显式声明 `id-token: write`；
2. **OIDC 准入控制（运维前置）**：华为云 IAM 信任委托 `github-actions` 必须通过信任策略 `sub` 限定到允许的 GitHub 组织/仓库/分支（如 `repo:org/repo:ref:refs/heads/main`），禁止 `repo:*` 等通配；未授权仓库的 OIDC 换证必须失败。该约束是防止任意 GitHub 仓库写入 `openlibing-github-action` 桶的唯一准入边界；
3. **平台变量隔离**：GitHub 只读 `GITHUB_*`、GitCode 只读 `ATOMGIT_*`，不做跨平台“取首个非空”兜底；双平台标志同时存在时以 GitCode 为准并告警，避免存量 GitCode 上报被误切桶/提供商；
4. **双桶白名单（可读集合由单桶扩展为双桶）**：后端只允许 `openlibing-gitcode-action`、`openlibing-github-action` 两个固定平台桶与两个固定对象前缀，桶名/前缀为代码常量，不可通过配置扩大；桶名取自 URL host、objectKey 取自 URL path，白名单外一律拒绝；本次改动**扩大了可读桶集合**，不是收敛；
5. **凭证传递**：OBS 临时凭证仅在进程内存中传递，不经命令行参数、不写入日志；
6. **输入边界**：`report_path` 路径处理与命令注入防护逻辑不变；
7. **日志**：不打印 AK/SK/SecurityToken；日志包含平台、桶名、对象 key 等可追溯信息；
8. **前端/展示**：无接口与页面变更，前端零改动；
9. **已知边界（风险等级：Medium）**：UT 覆盖率对象 key 仅含 `{repoName}`、不含 owner，无法直接校验 objectKey 与上报 `gitUrl` 的仓库归属一致性。缓解措施：`/ut/coverage/report` 为 APIG 机机接口需通过 IAM 签名认证；IAM 信任策略 `sub` 限定来源仓库；失败请求落失败记录并审计。彻底加固需在 OBS key 中加入 `{owner}/{repo}` 并做归属比对，属于破坏性 key 结构变更，列为后续独立需求，不在本次范围（与 `github-branch-metrics-display` 设计文档的已知边界一致）；
10. **dist 产物完整性**：发布前必须重新执行 `npm run package` 并核验 dist 已内联新逻辑（关键常量/函数），不能仅以 `node --check` 语法通过作为重建依据；
11. **运行时风险**：`node16` 已停止官方支持，GitHub 会强制按 node20 运行；本次保持 node16 以兼容 GitCode runner，后续随资源池升级到 node20。
