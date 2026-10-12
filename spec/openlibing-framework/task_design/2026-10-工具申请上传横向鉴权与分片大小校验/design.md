# 设计说明：工具申请上传接口横向鉴权与分片大小校验

## 1. 方案概述

对齐本仓既有的横向鉴权模式（`CommonService.verifyPermissions`），为工具申请的两个上传接口补齐鉴权与分片大小校验。

### 1.1 横向鉴权

- 复用 `UrlConstant.SAVE_TOOL_APPLY`（`/openlibing-framework/tool-apply/save-tool-apply`）作为鉴权 URL。
  - 原因：横向鉴权依赖 `menu_url_info.menu_url` **精确匹配**，复用「工具申请」菜单 URL 无需新增库内菜单数据；这两个接口本属同一申请页面上传动作，可访问该页面的角色即可上传。
- 鉴权上下文由请求参数提供（工具此时尚未创建，无法使用 `ownerProjectId`）：
  - `saveToolIcon(userId, projectId, toolName, iconFile)`
  - `saveToolSoftwarePack(userId, projectId, toolInfo, softwarePack, chunkIndex, totalChunks, uploadId)`
- 鉴权位置：**业务逻辑之前**（saveToolIcon 在查询工具是否存在之前；saveToolSoftwarePack 在解析 toolInfo 之前），失败即抛 `PermissionException`（fail-closed），由 `GlobalExceptionHandler` 统一返回。

### 1.2 分片上传大小校验

- 新增常量 `MAX_SOFTWARE_PACK_SIZE = 5L * 1024 * 1024 * 1024`（5GB），完整上传与分片上传共用。
- `validateSoftwarePackFile`（完整上传）改用该常量，行为不变。
- 分片路径在解析出 `uploadId`/`obsPath`/`obsUploadId` 后、上传 OBS Part 之前新增 `validateChunkSize(uploadId, softwarePack)`：
  1. 分片为空 → `分片内容不能为空`；
  2. 单分片 `getSize() > 5GB` → `单个分片大小超过5GB限制`；
  3. 通过 Redis `INCRBY`（`chunk_upload:size:{uploadId}`，原子自增，过期时间与会话一致）累计大小，累计值 `> 5GB` → `安装包总大小超过5GB限制`。
- 校验不通过时：`abortMultipartUpload` 中止 OBS 分段上传 + `cleanupChunkSession` 清理 Redis 会话（含累计大小键），返回失败信息。
- `cleanupChunkSession` 增加删除 `CHUNK_SIZE_PREFIX` 键。

采用 Redis 原子自增而非读改写 Hash，规避并发分片下的计数竞态。

### 1.3 分片上传类型校验

- 完整上传的类型校验（`ImageCheckUtil.uploadFileCheck`）依赖「扩展名 + 内容魔数」，两者都对**完整文件**成立；分片是整包的字节切片，除第 1 片外均不满足，因此只能对**首片**校验。
- 首片即文件头部：`chunkIndex == 1` 时调用 `validateChunkFileType`，读取前 4 字节并要求为 zip 魔数（本地文件头 `50 4B 03 04`、中央目录结束 `50 4B 05 06`、分卷 `50 4B 07 08`）。不依赖前端分片文件名，按内容判定，等价于校验整个文件头。
- 校验失败时同样 `abortMultipartUpload` + `cleanupChunkSession` 并返回 `只能上传zip格式安装包`；读取异常返回 `校验分片文件类型失败`。
- 说明：`ImageCheckUtil.getFileType` 为 private 且会整文件读入内存，无法复用，故在 `ToolApplyServiceImpl` 内实现轻量的魔数判断（仅读首片前 4 字节）。

## 2. 变更清单

| 文件 | 变更 |
| --- | --- |
| `business/controller/ToolApplyController.java` | `saveToolIcon` 增加 `projectId`（`@NotNull`+`@Min(0)`）；`saveToolSoftwarePack` 增加 `userId`（`@NotBlank`）、`projectId`（`@NotNull`+`@Min(0)`），透传 Service |
| `business/service/ToolApplyService.java` | 两个方法签名同步新增参数 |
| `business/service/impl/ToolApplyServiceImpl.java` | 两个方法入口新增 `verifyPermissions`；新增 `MAX_SOFTWARE_PACK_SIZE`/`CHUNK_SIZE_PREFIX` 常量；新增 `validateChunkSize`、`validateChunkFileType`/`isZipHeader` 与 zip 魔数常量；`chunkUpload` 调用校验；`cleanupChunkSession` 增删键；`validateSoftwarePackFile` 复用常量 |
| `test/.../ToolApplyControllerTest.java` | 更新调用签名，补充用例 |
| `test/.../ToolApplyServiceImplTest.java` | 新增鉴权与分片大小校验用例；`cleanupChunkSession` 断言改为 4 次删除 |

## 3. 兼容性与风险

- **接口契约变更**：新增必填请求参数，前端未同步前调用将 400（参数校验失败）。需前后端协同发布，已在 proposal 验收标准中标注。
- 复用 `SAVE_TOOL_APPLY` 菜单 URL：若后续安全要求为上传接口单独配置菜单权限，可再新增 `menu_url_info` 数据与独立 URL 常量。
- 分片重传（相同 `chunkIndex` 重复请求）会使累计值重复计数；当前实现采用会话失败即整体中止的策略，重传通常新建 `uploadId`，影响可接受。

## 4. 测试策略

| 层级 | 用例 |
| --- | --- |
| Controller | `saveToolIcon`/`saveToolSoftwarePack` 新签名调用与透传（含空文件参数校验） |
| ServiceImpl | `saveToolIcon`、`saveToolSoftwarePack` 均调用 `verifyPermissions`（绝对路径 `SAVE_TOOL_APPLY`）；`validateChunkSize`：空分片 / 单分片超限 / 累计超限 / 正常；`validateChunkFileType`：空分片 / 非 zip / 头部不足 4 字节 / zip 首片 / 读取异常；`cleanupChunkSession` 清理 4 个键 |
| 质量门禁 | `spotless:apply checkstyle:check compile spotbugs:check pmd:check` 全通过 |
| 安全审查 | 鉴权/上传相关改动执行安全审查 |
