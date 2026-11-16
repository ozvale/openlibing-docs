# mongo-regex-injection-path-filename — 实现任务

## 进度: 3/3 complete

- [x] Task 1（b018019d）：`OpenScanServiceImpl` 新增 `escapeRegex`
- [x] Task 2（b018019d）：`applyPathAndFileFilters` 的 path（L1152）与 fileName
      （L1154、L1158）三处拼接套用转义
- [x] Task 3（b018019d）：补充单测并交付 commit

## 交付记录

| 项         | 内容                                                                                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| commit     | `b018019ddd24ab51bd37d8762862dbaaa4b3fb9e`（`fix(analysis): escape user filters before building mongo regex`）                                                                                    |
| 分支       | `ms_scan`                                                                                                                                                                                         |
| 变更规模   | 2 文件，+99 / -5                                                                                                                                                                                  |
| 关联 issue | `Refs #106 #107 #113 #114`                                                                                                                                                                        |
| 验证方式   | `git show b018019d` 核实三处 `scanFile` 拼接点改动；静态核对当前 `applyPathAndFileFilters`（L1146-L1161）                                                                                         |
| 单测       | `getScanIssueAll_escapesRegexMetacharactersInUserFilters`（断言 `src/\(main\)\?`、`a\{2,\}\.java`）、`getScanIssueAll_keepsLiteralSemanticsForNormalFilters`（断言 `src/main/java`、`App\.java`） |
| 测试结果   | 本轮回溯未执行 `mvn test`（需私仓凭据），结果未验证                                                                                                                                               |

## 说明

- 单测入口为 `getScanIssueAll`，因其与 `getScanIssue` 共用同一 filter 方法；
  `/query` 入口级断言未新增，已在 proposal 验收标准中标注。
- `path` 为空、仅 `fileName` 的分支（L1158）已同步修复，未留绕过路径。
- 兄弟目录：`mongo-regex-injection-vendor-component`、
  `mongo-regex-injection-scanissue-query`、`mongo-regex-injection-scanissue-queryall`。
