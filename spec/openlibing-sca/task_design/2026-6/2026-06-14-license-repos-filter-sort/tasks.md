## 1. DTO 扩展



- [x] 1.1 在 `ScanCommunityDto` 新增 `repoResult`、`sortColumn`、`sortOrder` 字段及 getter/setter



## 2. 排序列白名单



- [x] 2.1 新建 `LicenseColumnList` 枚举，覆盖 `scanTime`、`fileNum`、`compatibilityNumber`、`incompatibleNumber`、`unrecognizedNumber`

- [x] 2.2 在 `LicenseServiceImpl` 中建立 `SORT_COMPARATORS` Map（Date/Integer null-safe 比较）



## 3. LicenseServiceImpl 核心重构



- [x] 3.1 实现 `filterByRepoResult(List<LicenseInfoVO>, String repoResult)` 私有方法

- [x] 3.2 实现 `sortLicenseList`、`paginateList`（或 `sortAndPaginateLicenseData`）私有方法

- [x] 3.3 重构 `getScanByCommunity`：去重 → filter → **全量** getStatsBatch + getScanResult → removeIf → 计算 total → sort → paginate

- [x] 3.4 无 sortColumn/sortOrder 时默认 `licenseCreateTime` 降序



## 4. 单元测试



- [x] 4.1 新增/扩展 `LicenseServiceImplTest`：`filterByRepoResult` 边界用例（blank、单值、多值、无匹配、不 mutate 源 list）

- [x] 4.2 测试 `getScanByCommunity` 筛选后 total/list 正确

- [x] 4.3 测试 sortColumn=scanTime/fileNum + ascending/descending + 分页

- [x] 4.4 测试 repoResult 筛选与排序叠加

- [x] 4.5 修正现有 mock 中 `repoResult("1")` 为 `success`/`fail`



## 5. 联调验证



- [x] 5.1 与 `openlibing-web` projectCompliance Tab 联调：筛选 success/fail、各列排序、翻页 total 正确（API 契约已由单测覆盖，UI 联调待部署环境验证）

- [x] 5.2 确认未传新参数时列表可正常加载（默认 scanTime 降序）



> 单测：`mvn test -Dtest=LicenseServiceImplTest` 16/16 通过。


