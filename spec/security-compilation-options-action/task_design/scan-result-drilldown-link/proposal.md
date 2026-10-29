# 【openLiBing】安全编译选项扫描插件结果输出增加openLiBing平台扫描结果链接

- **FE 需求**：【openLiBing】插件结果输出增加openLiBing平台扫描结果链接
- **业务 Issue**：https://gitcode.com/openlibing/code-metrics-action/issues/25
- **涉及仓库**：security-compilation-options-action（插件输出侧）、openlibing-cicd（上报响应与链接构建侧）
- **流程模式**：Full
- **日期**：2026-09-29

## 1. 需求背景

安全编译选项扫描插件（sec-option-scan）在流水线中扫描构建产物并上报后，工作流概览（ATOMGIT_OUTPUT）只输出 14 项编译选项的开启率。用户拿到结果后无法直接进入 openLiBing 平台查看该产物包的详细扫描结果（文件 × 扫描项矩阵、备案明细等），只能在平台中按仓库/流水线反复翻找，使用成本高。

平台前端已支持通过 URL 直接打开产物包详情页（`/apps/securityOptions/package-detail?recordId=...`），仅缺"链接生成与输出"环节：扫描记录 ID（recordId）当前虽已在上报响应中返回给插件，但插件未将其拼成平台链接输出，且同一 repoUrl 可能归属多个项目（需由服务端确定唯一跳转目标：取查询第一个项目，不返回多链接）。

## 2. 功能描述

1. **服务端（openlibing-cicd）**：`/build-artifact/sec-option/report` 上报响应由仅返回 recordId（`DataResult<Long>`）改为返回 `recordId + detailLink + tip`（单条详情链接 + 未录入提示）：
   - 按上报的 `gitUrl` 在 `repo_info` 中解析关联项目（同一 repoUrl 可属于多个项目），取查询第一个项目生成详情页链接（仅含 recordId 与 projectId；不返回多链接、不带项目名称）；
   - 未解析到任何项目时不返回链接，返回提示信息（tip）——该 repoUrl 未录入 openLiBing 任一项目，无法生成有效跳转链接；
   - recordId 为雪花 ID，响应中按字符串返回，避免 JS 端精度丢失。
2. **插件（security-compilation-options-action）**：上报成功后解析 `detailLink` / `tip`，单通道输出：ATOMGIT_OUTPUT 按产物包输出 `扫描结果（<包名>）url=<链接>` 概览行（每包固定 1 行；key 末尾小写 `url` 触发平台渲染为可点击链接，大小写敏感）；提示非空且无链接时输出提示行（`扫描结果（<包名>）=<tip>`，文案由服务端单点定义，插件不硬编码）；同步打印运行日志。（原 `ATOMGIT_STEP_SUMMARY` Markdown 超链接通道已移除，收敛为仅 `ATOMGIT_OUTPUT`。）
3. **插件鉴权模式保持不变**：OIDC 与 AK/SK 双模式并存（部分测试仓不适合纳入 OIDC 认证凭据授权项目），`apig-app-key`/`apig-app-secret` 输入项与旧网关路径全部保留，本次仅改造输出链路。
4. 上报失败时不输出链接（仅保留现有失败提示）。

不涉及：

- 前端改造：平台前端已支持链接直达，本次不改前端
- 插件扫描逻辑、14 项检测器判定口径、`core.setOutput` 数值输出
- 上报接口路径、入参（payload）结构；鉴权模式保持现状（OIDC 与 AK/SK 双模式并存，两套路径均保留）
- 平台域名在插件侧的配置：链接由服务端拼接完整 URL 返回，插件不感知平台地址
- 数据库表结构变更

## 3. 验收标准

- [ ] 上报成功后，工作流概览（ATOMGIT_OUTPUT）出现对应链接行，点击可在 openLiBing 平台直接打开对应产物包详情页（链接由 `recordId + projectId` 定位，打开沿用平台既有登录态），展示数据与本次上报的 recordId 一致
- [ ] 同一 repoUrl 属于多个项目时，仅输出查询第一个项目对应的 1 条链接（不返回多链接；行为确定可预期）
- [ ] 未纳管仓库（repoUrl 在 repo_info 中无匹配）时不输出链接，输出提示「当前仓未录入openLiBing平台，无法生成跳转链接，请先联系SRE完成代码仓录入。」
- [ ] 多产物包扫描时，每个产物包各自输出对应链接/提示，不合并、不遗漏
- [ ] 链接固定为 `recordId + projectId` 两类参数（不含项目名称、平台授权参数等其他字段），复制/分享后可直接打开
- [ ] 上报失败时不输出任何链接；无 `ATOMGIT_OUTPUT` 环境变量时跳过输出（不影响上报结果）
- [ ] 插件鉴权模式保持现状（OIDC 与 AK/SK 双模式并存、`apig-app-key`/`apig-app-secret` 输入项保留），两模式下链接输出行为一致
- [ ] 插件 `core.setOutput` 数值输出与现有 ATOMGIT_OUTPUT 开启率输出保持不变
- [ ] 链接构建/解析异常不影响上报主流程（仅记录告警；异常时不输出误报"未录入"提示）

## 4. 影响范围

- `openlibing/security-compilation-options-action`：`dist/index.js`（输出规则改造：`ATOMGIT_OUTPUT` 链接行/提示行单通道，每包固定 1 行）、`dist/scanner.js`（uploadInfo 携带 detailLink/tip）、`dist/uploaders/CicdUploader.js`（响应解析扩展；AK/SK 逻辑保留不动）、`action.yml`（不改）、README（输出章节链接与未录入提示说明）
- `openlibing/openlibing-cicd`：`BuildArtifactController#reportSecOptionScan` 响应类型、`SecOptionScanServiceImpl#reportScan` 链接构建（取查询第一个项目，`recordId + projectId` 拼接）、`RepoInfoMapper`（新增 `queryProjectsByUrl`：按 repo_url 解析关联项目，`GROUP BY project_id ORDER BY project_id` 取第一行）、新增响应 VO
- 无数据库表结构变更、无新增依赖
