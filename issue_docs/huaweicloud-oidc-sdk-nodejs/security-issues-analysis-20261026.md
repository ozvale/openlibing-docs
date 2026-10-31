# huaweicloud-oidc-sdk-nodejs 安全 issue 定性分析（2026-10-26）

> 依据 `gitcode-security-remediation` skill Phase 1，逐条对 open 安全 issue 做代码定位、
> 影响链路分析与分类，方案优先引用 `issue_docs/security-remediation-playbook.md`，
> 非问题判定引用 `issue_docs/security-non-issue-catalog.md`。
>
> 双基线核实（避免把「在途分支已改」误记为「master 已修复」）：
>
> - **基线 A（交付态，master）**：`origin/main` = `f0adbf8`
> - **基线 B（在途整改）**：`fix-security-remediation` = `475066d`（已合并 PR #3 / issue #5）
>
> 仓库形态：Node SDK（`src/`，整改前唯一第三方依赖为 `undici`，整改后零第三方依赖）
> + 3 个 GitCode Action（`.gitcode/actions/`，ncc 打包产物 `dist/` 入库，内含
> `@actions/core`/`@actions/http-client` 等三方内联代码）+ 本仓自身 CI workflow。

## 0. 结论速览

- 共 **17 条** issue：open 安全 **14 条**、closed 安全 2 条（#8 与 #6 同根因、#14 已关）、
  功能需求 1 条（#13，不在整改范围）。
- **1 条已实施待合入**（#5，PR #3 已含在 `fix-security-remediation`）。
- ~~**7 条真问题·等价加固**~~ **7 条已全部实施**（#7 #10 #15 #16 #17 #20 #21，2026-10-26 第二轮
  整改完成，commit `1694a33`，与 #18/#19 同分支待建 PR；#20 已按第 4 类影响声明实施，见 3.4）。
- **2 条已整改待 PR**（#19 依赖漏洞，2026-10-26 用户批准改为方案 C 零依赖回退，删除 undici 直接依赖，详见 4.2；
  #18 STS 端点拼接参数未校验，2026-10-26 用户决策改为按调用点补参数校验，详见 4.1）。
- **3 条非问题**（#6 #9 #12），已核实缓解因素/不可达路径，归档到
  `security-non-issue-catalog.md`。
- **1 条待裁决**（#11 账号 ID 硬编码），倾向非问题，请用户拍板。
- **分类修正（2026-10-26 业务逻辑复核）**：#20 `sslVerify: true` 属硬规则 2 第 4 类
  （fail-open → fail-closed），经用户批准后已按最小改动实施（见 3.4 影响声明），
  统一测试分支需实测自签 CA 场景。未实施方案的边界影响与「最小改动」记录见 3.2/3.3/3.4。

## 1. 汇总表

| 分类 | Issue | 处置 |
|---|---|---|
| 已实施·待 PR #3 合入主线 | #5 | 等待 PR #3 review 合入后关闭 |
| 已整改·待建 PR | #19 #18 #7 #15 #10 #17 #21 #16 #20 | #19 方案 C 零依赖 fetch 回退（4.2）；#18 按调用点补参数校验（4.1）；#7 #15 #10 #17 #21 #16 #20 于 2026-10-26 第二轮整改完成（3.1-3.4），均含在分支 `fix-undici-fetch-fallback`（commit `1694a33`） |
| 待用户裁决 | #11 | 建议非问题归档；如需外置走环境变量注入 |
| 非问题·归档 | #6 #9 #12 | 回复说明后关闭，回写非问题目录 |
| 已关闭（无需动作） | #8 #14 | #8 与 #6 同根因；#14 已由依赖升级关闭 |
| 功能需求（不在整改范围） | #13 | 不走安全整改流程 |

## 2. 已实施·待合入（3 条）

| Issue | 内容 | 证据链 | 状态 |
|---|---|---|---|
| #5 | SENINFO 公网地址硬编码（APIG 网关域名 6 处） | 基线 B `e667c90` 改动 `.gitcode/actions/test-apig-action/index.js:16-19`、`test-apig-obs-action/index.js:21-25` 及两份 `dist`：改为 `core.getInput('apig_url')` / `TEST_APIG_URL` 环境变量优先，保留原地址为回退默认值并登记 `gitleaks:allow` | PR #3 open，已进 `fix-security-remediation` |
| #19 | SCA：undici 5.x 存在已知漏洞 | `package.json` 原 `"undici": "^5.29.0"` 为唯一直接依赖，使用点仅 `src/http.js` 的 Node 16 回退分支。改为内联零依赖 `_nodeFetch`（Node 内置 `http`/`https`）并删除整个 `dependencies`；3 个测试 Action 用 ncc 重建 `dist`；新增单测 23 覆盖回退链路 | 分支 `fix-undici-fetch-fallback` 已推送（commit `69091ff`），待建 PR |
| #18 | STS 端点拼接参数未校验（region/stsAssumePath）+ OIDC 请求地址未强制 https | 按调用点补校验：`src/config.js` 的 `configure()` 对 `region`/`stsAssumePath` 白名单校验（先校验后写入，避免部分覆盖）；`src/oidc.js` 对 `ACTIONS_ID_TOKEN_REQUEST_URL` 强制 `https:`。通用 `sendRequest` 语义不变；3 个 Action 重建 `dist`；新增单测 24 覆盖全部拒绝场景 | 分支 `fix-undici-fetch-fallback` 已提交（`911230a`），待建 PR |

> 等价性（#5）：回退默认值与原硬编码逐字节一致，仅新增注入能力；输出契约未变。
> 待 PR #3 合入主线后再关闭 issue #5。
> 等价性（#19）：Node 18+ 仍走内置 fetch，路径与输出契约不变；node16 运行时走 `_nodeFetch`，
> 请求方法/头/体与返回结构 `{ status, headers, data }` 完全一致，`action.yml` 的 `using: node16` 不用改。

## 3. 已整改·待建 PR（7 条，2026-10-26 第二轮实施，commit `1694a33`）

### 3.1 发布流程 npm token 落盘（#7 + #15，同段代码合并一个 PR）

| Issue | 位置（基线 A/B 一致） | 代码事实 |
|---|---|---|
| #7 | `.gitcode/workflows/deploy.yml:53-59` | `echo "//registry.npmjs.org/:_authToken=\${NODE_AUTH_TOKEN}" > ~/.npmrc`，写后无清理 |
| #15 | `.gitcode/workflows/deploy.yml:56,59` | 同上，且未设权限（默认 644） |

- **根因**：同一段代码的「残留」与「权限」两个视角，属硬规则 4「同一块代码必须合并到一个 PR」。
- **整改**（`security-remediation-playbook.md` → 临时文件残留 + 权限最小化）：
  1. 写入前 `umask 077`（等价于原子 `chmod 600`，不改变文件内容与用途）；
  2. 发布后追加 `rm -f ~/.npmrc`（`if: always()`），覆盖发布失败路径。
- **等价性**：`npm publish` / `npm whoami` 的认证方式、registry、产物均不变；仅消除残留与放宽权限。
- **实施（commit `1694a33`）**：npmrc 写入改为 `(umask 077 && echo ... > ~/.npmrc)` 子 shell，
  新增 `Cleanup npmrc` 步骤（`if: always()` 执行 `rm -f ~/.npmrc`）。
- **验证**：workflow 语法 `check-yaml`；人工走一次 `workflow_dispatch`（非 tag，版本校验跳过）。

### 3.2 src 日志出口脱敏与日志注入（#10 + #17 + #21，同一批日志出口合并一个 PR）

| Issue | 位置 | 代码事实（基线 A） |
|---|---|---|
| #10（红线 7.1.11） | `src/oidc.js:54` | `error(\`OIDC Token 申请失败（HTTP ${res.status}）: ${JSON.stringify(res.data)}\`)`，唯一绕过 `maskBody` 的日志出口 |
| #17-1 | `src/oidc.js:54` | 同 #10 |
| #17-2 | `src/http.js:41` | `throw new Error(\`网络请求失败 ${method} ${url}: ${err.message}\`)`，URL query 随异常消息外泄 |
| #21 | `src/credentials.js:124` | `info(\`-- OIDC 免密换证开始：区域 ${cfg.region}，提供商 ${providerName}，委托 ${cfg.agencyName} --\`)`，`configure()` 可控值未清洗换行 |

- **对照证据**：同仓 `src/credentials.js:136/150` 已使用 `maskBody(res.data)`；`src/logger.js:80`
  已提供 `maskBody`（JSON 深度脱敏 + 非 JSON 文本 JWT 掩码），本组整改即「对齐既有惯例」。
- **整改**：
  1. `oidc.js:54` → `maskBody(res.data)`；
  2. `http.js:41` → 异常消息只保留 `method` + `host`（或对 query 掩码），不改变 `sendRequest` 返回结构；
  3. `credentials.js:124` → 拼接前对 `region`/`providerName`/`agencyName` 做换行与控制字符折叠
     （`String(v).replace(/[\r\n\t\u0000-\u001f]/g, ' ')`）。
- **等价性**：日志文本中敏感值被掩码、控制字符被折叠；非敏感内容、日志级别、出现时机、异常类型与消息前缀均不变。
- **验证**：`npm test`（含 `maskBody` 既有用例）；新增：伪造含 `\n` 的 `region` 断言日志单行、
  含 token query 的 URL 断言异常消息不含 query、OIDC 失败响应体断言被掩码。
- **业务逻辑影响（2026-10-26 复核）**：
  - #10 / #21：仅日志文本变化（掩码、控制字符折叠），属白名单内日志脱敏，返回结构与异常类型不变；
    但基于日志原文匹配的告警规则/脚本会失配，需在 PR 说明中列出。
  - #17-2：`sendRequest` 抛出的 `Error.message` 是调用方可捕获的对外文本（硬规则 2 第 1 类边缘），
    去掉 query 后文本会变。**已按最小改动实施**：保留 `method` + `host` + `path`，仅对 query **值**掩码
    （`_maskUrlQuery`，如 `?a=***`），既消除令牌泄露面，又不丢失可定位信息。
- **实施（commit `1694a33`，含单测 25）**：`oidc.js` 失败日志走 `maskBody`；`http.js` 新增
  `_maskUrlQuery`（URL 解析失败时正则退化掩码）；`credentials.js` 新增 `_foldForLog` 折叠
  region/providerName/agencyName 控制字符；3 个 Action `dist` 已重建。SDK 单测 1-26 全绿。

### 3.3 签名链路 header 大小写崩溃（#16，单独 PR）

- **位置**：`src/signer-v11.js:204-211`（构建 `allHeaders`）、`:232-233`（精确小写取值）。
- **代码事实（基线 A）**：
  - `:205` 存在性检查用 `k.toLowerCase() === 'x-sdk-date'`（大小写不敏感）；
  - 若调用方传入 `X-SDK-Date`，检查通过但不会补默认值；
  - `:232` `const time = allHeaders['x-sdk-date']` 取到 `undefined`；`:233` `time.substring(0, 8)` 抛 `TypeError`。
  - 同一问题也影响 `host`（`:209-210` 与 `canonicalHeaders` 的取值路径）。
- **定性**：真问题（安全编码要求·空指针引用），合法输入导致关键签名链路崩溃，非功能性缺陷。
- **整改**：构建 `allHeaders` 时统一将键名规范化为小写（保留原值），后续存在性检查与取值均走小写键；
  已全小写输入的签名结果逐字节不变。
- **行为影响声明**：仅把「传大写 header 崩溃」变为「正常完成签名」；签名算法、canonical 结构、输出
  `Authorization` 头格式均不变，属等价加固（不属硬规则 2 的「新增输入拒绝」）。
- **验证**：新增 `X-SDK-Date` / `Host` 大写入参用例，断言不抛错且签名字符串与全小写入参一致。
- **业务逻辑影响（2026-10-26 复核）**：若按「键名统一小写」实现，会改变 `sign()` **返回头对象的键名
  大小写**，且同时传入 `Host`/`host` 时 `SignedHeaders` 由 2 项变 1 项。
  **已按最小改动实施**：只修取值路径——新增 `_findHeader` 大小写不敏感查找 `x-sdk-date`，
  不改返回头键名、不改 `canonicalHeaders` 既有行为，对既有全小写入参签名结果逐字节不变
  （单测 26 断言大小写变体与全小写签名一致、返回头保留原始键名）。

### 3.4 Action 产物 TLS 证书校验关闭（#20，单独 PR + 统一自测）

- **位置（基线 A）**：
  - `.gitcode/actions/test-obs-action/index.js:41-46`
  - `.gitcode/actions/test-apig-obs-action/index.js:56-61`
  - 证据：`test-obs-action/dist/index.js:11867` `this.sslVerify = false`（SDK 默认），
    `:13400` `rejectUnauthorized: this.sslVerify || false`。
- **整改**（playbook → 第三方 SDK 不安全默认值）：两处 `new ObsClient({...})` 显式传 `sslVerify: true`，
  重新 `ncc` 构建 `dist`（**不直接改 dist**）。
- **等价性**：鉴权协议、上传语义、endpoint、bucket/key 均不变；仅恢复 TLS 证书校验。
- **风险与预案**：自托管 runner + 企业自签 CA 场景可能报证书错误 → 统一测试分支实测；报错时用
  `NODE_EXTRA_CA_CERTS` 注入企业根证书，**不回退关闭校验**。
- **业务逻辑影响（2026-10-26 复核·分类修正）**：`sslVerify: true` 属硬规则 2 **第 4 类失败语义
  （fail-open → fail-closed）**：自签 CA / TLS 中间代理场景会从「上传成功」变为「证书错误失败」。
  **已获用户批准按最小改动实施**（commit `1694a33`）：仅在两个 Action 的
  `new ObsClient({...})` 显式增加 `sslVerify: true`，不动 endpoint、AK/SK 注入方式、
  bucket/key 与上传参数；自签 CA 用 `NODE_EXTRA_CA_CERTS` 兜底，不新增开关、不回退关闭校验；
  `dist` 已 ncc 重建，3 个 Action 测试全绿。需在统一测试分支实测自签 CA 场景。

## 4. 已整改·待建 PR（2 条）

### 4.1 #18 STS 端点拼接参数校验（已实施·按调用点反向匹配）

| 子项 | 位置 | 原状 | 处置 |
|---|---|---|---|
| 1 | `src/credentials.js:103`（issue 写 `config.js:53`，实际端点在此拼接） | `` `https://sts.${cfg.region}.myhuaweicloud.com${cfg.stsAssumePath}` `` 无校验 | **已整改**：在唯一可控入口 `configure()` 补白名单校验 |
| 2 | `src/http.js:35` | `sendRequest` 不校验协议，允许 `http://` | **非问题**：通用 HTTP 工具，全仓无 `http://` 字面量，且强制 https 会打断本地调试与单测 23 |

- **方案（2026-10-26 用户决策）**：不改通用 `sendRequest`，而是**按调用点反向匹配**，只在真正携带
  敏感令牌的入口补参数校验，符合现有调用场景。
- **调用点全量审计**（`sendRequest` 共 4 处）：
  | 调用点 | URL 来源 | 是否需校验 |
  |---|---|---|
  | `src/credentials.js:103`（STS 换证） | `cfg.region`/`cfg.stsAssumePath`，仅由 `configure()` 覆盖 | ✅ 在 `configure()` 校验，覆盖全部下游 |
  | `src/oidc.js`（获取 ID Token） | 环境变量 `ACTIONS_ID_TOKEN_REQUEST_URL`，携带 Bearer 请求令牌 | ✅ 校验 `protocol === 'https:'` |
  | `src/credentials.js`（callApig 使用者传入 url） | 使用方入参，SDK 不掌握语义 | ❌ 保持通用工具语义 |
  | `src/credentials.js`（STS 模板拼接后调用） | 由前两项推导，已被入口校验覆盖 | ❌ 无需重复校验 |
- **实施内容**：
  1. `src/config.js`：新增 `REGION_PATTERN = /^[a-z0-9-]+$/` 与 `_validateOverride()`；`configure()`
     在写入前对全部 override 先校验，非法即抛 `TypeError`，避免配置被部分覆盖。
     - `region`：字符串且仅小写字母/数字/连字符（防 `@` 改变 URL 主机）。
     - `stsAssumePath`：字符串、以 `/` 开头、不含 `@`/空白/`?`/`#`/`://`。
  2. `src/oidc.js`：`new URL(reqUrl)` 后校验 `url.protocol !== 'https:'` 直接抛错，
     报错含协议与主机，**不发任何网络请求**。
  3. 3 个测试 Action 用 ncc 重建 `dist`，保持源码与产物一致。
  4. `test/openlibing-client.test.js` 新增单测 24：7 组非法值拒绝、校验失败不部分覆盖、
     合法值仍可用、http OIDC 地址拒绝且零请求。
- **行为影响声明（硬规则 3）**：属**新增输入拒绝**（硬规则 2 第 5 类），已获用户明确批准。
  - 只拒绝「本就不安全」的输入：默认 `region=cn-southwest-2`、默认
    `stsAssumePath=/v5/agencies/assume-with-oidc`、3 个 Action 仅 `configure({ debug })`，均不受影响。
  - 未处理 `sendRequest` 的 http 能力，本地调试与单测 23（`http://127.0.0.1`）行为不变。
- **验证**：`npm test` 全绿（单测 1-24）；3 个 Action `npm test` 全绿；`dist` 已含新校验逻辑。

### 4.2 #19 undici 5.x 依赖漏洞（已实施·方案 C 零依赖回退）

- **位置**：原 `package.json` `"undici": "^5.29.0"`（唯一直接声明）；唯一使用点原 `src/http.js`
  （Node 18+ 无内置 fetch 时的回退分支）。
- **方案演进（2026-10-26 用户决策）**：原方案 A/B 均要求把 3 个 Action 的 `using: node16`
  改为 `node20`（undici 6.x 要求 Node >= 18），存在 GitCode Actions 运行时是否支持 node20 的
  不确定性；方案 B（只留内置 fetch）会让 node16 运行时报错。最终采用**方案 C：零依赖回退**——
  不升级 undici，直接删除该依赖。
- **实施内容**：
  1. `src/http.js`：删除 `require('undici').fetch` 回退，内联 `_nodeFetch`，基于 Node 内置
     `http`/`https`，覆盖 `sendRequest` 所需的 method/headers/body 发送与 status/headers/text 读取；
     超时 300s 对齐 undici fetch 默认值（`headersTimeout`/`bodyTimeout`），不自动跟随重定向
     （调用方为 IAM/STS/APIG 固定接口，均不返回重定向）。
  2. `package.json`：删除整个 `dependencies` 字段，SDK 变为零第三方依赖；`package-lock.json`
     中 undici 条目清零。
  3. 3 个测试 Action 执行 ncc 重建 `dist`（未手工改产物，遵守硬规则 6）。
  4. 新增单测 23：临时移除 `globalThis.fetch`，用本地 http server 验证回退链路
     （状态码、响应头、请求方法、请求体）。
- **等价性**：Node 18+ 仍走内置 `fetch`，执行路径与输出契约不变；node16 运行时走 `_nodeFetch`，
  请求方法/头/体与返回结构完全一致；`action.yml` 的 `using: node16` 不需要改。
- **验证**：SDK `npm test` 全量通过（含新增用例 23）；3 个 Action `npm test` 全部通过；
  dist 重建后 SDK 侧无 undici 内联代码。
- **残留（独立问题，不在 #19 范围）**：3 个测试 Action 的 `dist` 仍有 undici，来源是
  `@actions/core` → `@actions/http-client@2.2.3` 的传递依赖（`undici ^5.25.4`），与 SDK 无关；
  如需清零需用原生实现替换 `@actions/core`，应单独立项整改。
- **交付**：分支 `fix-undici-fetch-fallback`（基于 `upstream/main` `9312c86`），
  commit `69091ff`，commit body `Fixes #19`。

## 5. 待用户裁决（1 条）

### #11 华为云账号 ID 硬编码（红线 5.3.2）

- **位置**：`src/config.js:11` `accountId: '4d29a984c4fe4e6eb5d404a853d0084e'`。
- **事实**：账号 ID 不是凭证/密钥；`configure({ accountId })` 已可覆盖（`config.js:53-64`）；
  该值决定 `iam::<accountId>:agency:<agencyName>` 与 OIDC provider URN，属功能必需默认值。
- **建议**：**非问题归档**（内置默认值 + 可覆盖 + 非敏感标识），与 playbook「公网地址硬编码」
  区分点在于：地址硬编码会导致环境切换必须改源码重新发版，而本项已具备运行时覆盖能力。
- **备选**：若要求外置，采用环境变量注入（`HUAWEICLOUD_OIDC_ACCOUNT_ID`），默认值保持原值不变，属白名单内等价加固。
- **请用户选择 A（非问题归档）/ B（环境变量注入）**。

## 6. 非问题（3 条，待回复后关闭）

| Issue | 判定依据（`security-non-issue-catalog.md`） | 已核实的缓解因素 |
|---|---|---|
| #6（+ 已关 #8，同根因） | 门禁设计：`pull_request_target` 检出并执行外部 PR 代码 | ① `pre-commit.yml:67` 的 pre-commit job **未引用任何 secrets**（`ROBOT_TOKEN` 只在 `pr-label-running`/`label-pr` 两个不检出 PR 代码的 job，`:30`/`:78`）；② 代码快照已无 `allow-unsafe-pr-checkout` 字段（见 `pre-commit.yml:42-46`）；③ 残留的 workflow 级 `permissions: pr: write` 收敛属平台侧整体加固，不在单仓整改范围 |
| #9 | 自有门禁配置中的可变 tag 依赖 | `openlibing/pr-label-action@v1.0.0`、`openlibing-pre-commit-action` 为一方式插件；hook 来自 `gh_mirrors`/`GitHub_Trending` 镜像的官方上游。可顺手固定 SHA，但不作安全整改项 |
| #12 | **新增模式**：捆绑三方库中条件性关闭证书校验（默认不可达） | `test-apig-action/dist/index.js:2161` `this._ignoreSslError = false` 为 `@actions/http-client` 默认值，仅当调用方传 `requestOptions.ignoreSslError` 才置 true；全仓（src 与 dist 调用侧）**无任何 `ignoreSslError`/`allowUnauthorized` 传参**，`:2551/:2575` 分支不可达。为三方库自带实现，属「三方库自带代码」噪音 |

> #12 需在 `security-non-issue-catalog.md` 新增「三方库条件性不安全默认值（不可达路径）」条目。

## 7. PR 分组策略（硬规则 4：同类同段合并）

| PR | 关联 Issue | 改动文件 | 说明 |
|---|---|---|---|
| PR-A（已实施） | #7 #15 | `.gitcode/workflows/deploy.yml` | 同段代码（npmrc 写入/清理/权限），commit `1694a33` |
| PR-B（已实施） | #10 #17 #21 | `src/oidc.js`、`src/http.js`、`src/credentials.js`、`test/` | 同一批日志出口脱敏与清洗，commit `1694a33` |
| PR-C（已实施） | #16 | `src/signer-v11.js`、`test/` | 独立缺陷（header 取值路径），commit `1694a33` |
| PR-D（已实施） | #20 | `.gitcode/actions/test-{obs,apig-obs}-action/index.js` + 重建 `dist` | Action 产物，commit `1694a33`，需统一自测 |
| PR-E（已实施） | #18 | `src/config.js`、`src/oidc.js`、`test/` + 3 个 Action 的 `dist` | 按调用点补参数校验；分支 `fix-undici-fetch-fallback`，待建 PR |
| PR-F（已实施） | #19 | `src/http.js`、`package.json`、`package-lock.json`、3 个 Action 的 `dist`/lock、`test/` | 零依赖回退替代升 undici；分支 `fix-undici-fetch-fallback`（`69091ff`），待建 PR |

> 实际交付形态：PR-A/B/C/D/E/F 全部落在同一分支 `fix-undici-fetch-fallback`
> （`69091ff` → `911230a` → `1694a33`）。因 3 个 Action 的 `dist` 为共用产物（各 1.6MB 单文件），
> 分分支提 PR 会产生大面积冲突，按硬规则 4「同一模块改动合并到一个 PR」合并为一个 PR 提交，
> PR 描述按上表分组说明各 issue 对应改动。

每个 PR 创建后同步合入 `fix-security-remediation` 分支供统一自测；全部 PR 打 `ai-assisted` 标签并关联 issue。

## 8. 验证与交付要求

- 等价加固类（PR-A/B/C/D）：`npm test` 全绿 + 新增边界用例；PR-D 额外重建 dist 并 diff 确认仅预期改动。
- 每轮交付必须在 commit message/回复中给出《业务逻辑影响声明》：
  「本改动未触及业务逻辑」或逐条列明触及点及类别。
- 业务逻辑影响评估：#18 已按用户决策改为「按调用点补校验」，影响评估见 4.1 行为影响声明，
  不再单独成文；#19 已获用户批准采用方案 C 实施（零依赖回退，无运行时升级），影响评估见 4.2 实施记录。
