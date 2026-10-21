# 安全漏洞 Issue 批次修复 — 归档

## 关联

- 业务 Issue（已修复 10 个）：
  - #280 规则控制器用户ID参数未验证导致认证绕过（CWE-287，严重）
  - #281 全量检查任务管理接口缺少身份认证机制（CWE-306，严重）
  - #282 问题屏蔽审核接口缺失认证导致未授权访问（CWE-306，严重）
  - #287 屏蔽审批/撤销接口操作者身份可伪造（CWE-287，高危）
  - #284 任务日志下载接口缺少权限校验导致越权访问（CWE-639，高危）
  - #288 屏蔽审核通过后撤销全部缺少服务端归属校验（CWE-639，高危）
  - #289 屏蔽撤销与已审撤销接口缺少资源归属校验（CWE-639，高危）
  - #292 问题屏蔽或签抢占与回滚未按操作人隔离（CWE-362，中危）
  - #278 规则查询接口参数未编码导致 HTTP 参数注入（高危）
  - #279 规则过滤器接口参数未编码拼接 URL 导致参数注入（高危）
  - #286 静态告警接收接口 obsUrl 未校验导致 SSRF 与本地文件读取（CWE-918，高危）
- 业务 Issue（豁免 2 个）：
  - #290 CI 工作流 action 引用未固定 commit SHA（CWE-829，中危）→ SIG 组结论维持 tag 引用
  - #291 Nacos 配置中心明文 HTTP 拉取（CWE-319，中危）→ `config.secure` 属性不存在，需平台开 TLS + 部署层变更
- 业务 PR：!366（分支 A：#280 #281 #282 #287）、!367（分支 B：#284 #288 #289 #292）、!368（分支 C：#278 #279 #286）
- docs PR：本文档

## 交付历程

| 批次 | 分支                         | 修复内容                                                                                                                                                                                                                                                                                    | commit                                                                                 |
| ---- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| A    | `fix-auth-trusted-identity`  | 前端接口补可信身份 + checkPermission 横向鉴权（RuleController/FulltaskController/ProblemshieldController/CheckboardController/FileDownLoadController/SelectionController/SensitiveController/IgnoretreeController/StaticAlarmController 等 18+ 接口）；前端 openlibing-web 同步补 projectId | `1b3566df`（批次1+2，18 文件）、`d3f41187`（批次3，5 文件）；web `f773864b`/`333678ec` |
| B    | `fix-auth-revoke-permission` | 撤销接口越权/并发：exportDebugFile 补 userId+checkPermission（#284）；ShieldAll PASS_REVOKE 候选归属约束（#288）；shieldRevoke/shieldPassRevoke 归属校验（#289）；或签抢占/回滚绑定操作人（#292）                                                                                           | `f1d46781`（8 文件）                                                                   |
| C    | `fix-param-injection-ssrf`   | listCriterions/listCriterionFilters 参数 URL 编码（#278/#279）；downloadAndParse 协议/主机白名单 + 超时 + 禁重定向（#286）                                                                                                                                                                  | `ea6af6f2`（4 文件）                                                                   |

## 用户自测反馈

- 每批次均由用户自测确认完成后才创建 PR，无遗留问题反馈。
- 编码阶段自检发现：分支 B 撤销/审核测试数据缺 userId 归属导致 6 例失败 → 补归属数据修复；shieldAllAudit 未设 auditModel.userId 导致回滚条件为 null 的生产隐患 → rollbackClaimedAudits 改为调用处显式传参。

## 最终验证

- 分支 A：全量 1483 测试 0 失败，编译通过。
- 分支 B：全量 1469 测试 0 失败，编译通过。
- 分支 C：全量 1470 测试 0 失败，编译通过；实测 apigateway SDK `setUrl` 对已编码序列不二次编码，确认无功能回归。
- 三批 PR 均打 `ai-assisted` 标签，关联对应业务 Issue。

## 设计偏差与取舍（用户确认的豁免）

1. **#278/#279「RuleModel 增加输入校验」豁免**：URL 编码已彻底闭合参数注入（`&`/`#`/`=` 百分号编码后仅为值内容）；自由文本搜索字段（ruleName）白名单会误伤合法输入、枚举校验与华为云外部接口契约耦合。已记入 commit `ea6af6f2` body 留痕。
2. **#290 豁免**：SIG 组结论建议使用 tag 引用，不固定 commit SHA；已评论记录，未来引入第三方 action 时再评估。
3. **#291 豁免**：`spring-cloud-alibaba 2025.1.0.0` 的 `NacosConfigProperties` 无 `secure` 字段（javap 验证），`config.secure` 会被静默忽略；`secure` 仅存在于 `NacosDiscoveryProperties`（服务注册语义）。真实传输加密需 CSE Nacos 平台开通 TLS + nacos-client `tls.enable` 系统属性 + 证书信任（cacerts），属部署级变更，单独跟踪。

## 可复用经验（已同步 ai_memory.md）

1. **checkPermission 横向鉴权模式**：接口补 `userId` 必填 + `projectId<=0` 拦截（403「projectId is invalid」）+ `authUtils.checkPermission("/openlibing-codecheck"+路径, projectId, userId)`（403「no permission」）；URL 约定 `/openlibing-codecheck` 前缀。
2. **apigateway SDK `setUrl` 对已编码序列原样保留**（不二次编码，仅规范化 `+`→`%20`）：URL 编码类修复可直接在 URL 构建层 `URLEncoder.encode`，合法值语义不变。
3. **GitCode issue `state_event` 仅接受 open/closed/reopen/close**：CLI 无法设置自定义状态（如"修复中"），需网页手动切换。
4. **报告建议需技术可行性核实**：`javap` 反编译依赖 jar 验证属性是否存在；SDK/框架行为写最小探针程序实测，不凭记忆推断；平台能力无法在代码仓验证时标注为部署级变更。

## 归档日期

2026-10-21
