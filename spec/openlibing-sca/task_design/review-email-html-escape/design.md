# review-email-html-escape — 技术设计

## 方案概述

在审核通知邮件正文拼装点做单点输出编码：`reviewRepoEmailContent` 中把来自 `RepoInfoEntity` 的
`projectName`、`repoName` 分别用 `org.springframework.web.util.HtmlUtils.htmlEscape()` 转义后再拼入 `<td>`。
不改模板、不改数据来源、不改邮件发送链路，仅消除拼接点的 HTML 注入面。

修复后该方法的数据流：

```
saveReviewRepoContent
  └─ repoInfoMapper.queryById(repoId) → RepoInfoEntity(projectName, repoName)   [外部可控]
       └─ reviewRepoEmailContent
            ├─ contentTitle: userName + 待审核条数
            └─ table row: HtmlUtils.htmlEscape(projectName) / HtmlUtils.htmlEscape(repoName)
                 + DateUtils.format(applyTime) + 固定文案 scaRemark
       └─ sendEmail
```

## 架构决策

| 决策                                                         | 理由                                                                                                            |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| D1：使用 `HtmlUtils.htmlEscape()` 而非自写替换函数           | Spring 自带方法已完成 `&`、`<`、`>`、`"`、`'` 的实体编码，避免自实现遗漏字符；项目已依赖 spring-web，无新增依赖 |
| D2：在拼装点转义，而不是在 `RepoInfoEntity` 入库或查询处转义 | 同一实体同时用于页面展示与业务判断，提前转义会污染数据（如仓库名校验、DB 存储）；输出编码应贴近输出点           |
| D3：只转义 `projectName` / `repoName`，其它字段维持原样      | 其余字段为服务端生成（申请时间、固定文案）或系统用户名，不属于 issue 指出的外部可控输入；避免扩大改动面         |
| D4：以字符串断言单测验证编码结果                             | 该方法返回 `String`，无需启动 Spring 上下文；沿用 `OpenScanDMServiceImplTest` 的 Mockito 直测风格               |

## 涉及文件

| 文件                                                                              | 操作 | 说明                                                                                                                      |
| --------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java`     | 修改 | 新增 `org.springframework.web.util.HtmlUtils` 导入；`reviewRepoEmailContent` 中 projectName/repoName 转义（L1408、L1411） |
| `src/test/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImplTest.java` | 修改 | 新增 `testReviewRepoEmailContent_HtmlEscape`                                                                              |

## 风险 & 缓解

| 风险                                         | 缓解                                                                                                                                                      |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 转义后邮件中项目名/仓库名显示为实体字符      | `htmlEscape` 只编码 5 个特殊字符，中文与常规字符原样输出；实体在 HTML 渲染后还原为原字符                                                                  |
| 单测只校验字符串，未覆盖邮件客户端渲染差异   | 验收项中标注"端到端渲染未验证"；编码正确性由断言直接保证                                                                                                  |
| 同类拼接尚未覆盖                             | `contentTitle` 中的 `userBasicInfo.getUserName()`、邮箱底部 `reviewUrl` 未转义；本轮不在 issue 范围，未验证其可控性，后续如有外部输入进入该链路需单独立项 |
| 邮件内容被下游二次处理（如富文本编辑器回存） | 未涉及；该内容直接发送，不回存                                                                                                                            |

## 跨仓影响

无。仅改 `openlibing-sca` 一个类与其单测；spec 文档归档 openlibing-docs 仓（本目录）。
