# ms-notice-20260910 — 实现任务

> PR [#304](https://gitcode.com/openlibing/openlibing-sca/pull/304) 已合入 `release_20260910`，任务全部完成。

## 进度: 12/12 complete

### 数据模型与继承（#75）

- [x] Task 1: Liquibase 新增 `manual_url` / `manual_content` 列（`20260909_add_tbl_project_notice_scan_detail_manual_flag.xml`，含幂等 preConditions 与 rollback）
- [x] Task 2: 实体 / Mapper 补列，新增 `selectLatestManualSuccess` 查询；`startScan` 落库前执行 `inheritManualSupplements`（content 继承优先，url 继承覆盖 SBOM 地址，查询失败降级告警）

### 补充异步化（#75）

- [x] Task 3: 新增 `ProjectNoticeScanSupplementEvent` 与 `markSupplementContent` / `markSupplementRescan` / `markSupplementProcessing` CAS 语句；`supplementNotice` 改为异步受理（content/downloadUrl 二选一、主表置 PROCESSING、事务后投递 supplement 消息）
- [x] Task 4: `AsyncProcessor` 按 `msgType` header 分派消息；新增 `processSupplement`（就绪登记、重扫失败隔离、重读 DB 全量明细重建合并文档、合并成功后统一置成功）；`processScan` 放宽状态门恢复孤儿 PROCESSING 扫描

### 查询与导出

- [x] Task 5: 新增 `ProjectNoticeScanInfoVO` / `ProjectNoticeScanDetailInfoVO` / `ProjectNoticeScanInfoQueryPo`，`/info` 接口支持状态过滤，未扫描返回 null
- [x] Task 6: 新增 `OpenlibingFrameworkClient` 统一导出 Feign（create / update）与 OBS DTO；`exportNotice` + `transferToExportBucket`（objectKey `yyyy-MM-dd/UUID`、Content-Disposition 指定文件名、expectedMessages 条件更新）；下线 `/release`、`/query`

### Copyright 与 purl 修复

- [x] Task 7: `replaceSpecialCharsCopyright` 剥离 `(?i)copyright` 前缀，`©` / `(c)` / `(C)` 整体移除且排在单字符之前（#76）
- [x] Task 8: `CGitPackageUrlResolver` git host 白名单 + 归档 / ref 页面路由归一化；`MavenPackageUrlResolver` 镜像 URL 去 `maven2/` 前缀；`downloadPackage` 对 `text/html` 响应判定失败

### 格式统一与依赖

- [x] Task 9: `NoticeMerger` 与人工补充项头部统一为 `Software: <名称> <版本>` 格式；`openlibing-common-sdk` 升级 1.0.20.6

### 测试与交付

- [x] Task 10: 补充 / 更新单元测试（ServiceImpl / AsyncProcessor / EventListener / Controller / CGit & Maven resolver / Copyright 归一化 / Executor）
- [x] Task 11: CI 流水线通过（ci-pipeline-passed），评审通过（lgtm / approved）后合入
- [x] Task 12: spec 文档归档至 openlibing-docs（本目录）
