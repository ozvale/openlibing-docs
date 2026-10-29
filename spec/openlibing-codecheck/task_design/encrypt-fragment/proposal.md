# Proposal: fragment 代码片段编码存储及日志泄露防护

## 需求背景

openlibing-codecheck 的 `task_result_details` 和 `task_inc_result_details` 两张 MongoDB 集合中，`fragment` 字段存储了用户源代码上下文片段（`CodeCheckIssueFragment.lineContent`）。这些代码数据属于用户数据，可能包含敏感信息（如明文密钥、API Token 等），存在以下问题：

1. **明文存储**：fragment.lineContent 以明文存储在 MongoDB 中，明文密钥等敏感信息在合规审计或数据库检索时会被直接命中
2. **日志泄露**：DatarecoveryDelegateImpl 中直接打印 `List<DefectVo>.toString()`，会将完整代码片段写入日志文件
3. **toString 泄露**：DefectVo 使用 Lombok `@Data` 注解，自动生成的 `toString()` 会递归打印 fragment 内容，任何日志打印 DefectVo 对象都会泄露代码片段
4. **规则示例泄露**：CodeCheckRuleVo 等 5 个规则类的 `rightExample`/`errorExample` 字段同样会被 `toString()` 打印到日志
5. **shield 表遗漏**：`full_shield_detail` 和 `inc_shield_detail` 两张表同样存储了 fragment，但未进行编码/解码处理
6. **解码安全漏洞**：`Base64.isBase64()` 无法区分纯字母明文（如 "pass"、"return"）和真正的 Base64 编码数据，导致历史明文被误解码为乱码

> 说明：本方案仅对 fragment.lineContent 做 Base64 编解码（非密码学加密），目的是避免明文密钥等内容在数据库中被直接审计/检索，**不涉及加密、解密**。工具类名 `FragmentCryptoUtil`、方法名 `encryptFragments`/`decryptFragments` 沿用历史命名，实际行为是 Base64 编码与解码。

## 验收标准

- [x] 新数据入库后 MongoDB 中 fragment.lineContent 为 Base64 编码值（task_result_details / task_inc_result_details）
- [x] 前端查询问题详情时 fragment 正常显示（自动解码）
- [x] 历史未编码数据查询不受影响（解码失败保留原值）
- [x] 日志中不再出现 fragment 代码片段内容
- [x] 日志中不再出现 rightExample/errorExample 内容
- [x] 编码失败时使用占位提示词，避免明文入库
- [x] full_shield_detail / inc_shield_detail 表入库前编码、查询后解码
- [x] CodeCheckIssueFragment.lineContent 添加 @ToString.Exclude 防止日志泄露
- [x] 解码时采用两阶段验证（isBase64 + 回检验证），纯字母明文不被误解码为乱码
- [x] tryDecryptLineContent 返回 Optional，不返回 null

## 关联

- 业务 Issue: openlibing/openlibing-codecheck#116
- 业务 PR: openlibing/openlibing-codecheck#203
