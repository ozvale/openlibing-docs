# 【openLiBing-Sbom】支持spdx3.0格式的sbom数据导出 — 详细设计

---

## 1. 方案设计

### 1.1 方案概述

新增 `Spdx3Writer`（实现 `SbomWriter` 接口），复用现有 `SpdxWriter` 生成 SPDX 2.2 JSON，经 externalRefs 兼容预处理后，调用 tools-java `SpdxConverter` 转换为 SPDX 3.0.1 JSON-LD 格式输出。

同时新增 `GET /sbom-api/exportSbomOptions` 端点，前端可动态获取 exportSbom 接口支持的合法 spec/specVersion/format 参数组合。

### 1.2 整体流程

```
Client (GET /sbom-api/exportSbom?spec=spdx&specVersion=3.0.1&format=json)
  │
  ▼
SbomController.exportSbom()
  │  调用 sbomService.writeSbom(productName, spec, specVersion, format)
  ▼
SbomServiceImpl.writeSbom()
  │  ① 校验 format 在 EXT_TO_FORMAT 中
  │  ② 校验 spec + specVersion 在 SbomSpecification 枚举中
  │  ③ WRITER_KEY_MAP 查路由: SPDX_3_0_1 → "SPDX3"
  │  ④ getSbomWriter("SPDX3") → Spdx3Writer.write(productName, format)
  ▼
Spdx3Writer.write()
  │  ① format guard: 非 JSON 立即抛异常
  │  ② 委托 spdxWriter.write(productName, JSON) → SPDX 2.2 JSON byte[]
  │  ③ processExternalRefsForSpdx3() → 时间戳归一化 + externalRefs 映射
  │  ④ convertSpdx2ToSpdx3() → 临时文件 → tools-java SpdxConverter → JSON-LD
  │  ⑤ 返回 byte[] 给 Controller 写 response stream
  ▼
Client 下载文件 (productName-SPDX-3.0.1-sbom.json)
```

### 1.3 架构决策

| 决策 | 结论 | 原因 |
|------|------|------|
| 实现方式 | 独立 `Spdx3Writer`，非在 `SbomServiceImpl` 内分支判断 | 保持统一 `getSbomWriter().write()` 路由模式 |
| 转换策略 | 先 2.2 后转换的两步策略 | tools-java 仅支持文件级转换、externalRefs 需预处理 |
| externalRefs 映射 | 5 种非标准类型 → OTHER/OTHER，原始信息存 comment | SPDX 3.0.1 规范对 referenceCategory/type 有严格约束 |
| 时间戳归一化 | 正则 `\.\d+Z$` → `Z` 去毫秒 | tools-java SpdxConverter 高精度时间戳解析失败 |
| format guard | write() 入口校验非 JSON 抛异常 | 提前拦截而非静默忽略，避免调用方误解 |
| exportSbomOptions | 独立端点 + 枚举 getter 取值 | 前后端枚举同步，新增枚举值时仅需加一行 |

---

## 2. 实现逻辑设计

### 2.1 Spdx3Writer.write() 三步流程

```
Step 1: 生成 SPDX 2.2 JSON
  spdxWriter.write(productName, JSON)
    → SbomRepository.findByProductNameWithPackages()
    → 装配 SpdxDocument → SbomMapperUtil.writeAsBytes() → byte[]

Step 2: externalRefs 预处理 (内存 JSON 树)
  processExternalRefsForSpdx3(spdx22Json)
    → JSON_MAPPER.readTree() 解析为 JsonNode
    → normalizeCreationTimestamp(root): 正则去毫秒
    → 遍历 packages[].externalRefs[]:
        if category ∈ NON_STANDARD_CATEGORIES
          → ref.put("referenceCategory", "OTHER")
          → ref.put("referenceType", "OTHER")
        → ref.put("comment", "v2_refCategory=...(原值);v2_refType=...(原值)")
    → JSON_MAPPER.writerWithDefaultPrettyPrinter().writeValueAsBytes() 回写

Step 3: tools-java 转换 SPDX 2.2 → 3.0.1 JSON-LD
  convertSpdx2ToSpdx3(processed)
    → Files.createTempFile("spdx22-", ".spdx.json")  写入 2.2 JSON
    → Files.createTempFile("spdx301-", ".jsonld")    先 deleteIfExists
    → SpdxConverter.convert(from, to, JSON, JSONLD, true)
    → Files.readAllBytes(toPath) → 返回结果
    → finally: 清理两个临时文件
```

### 2.2 format guard 逻辑

```
Spdx3Writer.write(productName, format)
  if format != SbomFormat.JSON
    → throw SbomRuntimeException("Spdx3Writer only supports JSON format")
  // 后续正常流程...
```

### 2.3 exportSbomOptions 组装逻辑

```
SbomServiceImpl.getExportSbomOptions()
  → List.of(
      SPDX_2_2.getSpecification() + SPDX_2_2.getVersion() + JSON.getFileExtName(),
      SPDX_2_2.getSpecification() + SPDX_2_2.getVersion() + XML.getFileExtName(),
      SPDX_2_2.getSpecification() + SPDX_2_2.getVersion() + YAML.getFileExtName(),
      SPDX_3_0_1.getSpecification() + SPDX_3_0_1.getVersion() + JSON.getFileExtName(),
      CYCLONEDX_1_4.getSpecification() + CYCLONEDX_1_4.getVersion() + JSON.getFileExtName(),
      CYCLONEDX_1_4.getSpecification() + CYCLONEDX_1_4.getVersion() + XML.getFileExtName(),
      CYCLONEDX_1_4.getSpecification() + CYCLONEDX_1_4.getVersion() + YAML.getFileExtName()
    )
  // RDF 排除: toRdfBytes() 抛 Not implemented
  // SWID 排除: getVersion() = null, 无 writer
```

### 2.4 非标准 externalRefs 映射表

| 原始 category | 转换后 category | 转换后 type | comment 存原始值 |
|---------------|-----------------|-------------|-------------------|
| EXTERNAL_MANAGER | OTHER | OTHER | v2_refCategory=EXTERNAL_MANAGER;v2_refType=(原) |
| PROVIDE_MANAGER | OTHER | OTHER | 同上 |
| RELATIONSHIP_MANAGER | OTHER | OTHER | 同上 |
| SOURCE_MANAGER | OTHER | OTHER | 同上 |
| PERSISTENT_ID | OTHER | OTHER | 同上 |
| 其他标准类型 | 不修改 | 不修改 | 仅记录 comment |

---

## 3. 类设计

### 3.1 新增类

#### Spdx3Writer

| 属性 | 说明 |
|------|------|
| 全限定名 | `org.opensourceway.sbom.service.writer.impl.spdx.Spdx3Writer` |
| 继承/实现 | `implements SbomWriter` |
| Spring 注解 | `@Service(value = SbomConstants.SPDX3_NAME + SbomConstants.WRITER_NAME)` → `@Service("SPDX3writer")` |
| 职责 | SPDX 3.0.1 格式 SBOM 导出 |
| 依赖 | `@Autowired SpdxWriter spdxWriter` |

**方法清单：**

| 方法 | 可见性 | 说明 |
|------|--------|------|
| `write(String, SbomFormat) → byte[]` | public | 导出入口，三步流程 + format guard |
| `writePackage(String, String, String, SbomFormat) → byte[]` | public | 未实现，抛 SbomRuntimeException |
| `processExternalRefsForSpdx3(byte[]) → byte[]` | private | externalRefs 预处理（时间戳归一化 + 类型映射） |
| `normalizeCreationTimestamp(JsonNode) → void` | private | 时间戳高精度归一到秒 |
| `processExternalRef(ObjectNode) → void` | private | 单个 externalRef 映射 |
| `convertSpdx2ToSpdx3(byte[]) → byte[]` | private | 调用 tools-java SpdxConverter |

**类常量：**

| 常量 | 类型 | 说明 |
|------|------|------|
| `NON_STANDARD_CATEGORIES` | `Set<String>` | 需映射的非标准 externalRef 类型集合（5 种） |
| `JSON_MAPPER` | `ObjectMapper` | Jackson JSON 解析器 |

#### SbomExportOptionVo

| 属性 | 说明 |
|------|------|
| 全限定名 | `org.opensourceway.sbom.model.pojo.vo.sbom.SbomExportOptionVo` |
| 继承/实现 | `implements Serializable` |
| 职责 | exportSbom 合法参数组合的响应 VO |

**字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `spec` | `String` | 规范名称 (SPDX / CycloneDX) |
| `specVersion` | `String` | 规范版本 (2.2 / 3.0.1 / 1.4) |
| `format` | `String` | 文件格式 (json / xml / yaml) |

### 3.2 修改的类

| 类 | 修改内容 |
|----|---------|
| `SbomSpecification` | 新增 `SPDX_3_0_1(SbomConstants.SPDX_NAME, "3.0.1", SpdxDocument.class)` 枚举值 |
| `SbomConstants` | 新增 `SPDX3_NAME = "SPDX3"` 常量 |
| `SbomContentType` | 新增 `SPDX_3_0_1_JSON_SBOM` + findBySpecAndFormat 分支 |
| `ReferenceType` | 新增 `OTHER("other")` |
| `SbomService` (接口) | 新增 `List<SbomExportOptionVo> getExportSbomOptions()` 方法声明 |
| `SbomServiceImpl` | 新增 `WRITER_KEY_MAP` 静态映射；新增 `getExportSbomOptions()` 方法实现 |
| `SbomController` | 导出文件名增加 specVersion 字段；新增 `GET /sbom-api/exportSbomOptions` 端点 |
| `SbomRepository` | 补充类级 Javadoc 和 @param/@return |

---

## 4. 数据模型设计

### 4.1 数据库

**本次需求不涉及数据库 schema 变更。**

导出流程读取已有表结构：

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `sbom` | SBOM 元数据 | id, product_id (外键), name, data_license, namespace, created |
| `package` | 软件包信息 | sbom_id (外键), name, version, external_refs |
| `file` | 文件信息 | sbom_id (外键), name, checksum |
| `sbom_element_relationship` | 元素关系 | sbom_id (外键), source_element_id, target_element_id, relationship_type |

SpdxWriter 通过 `SbomRepository.findByProductNameWithPackages()` 一次性加载 Sbom 及其 packages 集合，其余子集合通过 Hibernate `@BatchSize` 批量加载。

### 4.2 枚举类

#### SbomSpecification 新增值

```java
SPDX_3_0_1(SbomConstants.SPDX_NAME, "3.0.1", SpdxDocument.class)
```

- `specification = "SPDX"`, `version = "3.0.1"`
- `documentClass = SpdxDocument.class`（复用 SPDX 2.2 的文档实体类，exportSbom 场景仅用于路由查找）

#### SbomContentType 新增值

```java
SPDX_3_0_1_JSON_SBOM("SPDX_3_0_1_JSON_SBOM")
```

#### ReferenceType 新增值

```java
OTHER("other")
```

### 4.3 VO 类

#### SbomExportOptionVo

| 字段 | 类型 | 示例值 |
|------|------|--------|
| `spec` | `String` | `"SPDX"` / `"CycloneDX"` |
| `specVersion` | `String` | `"2.2"` / `"3.0.1"` / `"1.4"` |
| `format` | `String` | `"json"` / `"xml"` / `"yaml"` |

---

## 5. 性能设计

### 5.1 性能目标

| 接口 | 目标 | 说明 |
|------|------|------|
| `GET /sbom-api/exportSbom` (SPDX 3.0.1) | ≤ 3s | 新 spec 组合，首个请求含 tools-java 冷启动 |
| `GET /sbom-api/exportSbom` (SPDX 2.2, 已有) | ≤ 3s | 不受本次改动影响 |
| `GET /sbom-api/exportSbomOptions` | ≤ 50ms | 纯内存枚举拼接，无 I/O |

### 5.2 数据库索引

- 复用已有索引：`sbom` 表 `product_id_uk`（`product_id` 唯一索引），`SbomRepository.findByProductName()` 通过 `product.name` 关联查询，`product` 表 `name` 字段有唯一约束
- 导出场景专用方法 `findByProductNameWithPackages()` 使用 `@EntityGraph(attributePaths = {"packages"})` 预加载 packages，避免 N+1 查询
- 本次不新增索引

### 5.3 SQL 语句优化

- SpdxWriter 装配阶段使用 `@EntityGraph` 批量加载 packages，其余子集合（files、relationships）通过 Hibernate `@BatchSize` 批量加载
- 不存在循环内逐条查询，一次性 entity graph 加载完成数据获取

### 5.4 内存优化

- `processExternalRefsForSpdx3()` 使用 Jackson `JsonNode` 树模型解析，对中等规模 SBOM（<100 packages）内存开销在 MB 级
- 超大 SBOM（>1000 packages）场景：树模型解析可能导致 10+ MB 内存峰值，后续可考虑 Jackson Streaming API
- 临时文件在 finally 块中 `deleteIfExists` 确保清理，不残留磁盘文件

### 5.5 缓存

- **无缓存**：exportSbom 为实时导出接口，SBOM 数据每次需从 DB 刷新获取最新制品清单，不适合缓存
- 未来如果导出请求频繁且数据变更低频，可考虑：产品级别 SBOM 写入后标记版本号，导出接口根据版本号判断是否命中缓存

### 5.6 分布式并行处理

- 不涉及：exportSbom 为同步请求-响应模式，业务语义要求即时返回完整数据

### 5.7 异步处理

- 不涉及：导出请求是用户直接下载文件，需同步等待结果
- 前后端通过 HTTP Response Streaming 直接写入 `OutputStream`，不经过磁盘中转

### 5.8 算法优化

- 时间戳归一化：单次正则 `replaceFirst`，O(n) 复杂度
- externalRefs 遍历：每个 package 的每个 externalRef 做常数级处理（category 判断 + put），O(p * r)（p=package 数, r=externalRef 数/package）
- tools-java SpdxConverter：依赖第三方库内部实现，已验证为单文件全量读取-转换-写出模式

### 5.9 导出接口各阶段耗时分布（实测参考）

| 阶段 | 典型耗时 | 说明 |
|------|---------|------|
| SpdxWriter 装配 + 序列化 | 200-500ms | DB 查询 + 实体转换 + JSON 序列化 |
| externalRefs 预处理 | 50-200ms | JSON 树解析 + externalRefs 遍历 |
| SpdxConverter 转换 | 500-1500ms | tools-java 文件级 2.2 → 3.0.1 转换（含 I/O） |
| **Total** | **750-2200ms** | 3s 目标内 |

---

## 6. API 接口设计

### 6.1 导出 SBOM（已有接口，本次扩展参数组合）

| 属性 | 值 |
|------|----|
| URL | `GET /sbom-api/exportSbom` |
| 认证 | 继承项目已有鉴权逻辑 |
| Tags | 关键接口 |

**请求参数（query string）：**

| 参数 | 类型 | 必填 | 说明 | 新增组合 |
|------|------|------|------|----------|
| `productName` | `String` | 是 | 产品名称 | 不变 |
| `spec` | `String` | 是 | 规范名称 | 原支持 `spdx`/`cyclonedx` |
| `specVersion` | `String` | 是 | 规范版本 | **新增** `3.0.1` (组合 spec=spdx) |
| `format` | `String` | 是 | 文件格式 | 仅 `json` (SPDX 3.0.1 限制) |

**新增合法组合：**

```
spec=spdx, specVersion=3.0.1, format=json
```

**参数校验规则：**

1. `format` 必须在 `SbomFormat.EXT_TO_FORMAT` 中存在
2. `spec` + `specVersion` 必须在 `SbomSpecification.findSpecification()` 中找到
3. 路由查 `WRITER_KEY_MAP`：`SPDX_3_0_1 → "SPDX3"`，否则用 `specification.getSpecification()`（即 `SPDX` 查 `SpdxWriter`）
4. `Spdx3Writer.write()` 入口额外校验 format 必须为 JSON

**响应：**

| 场景 | Content-Type | 响应 |
|------|-------------|------|
| 成功 | `application/octet-stream` | Content-Disposition 含文件名 `{productName}-SPDX-3.0.1-sbom.json`，body 为 SPDX 3.0.1 JSON-LD |
| 参数错误 | `text/plain` | 错误消息字符串（如 "export sbom metadata failed"） |
| format 不是 json | — | 抛出 `SbomRuntimeException("Spdx3Writer only supports JSON format")` |

**文件名规则：**

```
格式: {productName}-{spec}-{specVersion}-sbom.{fileExt}
示例: myProduct-SPDX-3.0.1-sbom.json
```

### 6.2 查询合法参数组合（新增接口）

| 属性 | 值 |
|------|----|
| URL | `GET /sbom-api/exportSbomOptions` |
| 方法 | `GET` |
| 认证 | 继承项目已有鉴权逻辑 |
| Tags | 关键接口 |
| Content-Type | `application/json` |

**请求参数：** 无

**响应格式：**

```json
[
  {"spec": "SPDX", "specVersion": "2.2", "format": "json"},
  {"spec": "SPDX", "specVersion": "2.2", "format": "xml"},
  {"spec": "SPDX", "specVersion": "2.2", "format": "yaml"},
  {"spec": "SPDX", "specVersion": "3.0.1", "format": "json"},
  {"spec": "CycloneDX", "specVersion": "1.4", "format": "json"},
  {"spec": "CycloneDX", "specVersion": "1.4", "format": "xml"},
  {"spec": "CycloneDX", "specVersion": "1.4", "format": "yaml"}
]
```

**HTTP Status：**
| 状态 | 场景 |
|------|------|
| 200 | 成功返回列表 |
| 500 | 服务内部异常 |
| 403 | 未认证 |

**性能指标：**

| 指标 | 目标值 |
|------|-------|
| 平均延迟 | < 10ms |
| P99 延迟 | < 50ms |
| QPS 支持 | > 1000（纯内存操作） |

---

## 7. 安全设计

### 7.1 鉴权

- **继承原有鉴权逻辑**：exportSbom 和 exportSbomOptions 接口通过项目已有安全框架进行认证鉴权，不引入新的安全机制
- MbomController 类级未单独配置 `@PreAuthorize` 注解的场景，通过网关或 Filter 层统一拦截
- 未认证请求返回 403 Forbidden

### 7.2 敏感信息保护

**日志打印：**

- `SbomController.exportSbom()` 日志仅打印 `productName`、`spec`、`specVersion`、`format`，不打印请求体内容
- `Spdx3Writer` 各阶段日志仅打印耗时（ms）和数据大小（KB），不打印 JSON 内容
- `SbomServiceImpl.writeSbom()` 日志仅打印 spec/specVersion/format/cost，不打印导出内容
- `Spdx3Writer` 日志中使用 `{}` 占位符而非字符串拼接，避免敏感值被误拼接

**明文存储：**

- 不涉及：本次需求不修改数据库 schema，不新增存储字段
- SPI 3.0.1 导出产物为内存 byte[] 和临时文件，finally 块确保删除，不在磁盘残留

**可下载性：**

- 导出接口本身即下载用途，仅对已认证且有权限用户开放

### 7.3 硬编码防范

| 检查项 | 结果 |
|--------|------|
| appKey | 无硬编码 |
| token | 无硬编码，使用 `GC_TOKEN` 环境变量 |
| cookie | 无硬编码 |
| 数据库密码 | 通过 `application.properties` 占位符注入，无硬编码 |

### 7.4 审计日志

- `writeSbomFile()` 通过 `@LogApi(operationModule = OPERATION_MODULE_SBOM, operation = EXPORT_SBOM_FILE)` 记录操作审计
- `writeSbom()` 通过 `@LogApi(operationModule = OPERATION_MODULE_SBOM, operation = EXPORT_SBOM, isExport = true)` 记录导出操作审计，含 `isExport = true` 标识
- `exportSbomOptions` 为纯查询接口，无副作用，不记录审计日志（符合项目惯例）
- 操作记录包含：操作模块、操作类型、用户 ID、时间戳、请求来源 IP（由 `LogApi` AOP 切面统一拦截）

### 7.5 输入校验

- `format` 参数在 `SbomServiceImpl.writeSbom()` 中校验 `EXT_TO_FORMAT` 合法性
- `spec` + `specVersion` 在 `SbomServiceImpl.writeSbom()` 中校验 `SbomSpecification.findSpecification()` 合法性
- `productName` 在 SpdxWriter 中通过 `findByProductNameWithPackages()` 查询，不存在抛 RuntimeException
- 时间戳格式：`created` 字段经正则 `replaceFirst` 归一化，正则输入为 SPi 2.2 JSON 标准格式，不涉及用户外部输入
- externalRefs JSON 解析使用 Jackson 标准 API，不涉及 XSS/注入风险
- `Spdx3Writer.format guard` 在入口层捕获参数错误，避免非法 format 值流入转换流程

### 7.6 文件安全

- 临时文件命名使用 `Files.createTempFile("spdx22-", ".spdx.json")`，由 JVM 自动管理前缀后缀，不涉及用户输入拼接
- 临时文件在 finally 块中删除，异常路径也确保清理
- 不涉及文件上传

---

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| `org.spdx:tools-java` | 2.0.6 | SPDX 2.2 → 3.0.1 文件级转换 |
| `org.spdx:java-spdx-library` | 2.0.3 | SPDX 模型注册（SpdxModelFactory.init()） |
| Jackson ObjectMapper | Spring Boot 内置 | JSON 树解析 + externalRefs 预处理 |
| Spring Data JPA | Spring Boot 内置 | 实体查询 + EntityGraph |
| Hibernate | Spring Boot 内置 | 批量加载 + ORM |

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| tools-java 未来升级 API 变更 | 锁定版本 2.0.6 in pom.xml |
| 临时文件残留 | finally 块中 deleteIfExists，异常路径也确保清理 |
| SpdxConverter 要求输出文件不存在 | createTempFile 后立即 deleteIfExists(toPath) |
| 超大 SBOM JSON 树解析内存 | 中等规模 (<100 packages) 用树模型；超大场景可改为 Streaming API |
| 时间戳精度兼容性 | 正则 replaceFirst 去毫秒，仅修改 Z 结尾时间戳 |

## 跨仓影响

无。
