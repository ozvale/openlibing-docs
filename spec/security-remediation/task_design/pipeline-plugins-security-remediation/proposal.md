# proposal: 流水线插件安全整改（8 仓，150+ issue）

- **涉及仓库**: upload-sarif-action、upload-ut-action、pre-commit-action、pr-label-action、pr-sync-action、security-compilation-options-action、code-metrics-action、huaweicloud-oidc-sdk-nodejs
- **流程模式**: Full（跨 8 仓、跨模块、含外部契约与部署链路影响）
- **日期**: 2026-10-31
- **定性依据**: 各仓 `issue_docs/<repo>/security-issues-analysis-*.md`

## 1. 背景

openLiBing 的流水线能力由一组 GitCode Action 插件与一个 OIDC 认证 SDK 承载，覆盖构建、打包、PR 门禁、Nightly 扫描、覆盖率上报、SARIF 上报、标签同步等环节。这些插件统一运行在 GitCode 提供的容器 / 自托管 runner 上，直接持有仓库令牌、OBS 凭证、CI 日志与源码片段等高价值数据。

SenInfo / SENS / CodeQL / 红线落地 / 威胁分析 / argus 持续对上述仓产出 issue，共 150+ 条，特征为：

1. **量大且重复**：同一根因在不同仓、不同批次被反复提出（OBS `public-read`、`sslVerify` 默认关闭、`pull_request_target` 门禁形态、域名硬编码）。
2. **结论与场景强相关**：插件变量多由平台注入、配置方受控，很多「注入 / 越权」指控在当前部署形态下不可利用，照单全改会引入大量无意义分支。
3. **改错代价高**：输入、输出、上报字段、门禁退出码被下游流水线与后端消费，未经评估的行为变化会直接造成线上失败。
4. **留痕要求高**：需要能回答「这条 issue 为什么改 / 为什么不改 / 谁在什么时候拍板」。

核心矛盾不是「怎么改代码」，而是**如何在不动业务逻辑的前提下，建立一套可重复、可评审、可沉淀的处置流程**。

## 2. 目标

| 编号 | 目标 | 验收方式 |
|---|---|---|
| G1 | 对全部 open 安全 issue 逐条完成定性 | 每仓一份定性文档，覆盖该仓全部 open 安全 issue |
| G2 | 真问题按最小等价加固落地，不改变插件对外行为 | 原测试全过 + 新增边界用例 + 默认值/输出契约逐项比对 |
| G3 | 须评审项先出《业务逻辑影响评估》，批准后才编码 | 评审记录 + commit/PR 中的影响声明 |
| G4 | 改动可追溯、可回滚，一 issue（组）一 PR | PR 描述关联 issue，分支可独立回退 |
| G5 | 沉淀跨仓可复用的方案库与非问题判定库 | `security-remediation-playbook.md` / `security-non-issue-catalog.md` 持续增厚 |
| G6 | 每仓提供 `fix-security-remediation` 统一自测分支 | 分支可拉取、可联测、内容与 PR 一致 |

## 3. 非目标

- 不借整改做功能演进、重构、依赖大版本升级、格式化。
- 不替平台侧 / 后端整改（runner 隔离、workflow 级 permissions 收敛、后端下载鉴权）。
- 不追求「扫描器零命中」，被判定的非问题允许保留，靠归档结论去重。
- 不把安全整改与业务需求（如 api-scan workflow）混在同一批次。

## 4. 整改范围

| 序号 | 仓库 | 形态 | issue 范围 | 主要风险类型 |
|---|---|---|---|---|
| 1 | upload-sarif-action | Node Action | #10 ~ #31 | 公网地址、URI 越界读取、snippet 明文、TLS 校验、产物入库 |
| 2 | upload-ut-action | Node Action | #1 ~ #25 | 公网地址、OBS ACL、命令注入、临时文件、TLS 校验、产物入库 |
| 3 | pre-commit-action | Node Action | #20 ~ #48 | 令牌落盘/进 argv、公网地址、临时报告目录、shell 拼接 |
| 4 | pr-label-action | Node Action | #3 ~ #9 | 公网地址、token URL 传参、日志脱敏、标签名编码 |
| 5 | pr-sync-action | TypeScript Action | #1 ~ #22 | token 传参、日志脱敏、公网地址、HTTP 明文降级、轮询阈值 |
| 6 | security-compilation-options-action | Node + Python | #17 ~ #43 | 日志注入、pip 模块遮蔽、符号链接越界、gitUrl 凭证、死代码 |
| 7 | code-metrics-action | Node Action | #22 ~ #71 | obsutil 凭证 argv、命令拼接、临时文件、日志卫生 |
| 8 | huaweicloud-oidc-sdk-nodejs | Node SDK + 3 个测试 Action | #5 ~ #21 | 日志脱敏、npmrc 落盘、签名空指针、undici 依赖漏洞、TLS 校验 |

## 5. 验收标准

1. 8 仓全部 open 安全 issue 有明确定性，无「未分类」遗留。
2. 真问题·等价加固项全部落地，且交付声明中明确「未触及业务逻辑」。
3. 须评审项均有《业务逻辑影响评估》记录，且仅在批准后实施。
4. 非问题项归档到 `security-non-issue-catalog.md`，含判定理由与决策日期。
5. 每条整改 PR 关联对应 issue、打 `ai-assisted` 标签、附影响声明。
6. 每仓 `fix-security-remediation` 分支与已合入整改内容一致。
7. 平台 / 后端依赖项单独登记，不计入插件仓未修复数。

## 6. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 等价加固实际改变行为 | 下游流水线失败 | 默认值逐字节比对；统一测试分支联测；保留原路径兜底 |
| 扫描器重复开单 | 同结论反复处理 | 定性文档 + 非问题库去重，标注决策日期 |
| 多 PR 同改 `dist` 产物冲突 | PR 无法合并 | 按目标分支重新构建，不手工解二进制冲突 |
| 半整改状态（只改部分调用点） | 声称已修复但实际未闭环 | 全调用点清点表 + 双基线核实（交付态 + 在途态） |
