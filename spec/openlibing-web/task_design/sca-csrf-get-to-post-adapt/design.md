# design: 适配后端 SCA CSRF 修复（GET → POST）

## 方案概述

将前端 2 个 API 文件中共 10 处调用点的 HTTP method 从 GET 切换为 POST，URL 与参数传递方式保持不变。后端 PR #256 已将 `@GetMapping` 改为 `@PostMapping`，但 `@RequestParam` 注解保留，POST 请求下仍可从 query string 接收参数，因此前端调用方代码（`{ params: {...} }`）无需调整。

## 改造原则

1. **最小改动**：仅切换 HTTP method，不调整 URL、参数结构、响应处理、调用方代码。
2. **保持 query string 传参**：axios 在 POST 请求下，`params` 字段仍会拼到 URL query string（不会进 body），后端 `@RequestParam` 可正常接收，无需将 `params` 改为 `data`。
3. **不动调用方**：业务页面（`*.vue`）中的调用代码不变，仍传 `{ params: {...} }`。

## 文件级改动详情

### 文件 1: `apps/web-openlibing/src/api/scaApi/softWareCompent.js`

该文件使用 `apiClient.get(url, a, s)` / `apiClient.post(url, a, s)` 风格，第二参数 `a` 是 `AxiosRequestConfig`（即 `{ params: {...} }`）。

| 行号    | 方法名                              | 改造前                                                                                 | 改造后                                                                                  |
| ------- | ----------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 79-85   | `refreshConfirmNum`                 | `apiClient.get('/gateway/openlibing-sca/' + 'scan/refresh/confirmNum', a, s)`          | `apiClient.post('/gateway/openlibing-sca/' + 'scan/refresh/confirmNum', a, s)`          |
| 158-164 | `exportDataStatus`                  | `apiClient.get('/gateway/openlibing-sca/' + 'open/scan/putExportXLS', a, s)`           | `apiClient.post('/gateway/openlibing-sca/' + 'open/scan/putExportXLS', a, s)`           |
| 338-344 | `exportCommunityData`               | `apiClient.get('/gateway/openlibing-sca/' + 'open/scan/export/community/count', a, s)` | `apiClient.post('/gateway/openlibing-sca/' + 'open/scan/export/community/count', a, s)` |
| 350-356 | `exportLicenseData`                 | `apiClient.get('/gateway/openlibing-sca/' + 'license/export/community', a, s)`         | `apiClient.post('/gateway/openlibing-sca/' + 'license/export/community', a, s)`         |
| 490-496 | `exportBinaryLicenseComplianceData` | `apiClient.get('/gateway/openlibing-sca/' + 'binary/export/license/check', a, s)`      | `apiClient.post('/gateway/openlibing-sca/' + 'binary/export/license/check', a, s)`      |
| 502-508 | `exportBinaryNoticeData`            | `apiClient.get('/gateway/openlibing-sca/' + 'binary/export/notice', a, s)`             | `apiClient.post('/gateway/openlibing-sca/' + 'binary/export/notice', a, s)`             |

### 文件 2: `apps/web-openlibing/src/sca/src/api/softWareCompent.js`

该文件使用 `request({ url, method, params })` 风格，由 `request.js` 转发到 `apiClient[method](url, axiosConfig)`。

| 行号    | 方法名                | 改造前          | 改造后           |
| ------- | --------------------- | --------------- | ---------------- |
| 89-95   | `refreshConfirmNum`   | `method: 'get'` | `method: 'post'` |
| 178-184 | `exportDataStatus`    | `method: 'get'` | `method: 'post'` |
| 368-374 | `exportCommunityData` | `method: 'get'` | `method: 'post'` |
| 380-386 | `exportLicenseData`   | `method: 'get'` | `method: 'post'` |

> 注：该文件未实现 `exportBinaryLicenseComplianceData` 和 `exportBinaryNoticeData`，无需改造。

## 参数传递兼容性分析

### 后端接口签名（来自 PR #256 diff）

所有 6 个被改的后端接口均使用 `@RequestParam` 接收参数，例如：

```java
@PostMapping(value = "/export/community/count")
public ResponseEntity exportCommunityCount(
    @NotBlank @RequestParam(name = "community") String community,
    @RequestParam(name = "platform") String platform, ...) { ... }
```

### 前端调用方式

调用方在业务页面中传 `{ params: {...} }`：

```js
softWareCompent.exportCommunityData({
  params: {
    community: this.chooseCommunityValue,
    platform: this.choosePlatformValue,
  },
}).then(...)
```

### 兼容性结论

- axios 在 POST 请求下，`params` 字段会作为 query string 拼到 URL 上（参考 axios 文档：`params` 是 "URL parameters to be sent with the request"，与 method 无关）。
- 后端 `@RequestParam` 在 POST 请求下可从 query string 接收参数（Spring MVC 行为）。
- 因此**前端调用方代码完全不需要改动**，只需把 API 方法定义层的 `get` 切换为 `post`。

## 影响范围

### 直接影响

- 2 个 API 文件，10 处调用点。
- 6 个业务页面的功能（间接影响，调用方代码不变）：
  - `views/sca/softInformation/gitUrlList.vue`：批量确认后刷新统计、导出任务状态
  - `views/sca/softInformation/communityList.vue`：导出风险数据、导出 License 兼容性
  - `views/sca/softInformation/binaryList.vue`：二进制 Notice 导出
  - `views/sca/softInformation/binaryLicenseList.vue`：二进制 License 导出

### 不受影响

- `refresh/confirmNum/V2`（已是 POST，本次不动）
- `scan/confirm/V2`、`scan/confirm/path/V2`（已是 POST）
- 其他所有 GET 接口（后端未改）

### 潜在风险

1. **CSRF Token**：`ApiClient` 已在请求头注入 `Csrf-Token-Open-Li-Bing`（见 [ApiClient.ts:82-83](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/api/ApiClient.ts#L82-83)），POST 请求下也会自动带上，符合后端 CSRF 修复预期。
2. **环境时序**：后端 PR #256 未合入或未部署时，前端改为 POST 会导致 405。需协调前后端合入时机。
3. **CORS / 网关**：网关已配置 `/gateway/openlibing-sca/` 路由，POST 方法在网关层无特殊限制（其他 POST 接口已正常工作）。

## 验证策略

### 静态验证

- `pnpm lint`（ESLint）通过
- `pnpm build` 或 `pnpm dev` 启动无 TS 报错

### 动态验证（gamma 环境）

后端 PR #256 部署到 gamma 后，逐个验证 6 个功能点：

1. 进入 `软件成分 > 软件信息` 页面，触发批量确认 → 检查 `refreshConfirmNum` 是否返回 200
2. 触发导出任务 → 检查 `exportDataStatus` 是否返回 200
3. 在社区列表点击"导出风险数据" → 检查 `exportCommunityData` 是否返回 200
4. 在社区列表点击"导出 License 兼容性" → 检查 `exportLicenseData` 是否返回 200
5. 在二进制兼容性页面点击"导出 Notice" → 检查 `exportBinaryNoticeData` 是否返回 200
6. 在二进制 License 列表点击"导出" → 检查 `exportBinaryLicenseComplianceData` 是否返回 200

### 回归验证

- 检查 `refresh/confirmNum/V2`（已是 POST）未受影响
- 检查其他 GET 接口（如 `getCommunityTreeData`、`getRepos`）未受影响

## 替代方案（已否决）

- **方案 B：同时改 `params` 为 `data`**：将参数从 query string 迁移到 body。否决原因：后端 `@RequestParam` 在 POST 下可从 query string 接收，无需迁移；迁移反而增加改动面和风险。
- **方案 C：调用方也改造**：让业务页面传 `data` 而不是 `params`。否决原因：违反最小改动原则，无必要。

## 部署与回滚

- **部署时机**：建议后端 PR #256 合入并部署到 gamma 后，再合入前端 PR。
- **回滚**：revert 前端 PR 即可恢复 GET 调用。
