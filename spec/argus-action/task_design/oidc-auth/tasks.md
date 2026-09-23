# argus-action OIDC 认证整改 — 实现任务与验证记录

## 进度: 6/6

### Task A — 华为云侧（用户完成）

- [x] 确认 OIDC 身份提供商 / 信任委托 / oidc:sub 覆盖目标仓库 / APIG 接口 IAM 认证

### Task B — 插件仓（argus-action / vulnerability-hunting-action）

- [x] Task B1: `package.json` 增加 `@openlibing/huaweicloud-oidc-client@^0.0.5` + `@actions/core`（携带 undici 供 node16 回退）
- [x] Task B2: 改写 `argus-scan.js`，用 `callApig('GET', url, { 'x-stage': 'RELEASE' })` 替代 signer.js 签名；保留门禁/404/中文输出/退出码
- [x] Task B3: `action.yml` 移除 `scan-access-key`/`scan-secret-key`，新增 `debug` 输入；`using: node16`；`main: ./dist/index.js`
- [x] Task B4: 删除 `dist/signer.js`，ncc 重建 dist（858kB，内联 SDK+undici）+ zip 重新打包；`dist/index.js` 移出 gitignore 并入库
- [x] Task B5: 本地 mock 回归（拦截 fetch 模拟 STS 换证 + APIG 响应），5 场景全通过
- [x] Task B6: 提交 commit 交付（`1066185`，分支 oidc-auth）

### Task C — Test-action 测试仓 workflow

- [x] 顶层新增 `permissions: repository: read, id-token: write`
- [x] 移除 `scan-access-key`/`scan-secret-key` 输入，改为引用 `@oidc-auth` 分支（commit `e14873f`，分支 test-argus）

## 验证记录

### 本地 mock 回归（Task B5）

拦截 global fetch，注入 `HUAWEICLOUD_OIDC_TOKEN` 模拟 OIDC→STS→APIG 全链路：

| 场景                               | 数据                            | exit | 结果                 |
| ---------------------------------- | ------------------------------- | ---- | -------------------- |
| GATE（存量 5，scanSuccess=true）   | pendingConfirm 3 + pendingFix 2 | 非0  | ❌ 扫描未通过 ✓      |
| BOTH（存量 27，scanSuccess=false） | 27 + 0                          | 非0  | ❌ + ⚠️ 并存 ✓       |
| ONLY_SCANFAIL                      | 0 存量 + false                  | 0    | ⚠️ 门禁放行 ✓        |
| PASS                               | 0 存量 + true                   | 0    | ✅ 扫描通过 ✓        |
| NOTFOUND                           | 404 代码仓不存在                | 非0  | 错误：代码仓未配置 ✓ |

APIG 请求头捕获确认：`Authorization: V11-HMAC-SHA256 Credential=<AK>/<date>/cn-southwest-2/apic`、`X-Security-Token`、`x-sdk-date`、`x-stage: RELEASE` 全部正确。

### 真实 CI 端到端（测试机验证）

GitCode Actions 流水线日志确认：

- OIDC ID Token 申请成功（`iss=actions-results.atomgit.com`，`aud=huawei-cloud-service`）
- STS 换证成功，临时凭证有效期约 3599s
- APIG 调用 HTTP 200，`code:200`，scanSuccess:true → 扫描通过

## 遇到的环境问题（runner 侧，与插件无关）

- 自建主机 runner（openlibing-ci-pub，region=cn）执行时 step 无日志：listener 抛
  `ArrayIndexOutOfBoundsException`（`JobHostContext.addStepRunRecord`，`step_records_cnt` 少 1，
  最后一步越界）。同 workflow 在其他 runner（test2）正常 → 属于 runner agent 与平台 job
  协议不兼容，重建/换 agent 版本可解决，非插件问题。
- `Current runner version: 0` 为平台展示正常值，不影响执行。

## 提交与交付

- 插件仓：`oidc-auth` 分支 `1066185`（OIDC 改造），Test-action：`test-argus` `e14873f`
- 业务 Issue：https://gitcode.com/openlibing/vulnerability-hunting-action/issues/1（标签 ai-assisted）
- 业务 PR：待用户确认后创建（Phase 4），本文档随 docs PR 归档（Phase 5）
