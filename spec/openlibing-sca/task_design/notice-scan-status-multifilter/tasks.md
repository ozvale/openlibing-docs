# notice-scan-status-multifilter — 实现任务

## 进度: 0/8 complete

- [ ] Task 1: 新增 `ProjectNoticeScanMultiFilterQueryPo`（analysis/entity/dto，镜像 SBOM 请求体字段）
- [ ] Task 2: 新增 `ProjectNoticeScanStatusVO`（analysis/entity/vo，productName/status/statusName）
- [ ] Task 3: `OpenlibingSbomClient` 新增 `queryProductNamesByMultiFilter` 【安全约束：仅透传请求体契约，不新增参数；验证方式：编译 + Feign 契约与 SBOM Controller 注解比对】
- [ ] Task 4: `TblProjectNoticeScanMapper` + XML 新增 `selectLatestByProjectNames` 【安全约束：`#{}` 参数化 + `<foreach>`，禁止拼接；验证方式：单测 + XML 语法检查】
- [ ] Task 5: `ProjectNoticeScanService` / `Impl` 新增 `queryScanStatusByMultiFilter` 【安全约束：productType 前置校验；失败安全不降级；VO 最小化不透出 OBS 地址；验证方式：单测覆盖 5 场景】
- [ ] Task 6: `ProjectNoticeScanController` 新增 `POST /scanStatusByMultiFilter`（沿用既有异常模板）
- [ ] Task 7: 单测——ServiceImpl（正常映射/未扫描/空列表/SBOM 失败/productType 缺失）+ Controller 用例
- [ ] Task 8: 验证：`python scripts/run-mvn.py clean test`（定向 `-Dtest=ProjectNoticeScan*` 先跑，再全量）
