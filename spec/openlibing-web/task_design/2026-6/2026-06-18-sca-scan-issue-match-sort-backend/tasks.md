## 1. DTO 与白名单

- [x] 1.1 `ScanIssueQueryVO` 新增 `sortColumn`、`sortOrder` 字段
- [x] 1.2 新建 `ScanIssueColumnList` 枚举，首期含 `MATCHED("matched", "matched")`
- [x] 1.3 实现 `getMongoField(String sortColumn)` 白名单解析方法
- [x] 1.4 新增 `ScanIssueColumnListTest` 单元测试

## 2. 排序工具方法

- [x] 2.1 将 `FileUtil.getMatchedScore` 提取为 `public static parseMatchedScore(String matched)`（或等价 public 方法）
- [x] 2.2 在 `OpenScanServiceImpl` 新增 `resolveSortDirection(String sortOrder)` 方法
- [x] 2.3 新增 `isMatchedSort(ScanIssueQueryVO)` 判断是否需要走 Aggregation 路径

## 3. getScanIssue 核心改造

- [x] 3.1 抽取 `buildScanIssueCriteria(ScanIssueQueryVO, String scanId)`（或复用现有 criteria 构建，供 Query 与 Aggregation 共用）
- [x] 3.2 实现 `executeMatchedSortQuery(Criteria, Sort.Direction, int pageNo, int pageSize)`：
  - `$match` → `$addFields(matchedScore)` → `$sort` → `$skip` → `$limit`
- [x] 3.3 修改 `getScanIssue`：matched 排序走 Aggregation，否则保持 `scanFile ASC`
- [x] 3.4 确认 `count` 查询仍基于相同 criteria，不受排序影响

## 4. 测试

- [x] 4.1 `OpenScanServiceImplTest`（或新建）：matched 降序分页顺序正确
- [x] 4.2 测试：matched 升序、无排序参数（scanFile ASC）、非法 sortColumn 回退
- [x] 4.3 测试：`parseMatchedScore` 对 `"90%"`、空值、非法字符串的处理
- [x] 4.4 运行相关模块单元测试通过


