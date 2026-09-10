# 软件成分数据页漏洞刷新功能 — 归档

## 关联

- 业务仓: `openlibing/openlibing-sbom`（后端） + `openlibing/openlibing-web`（前端）
- 业务分支: 两仓 `feat-sbom-vul-refresh`
- 业务 Issue: openlibing/openlibing-sbom#74 (https://gitcode.com/openlibing/openlibing-sbom/issues/74，open，含 PR 回填评论)
- 业务 PR: openlibing/openlibing-sbom#137 (https://gitcode.com/openlibing/openlibing-sbom/pull/137，目标分支 `release_20260910_iter1`) / openlibing/openlibing-web#779 (https://gitcode.com/openlibing/openlibing-web/pull/779，目标分支 `release_20260910`)
- 历史作废: openlibing/openlibing-sbom#71（issue，时序问题作废）、#136 / openlibing/openlibing-web#778（PR，误按 master 建立后关闭）

## 交付历程

### openlibing-sbom（后端，3 commits）

- **feat(sbom): add vulnerability refresh via strategy pattern and async executor** — 核心交付，18 文件 +1426：
  - `POST /sbom-api/refresh`（productName + refreshType=VUL，@LogApi）
  - `SbomRefreshService` 编排：FINISH 校验 → ConcurrentHashMap 去重锁 → `VUL_REFRESHING` 状态占用（BUSY/异常恢复）→ 专用线程池派发
  - 策略框架：`SbomRefreshStrategy` SPI + Factory + `VulRefreshStrategy`（UVP 分批拉取 → REQUIRES_NEW 删旧写新 → 统计重算对齐 CollectStatisticsStep）
  - `sbomRefreshExecutor` 线程池（core=2/max=4/queue=64/AbortPolicy）+ 启动恢复 ApplicationRunner
  - `SbomConstants` 新增 `TASK_STATUS_VUL_REFRESHING`；前端状态映射同步补充
  - 保留 `dependencyCache/refresh` 后端接口不动
- **fix(sbom): flush pending external vul refs before statistics clear** — 测试环境验证发现 external_vul_ref 未入库：`saveAll` 仅挂起在 persistence context，统计重算的 `entityManager.clear()` 将其丢弃；修复为先 `flush` 再 `clear`，并按用户要求补充入库数量诊断日志（入库前/事务内/事务提交后三级）
- **chore(deps): upgrade openlibing-common to 1.0.20.6** — 与本特性无关的例行依赖升级（root pom dependencyManagement 统一管理）

### openlibing-web（前端，7 commits）

- **feat(sbom): replace dependency refresh entry with vul refresh button** — 移除"漏洞依赖刷新"按钮（后端接口保留），新增"漏洞刷新"按钮（二次确认 + 问号 tooltip + 权限），非完成态置灰 loading + 5s 轮询 queryScanStatus，完成通知常驻 + `scanStatusMap` 补 VUL_REFRESHING
- **fix(sbom): guard null form ref in notification refresh** — 通知"刷新数据"按钮点击报 `Cannot read properties of null (reading 'validate')`（产品表单已卸载），改为直接调用 `queryList(true)` + `queryProductStatistics()`
- **chore(sbom): rename notification button** — "刷新数据" → "刷新页面数据"
- **chore(sbom): align refresh notification button to right-aligned layout** — 按钮对齐"版本已更新"通知样式（文字下方 `text-align: right` + 默认尺寸）
- **merge prod/release_20260910** — 合入 release 分支，解决 index.vue 样式冲突（`.vul-refresh-tip` 与 `.export-tip-question` 共存）
- **fix(sbom): harden vul refresh feedback and polling lifecycle** — PR 检视修复：① 触发结果未知/缺失 status 时补兜底提示；② `setInterval` 改为响应后 `setTimeout` 调度（`scanStatusPollingActive` 标志防止 stop 被在途请求穿透）；③ keep-alive `onDeactivated` 停止轮询 + `onActivated` 按需恢复

## 用户自测反馈

多轮测试环境验证迭代（每轮新 commit，未 amend）：

1. 首轮：`external_vul_ref` 未入库 → 后端 flush 修复 + 诊断日志
2. UI 调整轮：确认弹窗加宽单行、完成通知加"刷新数据"按钮、按钮 null 报错修复、更名、右对齐
3. 检视修复轮：触发反馈兜底、轮询并发/乱序、keep-alive 轮询生命周期

## 最终验证

- 后端：53 个单测通过（SbomControllerTest 38 / SbomRefreshServiceTest 10 / VulRefreshStrategyTest 5）、`mvn compile` 通过、pre-commit 钩子全通过（含 Spotless/CheckStyle/SpotBugs/PMD）
- 前端：prettier/eslint 通过、gitleaks 通过、远端 Git 钩子 PASSED
- 测试环境（beta/gamma）多轮部署验证通过：按钮交互、置灰轮询、刷新覆盖、完成通知与刷新页面数据、解析中触发拦截、common 1.0.20.6 兼容性

## 设计偏差与取舍

| 项 | 原计划 | 实际交付 | 说明 |
|----|--------|----------|------|
| 通知按钮布局 | 初始竖排样式 | 右对齐布局 | 对齐既有"版本已更新"通知交互 |
| 轮询机制 | 固定 5s setInterval | 响应后 setTimeout 调度 | PR 检视指出慢请求下并发/乱序风险 |
| PR 目标分支 | 最初误按 master | sbom → `release_20260910_iter1`（新建）、web → `release_20260910` | 流程遗漏 G7 询问，补确认后重建 PR |
| 业务 Issue | 最初 #71 交付前误建 | #74 交付时正式创建 | 流程时序修正；`--label` 参数触发 403，标签未挂 |

## 经验沉淀

- JPA `saveAll` 后若同事务内 `entityManager.clear()`，必须先 `flush`，否则挂起插入被丢弃
- GitCode 保护分支（`release_*`）只能经 Web/API 创建；创建分支 API：`POST api.gitcode.com/api/v5/repos/{owner}/{repo}/branches`，body 为 `{"refs":"<起点>","branch_name":"<新分支>"}`
- GitCode 已建 PR 的目标分支不可通过 API 实际修改（PATCH 静默忽略），只能关闭重建
- keep-alive 缓存页面的轮询类副作用必须同时挂 `onDeactivated`（停止）与 `onActivated`（恢复）
