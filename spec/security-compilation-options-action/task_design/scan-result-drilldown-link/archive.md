# 【openLiBing】插件结果输出增加openLiBing平台扫描结果链接（安全编译选项扫描插件） — 归档

## 关联

- FE 需求：【openLiBing】插件结果输出增加openLiBing平台扫描结果链接
- 业务 Issue：openlibing/code-metrics-action#25
- 业务 PR：openlibing/security-compilation-options-action#27（分支 `scan-result-drilldown-link`，待合入 master）
- 业务 PR：openlibing/openlibing-cicd#598（分支 `scan-result-drilldown-link`，待合入 release_20261019_iter1）
- docs PR：本归档 PR（openlibing/openlibing-docs）
- 同 FE 姊妹文档：[spec/code-metrics-action/task_design/scan-result-drilldown-link/](../../../code-metrics-action/task_design/scan-result-drilldown-link/)（代码度量扫描插件侧，随本 docs PR 一并归档）

## 需求摘要

sec-option-scan 插件上报扫描结果后，工作流概览仅输出 14 项编译选项开启率，用户无法直接进入 openLiBing 平台查看该产物包的详细扫描结果（文件 × 扫描项矩阵、备案明细），只能在平台中按仓库/流水线反复翻找。本需求补齐「链接生成与输出」环节：

- 服务端（openlibing-cicd）：上报响应由 `DataResult<Long>` 扩展为 `recordId + detailLink + tip`；按 repoUrl 解析关联项目取第一个（多项目场景行为确定可预期），生成 `recordId + projectId` 单条详情链接；未录入仓库返回 tip 提示；查询/拼接异常仅告警、降级返回 recordId，不阻断上报。
- 插件（security-compilation-options-action）：上报成功后输出 `ATOMGIT_OUTPUT` 链接行（key 末尾小写 `url` 触发平台渲染为可点击链接）或未录入提示行（服务端 tip）；多产物包逐包输出、每包固定 1 行；输出通道已收敛为单一 `ATOMGIT_OUTPUT`（`ATOMGIT_STEP_SUMMARY` 通道移除）。
- 鉴权模式（OIDC / AK-SK 双模式）、扫描逻辑、上报接口与既有输出保持不变。

## 交付历程

### security-compilation-options-action（分支 scan-result-drilldown-link，PR #27 → master，head `1bfc1bc`）

- commit `31e8aa1`：feat 上报响应解析 detailLink/tip，STEP_SUMMARY 与 OUTPUT 双通道输出链接
- commit `6756858`：补充输出逻辑测试
- commit `dee09d3` / `987bba5`：OUTPUT key 增加 url 标识并调整为 `-url` 结尾（触发平台可点击渲染）
- commit `fb8b382` ~ `ca2fcd3`（4 个）：平台渲染规则验证探针（验证后清理）
- commit `e4320b1` / `9b828e0`：输出通道实验与回退（STEP_OUTPUT ⇄ ATOMGIT_OUTPUT）
- commit `4c38d6f`：docs 示例去除 codeHostingPlatformFlag
- commit `fae1025`：chore 移除验证探针与多余 outputs 声明
- commit `1d1e93a`：chore 文案定稿（安全编译选项扫描结果（<包名>）/ 扫描结果（<包名>）url）
- commit `1bfc1bc`：chore 移除 `ATOMGIT_STEP_SUMMARY` 通道（写入块与相关注释），仅保留 `ATOMGIT_OUTPUT`；README 同步为单通道说明

### openlibing-cicd（分支 scan-result-drilldown-link，PR #598 → release_20261019_iter1，head `2f7ea9735`）

- commit `757bb1506`：feat 上报响应返回 detailLink/tip（响应 VO + 项目查询 + 链接构建 + 单测）
- commit `2f7ea9735`：feat 链接移除 codeHostingPlatformFlag（联调后定稿）

## 用户自测反馈

- beta 环境端到端通过（用户确认）：流水线真实上报 → `ATOMGIT_OUTPUT` 链接输出 → 点击打开产物包详情页，数据与本次上报一致
- 多产物包构建逐包输出、包名与链接一一对应；缺失 `ATOMGIT_OUTPUT` 环境变量时跳过输出并 `core.warning` 告警降级，不影响上报结果
- 反馈：运行详情页中同一链接存在双通道重复呈现，展示位置与形态不可由插件统一控制 → 需求侧决策收敛为仅 `ATOMGIT_OUTPUT` 单通道（commit `1bfc1bc`，T17）
- AK/SK 与 OIDC 双鉴权下输出行为一致；既有 14 项开启率输出格式与内容不变

## 最终验证

- 单测：`SecOptionScanServiceImplTest` 54/54（新增 5 用例：多项目取第一 / `.git` 重试 / 未匹配 tip / DataAccessException 兜底 / 空 gitUrl）
- 冒烟：14 项 + URL 编码代理对（emoji）3 项，全部通过；pre-commit 检查 11/11 通过
- 边界：同一 repoUrl 多项目（仅 1 条链接）、未录入仓库（提示行、无链接）、取数异常（仅 recordId 兜底、无误报提示）
- 兼容：老插件 × 新服务端（`data?.recordId` 命中字符串 recordId，行为不变）；新插件 × 老服务端（无 detailLink/tip 时不输出链接）
- 平台端到端：beta 环境真实流水线引用 `scan-result-drilldown-link` 分支实跑，`ATOMGIT_OUTPUT` 链接输出与点击落地验证通过

## 设计偏差与取舍

1. 链接参数收敛（联调后定稿）：设计初版链接携带 `codeHostingPlatformFlag`（对齐流水线跳转链接范式、用于未登录无感授权）；联调评估后判定非必需（详情页取数仅依赖 recordId），链接收敛为最小参数集 `recordId + projectId`（commit `2f7ea9735`）
2. 文案定稿：「安全编译选项扫描结果（<包名>）」，便于多插件场景识别归属；OUTPUT 链接行 key 为「扫描结果（<包名>）url」、提示行 key 为「扫描结果（<包名>）」
3. 测试网关还原（已闭环）：联调期两插件分支 `cicdUrl`/`coderepoUrl` 曾指向 APIC 测试网关（beta 联调用）；联调完成后 sec 插件 `cicdUrl` 已还原为主干原值 `https://apig.openlibing.com:443`（commit `e0173f7`），cm 插件 `coderepoUrl` 同步还原（commit `ea73f9e`）
4. 链接域名随服务端环境变化：beta/gamma/生产分别生成 `beta.openlibing.com` / `gamma.openlibing.com` / `www.openlibing.com` 域名链接，插件不感知环境（仅消费服务端返回的 detailLink）
5. 输出通道由双通道收敛为单通道（需求决策变更）：初版同时写 `ATOMGIT_STEP_SUMMARY`（Markdown 超链接）与 `ATOMGIT_OUTPUT`（key=value 链接行）；因同一链接在两处分别呈现且展示形态不受插件控制，遂移除 `ATOMGIT_STEP_SUMMARY`，仅保留 `ATOMGIT_OUTPUT`（commit `1bfc1bc`）

## 可复用经验

- OUTPUT key 渲染规则：key 末尾为小写 `url` 时平台将值渲染为可点击链接（大小写敏感）；提示类文本行 key 不带 `url` 后缀，避免提示文本被渲染成无效链接
- 服务端单点定义：链接模板、平台地址（`getOpenlibingHost`）与未录入提示文案均由服务端单点定义，插件不做 URL 拼接与文案硬编码
- 链接构建旁路兜底：链接构建独立异常捕获，异常仅告警、降级返回 recordId，不阻断上报主流程与事务
- 老插件兼容：响应 `data` 由数值变对象时，老插件 `data?.recordId` 解析分支天然兼容（recordId 仅用于日志）
- 输出通道收敛（单通道）：同一链接多通道输出会在运行摘要与任务结果两处分别呈现，且展示位置与形态不可由插件统一控制；插件侧输出统一走 `ATOMGIT_OUTPUT`（代码只写一个通道、只判一个环境变量），运行日志 `core.info` 打印实际链接作为人工查看兜底
- 平台面板渲染不受插件控制：任务结果面板的条目顺序与类型判型（type/desc）由平台决定，外部 action 输出不判型时链接以纯文本呈现；插件侧应以「值本身可直接复制使用」为前提设计输出

## 归档日期

2026-10-15（输出通道收敛为仅 `ATOMGIT_OUTPUT` 后于 2026-10-19 同步更新本文档）
