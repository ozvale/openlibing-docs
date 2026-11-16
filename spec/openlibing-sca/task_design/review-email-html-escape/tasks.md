# review-email-html-escape — 实现任务

## 进度: 1/1 complete

- [x] Task 1: `OpenScanDMServiceImpl.reviewRepoEmailContent` 对 projectName / repoName 做 `HtmlUtils.htmlEscape`，并新增 `testReviewRepoEmailContent_HtmlEscape`（`583875ee`）

## 交付记录

| commit     | 摘要                                                        | 关联                                                       |
| ---------- | ----------------------------------------------------------- | ---------------------------------------------------------- |
| `583875ee` | fix(dm): escape project and repo names in review email html | commit message 未写 `Refs`；issue 正文声明由该 commit 修复 |

- 分支：`ms_scan`（业务仓 `openlibing-sca`）
- 代码变更：2 文件，+28 / -2（`OpenScanDMServiceImpl.java` +3/-2 导入与方法体；`OpenScanDMServiceImplTest.java` +25）
- 验证方式：
  - 单测 `OpenScanDMServiceImplTest#testReviewRepoEmailContent_HtmlEscape`，断言
    `proj<script>alert(1)</script>` 不再原样出现，且 `proj&lt;script&gt;alert(1)&lt;/script&gt;`、
    `repo&lt;b&gt;&amp;1&lt;/b&gt;` 出现在返回内容中。
  - 全量 `mvn test` 结果：本轮未记录（提交时未附测试输出），未验证。
- 回滚方式：还原该 commit 两处 `HtmlUtils.htmlEscape` 调用与单测。
