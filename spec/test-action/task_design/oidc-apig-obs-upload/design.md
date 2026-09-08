# test-action pytest-orch OIDC 化 APIG / OBS 上传 — 技术设计

> 来源：`openlibing/test-action` master commit `53998707e23041a1b071e931c818d56261fb3ea6`
> （`feat(pytest-orch): switch to OIDC for APIG and OBS uploads`，2026-09-02）。
> 本文档为该已合入变更的设计归档，覆盖方案设计、实现逻辑、类设计、数据模型、性能、API 接口、安全七个维度。

## 方案概述

`pytest-orch` 插件原先依赖两类长期静态凭证完成结果上报：`obs-ak` / `obs-sk` 输入（直连 OBS）与 `scheduler-secret` 内的 `apig_code` / `apig_key` / `apig_secret`（直连 APIG）。这些明文凭证会进入 CI 日志、子进程命令行和执行器日志目录，泄漏面与轮换成本都不可接受。

本次改造在 `run()` 既有编排内引入 `@openlibing/huaweicloud-oidc-client`，用 OIDC → STS 临时凭证替代全部长期凭证，并把上传能力从执行器侧收敛到插件侧：

1. 删除 `obs-ak` / `obs-sk` 输入，`scheduler-secret` 白名单由 7 字段收敛为 `auth_token` / `k8s_auth`。
2. 新增可选输入 `oidc-config`，仅透传显式字段给 SDK `configure()`，未传字段保持 SDK 内置默认。
3. 上传由执行器产出的 `output.json` 驱动：`XmlFiles` → APIG（multipart form-data，用例元数据上报）、`ArchiveLogDir` → OBS（`ObsPrefix` 作为对象键前缀，归档日志上传）。
4. 将 index.js 中 19 个输入校验函数抽取为独立模块 `validators.js`，并新增 4 个 OIDC / manifest 相关校验。

## 架构决策

- **临时凭证替代长期凭证**：`getCredentials()` 返回分钟级过期的 `accessKeyId` / `secretAccessKey` / `securityToken`，仓库与流水线不再持有永久 AK/SK；OBS 客户端用该三元组构造。
- **APIG 走 SDK `callApig` 而非手工签名**：`callApig("POST", url, headers, body)` 一行完成换证 + V11-HMAC-SHA256 签名 + `X-Security-Token` 注入 + 发送。APIG 指向 openlibing 平台固定端点，因此该路径调用 `configure()` **不传参**，使用 SDK 内置默认。
- **multipart 用 `form-data` 并一次性 `getBuffer()`**：V11 签名要求签名 body 与发送 body 字节一致，Buffer 形态可同时满足签名与发送；相比手工拼装 boundary 减少出错面。头字段写作首字母大写的 `"Content-Type"`，以覆盖 `callApig` 的默认头合并。
- **上传能力放在插件侧而非执行器侧**：执行器只产出 `output.json` 清单，插件负责落地上传，凭证与网络出口集中在 Action 运行时，便于统一脱敏与鉴权。
- **`output.json` 按不受信输入处理**：清单由测试执行侧代码间接产出，可被污染；任何用于文件读取或对象写入的字段必须先通过白名单、类型、上限与路径限定校验（威胁建模 FIND-02）。
- **上传属非关键路径**：13.5 / 13.6 失败一律降级为 `core.warning`，不改变退出码与 Step 14 之后的输出；但脱敏阶段目录级失败**跳过上传**（fail-closed），宁可丢归档也不泄漏密钥。
- **校验逻辑模块化**：抽出 `validators.js` 使纯校验函数可独立复用与单测，index.js 仅保留编排。

## 涉及文件

| 文件                                             | 操作 | 说明                                                                                                                 |
| ------------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------- |
| `pytest-orch/index.js`                           | 修改 | 接入 OIDC 上传（Step 13.5 / 13.6）、manifest 校验、日志脱敏、`silent` 执行；移除本地校验函数实现                     |
| `pytest-orch/validators.js`                      | 新增 | 19 个校验函数（含新增 `validateOidcConfig` / `validateOutputManifest` / `confinePathToRoots` / `validateObsPrefix`） |
| `pytest-orch/action.yml`                         | 修改 | 删除 `obs-ak` / `obs-sk`，新增可选 `oidc-config`                                                                     |
| `pytest-orch/package.json`                       | 修改 | 新增 `@openlibing/huaweicloud-oidc-client@^0.0.5`、`esdk-obs-nodejs@3.26.2`、`form-data@^4.0.0`                      |
| `pytest-orch/README.md`                          | 修改 | 补充 `oidc-config` 输入说明                                                                                          |
| `pytest-orch/dist/index.js`、`dist/licenses.txt` | 重建 | `ncc build` 内联新依赖，licenses 同步                                                                                |
| `pytest-orch/package-lock.json`                  | 重建 | 依赖锁                                                                                                               |

## 实现逻辑设计

### 主流程新增/变更环节

```text
Step 0   加载输入 → validators 校验
         ├ core.setSecret(schedulerSecretRaw)，并对解析后 ≥8 字符的字符串字段逐个注册掩码
         ├ collectSecretValues(...) → secretValuesToScrub（Set 去重 + 长度降序）
         └ validateOidcConfig(oidc-config) → oidcConfig（仅回填显式字段；空输入 → {}）

Step 12  执行 main.py
         └ exec.exec(venvPython, args, { silent: true,
                                         env: { ...process.env, SCHEDULER_SECRET },
                                         listeners: { stdout, stderr } })

Step 11  读取 output.json（原 Step 13 分组名调整）
         ├ validateOutputManifest(JSON.parse(...))     白名单 + 类型 + 上限，非法整体拒绝
         ├ outputAllowedRoots = [baseDir, testCaseDir, path.resolve(archiveLogDir)?]
         ├ XmlFiles[]    → confinePathToRoots + .xml 后缀校验 → safeXmlFiles
         ├ ArchiveLogDir → confinePathToRoots                → safeArchiveLogDir
         └ ObsPrefix     → validateObsPrefix                 → safeObsPrefix
         （单项非法 → core.warning + 跳过该项，不中断）

Step 13.5 上传 XmlFiles → APIG
Step 13.6 上传 ArchiveLogDir → OBS
Step 14   设置 outputs / Step 15 清理 ASKPASS
```

可信根目录：`baseDir = /tmp/pytest-orch/<workspace>`，`testCaseDir = <baseDir>/pytest-infra`（工作流检出的用例仓克隆目标），以及显式配置的 `archive-log-dir`。

### Step 13.5 — APIG 上传

`uploadXmlFilesViaApig(safeXmlFiles, pipelineId, pipelineRunId, jobRunId)`：

1. `configure()`（无参，SDK 内置默认，端点为 openlibing 平台）。
2. `FormData` 追加 `pipelineId` / `pipelineRunId` / `jobId`，来源为 `ATOMGIT_WORKFLOW_ID` / `ATOMGIT_RUN_ID` / `ATOMGIT_JOB_RUN_ID`（三者缺失即在 Step 0 抛错）。
3. 逐个 XML 文件 `fs.existsSync` 判存（缺失则 warning 跳过）→ `readFileSync` → 以 `filename` + `application/xml` 追加为 `files`。
4. `form.getBuffer()` 取 body，`form.getHeaders()["content-type"]` 取 boundary 头。
5. `callApig("POST", APIG_UPLOAD_URL, headers, body)`，`res.status` 落 2xx 判定成功，返回 `{ok, status, message}`。

### Step 13.6 — OBS 上传

1. **前缀决策**：`safeObsPrefix || \`pytest-orch/${pipelineRunId}/${jobRunId}/archive-log/\``。`ObsPrefix`缺失或校验失败时回退到**运行标识派生前缀**，不回退 manifest 原始值，也不允许`undefined` 参与对象键拼接。
2. **脱敏**：`scrubSecretsInDir(dir, secrets)` — `collectFilesSync` 递归收集 → 仅处理 `isFile()`、`size ≤ 10MB`、不含 `NUL` 字节的文本文件 → 对每个密钥明文 `split(secret).join("***")` 全量替换 → 仅在 `changed` 时回写。单文件失败 warning，目录遍历失败上抛 → 跳过上传。
3. **换证建客户端**：`const { region } = configure(oidcConfig)` → `await getCredentials()` → `new ObsClient({ access_key_id, secret_access_key, security_token, server: \`https://obs.${region}.myhuaweicloud.com\` })`。
4. **逐文件上传**：`objectKey = prefix + path.relative(folderPath, filePath).split(path.sep).join("/")` → `await client.putObject({ Bucket, Key, SourceFile })` → 依 `resp.CommonMsg.Status` 判定，失败携带 `CommonMsg.Code` / `Message` 立即返回。
5. **释放**：`finally { await client.close() }`。

### 错误呈现

新增 `formatStepError(value, fallback)`，兼容 `Error` / `{message|error|reason}` / 字符串 / 普通对象（`JSON.stringify` 失败降级 `String(value)`），保证记录日志这一动作本身永不抛异常。

## 类设计

插件为 CommonJS 函数式实现，**不引入自定义类与继承体系**，本次变更为「模块拆分 + 函数新增」，对外部类仅做实例化使用。

| 单元                            | 位置                            | 职责                                                                 |
| ------------------------------- | ------------------------------- | -------------------------------------------------------------------- |
| `validators` 模块               | `validators.js`（新增，751 行） | 纯输入校验与路径限定，仅依赖 `path` / `fs`，无副作用，导出 19 个函数 |
| `uploadXmlFilesViaApig`         | `index.js`                      | APIG multipart 上传编排                                              |
| `uploadArchiveLogDirToObs`      | `index.js`                      | OIDC 临时凭证批量上传编排                                            |
| `collectSecretValues`           | `index.js`                      | 收集待脱敏密钥明文（去重 + 长度降序，长值优先替换避免子串残留）      |
| `scrubSecretsInDir`             | `index.js`                      | 目录内文本日志就地脱敏                                               |
| `collectFilesSync`              | `index.js`                      | 递归收集文件路径（脱敏与上传共用）                                   |
| `formatStepError`               | `index.js`                      | 统一错误可读化                                                       |
| `assertSafePath` / `safeRemove` | `index.js`                      | 沿用原有 `/tmp/pytest-orch` 前缀约束，未改动语义                     |

外部类使用：`ObsClient`（`esdk-obs-nodejs`，实例化 → `putObject` → `close`，`finally` 保证释放）、`FormData`（`form-data`）。移除的外部契约依赖：下发给执行器的 `obsInfo.ak` / `obsInfo.sk`。

## 数据模型设计

无数据库与持久化 schema 变更，涉及五份数据契约。

### 1）下发执行器的 OBS 信息（字段缩减）

```js
obsInfo = JSON.stringify({ bucket_name, server, base_url }); // 移除 ak / sk
```

### 2）`scheduler-secret` 白名单

`["apig_code", "apig_key", "apig_secret", "x-hw-appid", "x-hw-signkey", "auth_token", "k8s_auth"]`
→ `["auth_token", "k8s_auth"]`；`≤10KB`、嵌套 `≤10` 层约束沿用 `validateJsonParam`。

### 3）`oidc-config` 输入模型（`OIDC_CONFIG_ALLOWED_FIELDS`）

| 字段                                                                    | 类型    | 校验                         |
| ----------------------------------------------------------------------- | ------- | ---------------------------- |
| `accountId` / `audience` / `agencyName` / `oidcProviderName` / `region` | string  | 出现时 `typeof === "string"` |
| `durationSeconds` / `refreshBufferSeconds`                              | number  | 出现时必须 `Number.isFinite` |
| `debug`                                                                 | boolean | 出现时严格布尔               |

语义：仅回填显式提供且非 `null` / `undefined` 的字段，未提供字段**绝不进入** `configure()`，从而保留 SDK 内置默认；空输入返回 `{}`；未知字段由 `validateJsonParam` 直接抛错。

### 4）`output.json` manifest 模型（`validateOutputManifest`）

字段白名单 6 项，超出白名单的键静默丢弃，类型非法整体抛错。

| 字段                                             | 类型     | 约束                                                            |
| ------------------------------------------------ | -------- | --------------------------------------------------------------- |
| `TestCaseOBSUrl` / `TestCaseFile` / `EnvLogFile` | string   | `≤4096` 字符                                                    |
| `XmlFiles`                                       | string[] | `≤200` 项；每项非空、`≤1024` 字符、禁 `\0` 与 `..`；逐项 `trim` |
| `ArchiveLogDir`                                  | string   | `≤4096`；禁 `\0` 与 `..`；`trim`                                |
| `ObsPrefix`                                      | string   | 见下                                                            |

顶层必须是 JSON 对象（数组 / 标量直接拒绝）。

### 5）OBS 对象键前缀模型（`validateObsPrefix`）

`≤512` 字符；字符集 `[A-Za-z0-9._\-/]`；禁止以 `/` 开头（必须相对）；按段检查禁止空段、`.`、`..`（段检查前剔除结尾斜杠，`a/b/` 合法）；返回值强制以 `/` 结尾。

最终对象键为 `{prefix}{relativePath}`，分隔符统一为 `/`，写入语义为**覆盖写**（无版本保护）。

## 性能设计

本次改造以「最小开销换取凭证安全」为取向，无专项性能优化，但内建多条上限与短路保护：

- **内存**：APIG 路径对每个 XML `readFileSync` 全量入内存并 `getBuffer()` 一次性序列化，依赖 manifest 侧 `XmlFiles ≤ 200 项 / 每项路径 ≤1024 字符` 约束总量；OBS 路径改用 `putObject({ SourceFile })` 交由 SDK 走文件路径上传，避免整目录读入内存。
- **I/O**：`scrubSecretsInDir` 以「`size > 10MB` 跳过」和「含 `NUL` 字节视为二进制跳过」两条规则短路，避免对大文件与二进制做无意义字符串化；仅在确实发生替换时回写文件。
- **网络**：逐文件串行 `await putObject`，无并发池与重试；首个文件失败即短路返回，不做无谓续传。
- **凭证**：`configure()` 为进程内单例，一次运行内 `getCredentials()` 仅调用一次；STS 有效期与提前刷新窗口通过 `durationSeconds` / `refreshBufferSeconds` 可配。
- **日志**：`silent: true` 配 `listeners` 原样转发，保证脱敏收益不牺牲执行器输出可见性。

## API 接口设计

### 1）Action 输入契约（破坏性变更）

| 输入                                              | 变更                    | 说明                                                |
| ------------------------------------------------- | ----------------------- | --------------------------------------------------- |
| `obs-ak` / `obs-sk`                               | **删除**（原 required） | 由 OIDC 临时凭证取代                                |
| `scheduler-secret`                                | 语义收紧                | required 不变，允许字段仅 `auth_token` / `k8s_auth` |
| `oidc-config`                                     | **新增**（optional）    | JSON 字符串，字段见数据模型第 3 项                  |
| `obs-bucket-name` / `obs-server` / `obs-base-url` | 保留                    | OBS 上传端点改由 `region` 推导；三者仍透传给执行器  |

输出契约（`pipeline-id` / `job-run-id` / `testcase-obs-url` / `testcase-file` / `env-log-file`）不变。

### 2）`validators.js` 新增导出签名

```js
validateOidcConfig(jsonStr: string): object             // 空输入 → {}
validateOutputManifest(rawManifest: object): object     // 结构/类型非法 → throw
confinePathToRoots(candidate: string, allowedRoots: string[], label: string): string
validateObsPrefix(prefix: string): string               // 归一化为以 "/" 结尾
```

### 3）`index.js` 新增内部函数签名（非对外 API）

```js
uploadXmlFilesViaApig(xmlFiles, pipelineId, pipelineRunId, jobId)
  → Promise<{ok: boolean, status?: number, message?: string}>
uploadArchiveLogDirToObs(folderPath, prefix, bucketName, oidcConfig)
  → Promise<{ok: boolean, uploaded?: number, message?: string}>
collectSecretValues(rawSecret: string, parsedSecret: object) → string[]
scrubSecretsInDir(dir: string, secretValues: string[]) → void
collectFilesSync(dir: string, results: string[]) → void
formatStepError(value, fallback = "unknown error") → string
```

### 4）对外部系统的调用接口

- **APIG**：`POST https://apig.openlibing.com/openlibing-sync/sync/testcase/metadata/upload-iam`，`multipart/form-data`，字段 `pipelineId` / `pipelineRunId` / `jobId` / `files`（可多个，`application/xml`）；鉴权由 `callApig` 内部注入（V11 签名 + `X-Security-Token`）；成功判定 `2xx`。
- **OBS**：`ObsClient.putObject({ Bucket, Key, SourceFile })`，端点 `https://obs.{region}.myhuaweicloud.com`；成功判定 `resp.CommonMsg.Status ∈ [200, 300)`。

## 安全设计

### FIND-01 凭证最小化与日志泄漏

- 长期 AK/SK 从「输入、`obsInfo`、manifest」三处彻底移出，运行时仅存分钟级 STS 临时凭证。
- `scheduler-secret` 原串及解析后 `≥8` 字符的字符串型字段值全部 `core.setSecret()` 注册为掩码，`@actions/core` 在**所有**日志输出中替换为 `***`。
- `exec.exec` 增加 `silent: true`，阻断对含 `--scheduler_secret` 命令行参数的自动回显；`listeners` 原样转发 stdout / stderr 保证输出不丢失；`env` 中并行提供 `SCHEDULER_SECRET` 作为双通道，待执行器 `main.py` 支持环境变量读取后即可移除 argv 传参（跨仓跟进）。
- 上传 OBS 前对目录内文本日志就地脱敏，防止 scheduler 密钥随日志持久化到对象存储并被长期留存。

### FIND-02 混淆代理（confused deputy）

- `output.json` 按不受信输入处理：白名单 + 类型 + 数量 / 长度上限，非法整体拒绝。
- `confinePathToRoots` 两段式限定：`path.resolve` 归一化后做可信根前缀比较，再对已存在路径 `fs.realpathSync` 复检，同时拦截**目录遍历**与**中间目录软链逃逸**；可信根仅限 `baseDir`、`testCaseDir` 与显式配置的 `archive-log-dir`。
- 文件类型限制：仅 `.xml` 后缀进入上传集合。
- 对象键前缀限制：`validateObsPrefix` 拒绝绝对路径、空段、`.`、`..`，字符集白名单化；前缀非法时回退运行标识派生前缀，**绝不回退原始不受信值**。
- 越界 / 解析失败一律 `core.warning` + 跳过该项，不放大为整条流水线失败。

### 失败语义

上传环节 `try / catch / finally` 三层包裹，非关键失败降级告警，不影响退出码；`ObsClient` 由 `finally` 保证关闭；脱敏阶段目录级异常上抛并跳过上传（fail-closed）。

### 供应链

新增 3 个 npm 依赖并重新打包 `dist/index.js` + `dist/licenses.txt`，需纳入 SCA 扫描基线。

## 风险 & 缓解

| 风险                                            | 缓解                                                                                      |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 消费方 workflow 未授予 OIDC 令牌权限 → 换证失败 | 上传环节非关键，失败仅 warning，主流程不受影响；需在 README 明示权限要求（见遗留项）      |
| APIG `upload-iam` 端点未配 IAM 认证 → 4xx       | 端点独立于原 appcode 路径（`-iam` 后缀），由服务端灰度；失败信息携带 HTTP status 与响应体 |
| `configure()` 单例被两次调用互相覆盖            | 当前顺序 13.5（无参默认）→ 13.6（带 `oidcConfig`）互不影响；顺序若变动需重评              |
| XML 全量入内存导致大结果集内存压力              | `XmlFiles ≤ 200 项` 上限；超限项在 manifest 校验阶段即被拒绝                              |
| 脱敏误改非日志文本文件                          | 限定在已通过路径校验的 `ArchiveLogDir` 内，跳过二进制与 `>10MB` 文件，仅替换已知密钥明文  |
| OBS 覆盖写导致历史归档被同名覆盖                | 前缀含 `pipelineRunId` / `jobRunId` 派生段，天然按运行隔离                                |

## 跨仓影响

- **`openlibing/openlibing-pytest-executor`**：执行器产出的 `output.json` 新增被消费的 `XmlFiles` / `ArchiveLogDir` / `ObsPrefix` 字段；`obsInfo` 不再含 `ak` / `sk`，执行器侧任何依赖该二字段的逻辑需同步下线。`main.py` 支持从 `SCHEDULER_SECRET` 环境变量读取后，可移除 argv 传参通道。
- **`openlibing/huaweicloud-oidc-sdk-nodejs`**：新增为运行时依赖，`configure()` 字段契约与 SDK 内置默认值强绑定，SDK 字段改名或语义变更需同步 `OIDC_CONFIG_ALLOWED_FIELDS`。
- **平台侧**：APIG 需提供 `upload-iam`（IAM 认证）接口；华为云 IAM 侧需注册 GitCode Actions 的 OIDC 提供商与委托（本插件运行在 GitCode Actions，使用 SDK 默认 `oidcProviderName`）。
- **接口契约**：Action 输入为破坏性变更（删 2 增 1 + 收紧 1），消费方 workflow 必须删除 `obs-ak` / `obs-sk`。

## 遗留项 / 后续跟进

以下问题在本次 commit 中**未处理**，建议单独提 issue 跟进：

1. `pytest-orch/README.md` 输入表仍保留 `obs-ak` / `obs-sk` 行，且 `scheduler-secret` 说明仍列旧白名单 7 字段（第 21–23 行），与 `action.yml` 现状不一致；缺少 OIDC 所需的 workflow 权限说明。
2. `workflow-example/Case-run-test.yml` 仍传 `obs-ak` / `obs-sk`（第 35–36 行），示例已失效。
3. APIG 上传地址硬编码于 `uploadXmlFilesViaApig` 内，无法按环境切换，建议提升为输入或集中常量。
4. 读取 `output.json` 的分组名由 `Step 13` 改为 `Step 11`，与既有 `Step 11: Install dependencies` 重名，且与后续 `Step 13.5 / 13.6` 序号不连贯（仅日志可读性问题）。
5. 新增 751 行 `validators.js` 未附带单元测试（`package.json` 无 `test` script），安全边界逻辑缺少回归保护。
6. OBS 上传为串行无重试，大目录归档耗时与瞬时网络抖动下的成功率有优化空间。
