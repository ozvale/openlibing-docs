# repos-contents-url-injection — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 新增 `validateFilePath`，在 `getReposContents` 入口拒绝空白、`..`、`?` `#` `&` `@` `\`、控制字符与空白（`38591bcc`）
- [x] Task 2: 新增 `encodeFilePath` 并在 `buildApiUrl` 使用编码后的 `file`；`getFileContentFromUrl` 接入 `SsrfsafeUrlUtil.validateUrl`（`38591bcc`）
- [x] Task 3: `getReposContents` 增加仓库权限校验（`4001` / `403`），Controller 与 Service 接口新增可选 `userId`（`f6c677ca`）
- [x] Task 4: 补充 `OpenScanServiceImplTest` 9 个用例并适配 `OpenScanControllerTest`（`38591bcc`、`f6c677ca`）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                                    | 关联                            |
| ---------- | ----------------------------------------------------------------------- | ------------------------------- |
| `38591bcc` | fix(analysis): harden getReposContents file param against URL injection | `Refs #119`                     |
| `f6c677ca` | fix(analysis): add repo permission check to getReposContents            | 无 Refs（与 #156 鉴权批次共用） |

关键 diff：

- `38591bcc`：`getReposContents` 首行 `validateFilePath(fileName)`；新增 `validateFilePath` / `encodeFilePath`；`buildApiUrl` 中 `String file = encodeFilePath(apiUrlDto.getFile())`；`getFileContentFromUrl` 首行 `SsrfsafeUrlUtil.validateUrl(urlString)`；新增 6 个单测用例。
- `f6c677ca`：Controller / Service 接口新增 `userId`；Service 实现增加 `prIsOpenSourceRepo` / `prDetailAuth` 分支（`4001` / `403`）；单测新增私仓未登录、无权限、开源仓匿名放行 3 个用例，既有用例适配新签名。

验证方式：

- 单测：`OpenScanServiceImplTest` 共 9 个相关用例（`getReposContents_rejectsBlankFileParam`、`getReposContents_rejectsPathTraversal`、`getReposContents_rejectsUrlInjectionChars`、`getReposContents_rejectsCrlfAndControlChars`、`encodeFilePath_encodesSegmentsButKeepsSlash`、`getReposContents_privateRepoWithoutUserRejected`、`getReposContents_userWithoutPermissionRejected`、`getReposContents_openSourceRepoWithoutUserAllowed`、`getReposContents_validatesOutboundUrlBeforeRequest`）。
- 静态核实：当前 `OpenScanServiceImpl#getReposContents` L1646-L1669 为校验 + 权限 + 取 scanInfo 顺序；`buildApiUrl` L1776 使用 `encodeFilePath`；`getFileContentFromUrl` L1807 调用 `SsrfsafeUrlUtil.validateUrl`。
- 未验证：未执行 `mvn test` 复核通过情况；未做前端联调验证 `userId` 透传后的私仓访问行为。
