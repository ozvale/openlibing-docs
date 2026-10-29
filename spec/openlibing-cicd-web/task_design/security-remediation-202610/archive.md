# openlibing-cicd-web 安全整改批次 — 归档（security-remediation-202610）

## 关联

- 分类去重分析（权威进度源）：[security-issues-analysis.md](../../../issue_docs/openlibing-cicd-web/security-issues-analysis.md)
- 业务 Issue：#100~#154（47 个原始扫描 issue）+ #155（匿名 401）+ #157（OSS 依赖漏洞），逐 issue 索引见分析文档第 6 节
- 修复 PR：#154~#160、#162、#164~#169、#174、#193（已关闭）、#195（已合入），完整清单与状态见分析文档 1.1 节
- 关键 PR 直链：
  - [PR #195](https://gitcode.com/openlibing/openlibing-cicd-web/merge_requests/195)（匿名 401 降级，2026-10-29 合入 `release_20261029_iter2`）
  - [PR #174](https://gitcode.com/openlibing/openlibing-cicd-web/merge_requests/174)（依赖漏洞）
  - [PR #165](https://gitcode.com/openlibing/openlibing-cicd-web/merge_requests/165) / [#169](https://gitcode.com/openlibing/openlibing-cicd-web/merge_requests/169)（组合 PR）
- docs PR：待创建（本分支 `spec-openlibing-cicd-web-security-remediation-202610`）

## 交付历程

整改自 2026-10-22 启动，至 2026-10-29 九个批次全部交付；修复分支已合入迭代开发分支 `develop_202610_iter2`。关键 commit：

- `1197181`/`16f6066`（PR #156）：SENINFO 硬编码 47 处处置 + majun/uem 死文件删除（26 files，+15/-31887）
- `df248d5`（PR #160）：Markdown 预览占位变量转义最终方案
- `43b6059`（PR #162）：跳转域白名单 `redirectGuard.ts`
- `0974ebe`（PR #163）：防重入锁 4 处批量加固
- `23f015d`→`7560975`→`7300432`（PR #164）：nginx 限流键加固 + CSP 两轮演进后整体移除
- `595cb28`（PR #166）：403 引导路由 + 正则输入侧防御
- `9783867`（PR #174）：pnpm overrides 依赖强制升级
- `8b1c552`（PR #195）：权限组匿名 401 静默降级
- `c387ca5`（fix-frontend-security-combined，Refs #46）：nginx 安全响应头 7 项 + `safeUrlOrBlank` 工具提取 + uem_f.js SRI 固定

## 用户自测反馈

- #127 Markdown 预览 XSS：初版双层方案（全局 markdownIt 配置 + 整篇 FilterXSS）两层均有缺陷（启动白屏 + 预览保真度回归），经 CI 审阅机器人指出后两次修正，收敛为占位变量值转义方案
- PR 检视意见循环：批次 5 组合修复曾按 review 意见修正 cache/mutex/regex（`84ad520`）；#119 镜像同步融合为「权限复核 + 防重入锁 + 确认框」三层
- PR #193 base 选择纠偏：base master 不符合迭代发布路径，关闭后改以 base `release_20261029_iter2` 重建为 PR #195 并合入

## 最终验证

- 各批次 `pnpm build` 通过（14~90s 不等）；Prettier unchanged；分支远端 Git Hooks Checking PASSED
- nginx 三环境一致性核对：8 关键点 ×3 文件全对齐；CSP 移除后残留核验为 0
- 全仓静态扫描：SENINFO 6 项引用模式零残留；HTML 字符串渲染类 XSS 面活代码清零
- `pnpm type-check` 失败为存量 vue-tsc 1.8.27 与 TS 5.9.3 工具链不兼容（stash 对照验证基线同样失败，与整改无关）
- 待上线观察：限流阈值 50 的 503 率；#117 上线前测试环境比对 14 个操作码授权

## 设计偏差与取舍

- **#104 CSP 豁免**：修复方案从「本层下发 CSP」演进为「架构决策豁免」——wujie-only 部署形态下子应用 nginx 响应头不生效，责任收敛主应用；已完成的两轮 CSP 改动整体移除
- **#107 处置升级**：由「挂起待后端实测」转为前端 `encodeURIComponent` 加固修复，后端实测保留为验证项
- **#140 处置升级**：由「无需整改」升级为死文件删除彻底闭环
- **#148 出局**：复核发现业务存在无登录场景，前端路由认证守卫不符合业务形态
- **组合 PR 策略**：#161/#163、#166/#168 因文件不相交零冲突分别合并为 #165/#169，减少评审队列；与 iter2 开发线的冲突在迭代分支本地择优融合
- **批次 9 落点**：#193/#195 为首个不进 `dev-chenning-anquan-202610` 安全分支、直接对齐迭代 release 分支的修复（批次 8 除外）

## 可复用经验

- `VMdEditor.markdownIt` 静态属性在 v-md-editor 2.3.18 lib UMD 构建中不存在，全局配置需走 vite alias（成本大于收益未采用）
- FilterXSS 不能作用于 markdown 解析前的整篇源码（会改写代码块/比较表达式且不可逆）；正确语义是「对注入的变量值做 HTML 实体转义」，而非「净化整篇文档」
- 动手改 nginx 前先 grep 点位确认代理拓扑（#134 初判「开启 verify 需核实 CA」过于保守，实际本层无 `proxy_pass`，正确修复是删除）
- 高风险改动（fail-closed、限流键、白名单）必须单独成批 + 明确上线验证项，不与零感知删除类混批
- 「修完反而挡住正常用户」型修复（#117/#125）要在方案层消除误伤面（未登录放行、灰度阈值），而非事后补救

## 归档日期

2026-10-29
