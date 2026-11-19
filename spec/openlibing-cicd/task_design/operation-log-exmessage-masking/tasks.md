# operation-log-exmessage-masking: 实现步骤

## 编码

- [x] 在 `OperationLogSensitiveMasker` 中预编译四条凭证正则（URL userinfo / 认证方案头 / 裸认证头 / 键值形态）
- [x] 新增 `maskText(String)`，按固定顺序串联四条规则，空值原样返回
- [x] 新增 `maskKeyValues`，用 `appendReplacement` 保留引号包裹形态
- [x] `mask()` 非 JSON 输入回退 `maskText`，不再原样返回
- [x] `maskNode` 对非敏感键的字符串值、数组字符串元素执行 `maskText`
- [x] `LoggingServiceImpl` 查询出参组装时对 `exMessage` 调用 `maskText`

## 测试

- [x] 覆盖空值 / 空白 / 无凭证普通文本原样返回
- [x] 覆盖 Bearer / Basic / 短凭据 / 引号包裹凭据
- [x] 覆盖裸 `Authorization` / `Cookie` 整行掩码
- [x] 覆盖键值形态、复合键名、含空格引号值、布尔值不误伤
- [x] 覆盖 URL 内嵌凭证（含仅口令形态）
- [x] 覆盖 `mask()` 对非 JSON 文本回退、对 JSON 非敏感键值与数组元素掩码
- [x] 覆盖原 JSON 敏感键名掩码行为不回退
- [x] 本地执行 `OperationLogSensitiveMaskerTest` 20 条用例全部通过
- [x] spotless / checkstyle / spotbugs / pmd 通过

## 评审整改

- [x] 修复 P1：JSON 分支非敏感键值绕过掩码，统一过 `maskText`
- [x] 补充 3 条用例：非敏感键凭证、数组元素凭证、普通文本不误伤
- [x] 就"写入侧明文"与"尾引号"两条意见给出结论并回复检视

## 交付

- [x] 业务分支 `fix-551-log-exmessage-masking` 提交并推送
- [x] 业务 PR #685 创建并关联 Issue #551，打 `ai-assisted` 标签
- [x] PR 合入 master（merge commit `bc59ded1a`）

## 回归（前端配合，待人工执行）

- [ ] 流水线日志页 →「失败信息」列，改造后异常文本正常展示，凭证段显示为 `***`
- [ ] 操作日志「数据详情」弹窗，`exMessage`、`oldData`、`newData`、`params` 展示正常
- [ ] 无敏感信息的异常文本不应出现 `***`（误伤检查）

## 检视跟进待办（本次未覆盖）

- [ ] 落库前掩码：`ex_message` 写入时同样过 `maskText`，避免库表直读暴露明文（待立项）
- [ ] 异常信息长度截断：按 Issue 要求限制 `ex_message` 落库长度，避免超长异常栈（待立项）
- [ ] 跨仓整改：`openlibing-coderepo` 的 `LoggingServiceImpl.maskRow`（第 420 行）同步补 `exMessage` 掩码
- [ ] 存量数据评估：确认已落库 `ex_message` 明文是否需要刷洗
