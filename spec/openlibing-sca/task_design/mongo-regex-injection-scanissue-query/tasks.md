# mongo-regex-injection-scanissue-query — 实现任务

## 进度: 3/3 complete

- [x] Task 1（b018019d）：`OpenScanServiceImpl` 新增 `escapeRegex`（L1139-L1144）
- [x] Task 2（b018019d）：`/query` 链路四个参数共 5 处拼接点套用转义
      （L1152、L1154、L1158、L1166、L1170）
- [x] Task 3（b018019d）：补充单测并交付 commit

## 交付记录

| 项         | 内容                                                                                                                                                            |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| commit     | `b018019ddd24ab51bd37d8762862dbaaa4b3fb9e`（`fix(analysis): escape user filters before building mongo regex`）                                                  |
| 分支       | `ms_scan`                                                                                                                                                       |
| 变更规模   | 2 文件，+99 / -5                                                                                                                                                |
| 关联 issue | `Refs #106 #107 #113 #114`                                                                                                                                      |
| 验证方式   | `git show b018019d` 核实 5 处拼接点改动；静态核对 `getScanIssue`（L1307）调用链与 `escapeRegex` 最终形态                                                        |
| 单测       | `escapeRegex_escapesAllRegexMetacharacters`、`getScanIssueAll_escapesRegexMetacharactersInUserFilters`、`getScanIssueAll_keepsLiteralSemanticsForNormalFilters` |
| 测试结果   | 本轮回溯未执行 `mvn test`（需私仓凭据），结果未验证                                                                                                             |

## 说明

- 单测入口使用 `getScanIssueAll`（与 `getScanIssue` 共用 filter），`/query` 服务方法未单独断言，
  已在 proposal 验收标准中标注。
- issue 修复建议 2（长度上限 + 字符白名单）未实施；建议 1（复用/抽取公共 `escapeRegex`）
  以同实现副本落地，未抽取公共类。
- 兄弟目录：`mongo-regex-injection-path-filename`、
  `mongo-regex-injection-vendor-component`、`mongo-regex-injection-scanissue-queryall`。
