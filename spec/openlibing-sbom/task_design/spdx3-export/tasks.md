# 【openLiBing-Sbom】支持spdx3.0格式的sbom数据导出 — 实现任务

## 进度: 11/11 complete

- [x] Task 1: 在 SbomSpecification 枚举中新增 SPDX_3_0_1 枚举值，新增 SbomConstants.SPDX3_NAME 常量
- [x] Task 2: 新增 Spdx3Writer（@Service("SPDX3writer")），实现 SbomWriter 接口，内部委托 SpdxWriter 生成 2.2 JSON → externalRefs 兼容处理 → tools-java 转 3.0.1 JSON-LD
- [x] Task 3: SbomServiceImpl 增加 WRITER_KEY_MAP 映射，将 SPDX_3_0_1 路由到 SPDX3writer
- [x] Task 4: 所有导出下载文件名增加 specVersion 字段
- [x] Task 5: 新增 ReferenceType.OTHER 枚举值 + SbomContentType.SPDX_3_0_1_JSON_SBOM
- [x] Task 6: 编译验证 + 全量测试通过（669 tests, 0 failures）
- [x] Task 7: 新增 Spdx3WriterTest + 更新 SbomServiceImplTest
- [x] Task 8: Spdx3Writer.write() 增加 format 校验，非 JSON 时抛出 SbomRuntimeException
- [x] Task 9: 新增 SbomExportOptionVo（spec/specVersion/format 三字段，从 SbomSpecification/SbomFormat 枚举 getter 取值）
- [x] Task 10: 新增 GET /sbom-api/exportSbomOptions 端点，返回合法 spec/specVersion/format 组合
- [x] Task 11: Codecheck 修复（Javadoc 补充、instanceof 守卫、未使用变量清理、重复 import 清理）
