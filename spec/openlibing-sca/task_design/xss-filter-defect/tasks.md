# 93 xss-filter-defect — 实现任务

## 进度: 1/1 complete

- [x] Task 1: `scanConfirmParseV2` 移除 `DefenseXssUtil.htmlEntityEncode` 调用，`clarifyRemark` 原样入库，删除无用 import（`cbf8645d`）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                               | 关联                                                  |
| ---------- | ------------------------------------------------------------------ | ----------------------------------------------------- |
| `cbf8645d` | fix(dm): store clarify remark verbatim, drop DefenseXssUtil encode | 提交 message 未写 `Refs #93`（按 issue 主题回溯关联） |

关键 diff（1 个文件，+1 / -3 行）：

- 删除 `import com.openlibing.sca.common.utils.DefenseXssUtil;`
- 删除 `String clarifyRemark = DefenseXssUtil.htmlEntityEncode(issuePo.getClarifyRemark());`
- `new TblConfirmReview(...)` 的 `clarifyRemark` 实参改为 `issuePo.getClarifyRemark()`

验证方式：

- 静态核实：`OpenScanDMServiceImpl` 当前 L1230 直接传 `issuePo.getClarifyRemark()`；全仓 grep `DefenseXssUtil` 仅命中其自身类与 `DefenseXssUtilTest`，无生产调用方。
- 静态核实：全仓无 `OncePerRequestFilter` / `XssFilter` / `Content-Security-Policy` 相关实现（全局过滤器未建立）。
- 单测：本提交**未新增或修改测试**；`OpenScanDMServiceImplTest` 中 `scanConfirmParseV2` 用例只断言返回的 `scanFile` 结果，未断言 `clarifyRemark` 落库值。本次回溯未执行 `mvn test`。

## 备注：与 issue 验收标准的差异

issue 期望"修复 `htmlStr` + 建立全局清洗 + 富文本白名单回归 + 策略文档"。本轮实际只解决了"备注被过滤器污染"这一数据完整性问题，并**移除了该字段的后端清洗**；`htmlStr` 缺陷、全局过滤器、CSP、策略文档均未覆盖，存储型 XSS 的残余风险转移给前端输出编码（未验证）。详见 `design.md` 风险表。
