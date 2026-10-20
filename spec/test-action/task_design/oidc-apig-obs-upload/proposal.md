# pytest-orch OIDC 化 APIG / OBS 上传 — 需求提案

> 本文档为已合入变更的**逆向归档**：需求、设计与任务清单从 `openlibing/test-action`
> master commit `53998707e23041a1b071e931c818d56261fb3ea6`（`feat(pytest-orch): switch to OIDC for APIG and OBS uploads`，2026-09-02）
> 的实际 diff 与源码还原，不追加原变更未包含的范围。

## 1. 需求背景

`pytest-orch` 是 `test-action` 仓下的 GitCode Actions 插件（复合 action：内联 checkout action + 调用插件自身 `dist/index.js`），负责在用例仓内完成 pytest 套件执行与结果上报。整改前它依赖**两类长期静态凭证**：

- `obs-ak` / `obs-sk` 两个 required 输入，用于直连华为云 OBS 上传归档；
- `scheduler-secret` 中的 `apig_code` / `apig_key` / `apig_secret` 等字段，用于直连 APIG 上报用例元数据。

上述明文凭证存在三条稳定泄漏路径：CI 日志（`@actions/exec` 默认回显完整命令行，而 `--scheduler_secret` 作为 argv 传入）、下发给执行器的 `obsInfo` 结构，以及随执行器落盘、最终被上传到 OBS 长期留存的日志目录。同时永久 AK/SK 无有效期、无最小权限边界，轮换需改动所有消费方 workflow。

## 2. 需求目标

以 OIDC 联邦换来的**分钟级 STS 临时凭证**替代全部长期凭证，并把「结果上传」能力从执行器侧收敛到插件侧统一实现，在消除明文凭证的同时保证流水线不因上报失败而中断。

## 3. 功能需求

### 3.1 输入契约调整

| 输入                                              | 变更                | 说明                                                                                                                                                    |
| ------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `obs-ak` / `obs-sk`                               | 删除（原 required） | 由 OIDC 临时凭证取代                                                                                                                                    |
| `scheduler-secret`                                | 语义收紧            | required 不变，允许字段由 7 项收敛为 `auth_token` / `k8s_auth`                                                                                          |
| `oidc-config`                                     | 新增（optional）    | JSON 字符串；仅 `accountId` / `audience` / `agencyName` / `oidcProviderName` / `region` / `durationSeconds` / `refreshBufferSeconds` / `debug` 允许出现 |
| `obs-bucket-name` / `obs-server` / `obs-base-url` | 保留                | OBS 上传端点改由 `region` 推导，三者仍透传给执行器                                                                                                      |

### 3.2 上传能力

| 能力           | 触发来源                                       | 目标系统                                                   | 失败语义       |
| -------------- | ---------------------------------------------- | ---------------------------------------------------------- | -------------- |
| 用例元数据上报 | `output.json` 的 `XmlFiles[]`                  | APIG `POST .../metadata/upload-iam`（multipart/form-data） | 非关键，仅告警 |
| 归档日志上传   | `output.json` 的 `ArchiveLogDir` + `ObsPrefix` | 华为云 OBS `putObject`                                     | 非关键，仅告警 |

### 3.3 不受信输入校验

`output.json` 由测试执行侧代码间接产出，属不受信输入。凡用于本地文件读取或远端对象写入的字段，必须通过白名单、类型、数量 / 长度上限、路径可信根限定与前缀合法性校验。

### 3.4 凭证防泄漏

调度器密钥必须在日志中掩码、不得因命令行回显泄漏，且随归档上传到 OBS 前必须从日志文件中就地脱敏。

## 4. 验收标准

### 4.1 功能验收

1. 插件不再接受 `obs-ak` / `obs-sk`，未配置 `oidc-config` 时也能以 SDK 内置默认完成上传。
2. `XmlFiles` 中的每个 XML 以 multipart `files` 字段上报，携带 `pipelineId` / `pipelineRunId` / `jobId`，HTTP 2xx 视为成功。
3. `ArchiveLogDir` 目录下文件按相对路径拼接到 `ObsPrefix`（或运行标识派生前缀）下逐个上传成功。
4. `scheduler-secret` 仅接受 `auth_token` / `k8s_auth` 两字段，其余字段被拒绝。
5. 下发给执行器的 `obsInfo` 不再含 `ak` / `sk`。

### 4.2 安全验收

6. `scheduler-secret` 原串及其解析后的字段值不出现在流水线日志明文中（含 `main.py` 子进程输出）。
7. 上传到 OBS 的日志文件中，已知密钥明文被替换为 `***`。
8. 构造 `XmlFiles: ["../../etc/passwd"]`、`ArchiveLogDir: "/"`、`ObsPrefix: "/other-bucket-path/"` 等清单时，对应条目被拒绝或告警跳过，不发生任意路径读取 / 任意前缀写入。
9. `oidc-config` 传入未知字段或错误类型时立即报错，不透传给 SDK。

### 4.3 兼容性验收

10. 上传任一步骤失败不改变 Step 14 之后的输出与流水线退出码。
11. `exec` 关闭回显后，执行器 stdout / stderr 仍完整可见。

## 5. 非功能需求

| 需求类型 | 描述                                                                                                         |
| -------- | ------------------------------------------------------------------------------------------------------------ |
| 性能     | 上传为串行逐文件处理，需通过数量 / 体积上限（`XmlFiles ≤200`、脱敏跳过 `>10MB` 与二进制）约束内存与 I/O 开销 |
| 可维护性 | 输入校验逻辑独立成模块，与编排逻辑解耦，可单独复用                                                           |
| 可观测性 | 上传结果按步骤分组输出，成功项与失败项均可定位到具体文件                                                     |
| 供应链   | 新增第三方依赖需同步重新打包 `dist/` 与 `licenses.txt`，纳入 SCA 基线                                        |

## 6. 关联 Issue

原变更未关联业务 Issue（早于本工作流规范落地）。本次归档识别出的 6 条遗留项建议单独建 issue 跟踪，清单见 [design.md](./design.md) 的「遗留项 / 后续跟进」与 [tasks.md](./tasks.md) 的 T-09 / T-10。

## 7. 交付信息

| 项          | 内容                                                           |
| ----------- | -------------------------------------------------------------- |
| 仓库 / 分支 | `openlibing/test-action` @ master                              |
| Commit      | `53998707e23041a1b071e931c818d56261fb3ea6`                     |
| 变更规模    | 7 个文件，+1462 / -4286（其中 `dist/index.js` 为重新打包产物） |
| 交付日期    | 2026-09-02                                                     |
| 归档日期    | 2026-09-08                                                     |
