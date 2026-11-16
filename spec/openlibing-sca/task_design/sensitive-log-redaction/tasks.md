# sensitive-log-redaction — 实现任务

## 进度: 5/5 complete

- [x] Task 1: 删除企业微信接口响应体日志，改固定文案（`6afc9a00`）
  - `sendHttpRequest`：`wechat message send success`、`wechat message send failed`、
    `wechat message send errorStream`；响应流仅 drain
  - 说明：该 commit 的 message 为"改类未使用，需删除"，实际同时包含本修复；issue 正文将其列为修复提交
- [x] Task 2: `getAccessToken` 异常日志去敏感消息并补单测（`72fe1c0c`）
  - `LOGGER.error("getAccessToken exception: {}", e.getClass().getSimpleName())`
  - 新增 `getAccessToken_shouldReturnEmptyAndNotLogSensitiveInfo_whenIoExceptionOccurs`，
    用 `ListAppender` 断言日志不含 gettoken URL、`corpsecret` 与解密密钥
- [x] Task 3: 批扫预期路径日志降级（`9ad54887`）
  - `ScanCommonServiceImpl.extractDiffContent`：JSON 探测失败 ERROR → debug
  - `ProjectNoticeScanAsyncProcessor.processSingleDetail`：ERROR + 堆栈 → 单行 WARN（带 `reason`）
- [x] Task 4: 按检视意见回调级别并最终定稿（`2a521f71`、`471bc3e8`）
  - `2a521f71`：单明细失败 WARN → INFO；patch 非 JSON debug → INFO
  - `471bc3e8`：patch 非 JSON 再回调为 debug（最终态）
- [x] Task 5: 静态核验与交付
  - `WeChatMessageSenderUtil` 中已无 `response` / `errorResponse` 变量参与日志
  - `getAccessToken` 日志不含 `e.getMessage()`
  - 全仓响应体日志排查与 CI 静态规则未做（P2）

## 交付记录

| commit     | 日期       | 摘要                                                                   | 关联                                    |
| ---------- | ---------- | ---------------------------------------------------------------------- | --------------------------------------- |
| `6afc9a00` | 2026-11-09 | 改类未使用，需删除                                                     | 无 Refs（issue 正文指定为修复提交）     |
| `72fe1c0c` | 2026-11-10 | fix(analysis): stop logging exception message in WeChat getAccessToken | `Refs #155`                             |
| `9ad54887` | 2026-11-12 | fix(dm): demote expected patch-parse and scan-detail failure logs      | 无 Refs                                 |
| `2a521f71` | 2026-11-12 | fix(dm): adjust demoted logs from debug/warn to info level             | 无 Refs（检视反馈）                     |
| `471bc3e8` | 2026-11-16 | 修改日志级别                                                           | 无 Refs（patch 非 JSON 最终回调 debug） |

- 分支：`ms_scan`（5 个 commit 均为 HEAD 祖先）
- 映射说明：批次清单给出的是 `72fe1c0c`/`9ad54887`/`2a521f71`/`471bc3e8`，未包含 issue 正文引用的
  `6afc9a00`；后三者 commit message 均无 `Refs #155`，属同批次日志治理，关联关系以本 spec 说明为准
- 验证方式：diff 复核 + 代码现状确认；本轮为回溯文档，**未执行 `mvn test`**（会写入 `target/`，
  超出只读约束）
- 测试覆盖（代码中已存在）：`WeChatMessageSenderUtilTest` 7 个用例，含敏感日志断言
- 未覆盖项：P2 全仓排查与 CI 静态规则；企业微信业务错误码（`errcode`）未解析，HTTP 200 即记成功
