# operation-log-exmessage-masking: 操作日志 exMessage 凭证明文暴露修复

## 需求背景

操作日志查询出参对 `old_data` / `new_data` / `params` 做了递归敏感字段掩码，但 `ex_message`（异常信息）被遗漏，原样返回给前端。异常信息中常见上游错误响应体、URL、认证头，会把下游系统的 token / 密码 / 连接串口令等明文暴露给有操作日志查看权限的项目成员。

与"字段级敏感键名"不同，`ex_message` 是自由文本，异常栈与上游响应体没有稳定的结构，单纯按 JSON 键名判定覆盖不到。

- 关联 Issue：https://gitcode.com/openlibing/openlibing-cicd/issues/551
- 关联 PR：https://gitcode.com/openlibing/openlibing-cicd/pulls/685

## 功能描述

- 新增 `OperationLogSensitiveMasker.maskText(String)`：面向自由文本的凭证模式掩码，输入空/空白时原样返回
- 掩码规则按固定顺序串联：
  1. URL userinfo：`scheme://user:password@host` → 口令段替换为 `***`（用户名可缺省，覆盖 Redis / AMQP 的"仅口令"写法）
  2. 认证方案头：`Bearer` / `Basic` 后的凭据掩码；凭据需长度 ≥6 且含数字/大写/符号，避免误伤 `bearer token` 之类的普通英文
  3. 裸认证头与会话头：`Authorization` / `Proxy-Authorization` / `Cookie` / `Set-Cookie` 整行掩码（已由第 2 条处理的不重复处理）
  4. 键值形态：`password|passwd|pwd|secret|token|access_token|private_key|app_secret|api_key|access_key(_id/_secret)` 等键名后的值掩码，兼容引号/JSON 包裹，排除 `yes|no|true|false` 等布尔诊断值
- `mask()` 行为对齐：非 JSON 输入回退到 `maskText`；JSON 中非敏感键的字符串值同样过一次 `maskText`；数组内的字符串元素同样处理
- `LoggingServiceImpl` 查询出参组装处补一行 `row.setExMessage(OperationLogSensitiveMasker.maskText(row.getExMessage()))`

## 验收标准

- [x] `maskText` 对 `null` / 空串 / 空白原样返回
- [x] URL 内嵌凭证被掩码：`redis://:secret123@10.0.0.1:6379` → `redis://:***@10.0.0.1:6379`
- [x] `Bearer` / `Basic` 后的凭据被掩码，短凭据、引号包裹凭据均覆盖
- [x] `Authorization: xxx`、`Cookie: xxx` 整行掩码
- [x] 键值形态覆盖复合键名（`accessKeyId`、`access_key_secret`、`app_secret`、`private_key` 等）
- [x] 引号包裹的含空格值整段替换并保留原引号，不被空格截断
- [x] 普通英文（如 `token expired, please retry`）不被误掩
- [x] `mask()` 对非 JSON 文本回退 `maskText`，不再原样返回
- [x] `mask()` 对 JSON 中非敏感键的字符串值、数组字符串元素也执行凭证掩码
- [x] `mask()` 仍能按敏感键名整段掩码，原有行为不回退
- [x] `LoggingServiceImpl` 查询出参的 `exMessage` 已过掩码
- [x] `OperationLogSensitiveMaskerTest` 共 20 条用例全部通过
- [x] 无 HTTP 接口契约变化、无数据模型变化、无配置项新增

## 影响范围

| 文件                                                                                         | 操作 | 说明                                                                            |
| -------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/cicd/common/operationlog/OperationLogSensitiveMasker.java`     | 修改 | 新增 `maskText` 与四条凭证正则；`mask` 增加纯文本回退、非敏感键值与数组元素掩码 |
| `src/main/java/com/openlibing/cicd/business/service/impl/LoggingServiceImpl.java`            | 修改 | 查询出参组装时对 `exMessage` 调用 `maskText`                                    |
| `src/test/java/com/openlibing/cicd/common/operationlog/OperationLogSensitiveMaskerTest.java` | 修改 | 新增 20 条用例覆盖文本掩码与 JSON 回退                                          |

无 pom 变更、无新增依赖。
