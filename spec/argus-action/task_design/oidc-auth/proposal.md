# argus-action OIDC 认证整改

## 需求背景

当前 argus-action 插件通过 `scan-access-key` / `scan-secret-key`（永久 AK/SK secrets）以 SDK-HMAC-SHA256 签名调用华为云 APIG 接口。永久密钥长期有效、泄露面大、轮换成本高、权限往往大于最小需要。

测试仓（Test-action）后续认证方式要转 OIDC 认证：基于 CI 流水线 OIDC ID Token → 华为云 STS 临时凭证 → V11-HMAC-SHA256 签名调用 APIG，全程零 AK/SK。

## 功能描述

- 使用 `@openlibing/huaweicloud-oidc-client` SDK 替代现有 `signer.js` 手工签名
- 移除 `action.yml` 的 `scan-access-key` / `scan-secret-key` 输入，新增 `debug` 输入
- 保留现有门禁/404/中文输出/退出码行为不变
- 打包方式从「拆分源文件直接运行」改为 **ncc 单文件产物**（runner 不执行 npm install，第三方 SDK 必须内联）
- `dist/index.js`（ncc 产物）从 gitignore 移除，作为运行时入口提交入库

不做什么：

- 不涉及华为云侧 IAM/APIG 配置（Task A 已由用户确认完成）
- 不涉及 Test-action 仓库 workflow 改动（Task C 单独完成）

## 验收标准

- [x] 插件仓库不含任何永久 AK/SK 输入或签名实现
- [x] 调用 callApig 完成 OIDC 免密换证 + V11 签名，日志出现换证/凭证获取成功关键步骤
- [x] 有存量漏洞（pendingConfirm+pendingFix>0）退出码非 0，summary 中文展示
- [x] 仅 scanSuccess=false 时门禁放行（exit 0）并提示
- [x] 代码仓 404 时中文引导录入 OpenLibing
- [x] 无存量且 scanSuccess=true 时通过
- [x] 本地 mock 回归测试覆盖上述分支
- [x] 真实 CI 端到端：OIDC 申请→STS 换证→V11 签名→APIG 200→门禁判定通过

## 影响范围

| 文件                                            | 操作 | 说明                                                             |
| ----------------------------------------------- | ---- | ---------------------------------------------------------------- |
| `actions/argus-action/package.json`             | 修改 | 增加 `@openlibing/huaweicloud-oidc-client`、`@actions/core` 依赖 |
| `actions/argus-action/dist/argus-scan.js`       | 修改 | 使用 callApig 替换 signer.js 签名                                |
| `actions/argus-action/dist/index.js`            | 新增 | ncc 产物（内联 SDK），运行时入口                                 |
| `actions/argus-action/dist/signer.js`           | 删除 | 不再需要                                                         |
| `actions/argus-action/action.yml`               | 修改 | 移除密钥输入、新增 debug、main 指向 dist/index.js                |
| `zip.js`                                        | 修改 | 打包 ncc 单文件产物                                              |
| `.gitignore`                                    | 修改 | 移除 dist/index.js 忽略                                          |
| Test-action `.gitcode/workflows/argus-scan.yml` | 修改 | 增加 id-token permission，移除密钥输入（Task C）                 |
