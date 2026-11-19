# 操作日志 exMessage 凭证明文暴露修复（#551）— 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/551 （安全问题，当前仍为 open）
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pulls/685
- 分支: `fix-551-log-exmessage-masking` → `master`
- 合并: merge commit `bc59ded1a`，合并时间 2026-11-19
- 本 PR 标签: `ai-assisted` / `approved` / `lgtm`

## 交付历程

- commit `f89b0b721`: fix(security) — 主体：新增 `maskText` 并对 `exMessage` 接入掩码，`LoggingServiceImpl` 补一行调用
- commit `b0244f214`: fix(security) — 正则加固：认证方案凭据增加长度与字符组成门槛，抑制普通英文误伤
- commit `8ec0e3c77`: fix(security) — 收口剩余缺口：复合键名、裸认证头与会话头、URL 仅口令形态
- commit `cf2cc4021`: fix(security) — 检视修复：JSON 分支非敏感键值与数组字符串元素统一过 `maskText`

## 关键验证

- `OperationLogSensitiveMaskerTest` 最终 20 条用例全部通过，覆盖文本掩码 16 条 + JSON 路径 4 条
- 覆盖矩阵：空值、普通文本、Bearer、Basic、短凭据、引号包裹凭据、裸 Authorization/Cookie、键值形态、复合键名、布尔值、URL userinfo（含仅口令）、JSON 非敏感键、JSON 数组元素、JSON 敏感键名
- 接口契约未变：`exMessage` 字段名、类型、可空性保持原样，仅取值被掩码
- spotless / checkstyle / spotbugs / pmd 通过

## 用户自测反馈与检视闭环

- P1（JSON 分支绕过）：`mask()` 在 JSON 路径只按"键名"判敏感，`{"msg":"password=hunter2"}` 这类非敏感键值可绕过全部规则。**确认为真问题**，commit `cf2cc4021` 修复并补 3 条用例
- "写入侧明文落库"：确认为既有架构问题（落库前不做掩码），不属于查询出参链路，已回复认可并建议单独立项，本 PR 不改
- "不补尾引号"：与当前实现不符（`maskKeyValues` 已用 `first + MASK + first` 保留两侧引号），已指出并关闭

## 设计偏差与取舍

- 选择在查询出口统一掩码，而非要求业务方改造异常抛出点：存量异常与第三方 SDK 异常无法逐个约束
- 误伤优先于全覆盖：凭据需长度 ≥6 且含数字/大写/符号，布尔值排除，接受"极少数异常格式凭证漏掩"的残余风险
- 未与写入侧联动：写入去敏涉及存储格式与历史数据，独立立项更稳妥

## 待办

- Issue #551 仍为 open，需在页面回归确认后关闭

## 可复用经验

- 自由文本脱敏的正则顺序不能交换：URL userinfo 必须先跑，否则 `:`、`@` 会被后续键值规则误切
- EasyExcel/日志类文本掩码要同时防"误伤"与"漏掩"，用字符组成门槛比单纯长度门槛更稳
- 结构化脱敏实现后必须专门复查"非敏感键"路径，键名白名单天然存在旁路

## 归档日期

2026-11-19
