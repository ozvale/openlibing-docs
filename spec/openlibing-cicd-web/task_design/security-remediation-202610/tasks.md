# openlibing-cicd-web 安全整改批次 — 实现任务（security-remediation-202610）

## 进度: 9/9 批次 complete（2026-10-29）

> PR 状态截至 2026-10-29：#195 已合入 `release_20261029_iter2`；#193 已关闭由 #195 承接；其余跨仓 PR 详见 [security-issues-analysis.md](../../../issue_docs/openlibing-cicd-web/security-issues-analysis.md) 1.1 节。

- [x] 批次 1 XSS 净化：#111 重试确认框 VNode 渲染（PR #159）、#127 Markdown 占位变量 HTML 转义（PR #160，`5bb8096`→`f780117`→`df248d5` 三次演进）、#140 iconfont 死脚本删除（PR #158）、#107 restful 路径参数 encodeURIComponent 加固（PR #157）
- [x] 批次 2 出站 URL 白名单：#136+#154+#115+#141+#116 下载/href 协议白名单 + `rel=noopener`（PR #161→并入组合 PR #165）、#106+#149 跳转域白名单 + referrer origin 校验（PR #162，`43b6059`）
- [x] 批次 3 nginx 专项：#101/#133/#145 cookie_suid 移除（PR #155）、#109/#144 限流键改 `$binary_remote_addr` + 阈值 10→50 + 死配置清理、#134 惰性配置删除（PR #164）；#104 CSP 经两轮演进后按 wujie-only 架构决策整体移除（`7300432`）
- [x] 批次 4 权限接线：#125 pipeline_retry 五触点补门禁 + 未登录放行（PR #167）、#117 fail-closed + #126 镜像删除/同步 handler 复核（PR #168→并入组合 PR #169）
- [x] 批次 5 信息泄露清扫：#102/#105/#142/#143 ApiClient 脱敏 + 弹窗通用化 + sessionStorage 归属校验/登出清理 #108（PR #154）；#121/#122/#123/#131/#129/#147/#110/#100 SENINFO 硬编码 47 处处置——删 33 处 + 1 处迁 `external-links.ts` 统一管理（PR #156，26 files +15/-31887）
- [x] 批次 6 防重入锁：#113 执行、#114 镜像构建（含补 ElMessage 导入）、#119 镜像同步（补确认框 + busy 锁）、#120 停止/单条同步（PR #163 `0974ebe`→并入组合 PR #165）
- [x] 批次 7 收尾：#118 403 引导路由补齐 + needCheck 五态语义（PR #166 `595cb28`→并入组合 PR #169）、#137 触发过滤正则输入侧防御（长度上限 200 + 嵌套量词启发式）
- [x] 批次 8 依赖漏洞：#157 OSS 扫描 8 个 HIGH 漏洞 `pnpm.overrides` 强制升级 dompurify/follow-redirects/markdown-it/toml（PR #174 `9783867`，首个直接进 `release_20261029_iter2` 的批次）
- [x] 批次 9 匿名 401 降级：#155 权限组只读查询接口固定 `disableToken: true` 静默降级（PR #193 base master 已关闭 → PR #195 base `release_20261029_iter2` 已合入，`8b1c552`）
- [ ] 暂缓（另行安排）：#112 fork PR Pwn Request、#124 钩子源固定 sha（pre-commit 供应链批次）
- [ ] 豁免存档（无需代码改动）：#104（wujie-only CSP 豁免）、#135（公网 DNS 用户决策豁免）、#148（路由守卫出局，issue 由用户删除）
- [ ] 收尾待办：#100 的 7 处工具链豁免申报文档；#107 后端可利用性实测验证项；各跨仓 PR 统一合入后关闭对应 issue
