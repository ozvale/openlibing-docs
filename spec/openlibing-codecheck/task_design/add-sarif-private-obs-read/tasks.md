# add-sarif-private-obs-read 实现步骤

## Task 1 ObsBucketService 接口扩展

- [x] 1.1 `ObsBucketService` 新增 `Path downloadToTempFile(String obsUrl, String expectedRepo) throws IOException`

## Task 2 ObsBucketServiceImpl 私有对象读取

- [x] 2.1 新增配置项 `obs.action.buckets`（共享，`application` data-id）与 `codecheck.alarm.obs.allowed-key-patterns`（服务私有），大小上限沿用 `codecheck.alarm.obs.max-file-size-mb`，均带代码默认值
- [x] 2.2 `SarifObsAccessPolicy` 以 `@PostConstruct` 解析并预编译白名单，非法配置告警后回落默认值；该 Bean 加 `@RefreshScope`，`ObsBucketServiceImpl` 不加，避免配置刷新关闭 `ObsClient`
- [x] 2.3 实现 URL 解析：协议校验、host 首段取桶、path 取 objectKey
- [x] 2.4 实现访问策略：桶白名单、目录白名单（正则 `lookingAt`）、`.sarif` 后缀、key 合法性（`..`/`\`/前导 `/`/长度）
- [x] 2.5 实现归属校验：key 分段 ≥ 5，第二段与 `expectedRepo` 忽略大小写相等，`unknown-repo` 不放行
- [x] 2.6 实现 `getObject` + 元数据预检 + `copyWithLimit` 流式落盘 + 失败清理临时文件

## Task 3 SarifParseServiceImpl 切换到私有读取

- [x] 3.1 注入 `ObsBucketService`，`downloadAndParse` 改为下载临时文件并解析，`finally` 删除临时文件
- [x] 3.2 删除 `HttpURLConnection` 下载、`CountingInputStream`、`validateObsUrl`、`isHostAllowed`、`obsHostWhitelist` 及超时常量
- [x] 3.3 保留 `parseAllUrls` 按 URL 失败隔离语义，日志补充文件大小

## Task 4 单元测试

- [x] 4.1 `ObsBucketServiceImplTest` 新增：非白名单桶拒绝、白名单外目录拒绝、非 `.sarif` 拒绝、路径穿越拒绝、`file://` 拒绝、归属仓库不一致拒绝、`unknown-repo` 拒绝、默认目录命中、Nacos 覆盖生效、元数据超限拒绝、流式计数超限中止、成功下载内容一致
- [x] 4.2 `SarifParseServiceImplTest` 改为 mock `ObsBucketService`，删除本地 HttpServer 或保留仅用于失败隔离用例；新增单 URL 下载失败不影响同批其他 URL 用例
- [x] 4.3 `StaticAlarmReceiveServiceImplTest` 新增：`unknown-repo` obsUrl 拒绝入库、正常仓库段 obsUrl 正常入库

## Task 5 验证

- [x] 5.1 `mvn -Dtest=ObsBucketServiceImplTest,SarifParseServiceImplTest,StaticAlarmReceiveServiceImplTest test` 通过（48 条：ObsBucketServiceImplTest 25、SarifParseServiceImplTest 9、StaticAlarmReceiveServiceImplTest 14）；最终 head `7836fb86` 执行 `mvn clean test` 全量 1612 条通过；增量行覆盖率 87.9%（门禁 80%）
- [x] 5.2 `mvn spotless:check` 通过
- [x] 5.3 确认未提交本地调试文件（`MongoConfig.java`、`RedisConfig.java`、`.codegraph/`、`.serena/`、`docs/`、`src/main/resources/cacerts`）

## Task 6 存量兼容性验证

- [ ] 6.1 抽样线上 `static_alarm_scan_run.obs_url`，逐条校验桶名、目录前缀、`.sarif` 后缀、段数、仓库段，确认存量对象均能命中新访问策略
- [ ] 6.2 若发现不满足策略的存量对象，评估其工具维度是否同时存在其他可用 URL，避免消失清理误判

> 6.1 / 6.2 尚未执行：存量 URL 对新访问策略的全量覆盖率**未验证**。已完成的只是首轮只读核查（3842 条 scanRun / 4335 个 obsUrl，`unknown-repo` 命中 0，仓库段不一致仅 1 组 1325 条且来自改造前已被 host 白名单拒绝的旧流水线），不含目录前缀 / 段数 / `.sarif` 后缀的全量校验。残余风险：若存量 URL 不命中新策略，读取阶段会被拒并计入 `ParseResult.errors`；当同一工具还有其他可用 URL 时 scanRun 为 PARTIAL_SUCCESS，被拒 URL 上的告警可能被消失清理，属不可逆数据丢失。

## Task 7 接收阶段拒绝 unknown-repo

- [x] 7.1 `StaticAlarmReceiveServiceImpl.buildScanRunEntity` 校验每条 obsUrl 的仓库段，`unknown-repo` 抛 `IllegalArgumentException` 并返回参数错误
- [x] 7.2 `ObsBucketServiceImpl.validateAccessPolicy` 取消 `unknown-repo` 放行，按归属不一致拒绝
- [x] 7.3 补齐接收拒绝/正常通过、读取拒绝的单测
- [x] 7.4 确认生产与 BETA 存量 `unknown-repo` 命中均为 0
