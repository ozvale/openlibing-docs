# mongo-regex-injection-vendor-component — 实现任务

## 进度: 3/3 complete

- [x] Task 1（b018019d）：`OpenScanServiceImpl` 新增 `escapeRegex`（转义全部正则元字符）
- [x] Task 2（b018019d）：`applyVendorComponentFilters` 的 `vendor`、`component` 两处拼接套用转义
- [x] Task 3（b018019d）：补充单测并交付 commit

## 交付记录

| 项         | 内容                                                                                                                                                            |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| commit     | `b018019ddd24ab51bd37d8762862dbaaa4b3fb9e`（`fix(analysis): escape user filters before building mongo regex`）                                                  |
| 分支       | `ms_scan`                                                                                                                                                       |
| 变更规模   | 2 文件，+99 / -5                                                                                                                                                |
| 关联 issue | `Refs #106 #107 #113 #114`                                                                                                                                      |
| 验证方式   | `git show b018019d` 核实 diff；静态核对当前 `applyVendorComponentFilters`（L1163-L1176）与 `escapeRegex`（L1139-L1144）                                         |
| 单测       | `escapeRegex_escapesAllRegexMetacharacters`、`getScanIssueAll_escapesRegexMetacharactersInUserFilters`、`getScanIssueAll_keepsLiteralSemanticsForNormalFilters` |
| 测试结果   | 本轮回溯未执行 `mvn test`（需私仓凭据），结果未验证                                                                                                             |

## 说明

- 同一提交覆盖四个 issue；本目录只记录 `vendor` / `component` 两个字段的修复证据
  （L1166、L1170 及对应单测断言）。`path` / `fileName`、`/query`、`/queryAll` 视角分别见
  `mongo-regex-injection-path-filename`、`mongo-regex-injection-scanissue-query`、
  `mongo-regex-injection-scanissue-queryall`。
- issue 修复建议中的"提取 `RegexUtils` 公共工具类"与"长度上限/字符白名单"本轮未实施，
  已在 proposal 验收标准中标注。
