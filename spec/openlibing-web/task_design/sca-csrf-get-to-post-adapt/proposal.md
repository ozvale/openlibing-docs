# proposal: 适配后端 SCA CSRF 修复（GET → POST）

## 背景

后端仓 `openlibing/openlibing-sca` 的 PR [#256](https://gitcode.com/openlibing/openlibing-sca/pull/256)（`fix(codeql): fix 81 CodeQL findings and security vulnerabilities`）为修复 CodeQL 静态扫描发现的 CSRF 漏洞，将 11 个状态变更类接口从 `@GetMapping` 改为 `@PostMapping`。后端计划合入 `release_20260730` 分支并发布到 gamma 环境。

前端仓 `openlibing-web` 中有部分接口调用与上述改造接口对应。后端合入后，前端如果不做对应适配，相关功能将出现 405 Method Not Allowed 错误。本需求负责在前端仓对受影响的接口调用进行 HTTP method 适配（GET → POST）。

## 需求范围

仅适配前端实际调用到的、被后端 PR #256 改为 POST 的接口。后端改了 11 个接口，前端实际用到 6 个唯一接口（在 2 个 API 文件中共 10 处调用点）。

### 前端实际需要改造的接口清单

| #   | 后端 Controller         | 后端方法             | 后端 URL（相对路径）      | 前端调用方法                        | 前端文件                                                 | 前端行号 |
| --- | ----------------------- | -------------------- | ------------------------- | ----------------------------------- | -------------------------------------------------------- | -------- |
| 1   | OpenScanDMController    | refreshConfirmNum    | `/refresh/confirmNum`     | `refreshConfirmNum`                 | `apps/web-openlibing/src/api/scaApi/softWareCompent.js`  | 79-85    |
| 2   | OpenScanController      | putExportXLS         | `/putExportXLS`           | `exportDataStatus`                  | `apps/web-openlibing/src/api/scaApi/softWareCompent.js`  | 158-164  |
| 3   | OpenScanController      | exportCommunityCount | `/export/community/count` | `exportCommunityData`               | `apps/web-openlibing/src/api/scaApi/softWareCompent.js`  | 338-344  |
| 4   | LicenseController       | getScanIssueQuery1   | `/export/community`       | `exportLicenseData`                 | `apps/web-openlibing/src/api/scaApi/softWareCompent.js`  | 350-356  |
| 5   | BinaryLicenseController | exportLicense        | `/export/license/check`   | `exportBinaryLicenseComplianceData` | `apps/web-openlibing/src/api/scaApi/softWareCompent.js`  | 490-496  |
| 6   | BinaryLicenseController | exportNotice         | `/export/notice`          | `exportBinaryNoticeData`            | `apps/web-openlibing/src/api/scaApi/softWareCompent.js`  | 502-508  |
| 7   | OpenScanDMController    | refreshConfirmNum    | `/refresh/confirmNum`     | `refreshConfirmNum`                 | `apps/web-openlibing/src/sca/src/api/softWareCompent.js` | 89-95    |
| 8   | OpenScanController      | putExportXLS         | `/putExportXLS`           | `exportDataStatus`                  | `apps/web-openlibing/src/sca/src/api/softWareCompent.js` | 178-184  |
| 9   | OpenScanController      | exportCommunityCount | `/export/community/count` | `exportCommunityData`               | `apps/web-openlibing/src/sca/src/api/softWareCompent.js` | 368-374  |
| 10  | LicenseController       | getScanIssueQuery1   | `/export/community`       | `exportLicenseData`                 | `apps/web-openlibing/src/sca/src/api/softWareCompent.js` | 380-386  |

### 后端改了但前端未调用的接口（无需适配，仅记录）

- `TblScancodeInfoController.getScanCodeInfo` (`/getScanCodeInfo`)
- `OpenPersonScanController.refreshVersionData` (`/refreshVersionData`)
- `OpenPersonScanController.refreshPersonData` (`/refreshPersonData`)
- `OpenScanController.versionSchedule` (`/versionSchedule`)
- `OpenScanDMController.refreshRepoidCommunityRepo` (`/refresh/repoid-community-repo`)

## 非目标

- 不修改后端代码（后端 PR #256 已在合入流程中）。
- 不重构前端 API 调用层（仅切换 method，不调整 URL、参数传递方式、返回处理逻辑）。
- 不处理 `refresh/confirmNum/V2`、`scan/confirm/path/V2` 等已是 POST 的接口。
- 不调整接口的请求参数格式（后端 `@RequestParam` 在 POST 下仍可从 query string 或 form body 接收，前端现有 `params` 传参方式保持不变即可兼容）。

## 验收标准

### 功能验收

1. **接口调用成功**：后端 PR #256 合入并部署到 gamma 后，前端以下功能在 gamma 环境验证可正常调用（不再返回 405）：
   - 批量确认后刷新统计数（`refreshConfirmNum`）
   - 导出任务状态查询（`exportDataStatus`）
   - 导出风险数据报表（`exportCommunityData`）
   - 导出 License 兼容性（`exportLicenseData`）
   - 二进制包级兼容性 License 导出（`exportBinaryLicenseComplianceData`）
   - 二进制包级兼容性 Notice 文件导出（`exportBinaryNoticeData`）

2. **参数传递正确**：POST 请求下，原 GET 的 query 参数仍按 `params`（axios 风格，挂到 URL query string）传递，后端 `@RequestParam` 能正确接收。

3. **行为一致**：响应内容、错误处理、loading 状态、UI 反馈与改造前一致。

### 工程验收

4. **改动范围受限**：本次提交仅涉及 2 个 API 文件中 10 处调用点的 `method`/`apiClient.get` → `apiClient.post` 切换，不得引入无关改动、格式化、重构。
5. **本地构建通过**：`pnpm build`（或 `pnpm dev` 启动）无 TypeScript / ESLint 报错。
6. **关联 Issue**：业务 PR 必须关联业务 Issue（按 AGENTS.md 规则）。
7. **PR 标签**：业务 PR 必须打上 `ai-assisted` 标签。

## 风险与回滚

- **风险**：后端 PR #256 可能尚未合入或未部署到目标环境。前端先合入会导致早期环境（仍为 GET）调用失败。
- **缓解**：前端 PR 与后端发布协调时机，建议在后端 gamma 部署完成后再合入前端；或在前端 PR 描述中明确标注"依赖后端 PR #256 合入"。
- **回滚**：仅需 revert 前端 PR 即可恢复 GET 调用。

## 关联信息

- 后端 PR：https://gitcode.com/openlibing/openlibing-sca/pull/256
- 后端目标分支：`release_20260730`
- 后端改动类型：CSRF 修复（`@GetMapping` → `@PostMapping`）
- 前端目标仓：`openlibing/openlibing-web`
- 前端目标分支：`feat-sca-csrf-adapt`（基于主仓 master 新建）
