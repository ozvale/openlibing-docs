# Proposal: openlibing-cicd-web 安全整改批次修复（security-remediation-202610）

## 需求背景

2026-10-22 安全扫描在 `openlibing/openlibing-cicd-web` 仓产出 **47 个 open 状态安全问题 issue（#100~#154）**，来自 10 个来源专项（威胁分析、漏洞挖掘、红线、编码要求、参数校验、华为 Web 规范、TOP 问题、应用安全测试、web 安全测试、OSS 扫描）。同一问题被多个专项重复扫出，按根因聚为 8 类：

| 类别               | 根因模式                                        | Issue 数 | 严重度区间 |
| ------------------ | ----------------------------------------------- | -------- | ---------- |
| A. XSS / URL 注入  | 动态 URL/HTML 直出，无协议白名单、无净化        | 11       | 严重~低    |
| B. 敏感信息硬编码  | 公网/内网地址、域名、appKey、邮箱、token 入配置 | 10       | 中~低      |
| C. 日志/控制台泄露 | Cookie/CSRF Token/错误原文进日志或弹窗          | 6        | 中~低      |
| D. Nginx 配置安全  | 限流键可伪造、缺安全头、TLS 校验关闭            | 5        | 中         |
| E. 权限/认证       | fail-open、权限码未接线、路由无守卫             | 5        | 中~低      |
| F. 防重入缺失      | 按钮/操作无 loading 锁，可重复提交              | 4        | 中~低      |
| G. CI/供应链       | fork PR 命令注入、钩子源未固定 sha              | 2        | 严重~低    |
| H. 数据残留/死代码 | sessionStorage 残留、遥测死代码、ReDoS          | 4        | 低         |

整改过程中又新增两个扫描批次：**issue #155**（流水线权限组匿名访问 401 打断页面，后端已整改、前端需静默降级适配）与 **issue #157**（OSS 扫描 8 个 HIGH 传递依赖漏洞）。

完整分类去重分析、逐 issue 点位与修复进度见 [security-issues-analysis.md](../../../../issue_docs/openlibing-cicd-web/security-issues-analysis.md)（该文档待另行归档入库，合入前链接暂不可达）。

## 需求描述

### 做什么

按「文件点位聚类 + 批次化 PR」策略完成前端侧安全整改：

1. **XSS 净化**（批次 1）：重试确认框 VNode 渲染、Markdown 预览占位变量转义、iconfont 死脚本删除、restful 路径参数编码加固
2. **出站 URL 白名单**（批次 2）：下载/`href` 直出统一接入 `safeUrlOrBlank`（仅 http/https）、`rel=noopener` 补齐、跳转目标域白名单 + referrer origin 校验
3. **Nginx 加固**（批次 3）：三环境移除 `cookie_suid` 会话凭证、限流键改 `$binary_remote_addr` + 阈值灰度、死配置/惰性配置清理、安全响应头加固
4. **权限接线**（批次 4）：`pipeline_retry` 触点补门禁、未注册操作码 fail-closed、镜像删除/同步 handler 权限复核
5. **信息泄露清扫**（批次 5）：ApiClient console 脱敏 + 错误弹窗通用化、SENINFO 公网地址硬编码 47 处全量去向处置（代码删除 33 处 + 迁 `external-links.ts` 统一管理 1 处 + 合理形态保留 3 处 + 工具链功能性引用待申报豁免 7 处 + 暂缓另行安排 2 处 + #135 公网 DNS 用户决策豁免 1 处）、遥测/majun 死配置文件整体删除
6. **防重入锁**（批次 6）：流水线执行/镜像构建/镜像同步/停止与单条同步 4 处补锁
7. **收尾**（批次 7）：403 引导路由补齐、触发过滤正则输入侧防御、sessionStorage 归属校验与登出清理
8. **依赖漏洞**（批次 8）：`pnpm.overrides` 强制升级 dompurify / follow-redirects / markdown-it / toml 共 8 个 HIGH 漏洞
9. **匿名 401 降级**（批次 9）：权限组两个只读查询接口固定 `disableToken: true`，匿名 401 静默降级不跳登录

### 不做什么（豁免/出局/暂缓，均有明确决策记录）

| Issue       | 处置         | 决策依据                                                                                                                                |
| ----------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| #104        | 架构决策豁免 | 本应用仅以 wujie 子应用形态挂载，本层 nginx 下发 CSP 不进浏览器渲染管线，责任收敛主应用（2026-10-27 定案，PR #164 中 CSP 改动整体移除） |
| #135        | 用户决策豁免 | 公网 DNS 硬编码可接受，且 `resolver` 供 `ssl_stapling` OCSP 查询属功能性配置（2026-10-23）                                              |
| #148        | 出局不修     | 业务本身存在无登录场景，前端路由认证守卫不符合业务形态，issue 由用户删除                                                                |
| #112 / #124 | 暂缓另行安排 | pre-commit 供应链问题（Pwn Request / 钩子源固定 sha），单独批次处理                                                                     |

## 验收标准

- [x] P0 唯一已验证高危（#111 存储型 XSS）修复，高危清零
- [x] 前端 HTML 字符串渲染类 XSS 面（dangerouslyUseHTMLString / v-html / innerHTML / document.write / eval）在活代码中物理清零
- [x] 累计闭环 42+ 个 issue 编号（含重复组合并闭环），每批次 `pnpm build` 通过
- [x] 出站跳转攻击面（#106/#149）以域白名单闭环，非法目标统一兜底跳本站首页，401/403 登录链路行为不变
- [x] nginx 三环境配置一致性核对通过（cookie_suid / 限流键 / 死配置三点位 ×3 文件对齐）
- [x] 权限加固方案已交付：#125 未登录放行设计消除误伤面、#117 fail-closed 统一口径
- [ ] 上线验证项待执行：#117 测试环境比对接口返回覆盖的 14 个操作码授权，确认无未注册码业务被误拦后方可放量
- [x] 匿名（未登录）访问流水线权限组页面不跳登录、无报错气泡，登录用户行为不变（PR #195 已合入）
- [x] 依赖升级后 `pnpm build` 通过，markdown-it 8→14 大版本跳跃以 Markdown 预览页人工回归兜底
- [x] 各批次远端 Git Hooks Checking PASSED，Prettier unchanged

## 影响范围

- **本仓（openlibing-cicd-web）**：nginx 三环境 conf、`src/api/ApiClient.ts` / `api.ts` / `urls.ts`、`src/utils/`（until.js 新增 `safeUrlOrBlank`、新建 `redirectGuard.ts`、删除 uem.js / jsagent.js / auth.js 死代码）、`src/majun/` vendored 死包删除、流水线/镜像/构建配置/测试结果等约 30 个视图组件、`package.json` + `pnpm-lock.yaml`、路由与权限 stores
- **跨仓关联**：后端仓待办（`/image/**` 归属校验、`/pipeline/run` 幂等、公开仓权限跳过、网关 projectId 变体路径）；主应用承担 CSP 统一下发责任（#104 豁免前提）
- **业务影响分档**：约 6 成改动零感知；轻微交互变化约 8 项；4 项带回归风险必须带测试修（详见 design.md 风险节）；灰度项已随架构决策消除
