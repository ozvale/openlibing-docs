# repos-contents-url-injection — 技术设计

## 方案概述

在 `getReposContents` 调用链的三个关键位置加固：

```
OpenScanController#getReposContents(scanId, file, userId, request)
  └─ OpenScanServiceImpl#getReposContents
       ├─ validateFilePath(fileName)            // 空白/../?/#/&/@/\ /控制字符/空白 -> ScaException
       ├─ 权限校验：userId 为空 -> prIsOpenSourceRepo 否则 4001
       │             userId 非空 -> prDetailAuth 否则 403
       ├─ getScanInfo -> processFilePath（剥离 community/repo 前缀）
       └─ fetchFileContent
            └─ buildApiUrl: encodeFilePath(file) 后拼接
                 └─ getFileContentFromUrl: SsrfsafeUrlUtil.validateUrl(url) -> HTTP GET
```

## 架构决策

| 决策                                          | 理由                                                                                                                   |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| D1 黑名单字符校验放在入口第一步               | `file` 是唯一用户可控拼接项；先拒绝危险字符，后续流程（查 scanInfo、解析仓库、外发请求）都不会被注入内容触达           |
| D2 拒绝 `..` 而非规范化后比较                 | `file` 是仓库内相对路径，出现 `..` 无合法用途；直接拒绝比 realpath 归一更简单，也避免归一化语义差异（Windows/Unix）    |
| D3 拒绝空白与全部控制字符（含 CR/LF、DEL）    | 防 HTTP 请求头/URL 注入与请求走私类变形；合法仓库路径不含空白                                                          |
| D4 按段 URL 编码并保留 `/`                    | 仅对路径段编码可保留目录层级；`+` 显式替换为 `%20`，避免 `URLEncoder` 表单语义把空格变 `+` 后被服务端误解              |
| D5 编码后再拼 `?ref=` 等固定查询参数          | 保证用户输入无法吞并或覆盖 `ref` 参数语义（`?`/`&`/`#` 已在 D1 拒绝，编码为第二道防线，如 `%`、非 ASCII 字符也被编码） |
| D6 外发前统一 `SsrfsafeUrlUtil.validateUrl`   | 与 `showFileHash` 既有实现保持一致；即使 host 拼接逻辑变化，也有一道统一出口校验                                       |
| D7 复用 `prIsOpenSourceRepo` / `prDetailAuth` | 与 `getTree` 的门禁权限语义一致，避免另写一套判断；4001/403 的语义与既有接口对齐                                       |
| D8 `userId` 设计为可选参数                    | 保持后端兼容：开源仓允许匿名访问；私仓匿名访问返回 `4001` 提示登录，不直接 500                                         |

## 关键实现（当前代码）

`validateFilePath`（`OpenScanServiceImpl`，包级静态）：

```
空 -> ScaException(PARAM_ERROR, "文件路径参数为空")
含 ".." -> ScaException(PARAM_ERROR, "文件路径不允许包含路径穿越字符")
任一字符为 ? # & @ \ 或 <0x20 或 0x7F 或 Character.isWhitespace -> ScaException(PARAM_ERROR, "文件路径包含非法字符")
```

`encodeFilePath`：

```
Arrays.stream(file.split("/", -1))
      .map(seg -> URLEncoder.encode(seg, UTF_8).replace("+", "%20"))
      .collect(joining("/"))
```

`getReposContents` 权限分支：

```
if (StringUtils.isEmpty(userId)) {
  if (!prIsOpenSourceRepo(scanId)) throw new ScaException(4001, "private repo, need login", ...);
} else if (!prDetailAuth(scanId, userId)) {
  throw new ScaException(403, "no permission", ...);
}
```

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                                                                                                                                                               |
| ------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenScanController.java`        | 修改 | `getReposContents` 新增 `@RequestParam(value = "userId", required = false) String userId` 并透传                                                                                   |
| `src/main/java/com/openlibing/sca/analysis/service/OpenScanService.java`              | 修改 | 接口签名新增 `userId` 参数与 Javadoc                                                                                                                                               |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`     | 修改 | `validateFilePath` / `encodeFilePath` 新增；`getReposContents` 接入参数校验与权限校验；`buildApiUrl` 使用编码后 `file`；`getFileContentFromUrl` 接入 `SsrfsafeUrlUtil.validateUrl` |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java` | 修改 | 9 个用例：空参数、`..`、URL 注入字符、CRLF/控制字符、编码规则、私仓未登录 4001、无权限 403、开源仓匿名放行、外发 URL 安全校验                                                      |
| `src/test/java/com/openlibing/sca/analysis/controller/OpenScanControllerTest.java`    | 修改 | 3 个既有用例适配 `userId` 参数                                                                                                                                                     |

## 风险 & 缓解

| 风险                                                                                           | 缓解                                                                                                           |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 合法文件名含空格或 `#`（如 `a #1.java`）被拒绝                                                 | 记录为行为变化；此类路径在平台仓库中罕见，若出现需放宽 D1 白名单并同步编码策略                                 |
| 前端未透传 `userId`，已登录用户访问私仓仍被 4001 拒绝                                          | 需要调用方同步改动（跨仓协作项）；`userId` 为可选参数保证后端向前兼容                                          |
| `encodeFilePath` 对已编码输入二次编码（`%` → `%25`）                                           | `file` 来自原始路径，正常不预编码；`%` 不属危险字符，编码后由下游 API 正确解码一次                             |
| `processFilePath` 在编码前剥离 `community/repo` 前缀，若前缀大小写不一致则不剥离，编码后仍安全 | 不影响注入防护；仅影响 URL 指向（404）                                                                         |
| `SsrfsafeUrlUtil.validateUrl` 抛出的 `IllegalArgumentException` 未被该接口捕获转换为业务错误   | 现有 `getFileContentFromUrl` 的 `catch (Exception)` 会兜底返回错误文案；单测按 `IllegalArgumentException` 断言 |
| 权限校验新增两次 DB/Feign 调用，接口延迟上升                                                   | 与 `getTree` 一致，且仅在请求进入时执行；如成为热点可后续加缓存                                                |

## 跨仓影响

- 前端/网关：`getReposContents` 需透传登录用户 `userId`，否则私仓文件读取被拒（4001）。
- 本次 commit `f6c677ca` 的权限校验与 #156（open-api-authz-hardening）存在交集，属同一批鉴权整改的共用改动。

## 明确不在范围

- SSRF 域名白名单、重定向跟随限制（见 SSRF 加固相关 spec）。
- `community` / `repo` 的输入校验。
