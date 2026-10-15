# 【openLiBing】插件结果输出增加openLiBing平台扫描结果链接（代码度量扫描插件） — 归档

## 关联

- FE 需求：【openLiBing】插件结果输出增加openLiBing平台扫描结果链接
- 业务 Issue：openlibing/code-metrics-action#25
- 业务 PR：openlibing/code-metrics-action#32（分支 `scan-result-drilldown-link`，待合入 master）
- 业务 PR：openlibing/openlibing-coderepo#215（分支 `scan-result-drilldown-link`，待合入 release_20261019_iter1）
- 前端协同：openlibing-web 链接落地能力由前端侧协同（不随本需求提业务 PR；beta 端到端已验证落地效果）
- docs PR：本归档 PR（openlibing/openlibing-docs）
- 同 FE 姊妹文档：[spec/security-compilation-options-action/task_design/scan-result-drilldown-link/](../../../security-compilation-options-action/task_design/scan-result-drilldown-link/)（安全编译选项扫描插件侧，随本 docs PR 一并归档）

## 需求摘要

代码度量扫描插件上报后，工作流概览只输出 5 项指标数值，用户无法直接进入 openLiBing 平台查看该仓库/分支的指标明细。本需求补齐「链接生成与输出」环节：

- 服务端（openlibing-coderepo）：上报响应由 `DataResult<String>` 扩展为 `message + detailLink + tip`；按 gitUrl 解析关联项目取第一个（既有排序：录入时间倒序），校验第一行项目分支登记（`repo_branch` 精确 + `has_branch='1'`），已登记即生成固定 1 条链接（复用分支管理页筛选参数 projectId/platforms/repoUrlLike/branchNameLike，不含 metricType、repoId、pipelineRunId）；仓未录入 / 分支未登记返回对应 tip；异常仅告警、降级不阻断上报受理。配套改造：`file-detail` 撤除 `pipelineRunId` 入参（按分支最新成功记录返回）、分支列表排序增加「精确命中置顶」、`RepoUrlUtil.normalize` 归一化下沉。
- 插件（code-metrics-action）：上报成功后双通道输出——ATOMGIT_STEP_SUMMARY Markdown 超链接（显示文本≠实际链接）+ ATOMGIT_OUTPUT 链接行（key 末尾小写 `url` 触发平台渲染可点击）；两类提示行；链接固定 1 条（不随项目数、指标数变化）。
- 链接落地（前端侧协同）：无 metricType 链接落地分支管理页并自动应用三筛选条件（精确命中行置顶），页面恒展示当前分支最新指标数据；异步导入窗口的页面提示文案由前端侧更新。
- 鉴权模式（OIDC / AK-SK 双模式）、扫描逻辑、上报接口路径与入参、message 语义保持不变。

## 交付历程

### code-metrics-action（分支 scan-result-drilldown-link，PR #32 → master，head `8a1b6fa`）

- commit `3728b5f`：feat 上报响应解析 detailLink/tip，双通道输出链接
- commit `0360bc4`：补充输出逻辑测试
- commit `0cb86eb`：修改日志输出
- commit `8a1b6fa`：chore 文案定稿（代码度量指标扫描结果 / 扫描结果url）

### openlibing-coderepo（分支 scan-result-drilldown-link，PR #215 → release_20261019_iter1，head `ed41c4a4`）

- commit `9c44b99a`：feat 上报响应返回 detailLink/tip（响应 VO + 分支登记校验 + 链接构建）+ 分支列表精确命中置顶 + file-detail 按分支最新记录返回（撤 pipelineRunId）+ 单测
- commit `ed41c4a4`：feat 链接移除 codeHostingPlatformFlag（联调后定稿）

## 用户自测反馈

- beta 环境端到端通过（用户确认）：流水线真实上报 → 双通道链接输出 → 点击落地分支页并自动应用三筛选条件（精确命中行置顶），展示最新指标数据
- 反馈：链接落地为「最新数据」口径，异步导入进行中点击链接可能短时看到上一轮数据 → 与前端侧确认，由前端侧更新页面提示文案（提示稍等同步完成后刷新），后端与插件不做额外改动
- 链接固定单条输出（不随项目数、指标数变化）；上报失败不输出链接

## 最终验证

- 单测：`CodeMetricsServiceImplTest` 46/46（含 7 个 buildReportVO 用例）、`CodeMetricsControllerTest` 5/5、`CodeMetricsImportConsumerTest` 5/5
- 冒烟：基于真实 bundle 的 vm 沙箱 7 场景（AK/SK 链接、分支提示、均空不输出、上报失败不输出、缺 STEP_SUMMARY、缺 OUTPUT、OIDC 全链路）全部通过
- 边界四态：命中 + 已登记（单条链接）/ 分支未登记（分支 tip，不回退其他项目）/ 仓未录入（仓 tip）/ 异常（空链接空提示）
- 排序：精确命中置顶（相近分支名 main 与 main-2 场景验证）
- 兼容：老插件 × 新服务端（仅判 code/msg、不读取 data）；旧前端 × 新服务端（携带 pipelineRunId 的 file-detail 调用被忽略、按分支最新记录返回）

## 设计偏差与取舍

1. 链接参数收敛（联调后定稿）：设计初版链接携带 `codeHostingPlatformFlag`（对齐流水线跳转链接范式、用于未登录无感授权）；联调评估后判定非必需，从链接中移除（commit `ed41c4a4`）；platforms 保留分支页筛选语义，platform 非 gitcode/gitee 时省略 platforms
2. 文案定稿：显示文本「代码度量指标扫描结果」；OUTPUT 链接行 key「扫描结果url」（末尾小写 url 触发可点击渲染）、提示行 key「扫描结果」
3. 前端侧协同定性：落地契约与前端侧对齐（三筛选自动应用 + 精确置顶 + 气泡口径 + 异步导入窗口提示文案），前端代码交付由前端团队负责，不随本需求提业务 PR
4. 测试网关还原（已闭环）：联调期插件分支 `coderepoUrl` 曾指向 APIC 测试网关（beta 联调用）；联调完成后已还原为主干原值 `https://apig.openlibing.com:443`（commit `ea73f9e`）

## 可复用经验

- 「最新口径」链接不携带 pipelineRunId：历史定位参数全面撤除（含 file-detail 入参收敛），页面恒展示最新数据，消除"历史/最新"语义冲突；旧调用携带旧参数被忽略、不报错
- 复用列表页既有筛选参数：链接不发明新参数，直接复用分支管理页 `platforms`/`repoUrlLike`/`branchNameLike` 既有字段；LIKE 模糊筛选与精确定位的语义差通过"精确命中优先"排序弥合（首屏第一位即目标）
- 链接构建旁路兜底：构建逻辑独立异常捕获，异常仅告警、降级返回空链接空提示（不误报"未录入"），不阻断上报受理
- 服务端单点定义：链接模板、平台地址（`openlibing.domain` 既有配置）与两类 tip 文案均由服务端单点定义，插件不做 URL 拼接与文案硬编码
- URL 归一化下沉单一来源：`RepoUrlUtil.normalize` 统一实现（UtCoverage 委托复用），消除第二份归一化逻辑
- 异步导入窗口的提示文案：页面按「最新数据」口径展示时，需提示用户"稍等同步完成后刷新"，由承载页面的前端侧更新文案

## 归档日期

2026-10-15
