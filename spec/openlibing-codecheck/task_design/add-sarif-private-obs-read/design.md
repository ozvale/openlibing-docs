# add-sarif-private-obs-read 设计文档

## 1. 方案设计

### 1.1 总体方案

把 SARIF 读取从「匿名 HTTP 下载」切换为「平台凭证私有对象下载」，并在下载前叠加访问策略校验：

```
StaticAlarmEventConsumer
  └─ SarifParseServiceImpl.parse(scanRun)
       └─ parseSingleUrl(scanRun, obsUrl)
            ├─ downloadAndParse(scanRun, obsUrl)
            │    └─ ObsBucketService.downloadToTempFile(obsUrl, scanRun.repo)
            │         ├─ URL 解析：bucket = host 首段，objectKey = path
            │         ├─ 访问策略：协议/桶白名单/目录白名单/.sarif 后缀/归属仓库/路径穿越
            │         ├─ OBS getObject(bucket, objectKey)（平台 AK/SK）
            │         ├─ 大小上限：元数据预检 + 流式计数兜底
            │         └─ 写入临时文件返回 Path
            ├─ Jackson 从临时文件解析 SarifSchema210
            └─ finally 删除临时文件
```

参考实现：`openlibing-coderepo` 的 `ObsBucketServiceImpl.downloadToTempFile`（代码度量 / UT 覆盖率已私有化）。差异点：本仓增加仓库归属校验、`.sarif` 后缀校验、目录白名单正则化与 Nacos 可覆盖。

### 1.2 方案取舍

| 决策           | 选择                                                 | 原因                                                                                            |
| -------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 读取方式       | esdk-obs-java（`ObsUtil.createObsClient`）           | 与存量 Excel 导出、coderepo 参考实现一致，复用平台静态 AK/SK 解密链路                           |
| 白名单可配置   | `@Value` + 默认值 + `@RefreshScope`                  | 与 `RepoHostKeywordSettings` 等本仓既有配置风格一致，Nacos properties 可直接覆盖并热生效        |
| 目录白名单形式 | 逗号分隔正则，`Matcher.lookingAt()` 前缀匹配         | 动态 `{toolName}-results/` 无法用固定前缀枚举；`lookingAt()` 同时兼容字面前缀与 `^...` 正则写法 |
| 归属校验位置   | `ObsBucketServiceImpl` 内，随 URL 解析一次完成       | 访问策略集中在一处，避免与 `SarifParseServiceImpl` 重复解析 URL 导致口径分叉                    |
| 拒绝的异常类型 | 统一 `IOException`                                   | 复用 `parseAllUrls` 既有的按 URL 隔离逻辑，单个 URL 失败不影响同批其他 URL                      |
| 临时文件       | `Files.createTempFile("sarif-", ".sarif")`，用后删除 | 避免大文件整体读入内存，且不改变解析链路入参类型                                                |
| 存量数据       | 不迁移 ACL、不清理既有对象                           | 用户确认：存量公开文件由插件侧治理，后端只做读取适配                                            |

## 2. 实现逻辑设计

### 2.1 ObsBucketServiceImpl.downloadToTempFile(obsUrl, expectedRepo)

1. `new URL(obsUrl)`；非法 URL → `IOException("obsUrl 非法")`。
2. 协议仅允许 `http` / `https`，拒绝 `file://` 等。
3. `host` 为空拒绝；`bucketName = host` 首段（第一个 `.` 之前）。
4. `objectKey = url.getPath()` 去掉前导 `/`。
5. 访问策略校验（全部不通过即 `IOException`，不触达 OBS）：
   - key 非空、不以 `/` 开头、不含 `..`、不含 `\`、长度 ≤ 1024；
   - `bucketName` 命中桶白名单（忽略大小写）；
   - `objectKey` 命中目录白名单任一条正则（`lookingAt`）；
   - `objectKey` 以 `.sarif` 结尾（忽略大小写）；
   - 路径按 `/` 分段 ≥ 5 段，第二段为仓库名，必须与 `expectedRepo` 忽略大小写相等；`unknown-repo` 无归属信息，读取时直接拒绝。
6. `getObject(bucketName, objectKey)`，先看 `ObjectMetadata.contentLength` 是否超上限，超限直接拒绝不落盘。
7. 创建临时文件，`copyWithLimit` 流式写入并计数，实际流量超限立即中止。
8. 任何失败路径删除可能已创建的临时文件；成功返回 `Path`，调用方负责删除。

### 2.2 白名单配置解析

| 配置项                                     | 默认值                                               | 解析规则                                                                                          |
| ------------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `obs.action.buckets`                       | `openlibing-gitcode-action,openlibing-github-action` | 共享配置（`application` data-id），逗号分隔，trim + 转小写，空项忽略                              |
| `codecheck.alarm.obs.allowed-key-patterns` | `^[a-z0-9][a-z0-9._-]*-results/`                     | 逗号分隔正则，`Pattern.compile` 失败时告警并丢弃该条；花括号量词内的逗号（如 `a{2,3}`）不参与拆分 |
| `codecheck.alarm.obs.max-file-size-mb`     | `500`                                                | 正数，≤0 时使用默认上限                                                                           |

`@PostConstruct` 中解析并缓存；类上标注 `@RefreshScope`，Nacos 变更后重建 Bean 重新解析。配置全部无效或为空时回落到代码默认值，服务不因配置错误启动失败。默认值统一放在代码常量中，`@Value` 的默认部分留空，避免正则里可能出现的花括号被 Spring 占位符解析提前截断。

默认目录正则与插件实际生成规则对齐：插件 `buildToolPrefix` 对工具名做 `toLowerCase()` + 非 `[a-z0-9]` 转 `-` + 去首尾 `-`，**无长度截断**，因此默认正则只约束首字符与 `-results/` 结尾（字符集 `[a-z0-9._-]` 为插件实际字符集的超集，兼容兜底前缀 `code-arts-check-results` 与 `pre-commit-results`），不设长度上限。

### 2.3 SarifParseServiceImpl

- 注入 `ObsBucketService`，`downloadAndParse(scanRun, obsUrl)`：
  - 调 `obsBucketService.downloadToTempFile(obsUrl, scanRun.getRepo())`；
  - `Files.newInputStream(tempFile)` 交给 Jackson 解析，日志记录 `Files.size(tempFile)` 与 runs 数；
  - `finally` 删除临时文件；
  - Jackson 3 的解析异常为非受检异常，保留 `catch (RuntimeException)` 记录日志后原样抛出（与现状一致）。
- 删除：`HttpURLConnection` 下载、`CountingInputStream`、`validateObsUrl`、`isHostAllowed`、`obsHostWhitelist` 配置、连接/读取超时常量及相关 import。
- 其余链路（多 URL 分组、工具识别、指纹、消失清理、快照、推送）不变。

### 2.4 边界与失败语义

| 场景                                      | 行为                                                                        |
| ----------------------------------------- | --------------------------------------------------------------------------- |
| 上报 obsUrl 仓库段为 `unknown-repo`       | 接收阶段拒绝入库，返回「参数错误：obsUrl 中的仓库名为占位值 unknown-repo…」 |
| 单个 URL 不在白名单 / 归属不符 / 下载失败 | 记入 `ParseResult.errors`，其他 URL 继续                                    |
| 全部 URL 失败                             | scanRun 置 FAILED，错误信息聚合所有 URL 原因（现状不变）                    |
| 部分 URL 失败                             | scanRun 置 PARTIAL_SUCCESS（现状不变，本次不改消失清理语义）                |
| 临时文件删除失败                          | 仅告警日志，不影响解析结果                                                  |
| 配置文件单条正则非法                      | 丢弃该条并告警，其余条目继续生效                                            |
| 配置文件为空或全部非法                    | 回退默认值并告警                                                            |

消失清理（`StaticAlarmOperation.resolveDisappearedIssues`）按本次成功解析的 tool 与 language 过滤：整个工具下载失败时该工具不在清理范围内，告警不会被误判为消失；仅当同一工具有多个 URL、部分 URL 被拒时，被拒 URL 的告警存在被清理的可能。

存量兼容性首轮验证（生产只读核查 3842 条 scanRun / 4335 个 obsUrl）：`unknown-repo` 命中 0 条；路径仓库段与 `scanRun.repo` 不一致的仅 1 组共 1325 条（`CI_gitcode` ↔ `gitcode`），来自华为云 CodeHub/DevMind 旧流水线，其 host 在改造前的 host 白名单中已被拒绝，不经过本链路；其余 49 组一致。`*-results/` 前缀、≥5 段、`.sarif` 后缀的全量覆盖率仍由 Task 6.1 跟进。

## 3. 类设计

| 类                                                          | 变更                                                                                                                                                                |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `business/service/ObsBucketService`                         | 新增 `Path downloadToTempFile(String obsUrl, String expectedRepo) throws IOException`                                                                               |
| `business/service/impl/ObsBucketServiceImpl`                | 新增白名单配置字段、`@PostConstruct` 解析、`downloadToTempFile`、`copyWithLimit`、`deleteQuietly`、`extractBucket`、`isAllowedKey` 等私有方法；类加 `@RefreshScope` |
| `business/service/impl/alarm/SarifParseServiceImpl`         | `downloadAndParse` 改为临时文件 + 凭证读取；删除匿名 HTTP 下载与 host 白名单相关代码                                                                                |
| `business/service/impl/alarm/StaticAlarmReceiveServiceImpl` | `buildScanRunEntity` 增加 obsUrl 仓库段校验，拒绝 `unknown-repo` 入库                                                                                               |
| `business/service/impl/ObsBucketServiceImplTest`            | 新增访问策略与大小上限用例                                                                                                                                          |
| `business/service/impl/alarm/SarifParseServiceImplTest`     | 下载源改为 mock `ObsBucketService`，新增单 URL 失败隔离用例                                                                                                         |

## 4. 数据模型设计

无 schema 变更、无 liquibase changeSet。`StaticAlarmScanRunEntity.obsUrl` 字段语义不变，仍为插件上报的 OBS 访问 URL 列表。

配置项（Nacos `OPENLIBING` / 对应 namespace）：

```properties
# application data-id：共享的 Action 上报桶位置，后续其他服务接入同类扫描结果时复用
obs.action.buckets=openlibing-gitcode-action,openlibing-github-action
# codecheck data-id：本服务读取侧的目录白名单与单文件大小上限
codecheck.alarm.obs.allowed-key-patterns=^[a-z0-9][a-z0-9._-]*-results/
codecheck.alarm.obs.max-file-size-mb=500
```

## 5. 性能设计

- 下载为流式写临时文件，内存占用与文件大小无关；单文件上限 500MB。
- 访问策略校验均为字符串/正则匹配，单次开销可忽略；正则列表在 `@PostConstruct` 预编译，不在每次调用时重复编译。
- OBS 客户端沿用既有懒加载单例，不额外创建连接。
- 与现状相比仅多一次本地临时文件写盘；解析从临时文件流读取，避免原有匿名 HTTP 连接的不稳定性。

## 6. API接口设计

无对外 HTTP 接口变更。`/codescan/v1/result/receive`（APIG）与 `/internal/codescan/v1/result/receive` 的入参出参、`obsUrl` 字段格式均不变，仅下载实现内部变更。

## 7. 安全设计

| 风险                               | 控制                                                                                                       |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 凭证被当作任意对象读取器（越权读） | 桶白名单 + 目录白名单 + `.sarif` 后缀 + 归属仓库校验，四者全部命中才读取                                   |
| 跨仓库读取他人扫描结果             | objectKey 第二段必须与 `repoUrl` 解析出的 `scanRun.repo` 一致；`unknown-repo` 无归属信息，接收与读取均拒绝 |
| SSRF / 本地文件读取                | 不再对 `obsUrl` 发起 HTTP 请求；仅解析 host 首段作为桶名、path 作为 key，`file://` 等协议直接拒绝          |
| 路径穿越                           | 拒绝含 `..`、`\`、前导 `/` 的 key；对象只读不写，临时文件名由 `createTempFile` 生成                        |
| 超大对象 DoS                       | 元数据预检 + 流式计数兜底，超限中止并清理临时文件                                                          |
| 敏感信息落日志                     | 日志只打印 `obsUrl` 与错误原因，不打印 AK/SK 与对象内容                                                    |
| 存量公开对象                       | 本次不迁移、不删除，由插件侧治理；后端读取私有/公开对象均走凭证，公有读属性不影响鉴权读取                  |

### 7.1 unknown-repo 目录的处理

插件仅在 `GITHUB_REPOSITORY` / `ATOMGIT_REPOSITORY` / `GIT_REPOSITORY` 全部缺失时使用 `unknown-repo` 兜底，实际 key 结构为：

```text
{tool}-results/unknown-repo/{yyyyMMdd.HH}/{runId|manual}/{basename}.sarif
```

其中第 4 段为时间批次、第 5 段为流水线运行 ID 或字面量 `manual`，文件名由调用方指定，均不具备不可猜测性。`obsUrl` 经上报接口进入后端，属外部可控输入，若读取阶段放行，调用方可构造 `{tool}-results/unknown-repo/<他人批次>/<固定文件名>.sarif` 绕过仓库归属校验，以平台凭证读取他人扫描结果。

因此改为接收阶段直接拒绝：`StaticAlarmReceiveServiceImpl` 对每条 obsUrl 解析路径，仓库段为 `unknown-repo` 即抛参数错误并返回明确提示；读取链路同步取消放行，按归属不一致拒绝。生产与 BETA 存量 `unknown-repo` 命中均为 0，改动无存量影响。
