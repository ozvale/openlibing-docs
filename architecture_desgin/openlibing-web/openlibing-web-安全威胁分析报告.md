# 安全威胁分析报告：openlibing-web

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\openlibing-web` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 前端/Nginx/构建配置检查） |
| 报告语言 | 中文 |
| 部署分类 | 前端单页应用（Vue 3 + Vite 7 + TypeScript，vben-admin fork，pnpm + Turborepo monorepo；主应用 `apps/web-openlibing`，openEuler + Nginx 1.24 容器，端口 8075，反代后端 k8s 微服务网关） |

---

## 一、系统概述

### 1.1 用途与技术栈

OpenLiBing **平台前端**：openEuler 开放原子平台的管理控制台 SPA，承载发布管理、漏洞视图、权限管理、通知公告、AI 工具、Ops/Argus/CICD 等微前端入口（wujie）。

- Vue 3.5 + Vite 7 + TypeScript + Pinia + Vue Router 4；UI 为 Element Plus / Ant Design Vue（vben 体系）；pnpm workspace + Turborepo（`apps/` + `packages/` + `internal/`）
- HTTP：两套并行体系——① vben 体系 `@vben/request`（`Authorization: Bearer`）；② 自研 `ApiClient.ts`（原生 axios，`withCredentials: true` Cookie 会话 + 自定义 CSRF 头 `Csrf-Token-Open-Li-Bing`）
- 部署：Nginx 1.24（`nginx_beta/gamma/prod/prod_new.conf`）反代 `/gateway → openlibing-gateway-*:8073` 及 `/ops /argus /ai /build /api-management` 等内部服务；Docker 容器非 root 运行

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 职责 | 信任边界 |
|---|---|---|---|
| Nginx 反代 | `apps/web-openlibing/nginx/nginx_prod*.conf` | 静态托管 + 反向代理 + CORS/限流/TLS | 外部 ↔ 平台边界 |
| 路由守卫 | `apps/web-openlibing/src/router/guard.ts` | 三层路由守卫、动态菜单 | 前端访问控制（UX 层） |
| accessStore | `packages/stores/src/modules/access.ts:102` | token/锁屏密码持久化（SecureLS AES） | 凭证存储边界 |
| ApiClient | `apps/web-openlibing/src/api/ApiClient.ts:80` | Cookie 会话 + CSRF 双提交令牌 | 浏览器 ↔ 网关 |
| request.ts | `apps/web-openlibing/src/api/request.ts:59` | vben Bearer 通道，baseURL 来自 env | 浏览器 ↔ API |
| xssFilter | `apps/web-openlibing/src/utils/until.js:267` | `xss` 库白名单消毒 | XSS 防线 |
| 环境配置 | `.env.production:8` / `.env.gamma:8` | API 基址（**指向外部 mock 域名**） | 构建边界 |
| 华为客服脚本 | `src/utils/loadHuaweiCS.ts:10` | 运行时注入第三方脚本 | 供应链边界 |

**关键信任边界**：① 浏览器 → Nginx（TLS/CORS/安全头）；② Nginx → 内网网关/微服务（`proxy_ssl_verify off`）；③ 前端路由守卫（**不可作为授权边界**，最终鉴权在后端）；④ 第三方脚本/iframe（华为客服、wujie 子应用、AI 工具）。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒 | 1 | 演示弱口令组件在生产布局中被引用 |
| T 篡改 | 4 | CORS 反射任意 Origin；第三方脚本无 SRI；Nginx→后端 TLS 不校验；v-html/markdown 注入面 |
| R 抵赖 | 0 | — |
| I 信息泄露 | 4 | token/锁屏密码存 localStorage（硬编码密钥"加密"）；生产 API 指向外部 mock 域；console 打印 userInfo；内网 IP/服务名入库 |
| D 拒绝服务 | 1 | 限流 key 基于可伪造的 `X-Real-IP` |
| E 权限提升 | 2 | 路由守卫 fail-open + 默认 super 角色；CORS+Credentials 跨站读取数据 |
| A 业务滥用 | 1 | 文件上传仅客户端校验 |

### 关键威胁场景

**场景 1（I/E，CORS 反射任意 Origin + 凭证）**：生产 Nginx 配置 `add_header 'Access-Control-Allow-Origin' '$http_origin' always;` 且 `Access-Control-Allow-Credentials: true`（`nginx_prod.conf:120-124`，beta/gamma/prod_new 同样）。业务会话依赖 Cookie（`ApiClient.ts:90 withCredentials:true`），任意恶意网站都可携带用户登录 Cookie 向 `/gateway/**` 发起跨域请求并读取响应体，导致用户数据、仓库/漏洞/发布信息被跨站窃取。`Allow-Headers` 还显式放行了 CSRF 头名。

**场景 2（E，前端访问控制 fail-open）**：路由守卫中 accessToken 检查整段被注释（`guard.ts:66-86`）；未取到用户信息时默认赋予 `roles:['super']`（`:95-100`）；无 `meta.auth` 标记的路由一律放行（`:149-151`）；权限数组为空即通过（`:167`）。一旦后端某接口遗漏鉴权，功能页与数据直接暴露。

**场景 3（I，凭证本地存储 + 硬编码密钥）**：accessToken、refreshToken 及**锁屏密码明文**持久化到 localStorage（`access.ts:102-110`），生产用 secure-ls AES"加密"，但密钥 `o-1-p2-libing-3` 硬编码在 `.env:12` 并构建进 bundle，任何人可提取解密——仅为混淆。任何 XSS 或恶意浏览器扩展均可还原 token。

---

## 三、安全发现明细

### 高危

#### FIND-01：Nginx CORS 反射任意 Origin 且允许凭证（跨站数据窃取）

| 属性 | 内容 |
|---|---|
| STRIDE | I / E（S） |
| CWE | [CWE-942](https://cwe.mitre.org/data/definitions/942.html) 过度宽松的跨域策略；[CWE-668](https://cwe.mitre.org/data/definitions/668.html) |
| OWASP | A05:2025 – Security Misconfiguration |
| 证据 | `apps/web-openlibing/nginx/nginx_prod.conf:120-124`（`nginx_prod_new.conf:120-124`、`nginx_beta.conf:116-120` 同样）：`add_header 'Access-Control-Allow-Origin' '$http_origin' always;` + `Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS'` + `Access-Control-Allow-Credentials 'true'`；Cookie 会话见 `ApiClient.ts:90` `withCredentials: true` |
| 风险 | `$http_origin` 原样回显 = 反射任意第三方网站 Origin，且允许凭证。恶意页面可代用户向 `/gateway/**` 发带 Cookie 的跨域请求并读取响应，窃取漏洞/发布/仓库/用户数据；配合放行的自定义头，CSRF 防护边界被削弱 |
| 修复建议 | 改 Origin 白名单：`map $http_origin $cors_origin { default ""; "~^https://([a-z0-9-]+\.)?openlibing\.com$" $http_origin; }` 后输出 `$cors_origin`；非白名单不输出 CORS 头；`Allow-Credentials` 仅对白名单域生效 |
| 修复成本 | 低 |

#### FIND-02：路由守卫鉴权被注释、默认 super 角色、权限判定 fail-open

| 属性 | 内容 |
|---|---|
| STRIDE | E |
| CWE | [CWE-862](https://cwe.mitre.org/data/definitions/862.html) 缺失授权；[CWE-285](https://cwe.mitre.org/data/definitions/285.html) 不当授权 |
| OWASP | A01:2025 – Broken Access Control |
| 证据 | `apps/web-openlibing/src/router/guard.ts`：`:66-86` accessToken 检查整段被注释；`:95-100` `userStore.userInfo || { id:0, realName:'Vben', roles:['super'], username:'vben' }`；`:149-151` `if (!to.meta || !to.meta.auth) { next(); }`；`:167` `(permissions.length === 0 || permissions.includes(to.meta.auth))` |
| 风险 | 前端访问控制多处"默认允许"：未登录不跳登录、无 auth 标记页面直接放行、权限空数组通过、super 角色兜底可能使动态菜单越权生成。前端守卫本为 UX 层，但此 fail-open 写法在后端接口遗漏鉴权时直接暴露功能页 |
| 修复建议 | 恢复 token 存在性检查；移除 super 兜底（未登录跳登录）；权限判定改 fail-close（空数组拒绝）；**所有敏感后端接口必须独立鉴权，不依赖前端** |
| 修复成本 | 低 |

### 中危

#### FIND-03：Token / 锁屏密码持久化于 localStorage，"加密"密钥硬编码在前端

- STRIDE：I ｜ CWE：[CWE-312](https://cwe.mitre.org/data/definitions/312.html) 明文存储敏感信息；[CWE-798](https://cwe.mitre.org/data/definitions/798.html) 硬编码凭证 ｜ OWASP：A02/A07:2025
- 证据：`packages/stores/src/modules/access.ts:102-110` `persist: { pick: ['accessToken','refreshToken','accessCodes','isLockScreen','lockScreenPassword'] }`；`packages/stores/src/setup.ts:24-44` `new SecureLS({ encodingType:'aes', encryptionSecret: import.meta.env.VITE_APP_STORE_SECURE_KEY })`；`apps/web-openlibing/.env:12` `VITE_APP_STORE_SECURE_KEY=o-1-p2-libing-3`
- 风险：accessToken/refreshToken/锁屏密码落 localStorage，生产 secure-ls AES 密钥构建进 bundle 可被提取解密，仅为混淆；XSS 或恶意扩展可直接还原 token；localStorage 不受 HttpOnly 保护
- 建议：会话凭证优先改后端下发 HttpOnly+Secure+SameSite Cookie；不持久化 lockScreenPassword；若必须本地存 token 改用 sessionStorage 并缩短有效期；移除硬编码密钥或明确定位为"防肉眼浏览"
- 修复成本：中

#### FIND-04：CSP 未启用、X-Frame-Options 被注释（点击劫持 + 无 XSS 纵深防御）

- STRIDE：T / E ｜ CWE：[CWE-1021](https://cwe.mitre.org/data/definitions/1021.html) 不当框架限制；[CWE-16](https://cwe.mitre.org/data/definitions/16.html) ｜ OWASP：A05:2025
- 证据：`nginx_prod.conf:103` CSP 行被注释；`:112` `# add_header X-Frame-Options SAMEORIGIN;`；beta 环境连 HSTS 也被注释（`nginx_beta.conf:97`）
- 风险：页面可被任意恶意站点 iframe 嵌套实施点击劫持；发生 XSS 时（本项目 v-html 使用面广，见 FIND-05）无 CSP 第二道防线拦截脚本/外联
- 建议：启用 CSP（至少 `default-src 'self'; frame-ancestors 'self' https://*.openlibing.com; object-src 'none'; base-uri 'self'`，按需放开 wujie/iframe/华为客服域名）；加 `X-Frame-Options: SAMEORIGIN` 或 CSP `frame-ancestors`
- 修复成本：低

#### FIND-05：大量 `v-html` 渲染，存在未消毒/依赖后端数据的注入面

- STRIDE：T（存储型/反射型 XSS）｜ CWE：[CWE-79](https://cwe.mitre.org/data/definitions/79.html) ｜ OWASP：A03:2025
- 证据：
  - 邮件内容直接渲染后端返回 HTML：`src/views/Publish/.../transferTestEmail.vue:21,25` `v-html="emailInfo.content"`（`emailInfo = res.result` 于 `:153/:186`；仅部分分支 `res.result.content = xssFilter(...)` 于 `:152/:185`，需保证所有赋值路径都过滤）
  - Markdown 策略页 `md.render()` 后直接 `v-html="compiledMarkdown"` 未接消毒：`src/views/Policy/PrivacyPolicy.vue:9,21`、`ContactUs.vue:9`、`cookieProtocol.vue:9`、`collectionChecklist.vue:9`（源为本地 md 资产，风险相对低，模式危险）
  - 代码查看页 `v-html="lineHtml()"`（`StaticAlarm/detail.vue:1658,1722`）基于 `escapeHtml()`（`detail.vue:420`），安全
  - 富文本 WangEditor 进出均经 `handleContent()` 过滤（`components/WangEditor.vue:75,84,96`），安全
  - 正面：项目引入 `xss@1.0.14`，`src/utils/until.js:267-368` 定制较严格白名单（删 `video`、移除所有 `style`、`img.src` 仅允许 `data:image/` 或同源 `:317-323`、`a` 标签协议处理）
- 风险：后端/用户可控 HTML 若绕过 xssFilter 直接 v-html，可执行任意脚本（结合 FIND-03 可窃取 token）
- 建议：所有渲染后端/用户可控 HTML 的 v-html 强制统一走 xssFilter/handleContent（重点核查 emailInfo.content 每个赋值点）；markdown-it 渲染后串联 xssFilter 或换 DOMPurify；升级 xss 库
- 修复成本：低

#### FIND-06：生产/Gamma 构建 API 基址指向第三方 vben 官方 Mock 服务器

- STRIDE：I / T（数据外发）｜ CWE：[CWE-829](https://cwe.mitre.org/data/definitions/829.html) 不可信来源 ｜ OWASP：A05/A10:2025
- 证据：`.env.production:8`、`.env.gamma:8` `VITE_GLOB_API_URL=https://mock-napi.vben.pro/api`；vben 体系 `requestClient` baseURL 来自该变量（`request.ts:22,109`）
- 风险：生产/gamma 模式下任何误用 vben requestClient 的业务请求都会发往外部第三方域名 mock-napi.vben.pro（数据外泄/响应被第三方控制）；自研 ApiClient 走相对路径 `/gateway`，但两套客户端并存极易踩坑
- 建议：生产/gamma 的 VITE_GLOB_API_URL 改为同源相对路径（如 `/gateway`），删除外部 mock 地址
- 修复成本：低

### 低危

#### FIND-07：硬编码内网地址 / 弱命名密钥文件 / k8s 内部服务名泄露

- STRIDE：I ｜ CWE：[CWE-532](https://cwe.mitre.org/data/definitions/532.html)
- 证据：`vite.config.mts:50` dev 代理内网 IP `target: 'http://192.168.0.94:8091'`；`nginx_prod.conf:152` `ssl_password_file "cert/abc.txt";`（弱文件名）；nginx 配置明文出现多个 k8s 内部服务 `openlibing-gateway-*.default.svc.cluster.local:8073`、`openlibing-ops-web-*:8097`、`openlibing-ai-web-*:8098`、`openlibing-cicd-web-*:8099`、`openlibing-develop-web-*:8901`（`nginx_prod.conf:221-278`）
- 风险：内网拓扑/IP 泄露扩大攻击面
- 建议：内网 IP/服务名通过环境变量/模板注入不入库；证书口令文件使用随机名并严格权限
- 修复成本：低

#### FIND-08：生产代码 console.log 打印用户信息

- STRIDE：I ｜ CWE：[CWE-532](https://cwe.mitre.org/data/definitions/532.html)
- 证据：`src/views/AiTools/AiTools.vue:43,54,59` `console.log('准备发送 userInfo:', userInfo, 'iframe src:', aiUrl.value)`；生产构建未剔除 console
- 风险：向 AI iframe 跨域传递的 userId/username/email 打印到控制台
- 建议：移除敏感日志，或构建时 `esbuild.drop:['console','debugger']`（生产）
- 修复成本：低

#### FIND-09：动态加载第三方脚本无 SRI / 协议相对 URL

- STRIDE：T（供应链/XSS）｜ CWE：[CWE-829](https://cwe.mitre.org/data/definitions/829.html)；[CWE-494](https://cwe.mitre.org/data/definitions/494.html)
- 证据：`src/utils/loadHuaweiCS.ts:10-12` `script.src = '//app.huawei.com/wecare/onlineservice/cs.js?hotlineId=M00047573&locale=zh-CN'` 运行时注入，无 integrity/SRI
- 风险：结合 FIND-04（无 CSP），CDN 被劫持即全站 XSS
- 建议：改 `https://`、加 SRI integrity 或在 CSP `script-src` 白名单限定该域
- 修复成本：低

#### FIND-10：限流 key 基于可伪造的 `X-Real-IP` 请求头

- STRIDE：D / A ｜ CWE：[CWE-807](https://cwe.mitre.org/data/definitions/807.html) 不可靠输入参与安全决策
- 证据：`nginx_prod.conf:58-61` `limit_req_zone $http_x_real_ip zone=...`
- 风险：`$http_x_real_ip` 为客户端请求头，攻击者可每次变换该头绕过限流/嫁祸他人
- 建议：使用 `$binary_remote_addr`，或经 real_ip 模块处理后的 `$remote_addr`
- 修复成本：低

#### FIND-11：Nginx 到后端 `proxy_ssl_verify off`

- STRIDE：T（MITM）｜ CWE：[CWE-295](https://cwe.mitre.org/data/definitions/295.html) 证书校验不当
- 证据：`nginx_prod.conf:132,216` 等所有反代块 `proxy_ssl_verify off;`；dev 代理 `secure:false`（`vite.config.mts:57`）
- 风险：与内网网关/微服务的 TLS 连接不校验证书，内网被渗透时可 MITM
- 建议：内网启用证书校验或 mTLS（`proxy_ssl_trusted_certificate`）
- 修复成本：中

#### FIND-12：Demo 登录组件含硬编码弱口令且被布局引用

- STRIDE：S / E ｜ CWE：[CWE-798](https://cwe.mitre.org/data/definitions/798.html)；[CWE-521](https://cwe.mitre.org/data/definitions/521.html)
- 证据：`src/views/_core/authentication/login.vue:60` `password: '123456'`（vben mock 账号 vben/123456）；被 `src/layouts/auth.vue:41` `import LoginForm from '#/views/_core/authentication/login.vue'` 引用
- 风险：vben 演示账号选择器会在登录表单自动填充 vben/123456；若该登录页生产可达，暴露误导性演示凭据/接口调用
- 建议：生产构建剔除 mock 账号选择逻辑，确认登录实际走 OAuth（`Login.vue` 的 gitee/gitcode 跳转）而非演示表单
- 修复成本：低

#### FIND-13：文件上传仅客户端校验

- STRIDE：T / A ｜ CWE：[CWE-602](https://cwe.mitre.org/data/definitions/602.html) 客户端防护
- 证据：多处 `el-upload` 如 `accept=".xlsx"`（SensitiveDict 等）、`beforeUpload/imageBeforeUpload`、WangEditor `uploadImgShowBase64=true`（`WangEditor.vue:49`）
- 风险：accept/beforeUpload 仅浏览器端约束可轻易绕过，上传内容安全性完全依赖后端
- 建议：后端必须做文件类型/魔数/大小/病毒校验；前端校验仅作体验
- 修复成本：低（前端侧）

---

## 四、正面安全实践（已核实）

1. **Docker 镜像加固完善**（`Dockerfile` / `apps/web-openlibing/Dockerfile`）：非 root `nginx(uid1000)` 运行、`passwd -l` 锁账号、`umask 0077/0027`、关闭历史记录、内核网络参数加固（禁重定向/源路由、syncookies、rp_filter）、目录 `chmod 500/700`、删除 gdb/perl/lua/gcc 等调试工具、`core 0`。
2. **Nginx 基础硬化**：`server_tokens off`、`autoindex off`、隐藏文件 `location ~ /\. { deny all }`、SPA `try_files ... /index.html`、HTML `no-cache`、`/assets` immutable、`X-Content-Type-Options: nosniff`、`Referrer-Policy`、生产 HSTS、TLS1.2/1.3 强 cipher + `ssl_prefer_server_ciphers` + OCSP stapling + `ssl_session_tickets off`、多级 `limit_req/limit_conn`。
3. **开放重定向/新窗口防护**：跳转中间页 `views/noticeBlank/index.vue` 校验 `javascript:/data:/vbscript:/file:` 危险协议与信任域名；`utils/until.js:217-249` `safeOpen()` 统一 `newWin.opener=null` 并拦危险协议；`WujieMiddleware.vue:249-250` 同样 `opener=null`。
4. **postMessage 校验 origin**：`views/Ops/opsIframe.vue:61` 接收时校验 `e.origin !== window.location.origin`；`AiTools.vue:46-52` 发送时显式指定 `targetOrigin`（非 `*`）。
5. **XSS 过滤白名单较严格**：`utils/until.js:267-368` 用 `xss` 库定制白名单，限制 `img.src`、去 `style`/`video`；代码高亮基于 `escapeHtml`。
6. **CSRF 双提交令牌**：`ApiClient.ts:82-83` 自定义 `Csrf-Token-Open-Li-Bing` 头（值取自 Cookie），配合跨域自定义头限制形成 CSRF 防护。
7. **生产构建**：`vite.config.mts:17` gamma/production 关闭 sourcemap；`VITE_NITRO_MOCK=false`、devtools 仅开发环境；`xlsx` 使用本地 tgz 固定来源。
8. **wujie 微前端**子应用 URL 来自静态路由 `meta.url`（`WujieMiddleware.vue:131`），非用户输入可控。

---

## 五、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01 | Nginx CORS 改 Origin 白名单，禁止反射 `$http_origin` + credentials | 低 |
| FIND-02 | 恢复路由 token 校验、权限 fail-close、移除 super 兜底 | 低 |
| FIND-04 | 启用 CSP / `frame-ancestors`（X-Frame-Options） | 低 |
| FIND-06 | 生产/gamma API 地址移除外部 mock，改同源相对路径 | 低 |
| FIND-08 | 移除敏感 console.log，生产 drop console | 低 |
| FIND-09 | 第三方脚本改 https + SRI / CSP 白名单 | 低 |
| FIND-10 | 限流 key 改 `$binary_remote_addr` | 低 |
| FIND-12 | 生产剔除 demo 弱口令登录组件 | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-03 | 凭证改 HttpOnly Cookie 或缩短有效期、不持久化锁屏密码、移除硬编码密钥 | 中 |
| FIND-05 | 全量核查 v-html（尤其 emailInfo.content）与 markdown 渲染均过消毒 | 低 |
| FIND-11 | Nginx→后端启用证书校验/mTLS | 中 |
| FIND-07 | 内网 IP/服务名改环境变量注入 | 低 |
| FIND-13 | 后端补文件类型/魔数/病毒校验（前端仅体验层） | 低（前端侧） |

---

## 六、分析假设与需验证项

1. **前端路由守卫/v-html 过滤/上传校验均属防御纵深/体验层**，最终授权与输入校验必须由后端网关与微服务保证；需结合 openlibing-gateway 报告确认网关是否对 `/gateway/**` 强制认证与授权。
2. FIND-01 的实际可利用性取决于 Cookie 的 `SameSite` 属性：需确认后端 Set-Cookie 是否带 `SameSite=None; Secure`（若是 `SameSite=Lax/Strict` 则跨站 POST 被浏览器拦截，但 GET 侧仍有风险）；建议在网关/后端核验。
3. `emailInfo.content` 的所有赋值分支是否均经过 xssFilter 需在运行时/源码全量确认（本报告发现 `:152/:185` 部分分支过滤，存在遗漏路径可能）。
4. Nginx 配置文件中 `ssl_password_file "cert/abc.txt"` 与证书文件是否实际进入镜像、权限如何，需在构建产物中核验。
5. 生产登录入口是否确实走 OAuth（gitee/gitcode 跳转）而非 vben 演示表单，决定 FIND-12 的实际暴露面。

## 七、参考标准

- STRIDE-A 威胁建模；OWASP Top 10:2025；CWE/MITRE；CIS Nginx/Docker 基线；OWASP Cheat Sheet（CORS、XSS 防护、点击劫持、会话管理、文件上传）。
