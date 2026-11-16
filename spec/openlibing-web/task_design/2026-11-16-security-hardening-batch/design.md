# design — 2026-11 安全加固批次

## 总体设计

三条横向基线贯穿全部修复，避免各点修复各自造轮子：

1. **主机白名单统一入口**：复用 `src/utils/until.js` 的 `isSafeClientRedirectUrl(url, allowedProtocols, allowedHostnames)`（支持 `*.example.com` 通配、精确 hostname 匹配），白名单数据集中在 `src/assets/js/config.json`（`GITCODE/GITEE/GITHUB/ATOMGIT HOSTS`、`AGENT_ARENA_REDIRECT_HOSTS`、`PLATFORM_ALLOWED_HOSTS`、`VSC_PLUGIN_ID_ALLOWLIST`）。iframe src 一律 `URLSearchParams.append` 组装（序列化时自动百分号编码，不做二次 encodeURIComponent 以免子应用双重解码）。
2. **富文本统一净化**：输出端一律过 `xssFilter`/`handleContent`；不新增自定义属性钩子，白名单属性交由 xss 库内置 `safeAttrValue` 处理。
3. **依赖精确锁版 + overrides**：catalog 与 overrides 全部写 lock 中实际解析版本（无 `^`），易受攻击传递依赖用 pnpm overrides 钉补丁版本，防止精确锁版的消费方绕过范围升级。

## 关键决策

### 1. repoUrl iframe 校验（M-0003，92eefa8e）

- 校验失败**丢弃参数并 console.warn**，不阻断页面——repoUrl 是增强参数而非必需参数，阻断会造成整页不可用。
- 不复用既有 `startsWith` 前缀式的 `validateSafeUrl`，改用精确 hostname 匹配，封堵 `gitcode.com.evil.com` 仿冒。

### 2. jumpIntermediate userinfo 剥离（38183cb0）

- `safeUrl` computed：`new URL()` 解析后清空 `username`/`password` 再序列化；展示、继续跳转校验、信任域保存三处统一用规范化后的真实地址。
- 解析失败回退原始字符串，保持既有行为；不含 userinfo 的正常 URL 输出不变。

### 3. openEuler 相对路径白名单（M-0027，2c0f7fd8）

原黑名单（拒 `..`、拒特定 scheme）存在 scheme 注入与 `%XX` 编码穿越残留缺口，改为白名单正向校验：

```js
function isValidRelativeRepoPath(path) {
  if (!/^[A-Za-z0-9._+~/-]+$/.test(path) || path.startsWith("//")) {
    return false;
  }
  return !path.split("/").includes("..");
}
```

- 字符集仅允许仓库路径合法字符，`javascript:`、`file:/`、`%2e%2e` 等注入形态自然被拒。
- `//` 开头拒协议相对 URL；分段比对 `..` 拒目录穿越。
- 非 openEuler 模式仍走既有 `isValidPackageUrl` 完整 URL 校验；`confirmSelected` 的 invalidUrl 门为唯一提交入口。

### 4. xssFilter 移除自定义 onTagAttr（M-0012，3af1431b）

自定义 `onTagAttr` 手工字符串拼接属性值且绕过库内置 `safeAttrValue`，是 href/javascript 混淆绕过的根源。删除后白名单属性经库内建安全处理输出；`detail.vue` 同时移除绕过外链确认流的 raw-href `plan` 块与注释死代码 `testReport`。

### 5. cookiePolicy disableToken（2c0f7fd8）

`privacyCookieConsent` 为埋点式同意上报，401 触发登录跳转属误伤（未登录用户首次访问即弹登录）。改 `{ disableToken: true }` 发送 + `.catch(() => {})` + `.finally` 关闭抽屉/写 cookie——请求失败也完成同意闭环，不阻塞页面。

### 6. CORS map 链式门控（FIND-01，1e3278a7）

`map $http_origin $cors_origin` 白名单 `https://*.openlibing.com`；Allow-Origin / Allow-Credentials / Allow-Methods / Allow-Headers / Max-Age 五个头全部经链式 map 门控——非白名单 Origin 或无 Origin 请求一个 CORS 头都收不到，替代原先「反射任意 Origin + 无条件 credentials」。

### 7. token 输入拦截统一（SENS-06，846d85c3）

- disableCopy 指令改为**命名模块级处理器**注册，unmounted 真正移除监听（原匿名函数永不解绑，重复挂载后拦截失效）。
- 拦截下沉到 `input-password` 基础组件（所有密码输入生效），`TokenCompositeInput` 补 contextmenu 拦截，与 GlobalConfigDialog 对齐。
- gitleaks 对 `.vue` 模板 camelCase 标识符（如 `:show-password="tokenVisible"`）误报加入 allowlist。

### 8. 域名收敛到 config.json（f4022fc6）

27 个文件散落域名/白名单收敛为 `src/assets/js/config.json` 单一事实源，经 Vite JSON 命名导入消费。范围：路由微应用 dev URL（约 19 处）、UEM/APM/华为 CS/JS Agent SDK 端点、四平台主机白名单、文档/备案/下载模板链接、AI_CODEFIX。附带修复 NoApplicationPermission.vue 中 WECARE URL 的 `&amp;` HTML 实体字面量问题（该处 URL 被当纯 JS 字符串处理，查询参数被解析成 `amp;hotlineId`）。

### 9. 依赖锁版策略（bed425a2）

- bump `@babel/core 7.29.6`、`@humanfs/node 0.16.8`、`colord 2.9.4`、`echarts 6.1.0`、`fast-uri 3.1.9`、`glob 14.0.2`、`katex 0.18.2`、`minimatch 11.0.1`、`nitropack 2.13.4`、`postcss-selector-parser 6.1.5/7.1.6`、`qs 6.16.1`、`serialize-javascript 7.1.3`、`turbo 2.9.14`。
- 加 overrides 使精确锁版的传递消费方也解析到补丁版本。
- catalog/override 与 lock 解析结果逐项对齐。合并 upstream 时冲突策略：保留我方精确锁版 + 补回 release 新增 `@vitest/coverage-v8: 3.2.4`，lock 由 `pnpm install` 重新生成。

## 影响范围

| 区域          | 文件（关键）                                                                                                                           |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 工具层        | `src/utils/until.js`（isSafeClientRedirectUrl/xssFilter）、`src/assets/js/config.json`（新增单一事实源）                               |
| iframe/微应用 | InterfaceManage（repoUrl）、manageRouter/InterfaceReview（URLSearchParams）、noMenu.ts                                                 |
| 跳转/重定向   | `jumpIntermediate`、`Content.vue`（vscode 白名单）、releaseComponents add/detail（planIssue）                                          |
| 富文本        | `src/majun/src/components/WangEditor.vue`、transferTestEmail（releaseComponents + LTS）                                                |
| 发布评审      | releaseComponents/add.vue（fullPath 白名单 + invalidUrl 门）                                                                           |
| 会话/凭证     | disableCopy 指令、input-password、TokenCompositeInput、GlobalConfigDialog、`utils/auth.js`、majun `auth.ts`、banner 轮询、cookiePolicy |
| 传输          | nginx 五套配置的 CORS map 链                                                                                                           |
| 依赖          | `pnpm-workspace.yaml`（catalog/overrides）、`pnpm-lock.yaml`、`package.json`、src/sca 死源码删除                                       |
| 配置          | `.env.beta/.env.gamma/.env.production`、majun config.json 删除、package.json preview script                                            |

## 测试与验证

- M-0027：Node 静态复现 18 例（原 PoC `169.254.169.254`、路径穿越、scheme 注入、`%2e%2e`、`//` 协议相对）全部拦截。
- userinfo 钓鱼：`https://www.openlibing.com@evil.example` 展示与跳转均指向真实主机。
- repoUrl 仿冒：`gitcode.com.evil.com` 拒绝、白名单主机放行。
- 依赖：`pnpm install` 无新增问题（既有 peer 警告不变）、gitleaks 误报 allowlist 生效。
- 合并验证：`pnpm install` + pre-commit 全 Passed；GitCode `mergeable: True`。

## 已知边界

- `checkReviewPackageUrl` 前端白名单只是第一道防线，服务端校验（协议/域名/IP 白名单 + 内网阻断）为 P0 待办，在后端仓落地。
- env 内网地址为联调临时状态，发布前需恢复域名。
- 遗留 token cookie 双写路径在 vben 迁移后已确认不可达（无入口/路由/引用），补属性仅为关闭扫描项（WEB-16）。
