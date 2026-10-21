# 安全漏洞 Issue 批次修复 — 实现任务

## 进度: 10/10 complete

### A 批（#280 #281 #282 #287）

- [x] RuleController / FulltaskController / ProblemshieldController 等 18+ 接口补 userId 必填 + checkPermission + projectId 非 0 校验（commit `1b3566df` 批次1+2、`d3f41187` 批次3）
- [x] openlibing-web 前端调用补 projectId（commit `f773864b` / `333678ec`）
- [x] 补充/更新 Controller 与 Delegate 测试，全量 1483 测试通过

### B 批（#284 #288 #289 #292）

- [x] exportDebugFile 补 userId + projectId 校验 + checkPermission（#284）
- [x] ShieldAll PASS_REVOKE 候选条件归属约束（#288）
- [x] shieldRevoke / shieldPassRevoke 归属校验 checkRevokeOwnership（#289）
- [x] 或签抢占/回滚绑定操作人，回滚操作人显式传参（#292）
- [x] 补充测试（403 越权用例 + 归属断言），全量 1469 测试通过（commit `f1d46781`）

### C 批（#278 #279 #286）

- [x] listCriterions / listCriterionFilters 参数 URL 编码（#278 #279）
- [x] obsUrl 协议/主机白名单 + 超时 + 禁重定向（#286）
- [x] 补充测试（编码断言 + 白名单/302/超时用例，端到端改本地 HttpServer），全量 1470 测试通过（commit `ea6af6f2`）

### D 批（#290 #291）

- [x] #290 按 SIG 结论豁免（维持 tag 引用），评论记录
- [x] #291 技术核实后豁免（secure 属性不存在），评论记录并建议部署层跟踪
