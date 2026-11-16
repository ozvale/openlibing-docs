# mongo-regex-injection-scanissue-queryall — 实现任务

## 进度: 3/3 complete

- [x] Task 1（b018019d）：`OpenScanServiceImpl` 新增 `escapeRegex`（L1139-L1144）
- [x] Task 2（b018019d）：`/queryAll` 复用的 `applyPathAndFileFilters` /
      `applyVendorComponentFilters` 共 5 处拼接点套用转义
- [x] Task 3（b018019d）：以 `getScanIssueAll` 为入口补充单测并交付 commit

## 交付记录

| 项         | 内容                                                                                                                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| commit     | `b018019ddd24ab51bd37d8762862dbaaa4b3fb9e`（`fix(analysis): escape user filters before building mongo regex`）                                                     |
| 分支       | `ms_scan`                                                                                                                                                          |
| 变更规模   | 2 文件，+99 / -5                                                                                                                                                   |
| 关联 issue | `Refs #106 #107 #113 #114`                                                                                                                                         |
| 验证方式   | `git show b018019d` 核实 filter 改动；静态核对 `getScanIssueAll`（L1363-L1384）调用链与 `mongoTemplate.find` 不分页形态                                            |
| 单测       | `getScanIssueAll_escapesRegexMetacharactersInUserFilters`、`getScanIssueAll_keepsLiteralSemanticsForNormalFilters`（均直接调用 `openScanService.getScanIssueAll`） |
| 测试结果   | 本轮回溯未执行 `mvn test`（需私仓凭据），结果未验证                                                                                                                |

## 说明

- 本 issue 与 `/query` 共用修复点，提交只改了 filter 与 `escapeRegex`，`getScanIssueAll`
  方法体未改动；单测选择 `getScanIssueAll` 入口，恰好直接覆盖本接口。
- 未覆盖项：`/queryAll` 鉴权/凭证/限流（issue 修复建议 2）、全量返回分页、长度白名单、压测。
- 兄弟目录：`mongo-regex-injection-path-filename`、
  `mongo-regex-injection-vendor-component`、`mongo-regex-injection-scanissue-query`。
