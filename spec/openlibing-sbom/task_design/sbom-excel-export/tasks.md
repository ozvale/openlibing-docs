# SBOM 导出异步化改造 — 实现任务清单

> change-name: `sbom-excel-export`　分支：`feat-sbom-excel-export`（openlibing-sbom / openlibing-web）
> 状态：已全部完成并归档，详见 [archive.md](./archive.md)

## openlibing-sbom（后端）

- [x] 1. pom：sbom-web 引入 `easyexcel`（4.0.3，对齐 codecheck）、`esdk-obs-java`（版本由 common BOM 管理）
- [x] 2. clients：`FrameworkClient` 新增 `createExportTask` / `updateExportTask` / `queryExportTask`
- [x] 3. clients：新增 Obs DTO（Create/Update/Query Request + Response，契约照抄 codecheck）
- [x] 4. 新增 `SbomExportType` 枚举（SBOM_PACKAGE / SBOM_DOCUMENT，枚举名即 obs_file.type 并决定路由线程池）
- [x] 5. 新增 `SbomExportStatusEnum`（中文 message 契约 + buildFailedMessage 截断 255 + QUEUE_FULL_REASON）
- [x] 6. 新增 `SbomExportExecutorConfig`（双 `ThreadPoolTaskExecutor`：Excel 并发 2 / 文档并发 1，AbortPolicy，参数 `@Value` 带默认值）
- [x] 7. 新增 `SbomObsBucketService` + Impl（懒加载 ObsClient、AK/SK 解密、uploadFile/deleteObject）
- [x] 8. 新增 `SbomPackageExportVO`（14 列 EasyExcel 注解 VO）
- [x] 9. `SbomController` 新增 `POST /exportSbomExcel`、`POST /exportSbomDocument`
- [x] 10. `SbomExportServiceImpl` 导出编排：submitExportTask（校验/鉴权/建任务/线程池 execute + 拒绝回写）、processExport（type 分发 + CAS 骨架）、processExportQuietly（线程池兜底 catch）、generatePackageExcel（分页游标 + EasyExcel 多 Sheet）、generateDocument（复用 writeSbom）、casUpdateStatus/queryExportRecord/updateExportFailure
- [x] 11. 配置：beta/gamma/prod 三个环境 properties 的 `spring.config.import` 增加 `optional:nacos:framework`（OBS/security.part1 由 framework data-id 统一下发，对齐 codecheck；线程池参数默认值可运行，可选配置；application.properties 不提交改动）
- [x] 12. 附带改动：ProductRepository 4 处查询 LEFT JOIN → INNER JOIN + IS NOT NULL（归档补充：并加 DISTINCT ON `id DESC` 确定性次级排序键）
- [x] 13. 单测：导出编排（建任务/线程池分发/队列打满拒绝回写）、CAS 状态流转、Excel 分批写入与空数据表头、附带改动 SQL 行为
- [x] 14. 本地验证：mvn 编译 + 相关单测通过
- [x] 15. pre-commit：对全部改动文件执行并通过

## openlibing-web（前端）

- [x] 16. `api/sbom/url.ts` + `api.ts`：新增 EXPORT_SBOM_EXCEL / EXPORT_SBOM_DOCUMENT
- [x] 17. `sbomExportDialog.vue` 重构：标题改「导出软件物料清单（SBOM）」、「类型」radio（SBOM 默认三级联动 / xlsx 隐藏联动）、确认统一走 `useExportTaskSubmit` 提交、移除 blob 下载（后按检视意见标题最终定为「导出软件物料数据」）
- [x] 18. `CompositionAnalysis/index.vue`：「全量导出」tooltip 文案更新
- [x] 19. `mapExportRecord.ts`：TYPE_LABEL 增加 SBOM_PACKAGE / SBOM_DOCUMENT（归档补充：《我的导出》表格新增「类型」列渲染标签）
- [x] 20. 验证：pnpm lint + check:type 通过
- [x] 21. pre-commit：对全部改动文件执行并通过

## 交付门禁

- [x] 22. 报告分支名 / 文件清单 / 验证结果 / pre-commit 结果（暂不 commit，等用户确认）
- [x] 23. 用户确认后：commit（后端主改动 + 附带改动独立 commit + 前端 commit）→ 合入测试分支部署验证（Phase 7）

## 实现期追加范围（过程中按用户指令/检视意见新增）

- [x] A1. 异步调度方案由 RabbitMQ 改双线程池隔离（删 Producer/Consumer/RabbitConfig，AbortPolicy + 队列打满回写）
- [x] A2. OBS 配置来源改为 framework Nacos data-id（`optional:nacos:framework`，对齐 codecheck）
- [x] A3. 文档导出对齐同步链路打包 .tar.gz（sbom + sha256 + 签名）
- [x] A4. Excel 导出字段空值口径与页面一致（`--`/Others）、「无风险」列宽修正
- [x] A5. 导出分批查询+VO 物化包 TransactionTemplate 短事务（修复线程池自调用懒加载异常）
- [x] A6. 顺带：制品列表/SCA 名单过滤无解析状态数据（独立 commit）
- [x] A7. 顺带：GitCode VCS 无条件重试层退避 1s→60s
- [x] A8. guava 升级 33.7.2-jre（清存量 CVE-2026-102554，过 oss-pr-scan 门禁）
- [x] A9. 第一轮检视修复（bot 12+3 条，10 采纳/1 误报/1 设计决策保留）
- [x] A10. 第二轮检视修复（@Async 执行器绑定/文件名双重编码/SUCCESS 回写失败清理孤儿对象）
- [x] A11. 前端 extractExportIdFromResponse 兼容 number 形态（修复 Integer 契约跨仓回归）
