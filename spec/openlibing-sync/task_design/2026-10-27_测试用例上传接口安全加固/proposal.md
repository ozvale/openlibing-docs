# 测试用例上传接口安全加固

## 需求背景

`testcase/metadata/upload` 接口在「蓝区性能数据上传归档」需求中引入了 `label` + `archivePath` 自定义归档路径能力。该能力将**客户端完全可控**的字符串直接拼接为 OBS 对象键（objectKey），且未对上传文件的类型、大小做业务级约束，存在以下安全与稳定性问题：

1. **label / archivePath 对象键注入**：`archivePath` 中的 `..` 等相对路径片段未做过滤，攻击者可构造出 `label/../../<他人pipelineId>/...` 形式的对象键，越权写入其他流水线的归档前缀。由于插件侧 `TestCaseMetadataParser` 按 `testcase-metadata/{pipelineId}/{pipelineRunId}/{pipelineJobId}/` 前缀扫描并解析 XML，污染该前缀即可向他人流水线的元数据注入内容。
2. **文件类型不受约束**：接口语义为「测试用例元数据上传」，但当前接受任意文件类型。可执行文件、脚本、网页类型文件均能落入 OBS 桶。
3. **单文件大小无业务级约束**：仅依赖 Spring multipart 容器级限制，缺少可返回明确业务错误码的二次校验。
4. **临时文件泄漏**：`File.createTempFile` 成功后若 `transferTo` 抛异常，临时文件不会被删除，长期累积导致磁盘耗尽。
5. **同名文件统计错乱**：`fileNameToObjectKeyMap` 以未净化的原始文件名作为 key，净化后重名的多个文件（如 `a/b.xml` 与 `a_b.xml`）会互相覆盖，导致成功/失败清单统计错误。

## 需求价值

1. **消除对象键注入风险**：通过 label 白名单 + archivePath 分段字符集与深度约束，杜绝越权写入他人归档前缀。
2. **限制危险文件类型**：以黑名单方式拦截可执行、脚本、网页类文件，其余常用类型放行，不影响既有业务上传。
3. **提升可观测性与可操作性**：为路径参数非法、文件类型非法、文件超限提供独立业务错误码，调用方可据此给出可操作的提示。
4. **消除资源泄漏**：修复临时文件泄漏与同名文件统计错乱两个既有缺陷。

## 功能描述

### 功能点 1：label 白名单校验

**目标**：`label` 只接受业务枚举内的取值，杜绝通过 label 写入任意归档前缀。

**白名单取值**（硬编码常量，配置中心可覆盖）：

| label                 | 业务含义     |
| --------------------- | ------------ |
| `precision`           | 精准测试     |
| `performance`         | 性能测试     |
| `simulation`          | 仿真测试     |
| `presmoke`            | 预冒烟       |
| `workflow-acceptance` | 工作流验收   |
| `test_label`          | 接口调试使用 |

**保留前缀**：`testcase-metadata` 是流水线归档路径的固定前缀（`testcase-metadata/{pipelineId}/{pipelineRunId}/{jobId}/`），插件侧按该前缀扫描并解析 XML，因此**不纳入 label 白名单**。label 为空时服务自动落到该前缀，无需通过 label 显式指定。

> 若配置中心误将 `testcase-metadata` 加入白名单，攻击者可用 `label=testcase-metadata` + 任意 `archivePath` 重建他人流水线的归档前缀。配置中心下发前需校验不含保留前缀。

**关键行为**：

- label 为空时走既有流水线归档路径（`testcase-metadata/{pipelineId}/{pipelineRunId}/{jobId}/{filename}`），**行为不变**
- label 非空时必须在白名单内，否则返回 `INVALID_LABEL` 错误码
- 白名单支持通过配置中心（Nacos）动态覆盖，新增业务标签无需改代码发版
- 配置中心未配置时使用代码内置默认值，保证本地与配置中心异常场景下功能可用

### 功能点 2：archivePath 分段校验

**目标**：archivePath 的每一段必须是安全的单段路径名，杜绝 `..` 相对路径片段。

**校验规则**：

- 段字符集：仅允许字母、数字、下划线、连字符、点（`[A-Za-z0-9._-]`）
- 段首字符：不允许为 `.`（排除 `.`、`..`、隐藏文件形态）
- 段长度：不超过 128 字符
- 路径深度：最多 8 层（预留 buffer）
- 段数不足 1 或存在空段（如 `a//b`）时拒绝

**关键行为**：

- 校验前先去除首尾斜杠，与既有 `StringUtils.strip(value, "/")` 行为保持一致
- archivePath 仍必须与 label 同时传入，既有约束不变
- 校验不通过返回 `INVALID_ARCHIVE_PATH` 错误码

### 功能点 3：文件类型黑名单

**目标**：拦截服务端可直接执行的文件类型，其余常用类型（`.xml`、`.json`、`.txt`、`.log`、`.html`、`.js`、`.zip`、`.tar`、`.gz` 等）一律放行。

**禁止的扩展名**（仅 7 个）：

| 类别         | 扩展名                            | 风险                                                                   |
| ------------ | --------------------------------- | ---------------------------------------------------------------------- |
| 服务端脚本   | `.jsp`、`.jspx`、`.php`、`.phtml` | 桶被误挂载为某应用的 WebRoot 时，文件可被服务端直接执行                |
| 跨平台可执行 | `.exe`、`.dll`、`.so`             | 二进制可执行文件，在桶被错误暴露或被下游解压执行的场景下可造成代码执行 |

**黑名单收敛依据**：

本接口的风险成立条件需要「OBS 桶被挂载为 WebRoot / 开启静态网站托管 / 归档文件被 CI 解压执行」等前提，当前 OBS 桶仅作为私有存储使用，**这些前提均不成立**。因此只保留唯一一类在误配置场景下能造成**服务端代码执行**的扩展名，其余类型不做限制：

| 曾列入黑名单但本次放行的类型           | 放行理由                                                                |
| -------------------------------------- | ----------------------------------------------------------------------- |
| `.sh`、`.bat`、`.cmd`、`.ps1`          | 脚本文件没有自动执行路径，仅作为归档内容存储无危害                      |
| `.jar`、`.war`、`.ear`、`.apk`、`.ipa` | 本身是压缩包，不是可执行文件                                            |
| `.js`、`.mjs`、`.svg`、`.swf`、`.html` | 桶未开启静态网站托管，不构成 XSS 载体；且是前端项目构建产物的常见组成   |
| `.asp`、`.aspx`、`.ashx`               | 与 `.jsp`/`.php` 同类，但本仓为 Java 技术栈，命中概率极低，不再单独列举 |

**关键行为**：

- 基于**净化后**的文件名判断扩展名，保证判定对象与实际落盘的文件名一致
- 不做文件内容嗅探（magic number 校验），仅按扩展名黑名单判断；双扩展名绕过（如 `a.exe.gz`）为已登记的残留风险，见 design.md 风险表
- 命中黑名单时该文件计入失败清单，不中断整批上传

### 功能点 4：单文件大小业务级校验

**目标**：在业务层提供可返回明确错误码的单文件大小限制。

- 业务级单文件上限：**16MB**
- 容器级 `max-file-size` 必须**严格大于**业务级上限（建议 24MB），使业务级校验先于容器层触发、`FILE_SIZE_EXCEED_LIMIT` 在真实链路上可达；否则容器会先拒绝请求，业务错误码永远不会被返回
- 容器级 `max-request-size`（整请求总量）的调整由用户在 Nacos 配置中心自行完成，不在本次代码改动范围内
- 超限文件计入失败清单，不中断整批上传

### 功能点 5：临时文件泄漏修复

**目标**：确保任何路径下创建的临时文件都被清理，且转换失败的文件在结果中可见。

- 将 `File.createTempFile` 与 `multipartFile.transferTo` 包裹在 try-finally 中
- finally 分支删除临时文件；已加入 `uploadInfoList` 的文件由既有的 `buildUploadResult` 清理逻辑兜底（避免重复删除）
- `transferTo` 抛 `IOException` 时，除记录日志外，还需把该文件加入失败清单（携带失败原因），保证失败文件不出现在成功列表、也不被静默丢弃

### 功能点 6：同名文件统计错乱修复

**目标**：净化后重名的文件不会互相覆盖统计条目。

- 废弃 `Map<String, String> fileNameToObjectKeyMap`，改为 `List<UploadEntry>`：每条独立持有 `displayName`（原始文件名）与 `objectKey`
- `buildUploadResult` 改为遍历列表逐条判定，不再依赖 map 的 key 唯一性；`a/b.xml` 与 `a_b.xml` 各自产生独立条目

## 验收标准

- [ ] label 非白名单取值时返回 `INVALID_LABEL`，且不产生任何 OBS 写入
- [ ] label 为空时行为与现有完全一致（流水线归档路径不变）
- [ ] label 白名单可通过配置中心动态覆盖，配置变更后无需重启即生效
- [ ] 配置中心缺失该配置时回退到内置默认白名单
- [ ] archivePath 含 `..` 段时返回 `INVALID_ARCHIVE_PATH`
- [ ] archivePath 超过 8 层时返回 `INVALID_ARCHIVE_PATH`
- [ ] archivePath 段长度超过 128 字符时返回 `INVALID_ARCHIVE_PATH`
- [ ] archivePath 含空段（`a//b`）时返回 `INVALID_ARCHIVE_PATH`
- [ ] 合法 archivePath（如 `team-x/2026-Q2/sprint-3`）正常通过并按原结构归档
- [ ] 上传黑名单扩展名文件（`.jsp` / `.jspx` / `.php` / `.phtml` / `.exe` / `.dll` / `.so`）时，该文件出现在失败清单
- [ ] 上传 `.sh` / `.bat` / `.cmd` / `.ps1` 文件时正常上传成功（按设计放行）
- [ ] 上传 `.xml` / `.json` / `.txt` / `.zip` / `.tar.gz` 等常用类型文件时正常上传成功
- [ ] 单文件超过 16MB 时，该文件出现在失败清单
- [ ] `transferTo` 抛异常时不残留临时文件
- [ ] 净化后同名的多个文件（如 `a/b.xml` 与 `a_b.xml`）在返回结果中各自有独立条目
- [ ] 现有 `TestCaseDataServiceImplTest` 全部用例仍然通过

## 影响范围

| 仓库            | 模块                                                        | 变更类型                                               |
| --------------- | ----------------------------------------------------------- | ------------------------------------------------------ |
| openlibing-sync | `SyncConstant.java`                                         | 修改：新增 label 白名单、大小上限、路径深度等常量      |
| openlibing-sync | `ResponseCodeEnum.java`                                     | 修改：新增路径参数非法、文件类型非法、文件超限错误码   |
| openlibing-sync | `infrastructure/config/UploadSecurityConfig.java`           | 新增：从配置中心读取 label 白名单，支持 Nacos 动态刷新 |
| openlibing-sync | `infrastructure/util/UploadSecurityValidator.java`          | 新增：label / archivePath / 扩展名 / 文件大小校验逻辑  |
| openlibing-sync | `api/controller/TestCaseDataController.java`                | 修改：接入路径参数与文件类型校验                       |
| openlibing-sync | `domain/service/testcase/impl/TestCaseDataServiceImpl.java` | 修改：单文件大小校验、临时文件清理、同名统计修复       |
| openlibing-sync | `src/test/.../TestCaseDataServiceImplTest.java`             | 修改：补充安全校验相关测试                             |

## 不在本次范围

- Spring multipart 容器级 `max-file-size` / `max-request-size` 的数值调整（由用户在 Nacos 配置中心自行完成）
- 上传接口的鉴权与限流加固
- OBS 桶侧的静态网站托管配置与访问权限策略
- OBS 桶的生命周期与存储配额治理
