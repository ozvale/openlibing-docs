# pytest-orch OIDC 化 APIG / OBS 上传 — 任务清单

> 逆向归档：T-01 ~ T-08 为 commit `53998707e23041a1b071e931c818d56261fb3ea6` 已落地的内容；
> T-09 / T-10 为该 commit **未处理**、需后续跟进的事项（保持 PENDING）。

## 任务总览

| 任务编号 | 任务描述                                                      | 状态    | 备注                         |
| -------- | ------------------------------------------------------------- | ------- | ---------------------------- |
| T-01     | 引入 OIDC / OBS / form-data 依赖并重新打包 dist               | DONE    | 含 licenses.txt 同步         |
| T-02     | `action.yml` 输入契约调整（删 obs-ak/obs-sk，增 oidc-config） | DONE    | 破坏性变更                   |
| T-03     | 抽取 `validators.js` 模块并新增 4 个 OIDC / manifest 校验     | DONE    | 19 个导出                    |
| T-04     | scheduler-secret 白名单收敛 + setSecret 掩码 + 脱敏值收集     | DONE    | FIND-01                      |
| T-05     | `exec.exec` 关闭回显 + listeners 转发 + env 双通道            | DONE    | FIND-01                      |
| T-06     | `output.json` manifest 白名单校验与可信根路径限定             | DONE    | FIND-02                      |
| T-07     | Step 13.5 XML 结果经 `callApig` 上传 APIG                     | DONE    | multipart                    |
| T-08     | Step 13.6 归档日志经临时凭证上传 OBS（含上传前脱敏）          | DONE    | fail-closed                  |
| T-09     | 为 `validators.js` 补充单元测试                               | PENDING | 751 行安全边界逻辑无回归保护 |
| T-10     | README 与 workflow-example 同步新契约                         | PENDING | 仍残留 obs-ak / obs-sk       |

## 任务详情

### T-01: 依赖引入与打包

**文件**: `pytest-orch/package.json`、`pytest-orch/package-lock.json`、`pytest-orch/dist/index.js`、`pytest-orch/dist/licenses.txt`

**实现内容**:

- 新增 `@openlibing/huaweicloud-oidc-client@^0.0.5`（`configure` / `getCredentials` / `callApig`）
- 新增 `esdk-obs-nodejs@3.26.2`，并将 `form-data@^4.0.0` 提升为直接依赖
- `esdk-obs-nodejs` 按精确版本锁定（非 `^` 区间）
- `ncc build` 重新打包内联新依赖，同步第三方 LICENSE 清单

**完成标准**:

- [x] 三项依赖进入 `dependencies`
- [x] lock 文件版本一致
- [x] `dist/index.js` 重新构建并随源码一并提交

### T-02: Action 输入契约调整

**文件**: `pytest-orch/action.yml`

**实现内容**:

- 删除 `obs-ak` / `obs-sk` 两个 required 输入
- 新增可选 `oidc-config`，`description` 中列明允许字段与「未指定字段使用 SDK 内置默认」语义
- 同步 `pytest-orch/README.md` 的 `oidc-config` 行

**完成标准**:

- [x] `obs-ak` / `obs-sk` 从 inputs 中移除
- [x] `oidc-config` 声明为 optional
- [ ] README 输入表其他行同步（见 T-10）

### T-03: 校验逻辑模块化

**文件**: `pytest-orch/validators.js`（新增 751 行）、`pytest-orch/index.js`

**实现内容**:

- 将 index.js 中 15 个既有校验函数迁出为独立模块
- 新增 4 个函数：`validateOidcConfig`、`validateOutputManifest`、`confinePathToRoots`、`validateObsPrefix`
- 模块保持纯净：仅依赖 `path` / `fs`，无副作用
- index.js 统一 `const validators = require("./validators")` 并保留薄封装（`validateGitUsername = validators.validateGitUsername` 等）

**完成标准**:

- [x] 19 个函数导出可用
- [x] index.js 内不再有重复校验实现
- [x] `validateOidcConfig` 仅回填显式字段，空输入返回 `{}`
- [x] `confinePathToRoots` 同时做 resolve 归一化前缀比较与 `realpathSync` 软链复检
- [x] `validateObsPrefix` 拒绝绝对路径 / 空段 / `.` / `..`，返回值强制以 `/` 结尾

### T-04: 密钥掩码与脱敏值收集

**文件**: `pytest-orch/index.js`（Step 0）

**实现内容**:

- `core.setSecret(schedulerSecretRaw)` 注册原始串掩码
- 解析成功后对长度 `≥8` 的字符串型字段值逐个 `core.setSecret`
- `collectSecretValues(raw, parsed)` 去重并按长度降序排列，供上传前脱敏使用

**完成标准**:

- [x] 白名单收敛为 `["auth_token", "k8s_auth"]`
- [x] 长值优先替换，避免子串残留
- [x] 掩码注册失败不影响主流程

### T-05: 子进程日志防泄漏

**文件**: `pytest-orch/index.js`（Step 12）

**实现内容**:

- `exec.exec(venvPython, args, { silent: true, env, listeners })`
- `env` 注入 `SCHEDULER_SECRET`，与 `--scheduler_secret` argv 形成双通道过渡（执行器支持 env 后可移除 argv）
- `listeners` 将 stdout / stderr 原样 `process.stdout/stderr.write` 转发

**完成标准**:

- [x] 不再自动回显含密钥的完整命令行
- [x] 执行器输出保持完整可见
- [ ] argv 传参通道下线（依赖执行器侧改造，跨仓跟进）

### T-06: manifest 校验与路径限定

**文件**: `pytest-orch/index.js`（Step 11）

**实现内容**:

- `validateOutputManifest(JSON.parse(...))` 整体结构校验
- 可信根集合 `[baseDir, testCaseDir, path.resolve(archiveLogDir)（仅 manifest 提供时）]`
- `XmlFiles[]` 逐条 `confinePathToRoots` + `.xml` 后缀检查
- `ArchiveLogDir` 走 `confinePathToRoots`；`ObsPrefix` 走 `validateObsPrefix`
- 非法项 `core.warning` + 跳过；`safeObsPrefix` 缺失或非法时回退 `pytest-orch/{pipelineRunId}/{jobRunId}/archive-log/`

**完成标准**:

- [x] 目录遍历与软链逃逸样本被拒绝
- [x] 非 `.xml` 文件不进入上传集合
- [x] 前缀不回退到不受信原始值，`undefined` 不参与对象键拼接
- [x] 单项失败不中断流水线

### T-07: APIG 上传（Step 13.5）

**文件**: `pytest-orch/index.js` — `uploadXmlFilesViaApig`

**实现内容**:

- `configure()` 无参使用 SDK 内置默认端点
- `FormData` 追加 `pipelineId` / `pipelineRunId` / `jobId` 与多个 `files`
- 逐文件 `existsSync` 判存 → `readFileSync` → `filename` + `application/xml`
- `getBuffer()` 作为签名与发送共用的同一 body；`"Content-Type"` 首字母大写覆盖默认头
- `callApig("POST", .../metadata/upload-iam, headers, body)`，2xx 判定成功
- `try / catch / finally` 包裹，异常降级 `core.warning`

**完成标准**:

- [x] 端点与原 appcode 路径独立（`-iam` 后缀）
- [x] 缺失文件仅告警跳过
- [x] 失败信息携带 HTTP status 与响应体前缀
- [x] `startGroup` 在 `finally` 中必然 `endGroup`

### T-08: OBS 上传（Step 13.6）

**文件**: `pytest-orch/index.js` — `uploadArchiveLogDirToObs`、`scrubSecretsInDir`、`collectFilesSync`、`formatStepError`

**实现内容**:

- 上传前 `scrubSecretsInDir` 就地脱敏：`collectFilesSync` 递归收集 → 跳过非文件 / `>10MB` / 含 `NUL` 的二进制 → `split(secret).join("***")` → 仅在发生替换时回写
- `const { region } = configure(oidcConfig)` → `await getCredentials()` → `new ObsClient({access_key_id, secret_access_key, security_token, server})`
- `objectKey = prefix + path.relative(...).split(path.sep).join("/")` → `await putObject({Bucket, Key, SourceFile})`
- `resp.CommonMsg.Status` 判定，失败携带 `Code` / `Message` 立即返回
- `finally await client.close()`

**完成标准**:

- [x] 客户端使用 STS 三元组，无永久 AK/SK
- [x] 单文件失败不影响其余文件计数逻辑正确
- [x] 脱敏目录级异常上抛并跳过上传（fail-closed）
- [x] 客户端资源在 `finally` 中释放

### T-09: 单元测试补充（PENDING）

**范围**: `pytest-orch/validators.js`（751 行）与 `index.js` 新增函数

**建议用例**:

- [ ] `validateOidcConfig`：空输入 / 未知字段 / 类型错误 / 显式字段透传
- [ ] `validateOutputManifest`：数组与标量顶层、超 200 项、含 `..` 项、非字符串项
- [ ] `confinePathToRoots`：`../` 遍历、软链逃逸、大小写与尾斜杠、根目录本身
- [ ] `validateObsPrefix`：绝对路径、空段、`.` / `..`、`a/b/` 合法、512 长度上限
- [ ] `scrubSecretsInDir`：多密钥替换、二进制跳过、`>10MB` 跳过、替换失败仅告警
- [ ] `formatStepError`：`Error` / 对象 / 字符串 / `JSON.stringify` 抛异常对象

**前置**: `pytest-orch/package.json` 目前无 `test` script 与测试框架依赖，需先补齐。

### T-10: 文档与示例同步（PENDING）

**文件**: `pytest-orch/README.md`、`workflow-example/Case-run-test.yml`

**待办**:

- [ ] README 输入表删除 `obs-ak` / `obs-sk` 行（现仍在第 21-22 行）
- [ ] README `scheduler-secret` 说明改为仅 `auth_token` / `k8s_auth`（现仍列旧白名单，第 23 行）
- [ ] README 增补 OIDC 所需的 workflow 令牌权限配置说明与失败排查
- [ ] `workflow-example/Case-run-test.yml` 删除 `obs-ak` / `obs-sk`（第 35-36 行），并按需补 `oidc-config`
- [ ] 明确「AK/SK → OIDC」消费方迁移指引
