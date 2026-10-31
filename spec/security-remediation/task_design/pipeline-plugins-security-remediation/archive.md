# archive: 流水线插件安全整改（8 仓）

- **归档日期**: 2026-10-31
- **关联**: [proposal.md](./proposal.md) / [design.md](./design.md) / [tasks.md](./tasks.md)
- **状态口径**: 整改 PR 均已合入默认分支；**部分 issue 仍处「须评审 / 暂缓 / 待补漏」状态，尚未全部闭环**，遗留项见第 4 节。

## 1. 交付结果总览

| 仓库 | 已合入安全 PR | 定性文档 |
|---|---|---|
| upload-sarif-action | #18 | `issue_docs/upload-sarif-action/security-issues-analysis-20261012.md` |
| upload-ut-action | #1、#3、#4、#5 | `issue_docs/upload-ut-action/security-issues-analysis-20261020.md` |
| pre-commit-action | #12、#13、#15、#20 | `issue_docs/pre-commit-action/security-issues-analysis-20261012.md` |
| pr-label-action | #3、#6 | `issue_docs/pr-label-action/security-issues-analysis-20261012.md` |
| pr-sync-action | #9 | `issue_docs/pr-sync-action/security-issues-analysis-20261020.md` |
| security-compilation-options-action | #31、#32、#33、#34 | `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md` |
| code-metrics-action | 安全 PR 已全部合入（open 列表已无安全项） | `issue_docs/code-metrics-action/security-issues-analysis-20261027.md` |
| huaweicloud-oidc-sdk-nodejs | #11、#12、#13、#14 | `issue_docs/huaweicloud-oidc-sdk-nodejs/security-issues-analysis-20261026.md` |

> PR 状态以 2026-10-31 `gitcode pr list -s merged` 实测为准。各仓当前 open PR 均为非安全类（api-scan workflow、UT 门禁、report_dir 重命名等）。

## 2. 处置结果统计口径

| 分类 | 处置 | 统计归属 |
|---|---|---|
| 真问题 · 等价加固 | 已实施并合入 | 已修复 |
| 真问题 · 须评审 | 已出影响评估并批准后实施；未批准者挂起 | 已修复 / 待评审 |
| 非问题 | 逐条确认后归档，附结论关闭 issue | **统一归入已修复 / 已处置**，不计入未修复 |
| 平台 / 后端依赖 | 标注暂缓，单独跟踪 | 不计入插件仓未修复数 |
| 功能需求类 | 移出安全整改范围 | 不计入统计 |

`pr-sync-action` 尚未完成全量闭环，单独列出，不与其他仓合并统计。

## 3. 知识沉淀

| 沉淀物 | 位置 | 本轮新增内容 |
|---|---|---|
| 整改方案库 | `issue_docs/security-remediation-playbook.md` | 公网地址集中配置、凭证传递收口、命令数组化、路径 realpath 终裁、日志 sanitize、临时文件治理、TLS 原生键名、产物治理 |
| 非问题判定库 | `issue_docs/security-non-issue-catalog.md` | 自有门禁可变 tag、pwn request 门禁形态、`id-token: write`、内联第三方产物、受信配置方输入、平台侧承接项 |
| 整改流程 | `.agents/skills/gitcode-security-remediation/` | 四阶段流程 + 六条硬规则 + 暂缓回退机制 |

## 4. 遗留项（尚未闭环）

### 4.1 等价加固待提 PR

| 仓库 | Issue | 内容 |
|---|---|---|
| upload-sarif-action | #27 | 临时目录不清理 |
| upload-sarif-action | #31 | 日志注入（外部字符串未清洗） |
| upload-sarif-action | #28 | 构建产物 zip 入库 |

### 4.2 须评审 / 补漏

| 仓库 | Issue | 内容 | 当前状态 |
|---|---|---|---|
| upload-sarif-action | #26、#29 | 扩展名/大小校验、region 校验 | 须评审，影响评估待出 |
| pr-sync-action | #11、#16、#21、#22 | AppCode 响应日志与非 2xx 错误消息未脱敏（PR #9 仅覆盖 OIDC 路径） | 半整改收口待补 |
| pr-sync-action | #9、#12、#13、#18 | 令牌中转第三方网关、http 明文降级、轮询下限、静默吞错 | 须评审 |
| pre-commit-action | #48、#43 | 日志注入、报告目录跨任务残留 | 待评估后提 PR |
| code-metrics-action | — | 检视意见收口；lizard 模块遮蔽评估 | 待处理 |
| huaweicloud-oidc-sdk-nodejs | #11 | 账号 ID 是否属敏感信息 | 建议非问题归档，待裁决 |

### 4.3 暂缓（平台 / 后端依赖）

| 事项 | 关联 issue | 恢复条件 |
|---|---|---|
| SARIF / 覆盖率对象 ACL 维持 `public-read` | upload-sarif #11/#25；upload-ut #1/#15/#18/#21 | 后端支持带凭证 / 预签名 URL 下载 |
| 对象 Key 增加组织维度 | upload-ut #11 | 后端 Key 结构契约升级 |
| 端到端报告签名 | sec-comp #21 | 后端联调排期（审计/存证能力） |
| App Code 静态凭证回退 | pr-sync #10 | 流水线全量声明 `id-token: write` + 网关全量 IAM |
| `@actions/io` 内联 `chmod 0666` | pr-sync #20 | 上游依赖升级或替换 |
| 标签并发竞态 | pr-label #8 | 需平台原子批量标签接口或工作流串行化（逻辑 bug，暂缓） |

## 5. 关键经验

1. **双基线核实**：必须同时核对交付态（默认分支）与在途态（PR / 统一测试分支），否则易把未合入修复误记为已修复（pr-sync 首轮即出现该偏差）。
2. **防半整改**：鉴权通道、脱敏改动必须做全调用点清点表，PR 描述需与 diff 逐条比对（pr-sync AppCode 分支曾遗漏）。
3. **SDK 键名陷阱**：`sslVerify` 与 `ssl_verify` 混用会让 TLS 校验静默失效，整改后必须回读 SDK 源码并加单测断言。
4. **产物纪律**：`dist/` 由打包重建，源码与产物同提交；多 PR 同改产物时按目标分支重建而非解二进制冲突。
5. **定性先于编码**：须评审项（七类行为变更）必须先出《业务逻辑影响评估》，未经批准不动代码。
6. **非问题也是资产**：归档理由与决策日期能显著降低下一批扫描的重复处置成本。

## 6. 后续

1. 按第 4 节清单清零遗漏项，优先补齐 pr-sync AppCode 脱敏（同一段代码半整改风险最高）。
2. 将本轮新增模式（可预测临时文件名、对象 Key 段清洗、SDK 键名校验、双基线核实、symlink realpath 终审）写入 playbook / catalog。
3. 平台侧登记：runner 隔离、workflow permissions 收敛、checkout 凭证传递（GIT_ASKPASS）、后端带凭证下载。
4. 流程自动化：定性文档生成、影响声明校验、dist 一致性校验、统一测试分支同步纳入 skill。
