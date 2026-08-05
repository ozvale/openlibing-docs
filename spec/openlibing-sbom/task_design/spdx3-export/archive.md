# 【openLiBing-Sbom】支持spdx3.0格式的sbom数据导出 — 归档

## 关联
- 业务 Issue: https://gitcode.com/openlibing/openlibing-sbom/issues/41
- 业务 PR: https://gitcode.com/openlibing/openlibing-sbom/merge_requests/87
- 目标分支: release_20260630_iter2
- FE 需求名称: 【openLiBing-Sbom】支持spdx3.0格式的sbom数据导出

## 交付历程

| commit | 说明 |
|--------|------|
| `2e51cc6e` | feat: 新增 SPDX_3_0_1 枚举 + REFERENCE_TYPE.OTHER + SbomServiceImpl 转换逻辑 |
| `b2c0edd2` | refactor: 移除冗余的 SPDX 3.0.1 format 校验 |
| `0b37d7c3` | refactor: 抽取 Spdx3Writer 为独立 Service，统一 writer 路由 |
| `5cf857c4` | fix: SpdxConverter 之前删除已存在的 temp 输出文件 |
| `cdbb1507` | feat: 下载文件名增加 specVersion |
| `192dddfe` | chore: 恢复 SpdxWriterNew 及测试类 |
| `f1a6d7be` | build: 新增 tools-java:2.0.6 依赖到 pom.xml |
| `0b27518` | feat(sbom): 新增 GET /sbom-api/exportSbomOptions 端点 + Spdx3Writer format 非 JSON 时抛异常 |
| `8a63d1a` | fix(spdx): Codecheck 修复（Javadoc 补充、instanceof 守卫、未使用变量） |
| `d53c5b9` | chore(sbom): 移除重复 HashMap/Map import |
| `d201e08` | fix(sbom): Codecheck 修复（SbomRepository 类级 Javadoc、@Operation 换行、toString 格式） |

## 用户自测反馈
- 发现 SpdxConverter 报 "output file already exists" 错误 → 修复 commit `5cf857c4`
- 要求恢复 SpdxWriterNew 测试类 → commit `192dddfe`
- 要求 NON_STANDARD_CATEGORIES 补充 RELATIONSHIP_MANAGER + SOURCE_MANAGER + PERSISTENT_ID
- 要求新增 exportSbom 合法参数组合查询接口 → 新增 GET /sbom-api/exportSbomOptions 端点
- 要求实现方式使用 SbomSpecification/SbomFormat 枚举 getter 而非硬编码字符串 → commit `d201e08` 改用枚举 getter

## 最终验证
- 编译: BUILD SUCCESS
- 全量单元测试: 669 tests, 0 failures, 0 errors
- PR CI: ci-pipeline-running (按流水线结果确认)

## 设计偏差与取舍
- **原计划删除 SpdxWriterNew → 实际保留**: 用户要求保留骨架代码，未注册 @Service 不影响功能
- **原计划在 SbomServiceImpl 内做 3.0.1 分支判断 → 改为独立 Spdx3Writer**: 保持统一的 `getSbomWriter().write()` 路由模式
- **NON_STANDARD_CATEGORIES 范围调整**: 初始仅 2 种 → 扩展为 5 种 (EXTERNAL_MANAGER / PROVIDE_MANAGER / RELATIONSHIP_MANAGER / SOURCE_MANAGER / PERSISTENT_ID)
- **新增 exportSbomOptions 端点**: 用户要求前端可动态获取合法参数组合，避免前后端枚举不同步
- **format guard 从无到有**: Spdx3Writer.write() 原本忽略 format 参数转硬传 JSON → 改为主动校验 format 非 JSON 时抛异常

## 可复用经验
- tools-java `SpdxConverter.convert()` 要求输出文件不存在，`Files.createTempFile()` 会立即创建文件，需在调用前手动删除
- tools-java 对毫秒精度时间戳 (如 `.000Z`) 解析失败，需正则归一化为 `Z`
- Spdx3Writer 的 externalRefs 预处理逻辑可复用于其他 SPDX 3.0.1 相关需求
- exportSbom 场景下，暴露合法 spec/specVersion/format 组合时，推荐使用枚举 getter 取值而非硬编码字符串，新增枚举值时自动覆盖

## 归档日期
2026-06-25 (原) / 2026-06-27 (补充归档)
