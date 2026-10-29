# openlibing-cicd-web 安全整改批次 — 技术设计（security-remediation-202610）

## 方案概述

按「**文件点位聚类 → 修复批次 → 独立 PR**」三级组织整改：同一文件被多个 issue 指向时一次修改闭环多个 issue；高风险改动单独成批便于独立回滚；全部以跨仓 fork PR 交付（base 安全分支 `dev-chenning-anquan-202610`，收尾批次改走迭代 `release_20261029_iter2`）。

## 架构决策

### D1 按文件点位聚类，最小化批次间冲突

- `nginx_{prod,beta,gamma}.conf` 三文件同步改：一次闭环 cookie_suid（#101/#133/#145）、限流键（#109/#144）、惰性配置（#134）等 8 个 issue
- `triggerDownloadByAnchor.ts` + 4 个本地副本同步修：协议白名单 + `rel=noopener`（#115/#141/#116）
- `MirrorManage/index.vue` 单文件聚合：确认框 + 防重入（#119）+ 权限复核（#126）三层融合
- 组合 PR 策略：#161+#163 零冲突合并为 #165、#166+#168 合并为 #169，减少评审队列

### D2 wujie-only 部署形态 → #104 CSP 转架构豁免

本应用唯一运行形态是 wujie 子应用挂载主应用：资源由主应用页面 fetch、JS 在 blob iframe 中继承主应用 CSP，子应用本层 nginx 下发的 CSP 响应头不进浏览器渲染管线、无实际防护收益。CSP 责任收敛主应用（四环境已强制模式且白名单覆盖本应用监控域）。PR #164 中 CSP 改动经 Report-Only（`23f015d`）→ 强制+监控域白名单（`7560975`）两轮演进后整体移除（`7300432`）。

### D3 限流键加固必须同步评估阈值

限流 zone 键由可伪造的 `$http_x_real_ip` 改为 `$binary_remote_addr`（TCP 真实对端），同步将 `limit_conn limitperip` 10 → 50（用户确认的保守值）：公司 NAT 出口下全体用户共享一个限流桶，不改阈值会直接误伤办公网并发。上线后监控 503 率即可暴露共享出口拓扑，再决定收紧。

### D4 权限加固防「修完误拦正常用户」

- **#125 `pipeline_retry` 门禁**：未登录放行 + 已登录走权限矩阵双通道，消除「权限码无人被分配→全员失去重试入口」的误伤面
- **#117 未注册操作码 fail-open → fail-closed**：与主路径口径统一；上线验证项为测试环境比对接口返回覆盖的 14 个操作码授权清单
- **#126 镜像 handler 复核**：handler 级权限复核 + 请求体补 projectId 归属上下文；根因在后端 `/image/**` 无归属校验，另建后端 issue 跟踪

### D5 出站 URL 白名单语义（已与需求方确认）

- **跳转白名单**（#106/#149，新建 `src/utils/redirectGuard.ts`）：本站 origin + wujie 主应用 origin（运行时 `window.parent.location.origin` 动态获取，跨域不可读时静默忽略），多环境零配置；非法目标 console.warn 后兜底跳本站首页；相对路径按当前页面解析天然同源放行，401/403 自动登录链路行为不变
- **下载/href 协议白名单**（#136/#154/#115/#141/#116）：`until.js` 提取 `isValidUrl` / `safeUrlOrBlank` 工具，仅放行 http/https，拦截 `javascript:` / `data:` / `vbscript:` 载荷；被拦截但 URL 存在时页面给 inline 提示

### D6 Markdown 预览 XSS 净化方案演进（#127）

| 演进      | 方案                                                                          | 结论                                                                                                                                                             |
| --------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `5bb8096` | 全局 `VMdEditor.markdownIt.set({ html: false })` + 整篇 FilterXSS             | 否决：`markdownIt` 静态属性在 v-md-editor 2.3.18 lib UMD 构建中不存在（启动白屏）；FilterXSS 作用于解析前源码会改写 `<module>`、`a<b && c>d`、代码块内容且不可逆 |
| `df248d5` | **最终方案**：占位变量值统一 HTML 实体转义（lodash `mapValues(ctx, escape)`） | 采纳：注入载荷实体化后无法构成标签，作者 markdown 结构与代码块完全保真                                                                                           |

### D7 匿名 401 静默降级（#155）

后端按安全整改对匿名请求返回 401 后，前端 ApiClient 的 401 分支会触发登出/自动重登跳转，打断匿名场景。修复：在 `src/api/api.ts` 调用层为权限组两个**只读查询**接口（`getPermGroups` / `queryPermGroupResourcePermissions`）固定附加 `disableToken: true`，401 落到页面级 catch → 置空权限组数据并回退全局权限矩阵，不跳转、不弹气泡；写操作 401 行为保持不变。

### D8 依赖漏洞用 pnpm overrides 强制升级（#157）

传递依赖漏洞无法等上游发版，沿用仓库既有 `pnpm.overrides` 模式强制升级：dompurify 3.4.0→3.4.17、follow-redirects 1.16.0→1.16.2、markdown-it 8.4.2/12.3.2→14.3.3（override 统一单版本）、toml 4.3.0→5.0.1。markdown-it / toml 大版本跳跃以 `pnpm build` + Markdown 预览页人工回归兜底。

## 涉及文件

| 文件/位置                                                       | 操作      | 说明                                                            |
| --------------------------------------------------------------- | --------- | --------------------------------------------------------------- |
| `nginx/nginx_{prod,beta,gamma}.conf`                            | 修改      | cookie_suid 移除、限流键/阈值、死配置与惰性配置清理、安全响应头 |
| `src/api/ApiClient.ts`                                          | 修改      | console 脱敏、错误弹窗通用化、403 needCheck 五态语义            |
| `src/api/api.ts`                                                | 修改      | 权限组查询接口 `disableToken: true`（#155）                     |
| `src/utils/until.js`                                            | 修改      | 提取 `isValidUrl` / `safeUrlOrBlank`                            |
| `src/utils/redirectGuard.ts`                                    | 新增      | 跳转目标域白名单校验                                            |
| `src/utils/uem.js`、`src/utils/jsagent.js`、`src/utils/auth.js` | 删除      | 遥测死代码/死代码整文件删除（闭环 #110/#129/#147）              |
| `src/majun/`、`src/assets/js/config.json`                       | 删除      | vendored 死包与死配置（闭环 #121/#123/#131 等）                 |
| `src/config/external-links.ts`                                  | 新增      | SENINFO 外链统一管理（#100 保留点位）                           |
| `src/utils/triggerDownloadByAnchor.ts` + 4 个本地副本           | 修改      | 协议白名单 + `rel=noopener`                                     |
| `PipelineDetail/Detail.vue` 等 ~30 个视图组件                   | 修改      | XSS 点位、防重入锁、权限门禁、403 引导等按批次分布              |
| `triggerFilters.js`                                             | 修改      | 正则输入侧防御（长度上限 + 嵌套量词启发式拦截，#137）           |
| `router/index.ts` + `NoPermission` 页                           | 修改/新增 | 403 引导路由注册（#118）                                        |
| `package.json`、`pnpm-lock.yaml`                                | 修改      | `pnpm.overrides` 依赖强制升级（#157）                           |
| `stores/app.ts`、`permissions-meta.ts`                          | 修改      | fail-closed（#117）、pipeline_retry 门禁接线（#125）            |

## 风险与缓解（业务影响四档）

| 档位                        | 内容                                                                                                                                    | 缓解                                                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 一、零业务影响（约 12 项）  | 死配置/死文件删除、日志脱敏、DNS                                                                                                        | 直接修                                                                                   |
| 二、轻微交互变化（约 8 项） | HTML 变文本显示、报错弹窗通用化、连点不再重复提交、镜像同步多一次确认框                                                                 | 知会产品/用户即可，无需回归                                                              |
| 三、有回归风险（4 项重点）  | #117 fail-closed 可能误拦未注册码业务、#125 补门禁、#136/#115/#141 白名单可能拦截非 http(s) 业务链接、#149/#106 白名单配错=锁死登录链路 | 修前 grep 数据源确认、#125 未登录放行设计、#117 测试环境比对 14 操作码、登录链路重点验证 |
| 四、高危改动需灰度（2 项）  | #104 加 CSP、#109 限流键改键                                                                                                            | #104 已随 wujie-only 决策整体移除；#109 阈值同步灰度 10→50 并监控 503 率                 |

> 高风险改动单独成批不与零感知删除类混批，便于独立回滚。

## 已知残余风险（2026-10-29 docs PR #1220 检视意见归档）

以下为已定案决策的边界条件说明，记录在案供后续评估，不改变本批次决策：

- **CSP 直连形态**（D2）：豁免论证仅覆盖 wujie 挂载形态；若子应用 URL 可被绕过主应用直连访问，该形态下无 CSP 防护。后续可在网关/入口层显式禁止直连，或评估最小兜底头（`frame-ancestors` / `X-Frame-Options`）
- **限流键反代前提**（D3）：`$binary_remote_addr` 仅在 nginx 为直连入口时等于真实客户端 IP；若入口存在网关/SLB 反代，需引入 nginx `real_ip` 模块从可信网段取真实地址，否则限流退化为全站单桶。上线前应核对入口拓扑，确认限流桶未被单一出口 IP 独占
- **Markdown 原始 HTML 残余面**（D6）：v-md-editor 2.3.18 无法关闭原始 HTML 渲染，占位变量转义不覆盖「模板正文直接书写 HTML/事件属性」通道；可评估对渲染产物统一过 DOMPurify/FilterXSS 作为加固项
- **#125 匿名放行与后端缺口叠加**（D4）：未登录放行 + 后端公开仓流水线跳过权限检查（待另建 issue）期间，匿名用户可触发公开仓流水线重试；后端缺口修复前该面保持开放
- **跳转白名单动态 origin**（D5）：主应用 origin 取 `window.parent.location.origin`，若页面被第三方域 iframe 嵌入，嵌入者域会被自动加入白名单；当前运行形态受控（仅 wujie 挂载、无独立部署），若未来开放任意 iframe 嵌入，需改为配置化白名单并在父 origin 命中已登记域时才放行

## 跨仓影响

- **openlibing-cicd（后端）**：`/image/**` 无归属校验（#126 根因）、`/project/pipeline/run` 无幂等（#113）、公开仓流水线跳过权限检查（#117/#125）、网关对非数字 projectId 变体路径跳过校验（#107 关联面）——均需后端仓另建 issue
- **web-openlibing（主应用）**：CSP 统一下发责任（#104 豁免前提，四环境已强制模式）
- **issue #155**：后端部分（匿名请求返回 401）已先行实施，本批次仅前端适配
