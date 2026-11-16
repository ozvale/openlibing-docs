# 93 xss-filter-defect — 技术设计

## 方案概述

不做"修过滤器"，而是**摘掉过滤器调用**：`cbf8645d` 删除 `scanConfirmParseV2` 中对 `clarifyRemark` 的 `DefenseXssUtil.htmlEntityEncode` 调用，改为原样入库。理由是当时唯一的生产调用点被一个有缺陷的过滤器污染数据（非白名单标签内容被替换为字面量 `null`），而该过滤器本身的安全收益可疑——`Jsoup.clean` 已能输出安全 HTML，其后的"对齐重组"只带来正确性损失。

## 架构决策

| 决策                              | 证据 / 理由                                                                                                                                                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 移除调用而不是修 `htmlStr`     | `htmlStr` 的对齐逻辑按 `tagName` 顺序匹配原始/清洗后元素（`int index` 单调推进 + 内层 `while(true)`），遇到重复/嵌套/白名单内嵌结构会索引漂移；正确重写需要重新定义"保留哪些非白名单内容"的产品语义，超出安全整改批次范围 |
| D2 `clarifyRemark` 原样入库       | 该字段由前端富文本编辑器产生，语义是"用户备注原文"；不做实体编码可避免 `"null"` 文本与内容丢失，也避免双重编码（前端编码 + 后端编码）导致显示错乱                                                                         |
| D3 保留 `DefenseXssUtil` 类与测试 | 本轮未删除工具类（提交只改 1 个文件）。当前该类无生产调用方（仅 `DefenseXssUtilTest` 引用），但保留意味着后续代码仍可能误用带缺陷的 `htmlStr`，属已知残余（见风险表）                                                     |
| D4 不引入全局过滤器               | 全局清洗会改变所有文本字段语义（纯文本 vs 富文本），需要字段级白名单设计；本轮未设计也未实现，接受"防线前移到前端"的取舍                                                                                                  |
| D5 记录而非静默                   | commit message 明示 "backend HTML sanitization of this rich-text field is removed"，避免后续误判后端已清洗                                                                                                                |

## 关键实现（当前代码）

```
// OpenScanDMServiceImpl#scanConfirmParseV2（约 L1230）
new TblConfirmReview(
    UUID.randomUUID().toString(),
    scanIssue.getScanFile(),
    ...
    clarifyEdition,
    issuePo.getClarifyRemark(),   // 原样入库（改动前为 DefenseXssUtil.htmlEntityEncode(...)）
    userId,
    issuePo.getReviewUserId(),
    ReviewStatus.UNDER_REVIEW.getValue(),
    ...
```

`DefenseXssUtil#htmlStr` 现状（未改动，L61-L83）：白名单标签命中时 `append(safeElement.outerHtml())`，未命中分支为 `String elementStr = null; stringBuffer.append(elementStr);`（`StringBuffer#append(String)` 对 null 写入字面量 `null`）。

## 涉及文件

| 文件                                                                          | 操作 | 说明                                                                                                                                 |
| ----------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java` | 修改 | 删除 `DefenseXssUtil` import 与局部变量 `clarifyRemark`；构造 `TblConfirmReview` 时改传 `issuePo.getClarifyRemark()`（`+1 / -3` 行） |

本提交无测试文件改动。

## 风险 & 缓解

| 风险                                                                          | 缓解                                                                                                                               |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 存储型 XSS：`clarifyRemark` 原样入库，若前端直接 `innerHTML` 回显则脚本可执行 | 属残余风险（本次改动主动放弃后端清洗）。需前端确认输出编码；建议后续补富文本白名单（`DefenseXssUtil.getSafeList()`）或全局过滤器   |
| `DefenseXssUtil#htmlStr` 仍带缺陷且有测试锁定旧语义，未来可能被再次调用       | 建议后续删除该工具类或重写 `htmlStr` 并替换 `DefenseXssUtilTest`；本轮未做                                                         |
| 历史数据中已被写入 `"null"` 的备注                                            | 未做数据修复；可在后续需求中按 `clarify_remark = 'null'` 或含 `null` 片段筛查（未验证影响行数）                                    |
| 富文本内容包含合法 HTML（如加粗、列表）时，前端若按纯文本渲染会丢失格式       | 该字段本就是富文本语义，需前端按富文本白名单渲染；前端实现未验证                                                                   |
| 与 JWT 链路叠加放大影响（issue 攻击场景 1）                                   | JWT 仅解码链路已在 `5852b0d2` 删除（见 `../jwt-decode-without-signature/`），攻击者无法伪造登录态，但 XSS 本身仍可用于窃取前端会话 |

## 跨仓影响

无代码级依赖。安全性依赖前端输出编码/富文本渲染策略，前端仓是否已做编码**未验证**；spec 文档归档 `openlibing-docs` 仓。
