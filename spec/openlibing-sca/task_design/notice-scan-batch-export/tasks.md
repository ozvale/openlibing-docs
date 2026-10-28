# notice-scan-batch-export — 实现任务

## 进度: 0/7 complete

- [ ] Task 1: 新增 `ProjectNoticeBatchExportPo`（analysis/entity/dto）
- [ ] Task 2: 新增 `NoticeBatchMerger`（dm/util，段级解析 + 跨制品去重，复用 NoticeMerger 包私有方法）【验证方式：NoticeBatchMergerTest 全分支】
- [ ] Task 3: `ProjectNoticeScanExecutor` 新增 `downloadObsObjectText` / `uploadFileToExportBucket` 【安全约束：objectKey 服务端规则推导、Content-Disposition 文件名 URL 编码】
- [ ] Task 4: `ProjectNoticeScanService` / `Impl` 新增 `exportNoticeBatch`（校验/建任务/异步提交）+ `doExportBatch`（下载/合并/上传/任务状态机）+ 专用线程池【安全约束：后台失败必置任务失败；失败安全不降级】
- [ ] Task 5: `ProjectNoticeScanController` 新增 `POST /exportBatch`（沿用既有异常模板）
- [ ] Task 6: 单测：`NoticeBatchMergerTest` + ServiceImpl（校验/部分跳过/全部缺失/后台成功与失败）+ Controller
- [ ] Task 7: 验证：定向单测 + 全量 `clean test` + spotless/checkstyle
