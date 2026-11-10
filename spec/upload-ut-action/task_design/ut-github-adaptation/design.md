# UT 测试覆盖率插件支持 GitHub · 设计文档

> FE 需求名称：【openLiBing-coderepo】UT测试覆盖率插件支持GitHub
> 关联 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/280

## 1. 方案设计

### 1.1 总体方案

采用**单份代码、运行时识别平台**，不维护 GitHub 专用分支。平台判定一次完成，后续只读取对应平台的变量：

```js
const isGithub = process.env.GITHUB_ACTIONS === "true";
```

GitHub Actions 注入 `GITHUB_ACTIONS=true`，GitCode Actions 不注入该变量；其余一律按 GitCode 处理。

### 1.2 上下文映射

| 语义        | GitHub                                                      | GitCode（保持现状）                              |
| ----------- | ----------------------------------------------------------- | ------------------------------------------------ |
| 平台判定    | `GITHUB_ACTIONS=true`                                       | 无该标志                                         |
| 仓库地址    | `GITHUB_SERVER_URL` + `/` + `GITHUB_REPOSITORY`             | `ATOMGIT_REPOSITORY_URL`（去 `.git`）            |
| 当前分支    | `GITHUB_REF_NAME`                                           | `ATOMGIT_REF_NAME`                               |
| PR 目标分支 | `GITHUB_BASE_REF`（`pull_request` / `pull_request_target`） | `ATOMGIT_HEAD_REF`（MR，保持既有行为）           |
| 运行 ID     | `GITHUB_RUN_ID`                                             | `ATOMGIT_RUN_ID`                                 |
| 提交 SHA    | `GITHUB_SHA`                                                | `ATOMGIT_SHA`                                    |
| 仓库名      | `GITHUB_REPOSITORY` 最后一段                                | `ATOMGIT_REPOSITORY` / `GIT_REPOSITORY` 最后一段 |
| 工作区      | `GITHUB_WORKSPACE`                                          | `WORKSPACE`                                      |

GitHub PR 事件统一下报到**目标分支**，与平台既有归属口径一致。

### 1.3 OIDC 认证

| 项         | 方案                                                                        |
| ---------- | --------------------------------------------------------------------------- |
| SDK 版本   | `@openlibing/huaweicloud-oidc-client` 由 `0.0.5` 升级到 `0.0.7`             |
| 身份提供商 | SDK 按 `GITHUB_ACTIONS` 自动选择 `GitHubActions` / `GitCodeActions`         |
| 信任委托   | SDK 按 `GITHUB_ACTIONS` 自动选择 `github-actions` / `gitcode-actions`       |
| 插件侧配置 | 不手写 `configure({ oidcProviderName, agencyName })`，避免覆盖 SDK 平台判定 |
| 凭据形态   | OIDC ID Token → STS 临时 AK/SK/SecurityToken，不落长期密钥                  |

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
- `report_path` / `region` / `env_type` / `obs_acl` 输入参数不变；
- 上报报文（`gitUrl` / `branchName` / `pipelineRunId` / `commitId` / `obsUrl`）结构不变；
- GitHub 生效前置：华为云 IAM 已注册 `GitHubActions` 提供商与 `github-actions` 委托；Workflow 声明 `permissions: id-token: write`。

## 2. 实现逻辑设计

### 2.1 upload-ut-action 主流程

1. `run()` 调用 `resolvePlatformContext(process.env)` 一次性解析平台上下文（仓库、分支、运行 ID、提交 SHA、仓库名、工作区）；
2. 解析输入参数并校验 `obs_acl` 白名单；
3. 扫描 `report_path` 并解析覆盖率报告，组装标准 JSON；
4. `ObsUploader.uploadAndNotify` 执行 OIDC 换证 → OBS 上传 → APIG 回调；
5. `setOutput('result', ...)` 写 step 输出（GitHub 优先 `GITHUB_OUTPUT`，GitCode 使用 `STEP_OUTPUT`）。

### 2.2 平台上下文解析

新增纯函数 `resolvePlatformContext(env)`，返回统一结构：

```js
{
  (isGithub,
    gitUrl, // 不含 .git
    branchName, // PR 为目标分支
    pipelineRunId,
    commitId,
    repoName,
    workspace);
}
```

- GitHub 分支：`pull_request` / `pull_request_target` 取 `GITHUB_BASE_REF`，其余取 `GITHUB_REF_NAME`；
- GitCode 分支：沿用现有逻辑（MR 取 `ATOMGIT_HEAD_REF`，其余取 `ATOMGIT_REF_NAME`）；
- 缺失关键字段时保持原有兜底（仓库名 `unknown-repo`、运行 ID 空 → OBS key 使用 `manual`）。

### 2.3 OBS 桶与上传

- `ObsUploader` 新增 `selectObsBucket(isGithub)` 纯函数，模块加载时按 `GITHUB_ACTIONS` 选定 `OBS_BUCKET` 与 `OBS_READ_ENDPOINT`；
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

| 场景                                | 处理                                                          |
| ----------------------------------- | ------------------------------------------------------------- |
| GitHub 上下文缺失（如本地直接运行） | 字段为空，仓库名兜底 `unknown-repo`，日志明确打印平台与上下文 |
| GitHub OIDC 换证失败                | 直接失败并返回 SDK 错误信息，不重试掩盖配置问题               |
| OBS 上传失败                        | 指数退避重试 3 次后失败，step 输出 `result=failed`            |
| APIG 回调失败                       | 告警降级，OBS 已上传数据可由平台补导入                        |
| 后端白名单未放行 GitHub 桶          | 回调返回明确业务失败并落失败记录，不会静默成功                |
| 未识别到报告                        | 保持现状：告警并以成功结束                                    |

## 3. 类设计

| 文件                                                    | 职责                                       | 本次变化                                                                                                      |
| ------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `upload-ut-action/index.js`                             | 入口：输入解析、上下文解析、扫描调度、输出 | 新增 `resolvePlatformContext`；删除分散的 `resolveBranch` / `resolveGitUrl`；`setOutput` 兼容 `GITHUB_OUTPUT` |
| `upload-ut-action/src/obs/ObsUploader.js`               | OIDC 换证、OBS 上传、APIG 回调             | 新增 `selectObsBucket`，桶与读地址按平台选择                                                                  |
| `upload-ut-action/package.json` + `package-lock.json`   | 依赖与版本                                 | OIDC SDK 升级 `0.0.7`；版本号与 `action.yml` 对齐                                                             |
| `upload-ut-action/action.yml`                           | Action 元数据                              | 描述补充双平台；版本随打包自增                                                                                |
| `upload-ut-action/README.md`                            | 用户文档                                   | 补充 GitHub 使用方式、`id-token: write`、输入参数表补齐 `obs_acl`                                             |
| `upload-ut-action/test/platform-context.test.js`        | 单测                                       | 新增双平台上下文解析用例                                                                                      |
| `upload-ut-action/test/obs-uploader.test.js`            | 单测                                       | 新增 `selectObsBucket` 用例                                                                                   |
| `upload-ut-action/dist/index.js`                        | ncc 打包产物                               | 由源码重新构建                                                                                                |
| `openlibing-coderepo/.../ObsBucketServiceImpl.java`     | OBS 下载白名单                             | 单桶 → 双桶集合                                                                                               |
| `openlibing-coderepo/.../ObsBucketService.java`         | 接口契约注释                               | 注释同步双桶                                                                                                  |
| `openlibing-coderepo/.../ObsBucketServiceImplTest.java` | 单测                                       | 新增 GitHub 桶下载成功用例                                                                                    |

## 4. 数据模型设计

### 4.1 数据库

无 DDL、无字段、无索引变更。

### 4.2 上报报文

`ut-coverage.json` 与回调请求体结构不变：

| 字段            | 说明                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| `gitUrl`        | 仓库地址（不含 `.git`；GitHub 为 `https://github.com/{owner}/{repo}`） |
| `branchName`    | 分支（PR 为目标分支）                                                  |
| `pipelineRunId` | 运行 ID（GitHub 为 `GITHUB_RUN_ID`）                                   |
| `commitId`      | 提交 SHA（GitHub 为 `GITHUB_SHA`）                                     |
| `lineCoverage`  | 行覆盖率（唯一必填指标）                                               |
| `fileDetails`   | 文件级行覆盖率明细                                                     |

### 4.3 OBS 对象模型

| 平台    | 桶                          | 对象 key                                              |
| ------- | --------------------------- | ----------------------------------------------------- |
| GitCode | `openlibing-gitcode-action` | `ut-coverage-action/{repoName}/{yyyyMMdd}.{HH}/{runId | manual}/ut-coverage.json` |
| GitHub  | `openlibing-github-action`  | 同上（结构完全一致）                                  |

## 5. 性能设计

- 平台上下文解析为纯内存变量读取，无额外进程或网络调用；
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
2. **平台变量隔离**：GitHub 只读 `GITHUB_*`、GitCode 只读 `ATOMGIT_*`，不做跨平台“取首个非空”兜底，避免语义混用；
3. **桶白名单收敛**：后端只允许两个固定平台桶与两个固定对象前缀，桶名/前缀为代码常量，不可通过配置扩大；桶名取自 URL host、objectKey 取自 URL path，白名单外一律拒绝；
4. **凭证传递**：OBS 临时凭证仅在进程内存中传递，不经命令行参数、不写入日志；
5. **输入边界**：`obs_acl` 仍做白名单校验；`report_path` 路径处理与命令注入防护逻辑不变；
6. **日志**：不打印 AK/SK/SecurityToken；日志包含平台、桶名、对象 key 等可追溯信息；
7. **前端/展示**：无接口与页面变更，前端零改动；
8. **已知边界**：后端白名单扩为双桶后，可读对象集合扩大；现有链路未校验 objectKey 中的 `{owner}/{repo}` 与上报 `gitUrl` 的归属一致性，该加固不在本次范围（与 `github-branch-metrics-display` 设计文档的已知边界一致）；
9. **运行时风险**：`node16` 已停止官方支持，GitHub 会强制按 node20 运行；本次保持 node16 以兼容 GitCode runner，后续随资源池升级到 node20。
