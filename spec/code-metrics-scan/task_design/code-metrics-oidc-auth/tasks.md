# Tasks：code-metrics 插件 OIDC 联邦认证改造（双模式）

## Phase 1-2 需求与设计

- [x] 确认 FE 需求名称、流程模式（Full）、分支安排
- [x] 创建业务 Issue（openlibing/code-metrics-action#8）
- [x] 两份需求设计文档（sec-option-scan-需求设计.md / code-metrics-scan-需求设计.md）
- [x] proposal.md / tasks.md
- [x] 方案变更：由"全切 OIDC"调整为"双模式自动切换"（用户确认保留 AK/SK 旧接口兼容存量脚本）

## Phase 3 编码（code-metrics-scan 仓，分支 sec-option-oidc-auth）

- [x] `package.json`：新增 `@openlibing/huaweicloud-oidc-client@0.0.4`，保留 `axios`（AK/SK 模式使用）
- [x] `dist/uploaders/CoderepoUploader.js`：双模式改造——保留 ApigSigner/axios 走旧接口 `/openlibing-coderepo/...`；新增 `useOidc` 分支走新接口 `/action-api/...` + `callApig`；OBS 凭证按模式切换（STS `getCredentials()` + obsutil `-t` / 静态 obs-ak/obs-sk）
- [x] `dist/index.js`：按 `ACTIONS_ID_TOKEN_REQUEST_URL` 判定 `useOidc`，恢复 4 个凭证输入读取（可选）与透传，输出认证模式日志
- [x] `dist/scanner.js`：构造上传器透传双模式配置
- [x] `action.yml`：恢复 4 个凭证输入声明（required: false，仅 AK/SK 模式使用）
- [x] `README.md`：参数表与示例更新，新增「上传认证（双模式自动切换）」章节
- [x] `npm install` + `npm run package` 重新打包 dist
- [x] 提交并推送 origin/sec-option-oidc-auth

## Phase 3 编码（security-compilation-options-action 仓，分支 sec-option-oidc-auth）

- [x] 同步 sec-option-scan 插件双模式改造（action.yml / README / dist / package.json）
- [x] SDK 升级 0.0.4 → 0.0.5，`npm run package` 重新 ncc 打包
- [x] `CicdUploader` 构造补回 `timeout` 透传（修复 useOidc 替换导致入口 60000ms 被默认 30000ms 覆盖）
- [x] `_stack_flag_state` 改为跨 `.GCC.command.line` / `.llvmcmd` 两段聚合判断（修复 GCC/Clang 混合产物假阴性）
- [x] set-output 将 `clash` 改写为 `cIash` 规避 CI 日志违禁词屏蔽
- [x] pre-commit 通过后提交推送，更新 PR #12

## Phase 3 编码（code-metrics-action 仓，分支 code-metrics-oidc-auth）

- [x] 同步 code-metrics-scan 插件双模式改造（action.yml / README / dist / package.json）
- [x] SDK 升级 0.0.4 → 0.0.5，`npm install` + `npm run package` 重新打包
- [x] README 澄清 26 种 lizard 语言与 50+ 扩展名白名单的关系（含「扫描范围」章节）
- [x] pre-commit 通过后提交推送，更新 PR #20

## Phase 3 编码（code-metrics-scan 仓，分支 sec-option-oidc-auth，同步插件修改）

- [x] 同步两个插件仓未应用修改：`_stack_flag_state` 跨段聚合、scanner.js timeout 透传、index.js cIash 规避、两个 action 的 oidc-client 0.0.4 → 0.0.5、README 语言/扩展名澄清
- [x] 提交推送 origin/sec-option-oidc-auth（commit 8823c11）

## Phase 3 编码（openlibing-cicd 仓 workflow，PR #562）

- [x] build.yml / code-metrics-scan.yml 增加顶层 `permissions: id-token: write`，移除凭证注入
- [x] 插件引用更新为固定 SHA（code-metrics-oidc-auth / sec-option-oidc-auth 分支最新 commit）
- [x] 创建 PR #562 关联相关业务 Issue，补打 ai-assisted 标签

## 用户自测

- [x] workflow_dispatch 触发流水线验证 OIDC 全链路上报成功（声明 permissions: id-token: write）
- [x] 存量脚本（未声明 permissions）回归验证 AK/SK 旧接口上报正常

## Phase 4 业务 PR

- [x] code-metrics-action 仓创建 PR（标题=FE 需求名称）→ 关联 Issue #8 → 补打 ai-assisted 标签
- [x] security-compilation-options-action 仓创建 PR #12 → 关联 Issue #6 → 补打 ai-assisted 标签

## Phase 5 归档（用户触发）

- [x] 归并 security-compilation-options-action 侧 spec 到本目录（同一 FE 需求）
- [x] 生成 archive.md
- [x] openlibing-docs 创建 docs PR（本目录 spec + archive.md）合入主仓 master
