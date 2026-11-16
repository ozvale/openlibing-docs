# Design: 软件包上传 zip 深度校验与压缩炸弹防护

## 1. 改动清单

| 文件                                                  | 动作 | 说明                                                                            |
| ----------------------------------------------------- | ---- | ------------------------------------------------------------------------------- |
| `common/utils/ZipSecurityCheckUtil.java`              | 新增 | zip 深度安全校验工具（结构合法性 + 条目数 + 解压总大小 + 压缩比，仅读中央目录） |
| `common/utils/ZipSecurityCheckUtilTest.java`          | 新增 | 工具级测试：正常/非法/空包/高压缩比/条目数/总大小                               |
| `business/service/impl/ToolApplyServiceImpl.java`     | 修改 | 3 个 Nacos 阈值配置 + 整片/分片两路径接入深度校验 + fail-closed 清理链          |
| `business/service/impl/ToolApplyServiceImplTest.java` | 修改 | 服务级测试：炸弹拒、非法拒、合并后炸弹删 OBS 对象、at-limit 用例改真实 zip      |

无 schema / 接口契约 / Liquibase 变更。

## 2. 关键设计

### 2.1 ZipSecurityCheckUtil（中央目录扫描）

- 基于 JDK `ZipFile` 遍历中央目录条目元数据，**不解压条目内容**，单次扫描代价为顺序 IO；`ZipFile` 原生支持 zip64
- `ZipException` → 结构非法拒绝；无条目 → 拒绝（空包无意义）
- 三项独立阈值（由调用方传入，工具自身不读配置）：
  - 解压后总大小 ≤ `maxUncompressedBytes`
  - 条目数 ≤ `maxEntryCount`（遍历中即判即拒，不落完整枚举）
  - 整体压缩比 = 解压总大小 / 压缩文件大小 ≤ `maxCompressionRatio`
- 条目 `entry.getSize() < 0`（声明大小未知/非法）→ 直接 fail-closed，否则总量与压缩比校验会被绕过
- 字符集用 `StandardCharsets.ISO_8859-1` 按字节 1:1 解码条目名：JDK 默认 UTF-8 严格校验会误拒 GBK 等无 UTF-8 标志位的合法 zip；本工具不消费条目名，字节解码保证任意合法 zip 可通过
- 校验通过返回 null，失败返回用户可读原因（大小描述优先 GB/MB/字节）

### 2.2 三个 Nacos 可选配置（ToolApplyServiceImpl）

| 配置键                                     | 默认值      | 含义             |
| ------------------------------------------ | ----------- | ---------------- |
| `tool.software.pack.max.uncompressed.size` | 10240（MB） | 解压后总大小上限 |
| `tool.software.pack.max.compression.ratio` | 100         | 整体压缩比上限   |
| `tool.software.pack.max.zip.entries`       | 100000      | zip 条目数上限   |

- `@Value("${key:default}")` 注入 String，解析时 trim + 正数校验 + `NumberFormatException` 回退默认值（WARN 日志），配置缺失/非法不影响服务启动

### 2.3 整片上传路径（saveToolSoftwarePack）

- `validateSoftwarePackFile` 保留 ImageCheckUtil 表层校验（魔数/扩展名/≤5MB）后，追加 `validateZipDeep`：
  - 落临时文件 `software-pack-check-*.zip` 后执行中央目录校验（≤5MB，临时文件成本可忽略）
  - `finally deleteTempFileQuietly` 清理；首版 `Files.copy` 未带 `REPLACE_EXISTING` 导致临时文件已存在抛 `FileAlreadyExistsException`，已修复
- 失败抛 `DataResultFailException`，沿用现有异常链返回

### 2.4 分片上传路径（completeChunkUpload，fail-closed）

OBS 合并成功后执行 `scanMergedSoftwarePack(obsPath)`：

- 从 OBS `downloadObject` 流式拷贝到临时文件，补齐原始设计"从OBS下载流式扫描"的意图
- **防御性硬上限**：`copyStreamWithLimit` 拷贝超过 `maxPackSize` 上限即中止并返回 -1——防止 Redis 累计大小计数被并发分片绕过后，异常大文件撑爆临时盘
- **失败关闭**：下载失败 / IO 异常 / 中断 / 校验不通过，一律视为校验失败 → 调用方 `deleteObject` 删除已合并 OBS 对象 + `cleanupChunkSession` 清理 Redis 会话 + 返回失败，不留孤儿对象
- **已知局限（统一 fail-closed）**：瞬时故障（OBS 下载超时/连接重置、Semaphore acquire 被中断）与用户侧可归因的校验不通过走同一清理链——瞬时故障场景已合并对象被删、分片会话被清，用户无法仅重传最后一片，需从首片整包重传。当前版本接受该取舍（实现简单、不留任何不可跟踪的残留数据）；后续可增强为分流处理：瞬时 IO/中断保留分片会话允许重试合并，仅校验不通过才删对象 + 清会话
- **并发控制**：`Semaphore(2)`（`MERGED_PACK_SCAN_CONCURRENCY`）限制同时扫描数，防止批量并发合并打满 OBS 下载带宽；acquire 被中断时恢复中断标志并 fail-closed
- 日志中 obsPath 经 `LogSanitizer.sanitize` 处理

### 2.5 不做的部分

- 嵌套 zip 炸弹（42.zip 类）递归扫描：顶层中央目录无法观测内层条目，需解压侧控制兜底；如需可作为后续增强
- 条目声明大小为 0 的绕过（data descriptor / 通用标志位 bit 3）：zip 允许条目在中央目录将解压大小写为 0 而实际 deflate 流极大，多数解压工具会 inflate 到流结束而非按声明大小截断——此时顶层解压总量与压缩比校验均被绕过（累计为 0），与嵌套炸弹属同类遗漏，需解压侧控制兜底。后续可增强：拒绝 `size == 0 && compressedSize > 0` 的条目 + 增加单条目压缩比上限

## 3. 测试策略

1. 工具级（`ZipSecurityCheckUtilTest`）：正常 zip 通过 / 魔数+垃圾非法 zip 拒绝 / 空条目拒绝 / 高压缩比（zeros，ratio>1000）拒绝 / 条目数超限拒绝 / 解压总大小超限拒绝
2. 服务级（`ToolApplyServiceImplTest`）：整片与分片路径炸弹被拒；分片合并后炸弹 → 断言 `deleteObject` + 会话清理被调用；合并后非法 zip 同样拒绝
3. 现有 at-limit 用例由伪 zip（魔数+全零，无法通过中央目录校验）改为真实 zip 构造
4. 回归：`python scripts/run-mvn.py spotless:apply test -Dtest=ZipSecurityCheckUtilTest,ToolApplyServiceImplTest`（实测 spotless 0 修正，60 个测试 0 失败 0 错误）
