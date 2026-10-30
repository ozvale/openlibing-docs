# 【openlibing-sbom】批量安全整改加固（Argus 扫描 + 威胁模型）— EDEVOPS 设计文档

---

## 0. 交付追溯

| PR                                                              | 分支流                                                 | 状态                | 闭环 Issue                                                                                                                                             |
| --------------------------------------------------------------- | ------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [#165](https://gitcode.com/openlibing/openlibing-sbom/pull/165) | `fix-argus-security-issues` → `release_20261029_iter2` | merged (2026-10-27) | Fixes #86；Refs #151 #153 #155 #157 #159 #160 #162                                                                                                     |
| [#168](https://gitcode.com/openlibing/openlibing-sbom/pull/168) | `fix_threat_problems` → `release_20261029_iter2`       | merged              | Refs #98 #99 #104 #107 #111 #117 #118 #119 #122 #124 #131 #134 #137 #140 #144（#137 为 #117 同缺陷重复报告，随 `8aee1722` 一并闭环）+ 1 个 feat commit |

---

## 1. 方案设计

### 1.1 背景

openlibing-sbom 服务经 Argus 安全扫描与威胁模型分析，累计发现 20+ 项安全缺陷，集中在五类风险：

1. **资源耗尽类**：GZIP 解压炸弹、解压内存放大、无上限分页、ReDoS 正则回溯
2. **注入类**：HTTP 响应头注入（Content-Disposition）、路径穿越/条件性 SSRF（purl 出口 URL）、XXE
3. **信息泄露类**：异常消息透出内部实现、日志泄露凭据/下载签名、误提交制品与测试归档含密钥
4. **供应链类**：Quartz 2.5.0-rc1 非正式版本、log4j 硬编码版本绕过 BOM 治理
5. **输入校验缺失类**：addProduct 空产品名、重复产品 productType 冲突报错不明确

### 1.2 方案概述

分两个 PR 批次整改，统一遵循"入口校验 → 解析限流 → 出口编码 → 日志脱敏 → 异常收敛"五层防线原则，不改变对外 API 契约（除删除不可达死端点外），全部行为变化配套单元测试。

- **PR #165**：Argus 扫描问题专项（I/L/M 级）+ SENINFO 密钥泄露
- **PR #168**：威胁模型加固批次一（P1/P2 级）+ 巡检修复批次二（泄露/卫生类）

### 1.3 五层防线架构

```
外部输入（SBOM 文件 / purl / 分页参数 / 文件名参数）
    │
    ▼
┌─ L1 入口校验 ──────────────────────────────────────────┐
│ #144 productName 非空校验                              │
│ #118 分页 pageSize 上限 100（@Max(100) / DTO 钳制）    │
│ #151 purl name/revision 拒绝 ../、裸 .. 段、?/# 元字符  │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ L2 解析限流 ──────────────────────────────────────────┐
│ #153/#98 GZIP 双上界 min(256MB, 压缩体×100) 超限即中止 │
│ #119 copyright 正则 >5000 字符跳过解析（防 ReDoS）      │
│ spring.codec.max-in-memory-size 256MB 解码缓冲上限     │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ L3 出口编码 ──────────────────────────────────────────┐
│ #111 exportPackageSbom 文件名 packageName/version 编码 │
│ #131 Content-Disposition spec/specVersion/format 编码  │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ L4 日志与产物脱敏 ────────────────────────────────────┐
│ #98 签名 URI 只记路径不记签名参数 / Gitee 凭据掩码      │
│ #159 obs_meta 失败日志只输出条目名与长度               │
│ #117/#137 SignatureUtil 临时文件 finally 递归清理      │
│ #86/#134 删除误提交密钥制品                            │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ L5 异常收敛 ──────────────────────────────────────────┐
│ #124 全局异常处理器 + Controller 5 处固定文案           │
│ #140 删除不可达死接口                                   │
└────────────────────────────────────────────────────────┘
```

### 1.4 关键技术决策

| 决策点      | 选择                                                                                              | 原因                                                                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 解压上限    | 双上界 `min(256MB 配置值, 压缩体×100)`，边解压边累计超限即中止                                    | 仅设绝对上限无法防"小体积高压缩比"炸弹；压缩比 1:100 远高于合法 SBOM 文本，炸弹（可达 1:1000）必被拦截；边解压边判断避免先解压完再校验的内存峰值 |
| 解码缓冲    | `spring.codec.max-in-memory-size` 收敛 1024MB → 256MB 并配置化                                    | 降低出站响应解码内存放大风险；256MB 兼容大体积 SBOM 发布场景，各客户端统一 `@Value` 读取                                                         |
| 分页上限    | 查询参数 `@Max(100)` 返回 400，请求体 DTO setter `Math.min` 钳制                                  | `@RequestParam` 走 Bean Validation 直接拒绝；`@RequestBody` 钳制保证旧调用方兼容不报错                                                           |
| ReDoS 防护  | 保留正则结构，靠输入长度钳制（5000 字符）将有界回溯成本压至毫秒级                                 | 正则嵌套结构是业务解析所需，改写风险大于收益；钳制后最坏成本有界                                                                                 |
| 异常外露    | 仅 `SbomRuntimeException`（业务语义）与 `AddProductException.getShowMessage()` 透出，其余固定文案 | 业务异常消息是调用方流程判断依据；技术异常消息可能含类名/SQL/路径等内部实现                                                                      |
| Quartz 版本 | 删除硬编码 `quartz.version`，交 Spring Boot BOM 托管（2.5.2 GA）                                  | 消除 rc 版依赖与版本旁路，BOM 统一治理                                                                                                           |
| log4j 版本  | 删除显式 dependencyManagement 覆盖，交 Spring Boot BOM（2.25.5）                                  | 同上，防止镜像配置/显式覆盖绕过统一治理                                                                                                          |
| 死接口处置  | 直接删除而非补鉴权                                                                                | standalone MockMvc 实证 private 方法不被 Spring MVC 映射（404），属不可达死代码，删除消除误用风险                                                |

---

## 2. 实现逻辑设计

### 2.1 GZIP 解压双上界（#153 / #98，PR #165 + #168）

```
publishSbomFileWithCompress(request)
  │
  ├─ Base64 解码 → compressedData
  │
  ├─ decompressedLimit = min(publishMaxDecompressedSize(默认256MB),
  │                          compressedData.length × 100)
  │     ├─ ≤ 0 → 拒绝（配置非法或压缩体为空）
  │     └─ 边解压边累计 inflateBytes
  │           ├─ inflateBytes > decompressedLimit → 立即中止解压，返回失败
  │           └─ 正常完成 → 继续发布流程
```

配套测试：`testPublishSbomFileWithCompress_GzipBombRejected`（1MB 零字节，压缩比 ≈1:1000，命中压缩比分支）、`_InvalidConfigRejected`（配置 ≤0）、`_DecompressFailed`。

### 2.2 purl 出口 URL 防护（#151 / #98）

- **#151（OpenHarmonyThirdPartyUtil）**：`isInvalidUrlSegment(name/revision)` 拦截 `../`、裸 `..` 段、`?`、`#`，命中即拒绝拼接出站 URL，防路径穿越与条件性 SSRF（携带服务端凭据读取同宿主未授权资源）
- **#98（VcsServiceImpl.getOwnerRepo）**：http/https 按 scheme 切分丢弃 host[:port]；scp 风格取首个冒号后路径

### 2.3 分页上限钳制（#118）

```
9 个分页接口
  ├─ 6 处 @RequestParam page/pageSize → @Max(100)，越界返回 400
  └─ 3 处 @RequestBody DTO → setter 内 Math.min(pageSize, 100) 钳制
```

### 2.4 ReDoS 防护（#119）

```
queryCopyrightByPackageId
  ├─ COPYRIGHT_PATTERN / COPYRIGHT_CLEAN_PATTERN 提升为 static final 预编译
  └─ copyright 长度 > MAX_COPYRIGHT_PARSE_LENGTH(5000)
        → 跳过正则解析，logger.warn，返回空结果（最坏成本 ~100ms）
```

### 2.5 信息泄露收敛（#124 / #159 / #98）

| 泄露点                                                       | 收敛后行为                                                                                   |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| GlobalExceptionHandler.handleAllExceptions                   | `error="服务器内部错误"`，`msg="系统繁忙，请稍后重试"`，完整堆栈仅 `logger.error` 服务端记录 |
| SbomController 3 处（UUID 解析/queryScanStatus/refreshSbom） | 固定文案，保留 `SbomRuntimeException` 业务消息透出                                           |
| ApigController UUID 解析                                     | 固定文案                                                                                     |
| publishSbomFile 非业务异常                                   | 固定 `publish sbom failed!`                                                                  |
| RepoMetaParserImpl obs_meta 失败日志                         | 仅输出条目名与 `fileContent.length()`，不输出内容                                            |
| GiteeApi 归档下载日志                                        | 只记路径部分，不记含签名的 redirect URI                                                      |
| gitUrl 凭据                                                  | `AddProductRequest.setGitUrl` 入口正则去除 userinfo，对象内不再持有凭据                      |

### 2.6 异常处理

| 场景                                                | 处理                                                                                                    |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 解压超限                                            | 返回 `decompress sbom content failed!`（HTTP 202 + success=false），服务端 error 日志                   |
| 分页参数越界（@Max）                                | Bean Validation → 400 `参数验证失败`                                                                    |
| addProduct 空产品名（#144）                         | `AddProductException("product name is required")`，`verify(productTypeRepository, never()).lockTable()` |
| 重复 addProduct productType 冲突（feat `0981aa92`） | 返回专用冲突报错，与"已存在"区分                                                                        |
| 签名失败                                            | finally 块递归清理临时目录与签名文件后再抛出                                                            |

---

## 3. 类设计

### 3.1 修改类清单

| 类                                                          | 变更                                                                                                                    | PR        |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------- |
| `SbomController`                                            | GZIP 双上界限流；5 处文件名拼接 URLEncoder；3 处异常固定文案；删除 2 个 private 死接口与 MAX_SIZE 常量                  | #165/#168 |
| `ApigController`                                            | UUID 解析固定文案；2 处文件名编码                                                                                       | #168      |
| `GlobalExceptionHandler`                                    | handleAllExceptions 对外固定文案 + 服务端完整堆栈日志                                                                   | #168      |
| `SbomServiceImpl`                                           | copyright 长度钳制 + 正则预编译；addProduct productName 非空校验                                                        | #168      |
| `SignatureUtil`                                             | 签名临时目录/签名文件 finally 块递归清理                                                                                | #168      |
| `Mapper` (utils)                                            | initMapper 增加 XXE 三项加固（SUPPORT_DTD=false / EXTERNAL_ENTITIES=false / SECURE_PROCESSING），与 initSbomMapper 对齐 | #165      |
| `OpenHarmonyThirdPartyUtil`                                 | 新增 isInvalidUrlSegment 校验，拼接前拦截遍历与元字符                                                                   | #165      |
| `RepoMetaParserImpl`                                        | obs_meta 解析失败日志只输出条目名与长度                                                                                 | #165      |
| `WebUtil` / `GiteeApi` / `GitCodeApi` / `LicenseClientImpl` | max-in-memory-size 1024MB 硬编码 → `@Value` 配置化                                                                      | #165/#168 |
| `AddProductRequest`                                         | setGitUrl 入口 userinfo 凭据脱敏                                                                                        | #168      |
| `PublishSbomRequest` / `SbomFileLogHandler`                 | toString/snapshot 不含 sbomContent 大字段（审计日志配套）                                                               | 先前合入  |
| `VcsServiceImpl`                                            | getOwnerRepo owner/repo 提取加固                                                                                        | #168      |
| 9 个分页接口所在 Controller/DTO                             | @Max(100) / setter 钳制                                                                                                 | #168      |

### 3.2 新增测试类

| 测试类                                  | 覆盖                                           |
| --------------------------------------- | ---------------------------------------------- |
| `MapperXxeTest`                         | XXE 内部 DTD 实体回归（加固回退时用例必失败）  |
| `OpenHarmonyThirdPartyUtilTest`（扩展） | 遍历拦截 / query 注入 / URL 编码断言           |
| `SbomControllerTest`（扩展）            | GZIP 炸弹 / 配置边界 / 解压失败 / 固定文案断言 |
| `SbomServiceImplTest`（扩展）           | testAddProduct_BlankProductName                |

### 3.3 资源与制品清理

| 清理项                                                     | PR   |
| ---------------------------------------------------------- | ---- |
| doc/assert 下 3 个误提交制品                               | #168 |
| 含硬编码密钥的 openGauss tracer 测试归档（含 base64 副本） | #165 |
| 废弃端点 `fetchOpenEulerRepoMeta`（匿名访问 + 双路径竞态） | #165 |
| 不可达死接口 `/getPackageUrl`、`/query/package/info`       | #168 |

---

## 4. 配置设计

无数据库 schema 变更。配置项变化：

| 配置项                                | 变化                         | 说明                                             |
| ------------------------------------- | ---------------------------- | ------------------------------------------------ |
| `spring.codec.max-in-memory-size`     | 1024MB → 256MB               | WebClient 解码缓冲上限                           |
| `sbom.publish.max-decompressed-size`  | 新增，默认 268435456 (256MB) | 解压绝对上限，可按部署调优                       |
| `start-openlibing-sbom.sh`            | 首行新增 `umask 0027`        | JVM 落盘产物权限 0644 → 0640，防同机其他用户读取 |
| `quartz.version` 硬编码属性           | 删除                         | Spring Boot BOM 托管 → 2.5.2 GA                  |
| `log4j` api/core/slf4j2-impl 显式版本 | 删除                         | BOM 托管 2.25.3 → 2.25.5                         |

---

## 5. 性能设计

| 关注点                   | 评估                                                                            |
| ------------------------ | ------------------------------------------------------------------------------- |
| 解压限流开销             | 边解压边累计计数，O(1) 额外开销；超限立即中止避免全量解压内存峰值               |
| copyright 长度钳制       | >5000 字符跳过解析，将最坏回溯从分钟/小时级压至 ~100ms，同时消除大输入 CPU 放大 |
| 分页上限                 | pageSize ≤100 约束单页内存与 SQL 返回行数，消除 pageSize=10000 型内存放大       |
| max-in-memory-size 256MB | 出站响应解码峰值受控，防恶意大响应内存放大                                      |
| umask 0027               | 无运行时开销，仅影响新建文件权限位                                              |

---

## 6. API 接口设计

### 6.1 行为变化（对调用方可见）

| 接口                                                  | 变化                                                                                 | 兼容性                                      |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------- |
| `POST /sbom-api/publishSbomFileWithCompress`          | 超压缩比/超上限请求返回 `success=false, errorInfo="decompress sbom content failed!"` | 恶意请求被拒；正常 SBOM（压缩比 <<100）无感 |
| 9 个分页接口                                          | pageSize>100：@Max 类返回 400；DTO 类钳制为 100 继续执行                             | DTO 钳制路径向后兼容                        |
| `addProduct`（sbom-api/apig-api）                     | 空产品名返回 `product name is required`；重复产品 productType 冲突返回专用报错       | 脏数据被入口拒绝                            |
| 异常响应                                              | 除业务异常外均为固定文案                                                             | 调用方若依赖异常明文需改读服务端日志        |
| `GET .../fetchOpenEulerRepoMeta`                      | **下线**（原为匿名端点）                                                             | 已核实无生产调用方，定时任务链路不受影响    |
| `POST /sbom-api/getPackageUrl`、`/query/package/info` | **删除**                                                                             | 本为不可达死代码（404），无兼容性影响       |

### 6.2 导出接口文件名编码

`exportSbomFile` / `exportSbom` / `exportAllPackageSbom` 的 Content-Disposition 拼接参数（spec/specVersion/format/packageName/packageVersion）全部 `URLEncoder.encode`，恶意文件名不再可注入响应头。

---

## 7. 安全设计

### 7.1 威胁 → 防线映射总表

| Issue       | 威胁                                   | 等级    | 防线                                   | 修复 commit         |
| ----------- | -------------------------------------- | ------- | -------------------------------------- | ------------------- |
| #153 / #98  | GZIP 解压炸弹                          | M/P1    | 双上界限流                             | PR#165 / `0b901c52` |
| #98         | 解码内存放大                           | P1      | max-in-memory-size 256MB               | `0b901c52`          |
| #118        | 分页内存放大 DoS                       | P2      | pageSize max 100                       | `620e0a68`          |
| #119        | ReDoS                                  | P2      | 长度钳制 + 预编译                      | `e0097421`          |
| #151        | purl 路径穿越/条件性 SSRF              | M       | isInvalidUrlSegment                    | PR#165              |
| #98         | VCS 出口 URL 路径穿越/注入             | P1      | scheme 解析加固                        | `0b901c52`          |
| #111        | 响应头注入（exportPackageSbom）        | P2      | 文件名 URLEncoder                      | `ab4c375b`          |
| #131        | 响应头注入（Content-Disposition 5 处） | P2      | 全参数 URLEncoder                      | 批次二              |
| #157        | XXE                                    | L       | XML_MAPPER 三项加固                    | PR#165              |
| #132        | XXE（sbom-ort）                        | -       | 代码已随解关联移除，主仓 Mapper 已加固 | 不适用              |
| #124        | 异常消息信息泄露                       | P2      | 固定文案 + 服务端日志                  | 批次二              |
| #98         | 签名 URI 签名参数泄露                  | P1      | 日志只记路径                           | `0b901c52`          |
| #98         | Gitee 下载凭据外传                     | P1      | userinfo 掩码（`[^/@]+@`）             | `0b901c52`          |
| #159        | 日志放大                               | I       | 只记条目名与长度                       | PR#165              |
| #86 / #134  | 误提交密钥/制品                        | SENINFO | 制品删除                               | PR#165 / 批次二     |
| #117 / #137 | 签名临时文件残留                       | P2      | finally 递归清理                       | `8aee1722`          |
| #122        | 落盘权限过宽                           | P2      | umask 0027                             | 批次二              |
| #140        | 不可达死接口                           | P2      | 删除                                   | 批次二              |
| #155        | 废弃匿名端点 + 双路径竞态              | M       | 端点下线                               | PR#165              |
| #144        | 空产品名脏数据                         | P2      | 入口非空校验                           | 批次二              |
| #160        | Quartz rc 版供应链风险                 | I       | BOM 托管 2.5.2 GA                      | PR#165              |
| #162 / #143 | log4j 版本旁路                         | -       | BOM 统一治理                           | PR#165              |

### 7.2 PR 检视意见处置

**PR #165 已采纳**：purl 校验扩展为路径遍历 + URL 元字符折中方案；XXE 负向用例改为内部 DTD 实体并收窄断言；name 遍历用例改为 URL 捕获断言并新增 query 注入用例；修正 GZIP 炸弹用例注释与重复赋值。

**PR #165 暂不处理（另行跟进）**：解压内存放大（P3）；workflow 凭据面（api-scan/oss-pr-scan 的 `pull_request_target` 模式，master 带入的既有 workflow）；oss-version-scan ref 硬编码。

### 7.3 遗留项（未修复，待后续决策）

| Issue                   | 现状                                                                        |
| ----------------------- | --------------------------------------------------------------------------- |
| #158                    | Spring 解码器官方包名 shim 类仍在仓（默认 10MB），待删除                    |
| #95 #102 #103 #138 #156 | 横向鉴权缺陷群（userId 空白放行/可伪造、资源型端点无功能级授权），待专项    |
| #149                    | CI 管道不可信 PR 检出（P0）                                                 |
| #100                    | 测试弱口令 postgres/123456 入仓                                             |
| #105                    | 生产 Swagger UI 开启                                                        |
| #92                     | SpotBugs 路径穿越告警定性                                                   |
| #89 #90                 | SENINFO/SecBinaryCheck 扫描结果表（URL 均为合法依赖仓地址；CVE 依赖治理项） |
| #106 #130 #141          | 平台级共性问题（CSE 端点/springdoc/CSRF），转框架侧统一策略                 |

### 7.4 测试与验证证据

| 验证项                        | 结果                                                             |
| ----------------------------- | ---------------------------------------------------------------- |
| sbom-web 全量 UT              | 770/770 通过（含 GlobalExceptionHandlerTest 同步 `78ee64d1`）    |
| SbomServiceImplTest           | 111/111（含新增空产品名用例）                                    |
| SbomControllerTest            | 42/42（GZIP 炸弹/配置边界/固定文案）                             |
| MapperXxeTest                 | 2/2（XXE 内部 DTD 回归）                                         |
| OpenHarmonyThirdPartyUtilTest | 6/6（遍历拦截/query 注入/URL 编码）                              |
| log4j BOM 托管在线编译        | 2.25.5 正常解析                                                  |
| pre-commit 全链               | Spotless/CheckStyle/SpotBugs/PMD/secrets 通过                    |
| 死接口不可达实证              | standalone MockMvc（与生产同源 RequestMappingHandlerMapping）404 |

### 7.5 审计与日志

- 所有脱敏/限流/钳制命中点均有服务端日志（error/warn/info 分级），固定文案仅用于对外响应
- 完整异常堆栈仅服务端 `logger.error`，外部响应不含实现细节
- 签名/Gitee 凭据/下载签名等敏感值不出现在任何日志输出中
