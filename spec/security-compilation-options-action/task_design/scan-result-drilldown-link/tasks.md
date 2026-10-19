# 【openLiBing】安全编译选项扫描插件结果输出增加openLiBing平台扫描结果链接 — 实现任务

- **业务 Issue**：https://gitcode.com/openlibing/code-metrics-action/issues/25

## 进度: 17/17 complete

## 服务端（openlibing-cicd）

- [x] T1：新增 `vo/secoption/SecOptionScanReportVO`（`String recordId` + `String detailLink`（固定单条链接，多项目取查询第一个项目；未命中/异常时为空）+ `String tip`）
- [x] T2：`RepoInfoMapper` 新增 `queryProjectsByUrl`（接口 + XML：`SELECT project_id, MAX(platform) AS platform FROM repo_info WHERE repo_url = #{repoUrl} AND project_id IS NOT NULL GROUP BY project_id ORDER BY project_id`；无 `assume_pr` 过滤，参数化 SQL，复用 `repoInfoMap` resultMap；**服务端取排序第一行作为唯一项目**）
- [x] T3：`SecOptionScanServiceImpl` 注入 `PipelineService`，新增 `buildReportVO(recordId, gitUrl)` / `resolveProject`（精确匹配 → 补 `.git` 重试；命中取查询**第一行** projectId 生成唯一 1 条链接（不再查询项目名称，响应不含项目名称）；未命中不返回链接、返回 tip 提示文案；查询/拼接异常兜底仅告警、不返回 tip）；链接拼接为 `recordId + projectId`（联调后移除 `codeHostingPlatformFlag`，commit `2f7ea9735`）
- [x] T4：`reportScan` 组装 VO 返回（recordId 字符串化，`DataResult.successData`）
- [x] T5：`BuildArtifactController#reportSecOptionScan` 返回类型改为 `DataResult<SecOptionScanReportVO>`
- [x] T6：单测/回归：`SecOptionScanServiceImplTest` 54/54 通过（新增 5 用例：multiProjectsTakesFirst / retriesWithGitSuffix / unmatchedRepoReturnsTip / dataAccessExceptionReturnsRecordIdOnly / blankGitUrlReturnsTipWithoutQuery）

## 插件（security-compilation-options-action）

- [x] T7：`dist/uploaders/CicdUploader.js#parseResult` 解析 `detailLink`（字符串）/ `tip`（保留原有 recordId 兼容分支）
- [x] T8：`dist/scanner.js` 上传成功后 `uploadInfo` 携带 `detailLink` / `tip`
- [x] T9：`dist/index.js` 输出规则（文案定稿）：ATOMGIT_OUTPUT 保留 key=value 概览行（链接行 `扫描结果（<包名>）url`=链接——key 末尾小写 `url` 触发平台渲染为可点击链接；提示行 `扫描结果（<包名>）`=提示文案；均空不输出）；判环境变量、失败 `core.warning` 兜底；每条内容 `core.info` 打印（原 STEP_SUMMARY 通道见 T17）
- [x] T10：`dist/index.js` 内联副本同步（scanner + uploader + 输出规则），保持 bundle 单文件分发
- [x] T11：鉴权模式保持核实（不改动）：`ApigSigner` 类、`AKSK_REPORT_PATH` 常量、`useOidc`/`apigAppKey`/`apigAppSecret` 参数与分支、`action.yml` 的 `apig-app-key`/`apig-app-secret` 输入项全部保留；本次改造仅限输出链路
- [x] T12：README 输出章节补充链接（`ATOMGIT_OUTPUT` 链接行/提示行）与未录入提示说明及示例；AK/SK 说明保持现状
- [x] T13：冒烟测试全通过（14 项 + URL 编码代理对 3 项）：stub 上报响应 → 单链接 1 行输出 / tip 非空输出提示行 / 两者均空不输出 / 上报失败不输出 / 无 ATOMGIT_OUTPUT 时跳过输出 / 两种鉴权模式均正常输出

## 联调验证

- [x] T14：beta 环境端到端通过（用户确认）：真实流水线上报（OIDC 与 AK/SK 双鉴权均验证）→ OUTPUT 链接输出 → 点击打开产物包详情页，展示数据与本次 recordId 一致
- [x] T15：边界场景验证通过：同一 repoUrl 多项目（仅返回查询第一个项目 1 条链接）、未录入仓库（输出提示行、不输出链接）、服务端取数异常（仅返回 recordId 兜底，不输出误报提示）
- [x] T16：兼容回归：存量插件 × 新服务端（老插件解析 `data?.recordId` 命中字符串 recordId，行为不变，代码级确认）
- [x] T17：输出通道收敛（需求决策变更）：移除 `ATOMGIT_STEP_SUMMARY` 通道（写入块与相关注释），仅保留 `ATOMGIT_OUTPUT`；README 同步改为单通道说明（commit `1bfc1bc`）

## 流程交付（Phase 4 / 5）

- [x] 业务 PR：openlibing/security-compilation-options-action#27（分支 `scan-result-drilldown-link` → master）、openlibing/openlibing-cicd#598（分支 `scan-result-drilldown-link` → release_20261019_iter1）；均关联 Issue #25、打 `ai-assisted` 标签
- [x] 用户自测确认完成；本 spec 三件套 + 归档文档随 docs PR 提交（与代码度量插件文档同属本 FE，随同一 docs PR 归档）
