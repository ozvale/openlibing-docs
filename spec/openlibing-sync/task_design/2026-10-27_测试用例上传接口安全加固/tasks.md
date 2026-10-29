# 测试用例上传接口安全加固 — 实现任务

## Task 0：前置核查（已完成）

- [x] 核查所有调用方实际使用的 `label` 取值，确认白名单覆盖完整
  - 检索范围：`openlibing-pytest-executor/plugins/upload_to_openlibing/`、其他仓的 HTTP 直调方
  - 核查结论：实际在用 label 为 `precision` / `performance` / `simulation` / `presmoke` / `workflow-acceptance` / `test_label`，与白名单一致
  - `nightly` 确认为**测试遗留值**，非真实在用，不纳入白名单
  - `testcase-metadata` 为流水线归档路径的**保留前缀**，不纳入白名单（label 为空时服务自动落到该前缀）
- [x] 确认 Nacos 中配置下发 dataId 为 `application` / `framework`（group `OPENLIBING`），与 `@NacosConfigListener` 监听的数据源一致
- [x] 确认配置键 `sync.upload.allowed-labels` 在 Nacos 中的下发位置

## Task 1：常量与错误码

- [ ] `SyncConstant.java` 新增常量：
  - [ ] `DEFAULT_ALLOWED_LABELS`：默认 label 白名单（`Set<String>`，不可变），6 项：
        `precision` `performance` `simulation` `presmoke` `workflow-acceptance` `test_label`
        （不含保留前缀 `testcase-metadata`）
  - [ ] `DENIED_FILE_EXTENSIONS`：扩展名黑名单（`Set<String>`，不可变），仅 7 个：
        `.jsp` `.jspx` `.php` `.phtml` `.exe` `.dll` `.so`
  - [ ] `MAX_UPLOAD_FILE_SIZE`：单文件大小上限（16MB）
  - [ ] `MAX_ARCHIVE_PATH_DEPTH`：archivePath 最大层数（8）
  - [ ] `MAX_ARCHIVE_PATH_SEGMENT_LENGTH`：单段最大长度（128）
- [ ] `ResponseCodeEnum.java` 新增错误码：
  - [ ] `INVALID_LABEL(40012, ...)`
  - [ ] `INVALID_ARCHIVE_PATH(40013, ...)`
  - [ ] `FILE_TYPE_NOT_ALLOWED(40014, ...)`
  - [ ] `FILE_SIZE_EXCEED_LIMIT(40015, ...)`

## Task 2：校验工具类

- [ ] 新建 `infrastructure/util/UploadSecurityValidator.java`
  - [ ] 私有构造，工具类不可实例化
  - [ ] `isValidLabel(String label, Set<String> allowedLabels)`：label 为空返回 true；否则判断是否在集合内
  - [ ] `isValidArchivePath(String archivePath)`：
    - [ ] 先 `StringUtils.strip(archivePath, "/")`
    - [ ] 空值返回 true（由调用方按 `hasArchivePath` 分流）
    - [ ] 按 `/` 切分，段数 > 8 返回 false
    - [ ] 逐段校验：非空、长度 <= 128、字符集 `[A-Za-z0-9._-]`、首字符非 `.`、不等于 `.` / `..`
  - [ ] `isDeniedExtension(String safeFilename)`：
    - [ ] 取最后一个点之后的部分作为扩展名，无扩展名（点号位置 <= 0）视为不命中
    - [ ] 转小写后比对黑名单
- [ ] 补充 JavaDoc，说明每个方法的判定依据

## Task 3：配置读取

- [ ] 新建 `infrastructure/config/UploadSecurityConfig.java`
  - [ ] `@Component`
  - [ ] 注入 `ConfigurableEnvironment`
  - [ ] `volatile Set<String> allowedLabels`，初始值取 `SyncConstant.DEFAULT_ALLOWED_LABELS`
  - [ ] `getAllowedLabels()` getter
  - [ ] 启动时（`@PostConstruct`）从 `sync.upload.allowed-labels` 加载，解析为集合（按逗号分隔、trim、忽略空项）
  - [ ] 解析结果为空集时回退 `SyncConstant.DEFAULT_ALLOWED_LABELS`
  - [ ] `@NacosConfigListener(dataId = "application", group = "OPENLIBING")` 监听变更并重新加载
        （dataId 需与配置下发位置一致，否则热重载不生效）
  - [ ] 加载失败（配置解析异常）时保留当前值并打错误日志，不影响服务可用性

## Task 4：Controller 接入校验

- [ ] `TestCaseDataController.java`：
  - [ ] 注入 `UploadSecurityConfig`
  - [ ] 在既有参数校验之后新增：
    - [ ] `hasLabel` 时，`UploadSecurityValidator.isValidLabel(label, config.getAllowedLabels())` 不通过 → 返回 `INVALID_LABEL`
    - [ ] `hasArchivePath` 时，`UploadSecurityValidator.isValidArchivePath(archivePath)` 不通过 → 返回 `INVALID_ARCHIVE_PATH`
  - [ ] 保持既有校验顺序不变（files 非空 → archiveConfig 解析 → label/archivePath 依赖关系 → 流水线参数 → 数量上限 → 新增路径校验）

## Task 5：Service 加固与缺陷修复

- [ ] `TestCaseDataServiceImpl.java`：
  - [ ] 注入 `UploadSecurityConfig`（用于读取白名单）或直接复用 Controller 传入的校验结果（实现时二选一，保持职责清晰）
  - [ ] 逐文件增加扩展名黑名单校验，命中则计入失败清单并跳过
  - [ ] 逐文件增加单文件大小校验（`multipartFile.getSize() > MAX_UPLOAD_FILE_SIZE`），超限则计入失败清单并跳过
  - [ ] 临时文件 try-finally 清理：成功后置空 `tempFile` 移交所有权，finally 中仅清理未移交的临时文件
  - [ ] `transferTo` 抛 `IOException` 时，除记录日志外把该文件加入失败清单（携带失败原因），避免失败文件被静默丢弃
  - [ ] 将 `Map<String, String> fileNameToObjectKeyMap` 替换为 `List<UploadEntry>` 列表结构，每条持有 `displayName`（原始文件名）与 `objectKey`
  - [ ] `buildUploadResult` 改为遍历列表逐条判定成功/失败
  - [ ] 响应结构保持不变：`success` 为 objectKey 列表，`failure` 为原始文件名列表
  - [ ] 文件级失败需能区分原因（类型非法 / 超限），用于日志与排查

## Task 6：单元测试

- [ ] 新建 `UploadSecurityValidatorTest.java`
  - [ ] label：空 / 白名单内 / 白名单外 / 保留前缀 `testcase-metadata`（应拒绝）
  - [ ] archivePath：合法单层 / 合法多层 / 含 `..` / 含中间 `..` / 含空段 / 超 8 层 / 段超长 / 段含非法字符
  - [ ] 扩展名：命中黑名单各类型（`.jsp` / `.php` / `.exe` / `.dll` / `.so`）/ 未命中（xml、json、txt、zip、tar.gz、html、js、sh）/ 双扩展名
- [ ] 新建 `UploadSecurityConfigTest.java`
  - [ ] 配置存在时正确解析
  - [ ] 配置缺失时回退默认白名单
  - [ ] 配置解析为空集时回退默认白名单
- [ ] 补充 `TestCaseDataServiceImplTest.java`
  - [ ] 危险类型文件进 failure 列表
  - [ ] 超限文件进 failure 列表
  - [ ] 同名文件（`a/b.xml` 与 `a_b.xml`）各自有独立条目
  - [ ] `transferTo` 异常时临时文件被清理，且该文件出现在 failure 列表
  - [ ] 既有 `buildObjectKey` 用例全部保持通过

## Task 7：格式化与验证

- [ ] 使用 `google-java-format`（版本与 `pom.xml` 中 `googleJavaFormat.version` 一致）格式化所有改动的 Java 文件
- [ ] 运行 `pre-commit run --all-files`，确认 ruff / trailing-whitespace 等 hook 通过
- [ ] 运行 `mvn -pl openlibing-sync-service -am test`，确认全部测试通过
- [ ] 运行 `mvn -pl openlibing-sync-service -am checkstyle:check spotbugs:check pmd:check`，确认静态检查通过
- [ ] 自检：确认未引入无关重构与格式化噪音（diff 仅含功能性改动）

## Task 8：配置中心配合（非代码，需运维/用户执行）

Nacos `application` / `framework` dataId（group `OPENLIBING`）为 **Properties 格式**，配置写法如下：

- [ ] 配置 label 白名单（不配置时回退代码内硬编码默认值）：
  ```properties
  sync.upload.allowed-labels=precision,performance,simulation,presmoke,workflow-acceptance,test_label
  ```
  > 不得包含保留前缀 `testcase-metadata`，否则可用 `label` + `archivePath` 重建他人流水线归档前缀。
  > 配置下发位置必须与 `@NacosConfigListener` 监听的 dataId 一致，否则热重载不生效。
- [ ] 调整容器级 multipart 限制（本次不涉及代码改动）：
  ```properties
  spring.servlet.multipart.max-file-size=24MB
  spring.servlet.multipart.max-request-size=<按实际批量计算的最小必要上限>
  ```
  > `max-file-size`（24MB）必须**严格大于**业务级 `MAX_UPLOAD_FILE_SIZE`（16MB），否则容器会先于业务层拒绝超限请求，`FILE_SIZE_EXCEED_LIMIT` 永远不可达。
  > `max-request-size` 按「单次最多 100 个文件」的实际批量计算最小必要上限（100 × 16MB ≈ 1.6GB，配置值取略高于该值即可），**不建议直接照抄 2GB**。
  > 放开前须确认网关 / 鉴权侧对请求体大小的限制同步放开，且上传接口的鉴权与限流已到位，避免单个 1.6GB 请求耗尽容器 temp 磁盘。
- [ ] 验证配置变更后白名单热生效（上传一个新增 label 的文件，无需重启即通过）
- [ ] 验证配置变更日志中出现 `Reloaded upload allowed labels`，确认配置被正确解析

## 交付与归档

- [ ] 关联业务 Issue（无则先创建）
- [ ] 代码仓 PR（目标分支 `master`，打 `ai-assisted` 标签）
- [ ] 用户自测确认
- [ ] docs 仓归档 PR（分支 `spec/openlibing-sync/2026-10-27_测试用例上传接口安全加固`，目标 `master`）
