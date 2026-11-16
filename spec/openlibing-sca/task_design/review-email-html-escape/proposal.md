# review-email-html-escape — 审核通知邮件 project/repo 名称 HTML 转义（#159）

## 需求背景

业务 Issue：[openlibing/openlibing-sca#159](https://gitcode.com/openlibing/openlibing-sca/issues/159)
（【安全】【合法合规审核】审核通知邮件 project/repo 名称未 HTML 转义，存在 HTML 注入风险）。

- 漏洞类型：HTML 注入 / 跨站脚本（CWE-79），低危。
- 问题位置：`src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java`
  `reviewRepoEmailContent` 方法。issue 中标注约 L1356/L1359；实际修改点在 commit `583875ee`
  的 hunk `@@ -1353,10 +1354,10 @@`，当前代码位于 L1405-L1419 的表格行，两处转义调用在 L1408、L1411。
- 数据来源：`repoInfoMapper.queryById` 返回的 `RepoInfoEntity.projectName` / `repoName`，属平台外部可控数据（仓库名来自代码托管平台）。
- 风险与影响：项目名/仓库名中的 `<`、`>`、`&`、`"` 等字符会破坏审核通知邮件 HTML 结构；邮件客户端通常不执行脚本，但可造成内容伪造、链接/文案篡改与排版破坏，直接影响合法合规审核通知的可信度。

受影响链路：`saveReviewRepoContent` → `reviewRepoEmailContent` → `sendEmail`。

## 功能描述

**做什么**：

1. 在拼装审核通知邮件 HTML 正文时，对 `projectName`、`repoName` 统一做 HTML 转义（`HtmlUtils.htmlEscape`）。
2. 补充单测，验证 `<script>`、`<b>`、`&` 等字符被编码为 HTML 实体。

**不做什么**：

- 不改造邮件模板体系，不引入 Thymeleaf/Freemarker 等模板引擎（该邮件正文为 Java 字符串拼接）。
- 不改动同一方法内其它字段（审核人、申请时间等）的展示逻辑。
- 不改动合法合规审核与邮件发送的业务流程、收件人计算逻辑。
- 不对 `reviewRepoEmailContent` 之外的其它邮件正文统一加固（本轮仅覆盖 issue 指定链路，其它邮件如有同类拼接需另立 issue）。

## 验收标准

- [x] `repoInfoEntity.getProjectName()` 拼入 HTML 前经 `HtmlUtils.htmlEscape()` 转义（`583875ee`）
- [x] `repoInfoEntity.getRepoName()` 拼入 HTML 前经 `HtmlUtils.htmlEscape()` 转义（`583875ee`）
- [x] 新增单测 `testReviewRepoEmailContent_HtmlEscape`，断言 `<script>alert(1)</script>` 不再原样出现，
      且 `proj&lt;script&gt;alert(1)&lt;/script&gt;`、`repo&lt;b&gt;&amp;1&lt;/b&gt;` 出现在结果中（`583875ee`）
- [x] 既有邮件内容用例不受影响（未修改既有用例；`OpenScanDMServiceImplTest` 中同方法既有用例保持不变）
- [ ] 端到端真实邮件渲染验证：本轮未覆盖（单测只断言字符串内容，未接入邮件客户端渲染）
- [ ] 其它邮件正文同类拼接的排查：本轮未覆盖（issue 仅指向该方法）

## 影响范围

- 仓库：`openlibing-sca`（dm 模块）。
- 接口：无变化（邮件为内部异步通知，不对外暴露 HTTP 契约）。
- 配置：无变化。
- Schema：无变化。
- 输出形态：邮件正文中项目名/仓库名的特殊字符转为 HTML 实体，正常字符（含中文）不受影响。
