# 【openLiBing-Sbom】支持spdx3.0格式的sbom数据导出

## 需求背景
SPDX 3.0 于 2023 年正式发布，相比 2.3 版本在依赖模型、机器友好性、扩展性方面有质的飞跃。美国行政令 14028、中国《软件供应链安全要求》(2025 版)、欧盟 DSA 均要求或建议采用 SPDX 3.0 格式。当前 openlibing-sbom 仅支持 SPDX 2.2 格式导出，需新增 SPDX 3.0.1 格式支持。

## 功能描述
- 复用现有 `/sbom-api/exportSbom` 接口，新增 `spec=spdx, specVersion=3.0.1, format=json` 参数组合
- 内部流程：Spdx3Writer 委托 SpdxWriter 按 SPDX 2.2 格式从 DB 装配数据生成 JSON → 时间戳归一化 (`.000Z` → `Z`) → externalRefs 非标准类型映射为 OTHER → 调用 tools-java SpdxConverter 转换为 SPDX 3.0.1 JSON-LD
- 非标准外部引用类型 (EXTERNAL_MANAGER/PROVIDE_MANAGER/RELATIONSHIP_MANAGER/SOURCE_MANAGER/PERSISTENT_ID) 在转换前映射为 OTHER/OTHER，原类型信息保留在 comment 字段
- 所有导出下载文件名增加 specVersion 字段，便于区分 SPDX 2.2 与 3.0.1 导出
- 新增 `GET /sbom-api/exportSbomOptions` 端点，返回 exportSbom 接口支持的所有合法 spec/specVersion/format 组合（从 SbomSpecification / SbomFormat 枚举 getter 取值）
- Spdx3Writer.write() 增加 format 校验，非 JSON 时抛出 SbomRuntimeException

## 不做什么
- 不新增接口，复用现有 exportSbom
- 不修改数据库 schema
- 不支持 SPDX 3.0.1 的 XML/YAML/RDF 格式（仅 JSON）
- 不修改 SBOM 导入流程

## 验收标准
- [x] 调用 exportSbom 接口传入 spec=spdx, specVersion=3.0.1, format=json 返回有效的 SPDX 3.0.1 JSON-LD 文件
- [x] 结果文件中的 externalRefs 非标准类型已映射为 OTHER，comment 保留原始类型信息
- [x] 现有 SPDX 2.2 导出功能不受影响（669 tests 通过无回归）
- [x] 导出文件名包含 specVersion（如 `product-SPDX-3.0.1-sbom.json`）
- [x] exportSbom 接口传入非 JSON format 时返回错误而非静默忽略
- [x] GET /sbom-api/exportSbomOptions 正确返回 7 个合法组合（SPDX 2.2 json/xml/yaml + SPDX 3.0.1 json + CycloneDX 1.4 json/xml/yaml）

## 影响范围
| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../SbomConstants.java` | 修改 | 新增 SPDX3_NAME 常量 |
| `model/.../SbomSpecification.java` | 修改 | 新增 SPDX_3_0_1 枚举 |
| `model/.../SbomContentType.java` | 修改 | 新增 SPDX_3_0_1_JSON_SBOM 类型 |
| `model/.../ReferenceType.java` | 修改 | 新增 OTHER 枚举值 |
| `sbom-web/.../Spdx3Writer.java` | **新增** | SPDX 3.0.1 导出核心逻辑 |
| `sbom-web/.../SpdxWriterNew.java` | 保留 | 骨架代码（无 @Service，未启用） |
| `sbom-web/.../SbomServiceImpl.java` | 修改 | 增加 WRITER_KEY_MAP 路由映射 + exportSbomOptions 查询方法 |
| `sbom-web/.../SbomController.java` | 修改 | 下载文件名增加 specVersion + 新增 GET /exportSbomOptions 端点 |
| `sbom-web/.../SbomService.java` | 修改 | 新增 getExportSbomOptions() 接口方法 |
| `model/.../SbomExportOptionVo.java` | **新增** | exportSbomOptions 返回 VO |
| `dao/.../SbomRepository.java` | 修改 | 补充 Javadoc |
| `pom.xml` + `sbom-web/pom.xml` | 修改 | 新增 tools-java:2.0.6 依赖 |
