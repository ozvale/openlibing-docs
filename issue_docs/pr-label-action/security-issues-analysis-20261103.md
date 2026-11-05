# pr-label-action 安全 issue 定性分析（2026-11-03）

> 分析基准：`upstream/main`（HEAD: b26940e）。本地仓 HEAD 1f6bee3 与 upstream/main 在 `src/`、`action.yml` 上完全一致（仅 `.gitcode/workflows/` 两个文件落后 2 个 merge commit），下文行号以 upstream/main 为准。
> 本批覆盖 open 的 3 条安全 issue：#8、#12、#13。#10（接入接口兼容性扫描 workflow）为功能需求，不纳入安全整改。
> 历史已关闭 #3 / #4 / #5 / #7 / #9 / #11 已由 commit d1cf324（token 改 Bearer + 全链路 redact + 默认地址白名单）与 2dd81f9（endpoints 集中配置 + 标签名 encodeURIComponent）覆盖，本批不重复分析，仅对同根因残留做比对。

## 汇总

| 分类 | Issue | 处理建议 |
| ---- | ----- | -------- |
| 真问题·等价加固（可直接做） | #12 | `maskToken` 统一遮蔽为 `****`，不再保留首末各 2 字符；只改日志内容，不改任何接口行为 |
| 真问题·等价加固（可直接做） | #13 | 点 1（labelName 未编码拼 URL）已由 #11 的 `encodeURIComponent` 修复；点 2（日志注入）新增日志出口清洗（剥离 CR/LF 与控制字符） |
| 非问题（用户决策 2026-11-03） | #8 | 互斥标签并发竞态按非安全问题处理，本轮不做任何改动，暂不处理 |
| 非安全项，不处理 | #10 | 功能需求（api-scan workflow），不在本流程范围 |

---

## 一、#12 token 掩码保留首末各 2 字符落日志【中】

### 1.1 现状核实

| 位置 | 现状 | 结论 |
| ---- | ---- | ---- |
| [src/index.js:35-38](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L35-L38) | `maskToken` 逻辑：`str.substring(0, 2) + "****" + str.substring(str.length - 2)`，长度 ≤4 时直接 `****` | 属实，token 首末各 2 字符落日志 |
| [src/index.js:42-53](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L42-L53) | `redact` 先按实际 token 值替换为 `maskToken(token)`，再兜底替换 `access_token=...` 与 `Bearer xxx` | #4 整改后全链路日志已过 redact，明文 token 本身不再落日志；残留仅为“掩码露出 4 字符” |
| [src/index.js:145-172](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L145-L172) | 请求 URL / headers / body、响应 headers / body、错误消息均经 `redact` | 覆盖完整，无旁路日志 |
| `dist/index.js` | 已确认包含同一 `substring(0,2)+"****"` 实现，源码与产物同步 | 无 dist 漂移 |

补充：`info(`  Token: ${TOKEN_SOURCE}`)`（[src/index.js:321](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L321)）只打印 token 来源（`input` / `ATOMGIT_TOKEN` / `none`），不打印值，无泄露。

### 1.2 风险与定性

- token 鉴权已改为 `Authorization: Bearer`（#9 整改），不再随 URL 进入平台/代理访问日志，剩余风险仅为流水线日志中暴露 32 位以上 token 的首末各 2 位（4 字符）。
- 属**日志脱敏**形态（硬规则 1 白名单），改成全遮蔽不改变任何 API 调用、输出变量与失败语义。
- 定性：**真问题·等价加固**，可直接实施。

### 1.3 整改方案

- `maskToken` 直接返回 `"****"`（删除首末字符保留逻辑）。
- 影响面：所有经 `redact` 的日志文本中，token 位置由 `xx****xx` 变为 `****`。日志内容变化属日志脱敏允许范围，不构成对外契约。
- `dist` 由 `npm run package` 重建，不手改产物。

---

## 二、#13 日志输出未转义用户输入（日志注入）【低】

### 2.1 逐点核实

| 序号 | issue 描述 | 现状（upstream/main b26940e） | 结论 |
| ---- | ---------- | ----------------------------- | ---- |
| 1 | `src/index.js:182` labelName 未编码直接拼入 URL | [src/index.js:209](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L209) 已为 `${api}/pulls/${prNumber}/labels/${encodeURIComponent(labelName)}`；`addLabel` 的标签名走 JSON 请求体（[src/index.js:193](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L193)），不拼 URL | 已由 #11 修复（同根因），本批无需再改 |
| 2 | `src/index.js:121-125,141,219-220` 含原始标签名的 URL、响应体、names 原样输出 | 行号已随 #4/#5 整改偏移，实际残留见 2.2 清单；`info` / `warning` 直接 `console.log`，无 CR/LF 与控制字符清洗 | 属实，需整改 |

### 2.2 日志注入残留点（当前行号）

| 位置 | 外部数据 |
| ---- | -------- |
| [src/index.js:145](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L145) | 请求 URL（含已编码 labelName） |
| [src/index.js:147-150](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L147-L150) | 请求头、请求体（含原始 labelName） |
| [src/index.js:163-165](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L163-L165) | API 响应头、响应体（平台返回内容） |
| [src/index.js:187,195,199,202](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L187-L202) | addLabel 的 labelName、错误 message |
| [src/index.js:207,214,218,222](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L207-L222) | removeLabel 的 labelName、错误 message |
| [src/index.js:248](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L248) | 现有标签名列表（names） |
| [src/index.js:252,256](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L252-L256) | JSON 解析错误 message、HTTP 状态 |
| [src/index.js:322-323,352,355](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L322-L355) | add/remove 标签清单、SKIP 清单 |
| [src/index.js:396-398](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L396-L398) | 结果汇总中的标签名 |

### 2.3 风险与定性

- 攻击面：`add_labels` / `remove_labels` 来自工作流配置（仓库维护者可写）；响应体/标签名来自平台数据。PR 作者一般无法直接控制标签名，因此实际可利用性低，issue 自身也标注“实际风险较低”。
- 若标签名含 `\n`，可在流水线日志中伪造后续行（如伪造 `::warning::` / 结果块），干扰人工判读，不影响标签操作结果。
- 属**日志清洗/脱敏**形态（硬规则 1 白名单），不改变 API 调用与标签状态。
- 定性：**真问题·等价加固**，可直接实施。

### 2.4 整改方案（待裁决 A/B）

| 方案 | 改动 | 说明 |
| ---- | ---- | ---- |
| A（建议） | 在日志出口 `info()` / `warning()` 内统一 `sanitizeLog`：剥离 `\r`、`\n` 与 `\x00-\x1F`、`\x7F` 控制字符（替换为空格） | 覆盖全部出口，后续新增日志自动受保护；与 upload-sarif-action 的 console 出口统一清洗口径一致。`setFailed` 的 `console.error` 保留原样（错误栈需要换行） |
| B | 逐点只清洗 labelName / 响应体 / names 的插值处 | 改动面更小，但新增日志点容易漏 |

- `dist` 由 `npm run package` 重建。
- 说明：`::warning::` 工作流命令本身也在被清洗的字符串内，清洗只作用于消息内容，不影响命令前缀。

---

## 三、#8 互斥状态标签并发竞态（TOCTOU）— 非问题（用户决策）

> **决策**：2026-11-03 用户明确「#8 非安全问题，先不管」。本节保留证据备查，后续扫描再命中同根因时直接复用该结论，不重复分析。

### 3.1 现状核实

| 步骤 | 位置 | 现状 |
| ---- | ---- | ---- |
| 读取 | [src/index.js:329](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L329) `fetchLabels` | 单次 GET，无 ETag / 版本号 |
| 过滤 | [src/index.js:344-357](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L344-L357) | 基于读取结果过滤 add / remove |
| 写入 | [src/index.js:374-392](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L374-L392) | 先逐个 POST 添加，再逐个 DELETE 删除；单步失败仅置 `allOk=false`，无重试、无回滚 |
| 无锁 / 串行化 | 全文件 | 无本地锁、无平台原子批量写、无写后复核 |

消费方现状（证据）：

- 本仓 [.gitcode/workflows/pre-commit.yml](file:///e:/work/huawei/fork/pr-label-action/.gitcode/workflows/pre-commit.yml)：`initiate` 阶段加 `ci-pipeline-running` 并删 `passed,failed`，`post` 阶段加 `passed/failed` 删 `running`，**未配置 `concurrency`**。
- openlibing-docs 仓 `.gitcode/workflows/pre-commit.yml` 同一模式，同样**未配置 `concurrency`**。

因此两条流水线交错时确实可能出现 `passed` 与 `failed` 并存，或残留过期 `running`。确定性部分：某一步 DELETE 失败时，该互斥标签会残留，`fail_on_error` 默认 true 只让 step 失败，不纠正标签。

### 3.2 为什么不属于等价加固

- issue 建议的三条修法都改变行为或依赖平台能力：
  1. **工作流层 concurrency 串行化**：改动落在各消费仓工作流，不在本插件；且会改变流水线排队语义（新提交取消旧运行），影响面大。
  2. **平台原子批量标签接口**：需先确认 GitCode API v5 是否提供标签全量替换/原子批量接口；若采用“全量替换”，还会覆盖插件未接管的其它标签（如人工加的 `lgtm`），属**输出契约/默认行为变化**（硬规则 2-1/2-2）。
  3. **写后复核 + 重试**：复核仅告警属等价加固；但“重试删除”会改变请求次数与失败语义（硬规则 2-4），需评审。
- 定性修订：2026-11-03 用户决策按**非安全问题**处理，本轮不做插件侧改动；真正的互斥保证仍建议由消费方工作流加 `concurrency` 解决。

### 3.3 候选方案（本轮不采纳，仅备查）

| 方案 | 改动 | 分类 | 说明 |
| ---- | ---- | ---- | ---- |
| A | 写入完成后重新 `fetchLabels`，检测互斥集合并存时输出 `::warning::`（可选新增输入 `verify_mutex_labels`，缺省关闭＝零行为变化） | 等价加固（仅观测） | 插件侧能做到的上限；不纠正标签，只暴露问题，需配合消费方 concurrency 才根治 |
| B | 删除失败时重试 N 次（如 2 次，固定小重试） | 失败语义/请求次数变化 → 须评审 | 减少“删除失败残留”的确定性场景，但无法解决跨流水线交错 |
| C | 改用平台原子批量替换接口 | 契约变化 → 须评审 | 需先验证接口存在与语义（是否覆盖未列出标签），风险最高 |
| D | 不做插件侧改动，转由消费方工作流加 `concurrency`，本 issue 按平台/使用方职责归档 | 非问题（平台/使用方） | 与 #6/#7（pwn request、可变 tag）同类口径：门禁正确性属工作流配置职责 |

---

## 四、用户裁决与整改执行记录

### 4.1 用户裁决（2026-11-03）

1. **#8**：非安全问题，先不管（不实施任何方案）。按 Phase 3.4 询问后，用户选择**暂不归档**到知识库，结论仅保留在本定性文档。
2. **#12**：按 `maskToken` 统一遮蔽为 `****` 整改。
3. **#13**：按方案 A（`info()`/`warning()` 出口统一 sanitize）整改。
4. **PR 拆分**：#12 与 #13 合并为一个 PR（同属日志工具区）。

### 4.2 执行记录

| 项目 | 内容 |
| ---- | ---- |
| 整改分支 | `fix-log-sanitize`（基于 `upstream/main` b26940e） |
| 提交 | `614b7ac fix(security): mask token fully and sanitize log output` |
| PR | openlibing/pr-label-action#7（`ai-assisted`） |
| 统一测试分支 | `fix-security-remediation` 已合入，推送至 fork，HEAD `cd984ac` |
| 改动文件 | `src/index.js`、`dist/index.js`（ncc 重建）、`AGENTS.md`（同步函数说明） |
| 验证 | `node --check` 通过；源码函数冒烟通过（CRLF 清洗、`maskToken()` 返回 `****`、`redact` 全遮蔽）；dist 确认包含新实现 |

**业务逻辑影响声明**：本改动未触及业务逻辑。仅日志文本变化（掩码 `xx****xx`→`****`、日志中 CR/LF 与控制字符替换为空格），API 请求/响应、标签状态、输出变量、退出码与 `fail_on_error` 语义均不变。

**待办**：用户拉取 `fix-security-remediation` 自测通过后，才合入 main 并归档；自测通过后再将「日志注入清洗」方案回写 playbook。
