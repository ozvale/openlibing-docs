# 93 xss-filter-defect — clarifyRemark 原样入库、移除有缺陷的 DefenseXssUtil 过滤

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/93
（【安全】【安全威胁】XSS 过滤工具存在逻辑缺陷且缺少全局过滤器，存储型 XSS 风险）

`DefenseXssUtil#htmlStr`（`src/main/java/com/openlibing/sca/common/utils/DefenseXssUtil.java`）在 `Jsoup.clean` 之后再做"原始标签与清洗后标签按顺序对齐重组"：对非白名单标签执行 `String elementStr = null; stringBuffer.append(elementStr);`，注释声称"使用 StringEscapeUtils 转义特殊字符"但从未调用，实际结果是向输出写入字面量 `null` 文本并丢弃标签内的合法内容。该工具类原先只有一处生产调用：`OpenScanDMServiceImpl#scanConfirmParseV2` 对 `clarifyRemark` 调用 `htmlEntityEncode`，因此用户填写的确认备注会被污染。全仓也无任何全局 XSS 过滤器。

归类：CWE-79（Improper Neutralization of Input During Web Page Generation）/ 数据完整性缺陷。

## 功能描述

**做什么**（实际落地口径）：**移除有缺陷的过滤调用，让 `clarifyRemark` 原样入库**，而不是修复过滤器：

1. 删除 `OpenScanDMServiceImpl#scanConfirmParseV2` 中的 `String clarifyRemark = DefenseXssUtil.htmlEntityEncode(issuePo.getClarifyRemark());`；
2. `new TblConfirmReview(...)` 的 `clarifyRemark` 参数改为直接传 `issuePo.getClarifyRemark()`；
3. 删除随之无用的 `DefenseXssUtil` import。

提交说明明确记录："Note: backend HTML sanitization of this rich-text field is removed with this change."

**不做什么**（本轮未覆盖，与 issue 验收标准的差异）：

- 不重构 `DefenseXssUtil#htmlStr`（对齐重组逻辑、`append(null)`、`StringEscapeUtils` 注释不一致等问题全部保留，类文件未改动）；
- 不删除 `DefenseXssUtil` 及其 15 个单测（该类现在没有生产调用方，但仍在仓内，可被后续代码误用）；
- 不注册全局 XSS 清洗过滤器（无 `XssFilter` / `OncePerRequestFilter` / 参数包装 / Jackson `String` 处理器）；
- 不做纯文本字段全转义 / 富文本字段白名单的分层策略；
- 不增加 `Content-Security-Policy` 响应头，也不改前端输出编码（前端行为未验证）；
- 不新增任何单测（本提交只改了 1 个文件，`+1 / -3` 行）。

## 验收标准

- [x] 备注内容不再被 `htmlStr` 链路污染：`clarifyRemark` 原样写入 `tbl_confirm_review`，不再出现字面量 `"null"` 文本或内容被丢弃
- [ ] `htmlStr` 单测覆盖"非白名单标签内容不丢失、无 `"null"` 文本"（本轮未覆盖：`htmlStr` 未修改，`DefenseXssUtilTest` 15 个用例仍按旧语义断言）
- [ ] 全局 XSS 清洗生效：`<script>`、`<img onerror>` 入库前被清洗/转义（本轮未覆盖：无过滤器，且本提交移除了唯一一处后端清洗）
- [ ] 富文本字段白名单标签与样式回归无破坏（本轮未覆盖：后端不再清洗该字段，完全依赖前端输出编码）
- [ ] 清洗与转义策略有文档说明、新字段接入有指引（本轮未覆盖：仅 commit message 提示）
- [ ] 相关单元测试通过、覆盖率达标（本轮无新增/修改测试；本地 UT 日志中 `OpenScanDMServiceImplTest` 曾出现 2 个与本次改动无关的用例错误，后续 `0b6a0555` 已适配；本次回溯未重跑 `mvn test`）

## 影响范围

- 仓库：`openlibing-sca`（`dm` 模块，`OpenScanDMServiceImpl`）。
- 接口：无路由/参数变化；`scanConfirmParseV2` 入库的 `clarifyRemark` 内容语义变化（原样保存，不再 HTML 实体编码）。
- 数据：`tbl_confirm_review.clarify_remark` 新写入数据为原始文本；历史数据中已存在的 `"null"` 污染不会被回修（未做数据修复）。
- 安全性质变化（重要）：后端不再对 `clarifyRemark` 做 HTML 清洗，存储型 XSS 的防线从"服务端（有缺陷）过滤"变为"完全依赖前端回显编码"，属残余风险，需前端确认。
- 配置 / schema / 部署：无。
