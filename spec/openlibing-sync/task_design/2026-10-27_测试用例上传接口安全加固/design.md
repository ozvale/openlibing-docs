# 测试用例上传接口安全加固 — 技术设计

## 方案概述

在 `openlibing-sync-service` 中对 `testcase/metadata/upload` 接口做安全加固，核心是三件事：

1. **路径参数收敛**：`label` 走白名单（硬编码默认值 + 配置中心可覆盖），`archivePath` 走分段字符集与深度校验，从源头杜绝对象键注入。
2. **上传内容约束**：文件类型走黑名单，单文件大小走业务级二次校验。
3. **既有缺陷修复**：临时文件泄漏、同名文件统计错乱。

校验逻辑集中到 `UploadSecurityValidator`（无状态工具类），配置读取集中到 `UploadSecurityConfig`（`ConfigurableEnvironment` + Nacos 监听），与仓内既有的 `RateLimitConfig` 保持同一范式。

## 架构决策

- **label 用白名单而非字符集校验**：label 是业务枚举（精准测试/性能测试/仿真测试等），值域有限且可枚举，白名单强度远高于字符集正则，能直接杜绝「把 label 当成任意归档前缀写入」。
- **archivePath 用字符集 + 深度校验而非路径归一化**：OBS 是扁平键值存储，不存在本地文件系统那种 `..` 目录回溯语义，`Paths.get(...).normalize()` + `startsWith()` 的本地路径防护写法在此不适用。正确做法是把每个路径段约束成安全的单段名，从根本上排除 `..`、空段、超长段。
- **文件名黑名单而非白名单**：业务上传类型较多（xml/json/txt/log/html/zip/tar.gz 等），白名单会误杀；黑名单聚焦可执行、脚本、网页脚本三类高危扩展名。
- **不做文件内容嗅探**：仅按扩展名判断，简化实现；相应地在风险表中登记「`a.exe.gz` 这类双扩展名绕过」为已知残留风险。
- **单文件大小业务级校验值为 16MB**：容器级 `max-file-size` 必须**严格大于**该值（建议 24MB），使业务级校验先于容器层触发、`FILE_SIZE_EXCEED_LIMIT` 可达；取相等值会让容器先拒绝请求，业务错误码形同虚设。容器级 `max-request-size`（整请求总量）不在本次改动范围，由用户在 Nacos 配置中心自行调整。
- **白名单默认值硬编码 + 配置中心可覆盖**：配置中心未配置或不可用时回退到内置默认集合，保证功能可用性；配置中心可用时支持动态生效，新增业务标签无需改代码发版。
- **校验失败的粒度**：路径参数非法（label / archivePath）属于请求级错误，整个请求拒绝并返回错误码；单个文件类型非法或超限属于文件级错误，仅该文件计入失败清单，不中断整批上传。

## 涉及文件

| 文件                                                        | 操作 | 说明                                                                                                       |
| ----------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------- |
| `infrastructure/constant/SyncConstant.java`                 | 修改 | 新增 label 默认白名单、扩展名黑名单、单文件大小上限、archivePath 深度与段长上限常量                        |
| `infrastructure/response/ResponseCodeEnum.java`             | 修改 | 新增 `INVALID_LABEL`、`INVALID_ARCHIVE_PATH`、`FILE_TYPE_NOT_ALLOWED`、`FILE_SIZE_EXCEED_LIMIT` 四个错误码 |
| `infrastructure/config/UploadSecurityConfig.java`           | 新增 | 从配置中心读取 label 白名单，缓存 + Nacos 变更监听清缓存                                                   |
| `infrastructure/util/UploadSecurityValidator.java`          | 新增 | label / archivePath / 扩展名 / 文件大小校验逻辑，无状态静态方法                                            |
| `api/controller/TestCaseDataController.java`                | 修改 | 接入 label、archivePath、文件类型校验；按错误类型返回对应错误码                                            |
| `domain/service/testcase/impl/TestCaseDataServiceImpl.java` | 修改 | 单文件大小校验；临时文件 try-finally 清理；上传条目改为列表结构修复统计错乱                                |
| `src/test/.../TestCaseDataServiceImplTest.java`             | 修改 | 补充安全校验相关测试                                                                                       |
| `src/test/.../UploadSecurityValidatorTest.java`             | 新增 | 校验工具类单元测试                                                                                         |
| `src/test/.../UploadSecurityConfigTest.java`                | 新增 | 配置读取与回退逻辑单元测试                                                                                 |

## 配置项设计

### 配置键

| 配置键                       | 类型           | 默认值                                                                     | 说明                                                                                   |
| ---------------------------- | -------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `sync.upload.allowed-labels` | 逗号分隔字符串 | `precision,performance,simulation,presmoke,workflow-acceptance,test_label` | 允许的 label 白名单（保留前缀 `testcase-metadata` 不入白名单，仅由流水线归档路径使用） |

配置中心（Nacos）中的位置：随 `application` / `framework` dataId（group `OPENLIBING`，Properties 格式）下发，与 `@NacosConfigListener` 监听的 dataId 保持一致，通过 `ConfigurableEnvironment.getProperty` 读取，读取不到时回退硬编码默认值。

> **dataId 一致性**：配置下发位置与 `@NacosConfigListener` 的 dataId 必须同为 `application` / `framework`。若配置放在 `sync-service` 而监听的是 `application`，则配置变更不会触发热重载，白名单只在服务启动时生效。
>
> **保留前缀约束**：`testcase-metadata` 是流水线归档路径的固定前缀，不得加入白名单，否则 `label=testcase-metadata` + 任意 `archivePath` 可重建他人流水线的归档前缀。配置中心下发前需校验不含该前缀。

### Nacos 动态刷新

沿用 `RateLimitConfig` 的成熟范式：

```java
@Component
public class UploadSecurityConfig {
  // 缓存
  private volatile Set<String> allowedLabels = SyncConstant.DEFAULT_ALLOWED_LABELS;

  private final ConfigurableEnvironment environment;

  public UploadSecurityConfig(ConfigurableEnvironment environment) {
    this.environment = environment;
  }

  public Set<String> getAllowedLabels() {
    return allowedLabels;
  }

  /** Nacos 配置变更时重载白名单（dataId 需与配置下发位置一致） */
  @NacosConfigListener(dataId = "application", group = "OPENLIBING")
  public void onChange(String config) {
    reload();
  }

  private void reload() {
    String raw = environment.getProperty("sync.upload.allowed-labels", String.class, null);
    Set<String> labels = parse(raw);
    this.allowedLabels = labels.isEmpty() ? SyncConstant.DEFAULT_ALLOWED_LABELS : labels;
    log.info("Reloaded upload allowed labels: {}", this.allowedLabels);
  }
}
```

**要点**：

- 使用 `volatile` 保证配置变更后其他线程可见
- 配置为空或解析后为空集时回退默认白名单，**不允许因配置失误导致所有 label 被拒**
- 保留 `DEFAULT_ALLOWED_LABELS` 硬编码常量作为兜底，避免配置中心故障导致上传功能完全不可用
- 监听 dataId 与配置下发 dataId 必须一致（均为 `application` / `framework`），否则热重载不生效

## 校验规则设计

### label 白名单校验

| 条件                | 结果                       |
| ------------------- | -------------------------- |
| label 为空 / 仅斜杠 | 通过，走既有流水线归档路径 |
| label 在白名单内    | 通过                       |
| label 不在白名单内  | 拒绝，`INVALID_LABEL`      |

**保留前缀约束**：`testcase-metadata` 是流水线归档路径的固定前缀（`testcase-metadata/{pipelineId}/{pipelineRunId}/{jobId}/`），插件侧按该前缀扫描并解析 XML，因此**不在白名单内**。若它被加入白名单，攻击者可用 `label=testcase-metadata` + 任意合法 `archivePath` 重建他人流水线的归档前缀，与「label 为空」时服务自动落到该前缀的行为等价，从而绕过主防线。

因此白名单的完整性依赖两点：默认白名单不含该前缀，且配置中心下发时同样校验不含该前缀。

**兼容性说明**：既有 `TestCaseDataServiceImplTest` 中使用的 `performance`、`nightly`、`simulation` 三个 label 中，`nightly` **不在**业务白名单内，改造后该值会被拒绝。需要评估 `nightly` 是否为真实在用的 label：

- 若在用 → 需加入白名单
- 若为测试遗留 → 更新测试用例

> 该项为实施前的必查项，见 tasks.md Task 0。

### archivePath 分段校验

校验对象为**去除首尾斜杠后**的字符串，与既有 `StringUtils.strip(value, "/")` 行为一致。

单段合法规则：

| 规则     | 正则                      | 说明                         |
| -------- | ------------------------- | ---------------------------- |
| 字符集   | `^[A-Za-z0-9._-]{1,128}$` | 仅字母数字下划线连字符点     |
| 首字符   | 非 `.`                    | 排除 `.`、`..`、隐藏文件形态 |
| 显式排除 | 不等于 `.` / `..`         | 双重保险                     |

整体规则：

| 条件                  | 结果                         |
| --------------------- | ---------------------------- |
| 段数 > 8              | 拒绝，`INVALID_ARCHIVE_PATH` |
| 存在空段（如 `a//b`） | 拒绝，`INVALID_ARCHIVE_PATH` |
| 任一段不满足单段规则  | 拒绝，`INVALID_ARCHIVE_PATH` |

**实现要点**：`"a/".split("/")` → `["a"]`（尾部空串被 Java 丢弃），`"a//b".split("/")` → `["a", "", "b"]`（中间空串保留）。校验前已 strip 首尾斜杠，因此「首尾空段」不会出现，「中间空段」会被正确识别并拒绝。

### 文件类型黑名单

扩展名提取规则：

```java
int dot = filename.lastIndexOf('.');
// dot <= 0 表示无扩展名（dot == 0 即以点开头的隐藏文件，也视为无扩展名）
String extension = dot > 0 ? filename.substring(dot).toLowerCase() : "";
```

黑名单常量（`SyncConstant.DENIED_FILE_EXTENSIONS`）：

```
.jsp .jspx .php .phtml
.exe .dll .so
```

**黑名单收敛依据**：

上述两类扩展名的风险成立，需要「OBS 桶被挂载为 WebRoot」或「归档文件被下游解压执行」等前提。当前 OBS 桶仅作为私有存储使用，**这些前提均不成立**，因此只保留唯一一类在误配置场景下能造成服务端代码执行的类型，其余类型全部放行：

| 放行类型                           | 理由                                                            |
| ---------------------------------- | --------------------------------------------------------------- |
| `.sh` `.bat` `.cmd` `.ps1`         | 脚本无自动执行路径，仅作为归档内容存储                          |
| `.jar` `.war` `.ear` `.apk` `.ipa` | 本身是压缩包，非可执行文件                                      |
| `.js` `.mjs` `.svg` `.swf` `.html` | 桶未开启静态网站托管，不构成 XSS 载体；且为前端构建产物常见组成 |
| `.asp` `.aspx` `.ashx`             | 与 `.jsp`/`.php` 同类，Java 技术栈下命中概率极低                |

**主防线说明**：扩展名黑名单是**次要兜底**，本接口真正的安全主防线是 **label 白名单 + archivePath 分段校验**——二者共同保证攻击者无法构造出落入他人 `testcase-metadata/{pipelineId}/{runId}/{jobId}/` 前缀的 objectKey，从而阻断「向他人流水线注入恶意 XML」这一实质危害。

该结论的前提是 **`testcase-metadata` 不在 label 白名单内**：一旦它被加入白名单，`label=testcase-metadata` + 任意合法 `archivePath` 即可重建他人流水线的归档前缀，主防线随即失效。详见上文「保留前缀约束」。

**判断依据**：基于**净化后**的文件名（`safeFilename`）判断，与既有 `TestCaseDataServiceImpl` 的文件名净化逻辑保持一致。净化规则 `[^A-Za-z0-9._-] → _` 保留了点号，因此 `a.exe.xml` 的扩展名为 `.xml`，可被放行（已知残留风险，见风险表）。

### 单文件大小校验

| 项               | 值         | 说明                                                              |
| ---------------- | ---------- | ----------------------------------------------------------------- |
| 业务级单文件上限 | 16MB       | `SyncConstant.MAX_UPLOAD_FILE_SIZE`                               |
| 容器级单文件上限 | > 16MB     | `spring.servlet.multipart.max-file-size`（Nacos 可调），建议 24MB |
| 容器级整请求上限 | Nacos 可调 | `spring.servlet.multipart.max-request-size`（本次不涉及）         |

**必须留出级差**：容器级 `max-file-size` 若与业务级上限相等（都是 16MB），容器会先于业务层拒绝超限请求，`FILE_SIZE_EXCEED_LIMIT` 在真实链路上永远不会被返回，等于该错误码与整段业务级校验失效。容器级上限必须**严格大于**业务级上限，才能让业务层先判定、返回可区分的错误码，并让文件级语义（仅该文件进失败清单、其余文件正常上传）真正生效。

## 关键实现

### UploadSecurityValidator

无状态工具类，方法均为静态：

```java
public final class UploadSecurityValidator {

  private UploadSecurityValidator() {}

  /** 校验 label 是否在白名单内 */
  public static boolean isValidLabel(String label, Set<String> allowedLabels) { ... }

  /** 校验 archivePath 分段合法性 */
  public static boolean isValidArchivePath(String archivePath) { ... }

  /** 校验文件扩展名是否命中黑名单 */
  public static boolean isDeniedExtension(String safeFilename) { ... }
}
```

`isValidLabel` 中 label 为空的场景直接返回 `true`（空 label 走流水线路径，无需白名单判定），由调用方在 Controller 层按 `hasLabel` 分流。

### 临时文件泄漏修复

改造前的问题：`File.createTempFile` 成功但 `transferTo` 抛异常时，临时文件不进入 `uploadInfoList`，既有的 `buildUploadResult` 清理逻辑覆盖不到，文件残留在 `java.io.tmpdir`。

```java
File tempFile = null;
try {
    tempFile = File.createTempFile("upload_", "_" + safeFilename);
    multipartFile.transferTo(tempFile);
    String objectKey = buildObjectKey(label, archivePath, pipelineId, pipelineRunId, jobId, safeFilename);
    uploadInfoList.add(new ObsUploadInfo(objectKey, tempFile));
    uploadEntries.add(new UploadEntry(filename, objectKey));
    tempFile = null;  // 移交所有权给 uploadInfoList，由 buildUploadResult 清理
} catch (IOException e) {
    logger.error("Failed to convert multipart file: {}", LogSanitizer.sanitize(filename), e);
    // 转换失败的文件必须进入失败清单，否则该文件在结果中完全不可见（静默丢失）
    rejectedFileNames.add(filename);
} finally {
    if (tempFile != null && tempFile.exists() && !tempFile.delete()) {
        logger.warn("delete temp file:{} fail.", LogSanitizer.sanitize(tempFile.getAbsolutePath()));
    }
}
```

`tempFile = null` 的所有权移交是关键：入队成功后置空，避免 finally 分支提前删除掉还要上传的文件。

**失败文件必须可见**：`catch` 分支除记录日志外，还需把文件加入失败清单（携带失败原因）。否则 `transferTo` 失败的文件既不在 `success` 也不在 `failure`，调用方无法感知该文件丢失，且 `failure` 为空会让人误判为「全部上传成功」。

### 同名文件统计错乱修复

改造前的问题：`fileNameToObjectKeyMap` 是 `Map<String, String>`，key 为**原始文件名**。

- 同一原始文件名重复上传时，key 碰撞，后写入的覆盖先写入的，返回结果少统计文件
- `a/b.xml` 与 `a_b.xml` 净化后得到相同 `safeFilename`，objectKey 相同，但因原始文件名不同，map 中是两条独立记录，两条都会命中同一个 objectKey 的成功判定

改造方案：将 `Map<String, String>` 替换为 `List<UploadEntry>`，每个条目独立持有 `displayName`（原始文件名，用于失败清单展示）与 `objectKey`：

```java
/** 上传条目：保留原始文件名用于失败清单展示 */
private static final class UploadEntry {
  private final String displayName;
  private final String objectKey;
  ...
}
```

`buildUploadResult` 改为遍历列表逐条判定，不再依赖 map 的 key 唯一性。

**响应语义保持不变**：`success` 仍返回 objectKey 列表，`failure` 仍返回原始文件名列表，调用方无需适配。

## 数据流

```
客户端
    │  POST testcase/metadata/upload
    │  files=[metadata.xml, data.xml]
    │  archiveConfig={"label":"performance","archivePath":"20260612/143025"}
    ▼
TestCaseDataController
    │  1. files 非空校验
    │  2. archiveConfig JSON 解析
    │  3. hasArchivePath && !hasLabel        → BAD_REQUEST
    │  4. !hasLabel && !hasPipelineParams    → BAD_REQUEST
    │  5. files.size() > 100                 → FILES_UPLOAD_EXCEED_LIMIT
    │  6. hasLabel && !白名单                 → INVALID_LABEL
    │  7. hasArchivePath && !分段合法          → INVALID_ARCHIVE_PATH
    ▼
TestCaseDataServiceImpl
    │  8. 逐文件：净化文件名 → 扩展名黑名单 → 单文件大小
    │     ├─ 类型非法/超限 → 计入失败清单，跳过上传
    │     └─ 通过 → createTempFile → transferTo → 加入上传队列
    │        （try-finally 保证临时文件不泄漏）
    ▼
ObsUtilClient.batchUploadFiles
    ▼
OBS: performance/20260612/143025/metadata.xml
```

## 接口变更

### 请求参数变更

**无**。本次不改接口签名，`label` / `archivePath` 已在「蓝区性能数据上传归档」需求中引入。

### 响应码变更

新增 4 个业务错误码：

| 错误码                   | 数值  | 中文                     | 英文                    |
| ------------------------ | ----- | ------------------------ | ----------------------- |
| `INVALID_LABEL`          | 40012 | label 取值不在允许范围内 | invalid label           |
| `INVALID_ARCHIVE_PATH`   | 40013 | 归档路径参数非法         | invalid archive path    |
| `FILE_TYPE_NOT_ALLOWED`  | 40014 | 文件类型不被允许         | file type not allowed   |
| `FILE_SIZE_EXCEED_LIMIT` | 40015 | 文件大小超出限制         | file size exceeds limit |

**响应结构不变**：仍为 `Result` 包裹的 `Map`，`success` 存 objectKey 列表、`failure` 存原始文件名列表。

### 错误码使用边界

| 错误码                   | 触发层级 | 表现                                      |
| ------------------------ | -------- | ----------------------------------------- |
| `INVALID_LABEL`          | 请求级   | 整个请求失败，返回错误码                  |
| `INVALID_ARCHIVE_PATH`   | 请求级   | 整个请求失败，返回错误码                  |
| `FILE_TYPE_NOT_ALLOWED`  | 文件级   | 该文件进 `failure` 列表，其余文件正常上传 |
| `FILE_SIZE_EXCEED_LIMIT` | 文件级   | 该文件进 `failure` 列表，其余文件正常上传 |

文件级错误不进 `failure` 列表会丢失可观测性；文件级错误直接拒绝整个请求则会让一个坏文件阻断整批 100 个文件的上传，因此采用文件级粒度。

**可达性前提**：`FILE_SIZE_EXCEED_LIMIT`（40015）只有在容器级 `max-file-size` **严格大于**业务级上限时才可达——否则容器会先拒绝请求，业务层根本收不到超限文件，该错误码形同虚设。同理 `FILE_TYPE_NOT_ALLOWED`（40014）当前也不作为整批错误码返回，仅作为文件级失败原因的标识。

## 测试设计

### UploadSecurityValidatorTest

| 用例                     | 输入                                                                             | 期望                                             |
| ------------------------ | -------------------------------------------------------------------------------- | ------------------------------------------------ |
| label 为空               | `""`                                                                             | 通过                                             |
| label 在白名单           | `performance`                                                                    | 通过                                             |
| label 不在白名单         | `nightly`                                                                        | 拒绝（`nightly` 为测试遗留值，非真实在用 label） |
| label 为保留前缀         | `testcase-metadata`                                                              | 拒绝（保留前缀，不得入白名单）                   |
| archivePath 合法单层     | `20260612`                                                                       | 通过                                             |
| archivePath 合法多层     | `team-x/2026-Q2/sprint-3`                                                        | 通过                                             |
| archivePath 含 ..        | `../other`                                                                       | 拒绝                                             |
| archivePath 含中间 ..    | `a/../../b`                                                                      | 拒绝                                             |
| archivePath 含空段       | `a//b`                                                                           | 拒绝                                             |
| archivePath 超 8 层      | 9 段                                                                             | 拒绝                                             |
| archivePath 段超长       | 129 字符                                                                         | 拒绝                                             |
| archivePath 段含非法字符 | `a b`（含空格）                                                                  | 拒绝                                             |
| 扩展名命中黑名单         | `a.exe` / `a.jsp` / `a.php`                                                      | 拒绝                                             |
| 扩展名未命中             | `a.xml` / `a.json` / `a.txt` / `a.zip` / `a.tar.gz` / `a.html` / `a.js` / `a.sh` | 通过                                             |
| 双扩展名                 | `a.exe.xml`                                                                      | 通过（已知残留风险）                             |

### TestCaseDataServiceImplTest 补充

| 用例                               | 验证点                                      |
| ---------------------------------- | ------------------------------------------- |
| 单文件超限                         | 该文件进 failure 列表，其余成功             |
| 危险类型文件                       | 该文件进 failure 列表                       |
| 同名文件（`a/b.xml` 与 `a_b.xml`） | 返回结果中两条独立条目                      |
| transferTo 异常                    | 临时文件被清理，且该文件出现在 failure 列表 |

### 既有测试兼容性

既有 `TestCaseDataServiceImplTest` 中 `testBuildObjectKey_labelAlone_noPipelineParams` 使用 label `nightly`，`testBuildObjectKey_labelWithoutArchivePath_labelDirectPath` 使用 `performance`。

**已确认**：`nightly` 为测试遗留值，非真实在用 label，不纳入白名单。

`buildObjectKey` 方法本身不做白名单校验（校验在 Controller 层），因此这些**直接调用 buildObjectKey 的既有测试不受影响**，可保持原样通过。若后续新增 Controller 层的白名单校验测试，`nightly` 应作为「白名单外取值」的负向用例使用。

## 风险 & 缓解

| 风险                                      | 影响                                                            | 缓解                                                                                                                                                          |
| ----------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 白名单遗漏真实在用 label                  | 上传功能被误拒                                                  | 已核查各调用方实际使用的 label 值均覆盖（`precision` / `performance` / `simulation` / `presmoke` / `workflow-acceptance` / `test_label`）；配置中心可动态补充 |
| 保留前缀 `testcase-metadata` 被加入白名单 | 可用 `label` + `archivePath` 重建他人流水线归档前缀，主防线失效 | 默认白名单不含该前缀；配置中心下发前校验不含该前缀；label 为空时服务自动落到该前缀，无需显式指定                                                              |
| 配置中心配置错误导致全部 label 被拒       | 上传功能不可用                                                  | 配置为空或解析为空集时回退硬编码默认白名单                                                                                                                    |
| 黑名单遗漏新型危险扩展名                  | 危险文件仍可上传                                                | 黑名单已收敛为「服务端可执行」一类，风险场景需桶被误配置才成立；接受残余风险                                                                                  |
| 双扩展名绕过（`a.exe.gz`）                | 危险文件伪装成普通类型                                          | 本期不做内容嗅探，已在风险表登记为已知残留风险；如需收敛可在后续迭代补充 magic number 校验                                                                    |
| 容器级 `max-file-size` 未大于业务上限     | 容器先于业务层拒绝超限请求，`FILE_SIZE_EXCEED_LIMIT` 不可达     | 容器级上限必须严格大于业务级上限（建议 24MB vs 16MB），已在配置项设计与 tasks.md Task 8 中明确                                                                |
| 容器级 `max-request-size` 未同步调整      | 批量上传（多文件总和超限）仍被框架层拒绝                        | 本次不涉及，由用户在 Nacos 自行调整；文档已提示                                                                                                               |
| 校验提前拒绝改变既有调用方行为            | 既有调用方若使用了白名单外的 label 会收到 400                   | 已核查调用方 label 取值均在白名单内；提供明确错误码便于定位                                                                                                   |
| Nacos 监听 dataId 与配置下发位置不一致    | 白名单热重载不生效，仅启动时读取一次                            | 监听 dataId 与配置下发 dataId 统一为 `application` / `framework`（group `OPENLIBING`），与 `RateLimitConfig` 读取路径一致                                     |

## 跨仓影响

- **openlibing-sync**：本次唯一改动的代码仓，接口签名与响应结构均不变，向后兼容。
- **openlibing-pytest-executor**：`upload_to_openlibing.py` 的 `--label` 取值需落在白名单内。现有脚本文档中出现的 `performance`、`simulation` 均在白名单内；`--label` 的 help 文本中提及的 `precision` 也在白名单内。**若业务侧新增 label 标签，需同步在配置中心补充白名单**（但不得加入保留前缀 `testcase-metadata`）。
- **其他调用方**：`upload_to_openlibing.py` 之外的直接 HTTP 调用方（如 IDE 插件、workflow 验收脚本）需确认其 label 取值合法性。`workflow-acceptance`、`test_label` 已在白名单内，覆盖这两类场景。
