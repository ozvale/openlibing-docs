# NOTICE 扫描明细依赖类型与按依赖范围导出 — 实现任务

## 进度: 0/9 complete

- [ ] Task 1: Liquibase 迁移脚本 ×2（detail 表 dependency_type + scan 表 direct_merged_oss_url）+ include
- [ ] Task 2: 枚举 `ProjectNoticeDependencyType` / `NoticeExportScope` + 实体/VO/Po 字段（含 scan 实体 directMergedOssUrl）
- [ ] Task 3: Feign `queryPackageDependencyTypes` + SBOM 行 DTO
- [ ] Task 4: Mapper（detail 加列 + `batchUpdateDependencyType`；scan 加列 + `selectAllByProjectName` + `updateDirectMergedOssUrlByScanId`）
- [ ] Task 5: 扫描填充 `fillDependencyTypes`（归并规则 + 失败降级）
- [ ] Task 6: 双文件生成（AsyncProcessor processScan / processSupplement 输出全量 + direct 合并文件并回填列）
- [ ] Task 7: 回填接口（Controller/Service/Po/VO，全部历史扫描，幂等；完成后为最新扫描重建 direct 文件）
- [ ] Task 8: 导出拆分（scope 校验 + FULL/DIRECT 纯转存，缺失报错/跳过）
- [ ] Task 9: 单测（归并规则、scope 校验、双文件生成、回填、导出转存）+ `run-mvn.py clean test` 验证
