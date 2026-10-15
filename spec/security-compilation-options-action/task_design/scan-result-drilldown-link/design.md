# 【openLiBing】安全编译选项扫描插件结果输出增加openLiBing平台扫描结果链接 — 技术设计

- **FE 需求**：【openLiBing】插件结果输出增加openLiBing平台扫描结果链接
- **业务 Issue**：https://gitcode.com/openlibing/code-metrics-action/issues/25
- **涉及仓库**：security-compilation-options-action、openlibing-cicd
- **流程模式**：Full
- **日期**：2026-09-29

## 1. 方案设计

### 1.1 背景与现状

**插件上报链路**：sec-option-scan 在流水线中扫描产物包后，由 `CicdUploader.upload()` 将概览与文件明细上报到 openlibing-cicd：

- `POST /action-api/build-artifact/sec-option/report`（OIDC 联邦认证，`callApig` 签名）

历史上另有 AK/SK 模式的旧网关路径 `/openlibing-cicd/...`（`ApigSigner` 签名 + `apig-app-key`/`apig-app-secret` 输入）与 OIDC 并存：OIDC 为用户主用路径，**AK/SK 模式本次保留**（部分测试仓不适合纳入 OIDC 认证凭据授权项目），本次改造不改变插件鉴权模式。后端 `BuildArtifactController#reportSecOptionScan` → `SecOptionScanServiceImpl#reportScan`（`@Transactional`）完成入库（`sec_option_scan_record` + `sec_option_scan_file_detail`），当前响应为 `DataResult<Long>`，`data` 即雪花 recordId。

**平台前端现状**：产物包详情页 `/apps/securityOptions/package-detail?recordId=...&projectId=...` 已支持 URL 直接定位。页面取数（`fetchRecord`）仅依赖 `recordId`，`projectId` 用于还原项目上下文（新开页由 `Content.vue#getProject` 依 URL 中 projectId 还原项目）。因此 sec-option 记录是项目无关的全局数据，链接的可用性只取决于 recordId。

**问题**：插件已拿到 recordId 但未生成链接；用户需手工在平台中翻找；同时同一 repoUrl 可能归属多个项目（不同 projectId），链接需由服务端确定唯一跳转目标（取查询第一个项目，不返回多链接）。

### 1.2 改造目标

- 服务端在上报响应中返回**固定 1 条**详情链接：按 repoUrl 解析关联项目，取查询第一个项目生成链接（链接仅含 `recordId + projectId`；不返回多链接、不带项目名称）；未解析到项目时返回提示信息（tip），不返回链接
- 插件在上报成功后把链接以 Markdown 超链接（显示文本≠实际链接）输出到工作流运行摘要（ATOMGIT_STEP_SUMMARY），并保留 ATOMGIT_OUTPUT 概览行与运行日志（链接行 key 末尾小写 `url` 触发平台渲染为可点击链接）；未录入场景输出提示行
- 保留插件既有 AK/SK 模式（与 OIDC 并存，部分测试仓不适合纳入 OIDC 凭据授权项目），本次不改变插件鉴权与上报路径
- 不改变上报接口路径、入参、扫描逻辑与现有输出

### 1.3 总体方案

```text
security-compilation-options-action
  scanner.scan() → uploadInfo
      │  CicdUploader.upload()
      │  POST /action-api/build-artifact/sec-option/report（鉴权模式现状不变：OIDC 或 AK/SK）
      ▼
openlibing-cicd  BuildArtifactController#reportSecOptionScan
  SecOptionScanServiceImpl#reportScan（@Transactional）
      1) saveScanRecord + saveFileDetails 入库
      2) buildReportVO(recordId, gitUrl)：
         repo_info 按 repo_url 解析 projectId（精确匹配 → 补 .git 重试；取查询第一行）
         → 取第一个项目拼单条链接（recordId + projectId）；未命中 → detailLink 空 + tip 提示
      ▼
  DataResult<SecOptionScanReportVO> { recordId(String), detailLink(String), tip }
      ▼
插件 parseResult → scanner.uploadInfo.detailLink / tip → index.js
  ATOMGIT_STEP_SUMMARY 追加 Markdown 超链接：- [安全编译选项扫描结果（<包名>）](实际链接)（显示文本≠实际链接）
  ATOMGIT_OUTPUT 同步追加 扫描结果（<包名>）url=链接 概览行（key 末尾小写 url → 平台渲染可点击；机器消费）+ core.info 打印
```

### 1.4 关键决策

1. **链接由服务端拼接完整 URL（多项目取查询第一个项目）**：存在同一 repoUrl 对应不同项目（不同 projectId）的情况，插件无法自行判断该返回哪个链接，服务端按查询顺序取第一个项目生成单条链接（不返回多链接）；且平台地址属于环境配置，放在服务端可避免插件新增平台地址配置项，参数模板（路径/参数名）保持单一来源。
2. **repo_info 按 repo_url 全量解析项目，不带 `assume_pr` 过滤**：现有 `queryProjectIdByUrl` 带 `assume_pr = '1'` 过滤；测试库实测 1160 行中 `assume_pr='1'` 仅 151 行（约 13%），复用会导致绝大多数仓库解析不到项目、无法生成链接。新增查询方法仅按 repo_url 匹配。
3. **匹配规则沿用仓库既有范式**：精确匹配 `repo_url = gitUrl`，未命中且 gitUrl 不以 `.git` 结尾时补 `.git` 重试（对齐 coderepo `findRepoByUrl` 的既有做法）。
4. **未解析到项目时不返回链接、返回提示信息（tip）**：该场景说明 repoUrl 未录入 openLiBing 任一项目，此时输出无 projectId 的链接虽技术上可打开页面，但对用户无有效上下文、且会掩盖"仓库未录入"这一真实问题；改为返回提示文案，由插件在概览中提示用户联系 SRE 完成代码仓录入。提示文案由服务端单点定义（插件不硬编码）；异常场景（DB 查询失败等）不返回提示，仅告警日志，避免误导。
5. **recordId 按字符串返回**：雪花 ID 为 19 位，超出 JS `Number.MAX_SAFE_INTEGER`（2^53-1），按数值返回会在插件侧失真。
6. **仅上报成功后输出链接**：与现有"输出概览/指标"的时机一致；上报失败时不上报数据不落库，输出链接无意义。
7. **链接以 Markdown 超链接双通道输出：显示文本≠实际链接**：`detailLink` 为固定单条链接（多项目取查询第一个项目，不带项目名称），插件把链接渲染为 Markdown 超链接（`- [安全编译选项扫描结果（<包名>）](实际链接)`）写入 `ATOMGIT_STEP_SUMMARY`（官方文档确证该通道渲染 Markdown、展示于工作流运行详情页），显示文本与链接解耦；同时保留 `ATOMGIT_OUTPUT` 的 `key=value` 概览行（链接行 key 为 `扫描结果（<包名>）url`——key 末尾小写 `url` 触发平台渲染为可点击链接、大小写敏感；固定 1 行；供 `steps.<id>.outputs.<name>` 机器消费、兼容既有消费方）。
8. **链接构建异常不阻断上报**：构建逻辑独立兜底捕获，异常时仅告警并返回 `recordId + 空 detailLink + 空 tip`。
9. **保留 AK/SK 模式（本次不移除）**：OIDC 与 AK/SK 双模式并存，AK/SK 的旧网关路径（`/openlibing-cicd/...`）与静态凭证输入项（`apig-app-key`/`apig-app-secret`）全部保留（部分测试仓不适合纳入 OIDC 认证凭据授权项目）；本次仅做输出链路改造，不触碰鉴权与上报路径。
10. **链接不携带平台授权参数（联调后定稿）**：链接仅由 `recordId + projectId` 构成，保持最小参数集。`codeHostingPlatformFlag` 在联调评估后判定非必需（产物包详情页取数仅依赖 recordId，projectId 仅作项目上下文还原），从链接中移除（commit `2f7ea9735`）。

## 2. 实现逻辑设计

### 2.1 服务端（openlibing-cicd）

1. **响应类型调整**：`BuildArtifactController#reportSecOptionScan` 返回类型 `DataResult<Long>` → `DataResult<SecOptionScanReportVO>`，方法体不变（继续委托 `secOptionScanService.reportScan(request)`）。
2. **`SecOptionScanServiceImpl#reportScan`** 在入库完成后、返回前组装响应对象（新增私有方法 `buildReportVO(Long recordId, String gitUrl)`）：
   - `recordId` 取 `String.valueOf(recordEntity.getId())`（雪花 Long → String）；
   - 方法体整体 try-catch 兜底（最后防御性捕获 `Exception`，处理 DB 访问异常等运行时类型），分三种结果：
     - 命中项目：`detailLink` = 单条链接（取查询第一个项目），`tip` 为空；
     - 未命中项目：`detailLink` 为空，`tip` = 提示文案「当前仓未录入openLiBing平台，无法生成跳转链接，请先联系SRE完成代码仓录入。」；
     - 查询/拼接异常：`logger.warn` 记录 gitUrl 与异常摘要，`detailLink` 为空、`tip` 为空（不输出提示，避免误报"未录入"）；
   - 返回 `DataResult.successData(vo)`（保持 msg 与现有 `successData` 行为一致）。
3. **`resolveProject(gitUrl)`**：`RepoInfoMapper#queryProjectsByUrl` 查询（返回 projectId + platform，`ORDER BY project_id` 升序，取**第一行**作为唯一项目）；结果为空且 gitUrl 不以 `.git` 结尾时以 `gitUrl + ".git"` 重试一次；两次均为空返回空。
4. **链接拼接（单条）**：取第一行 `projectId` 生成唯一 1 条链接（不再查询项目名称，响应不含项目名称），url = `host + "/apps/securityOptions/package-detail?recordId=" + recordId + "&projectId=" + projectId`；recordId/projectId 均为纯数字，模板固定，不做 URL 编码、无拼接注入面。
5. **平台地址**：注入 `PipelineService`，复用 `PipelineService#getOpenlibingHost()`（beta/gama/prod 环境映射已有实现），不新增平台地址配置与判定逻辑。
6. **RepoInfoMapper 新增查询**（接口 + XML）：
   - 方法：`List<RepoInfoEntity> queryProjectsByUrl(@Param("repoUrl") String repoUrl)`（复用既有 `repoInfoMap` resultMap，仅 projectId/platform 字段有效）
   - SQL：`SELECT project_id, MAX(platform) AS platform FROM repo_info WHERE repo_url = #{repoUrl} AND project_id IS NOT NULL GROUP BY project_id ORDER BY project_id`（参数化查询，命中既有索引 `idx_repo_url`；不含 `assume_pr` 过滤，见 1.4-2；每 projectId 一行，**服务端取排序第一行作为唯一项目**）

### 2.2 插件侧（security-compilation-options-action）

1. **`dist/uploaders/CicdUploader.js#parseResult`**：在现有 recordId 解析基础上新增 `detailLink` / `tip` 解析（`resData?.data?.detailLink` 为非空字符串时透传，否则为空；`tip` 按字符串透传），返回 `{ success, recordId, detailLink, tip }`；原有兼容分支（`data` 为数值/字符串、`resData.recordId` 等）全部保留，老服务端响应仍可正常解析。
2. **`dist/scanner.js`**（`SecOptionScanner`）：上传成功后 `result.uploadInfo = { success: true, recordId, detailLink, tip }`（携带 detailLink 与 tip）。
3. **`dist/index.js`** 入口（双通道输出）：
   - 扫描循环内收集每个产物包的链接与提示：`target.packageName` → `result.uploadInfo.detailLink / tip`；
   - **ATOMGIT_STEP_SUMMARY 通道**：追加 Markdown 超链接行 `- [安全编译选项扫描结果（<包名>）](实际链接)`（固定 1 行，不随项目数变化；未录入时输出纯文本提示行 `- 安全编译选项扫描结果（<包名>）：<tip>`），使运行摘要页呈现可点击链接而无需暴露长 URL；无 `ATOMGIT_STEP_SUMMARY` 环境变量时跳过（写入失败仅 `core.warning`，与 ATOMGIT_OUTPUT 各自独立判定、互不影响）；
   - **ATOMGIT_OUTPUT 通道**：保留并追加 `key=value` 概览行（`扫描结果（<包名>）url`=`<实际链接>`，固定 1 行；key 末尾小写 `url` 触发平台渲染为可点击链接，大小写敏感），供 `steps.<id>.outputs.<name>` 机器消费（详见 item 4 表）；
   - 对每条链接 `core.info` 打印（打印实际链接），便于运行日志直接查看；
   - 两通道各自判环境变量、各自兜底：任一通道不可用不影响另一通道与上报结果。
4. **输出规则（双通道）**：
   - **ATOMGIT_STEP_SUMMARY（主展示通道，Markdown 超链接）**：显示文本与链接解耦（显示文本 ≠ href）：

| 场景                        | Markdown 行                                                        | 说明                      |
| --------------------------- | ------------------------------------------------------------------ | ------------------------- |
| detailLink 非空             | `- [安全编译选项扫描结果（<包名>）](<实际链接>)`                   | 固定 1 行，不随项目数变化 |
| 未录入（无链接且 tip 非空） | `- 安全编译选项扫描结果（<包名>）：<提示文案>`（纯文本行，无链接） | 插件不硬编码文案          |

- **ATOMGIT_OUTPUT（兼容通道，机器消费）**：保留 key=value 纯值行（供 `steps.<id>.outputs.<name>` 取值、兼容既有消费方），链接行 key 末尾为小写 `url`（平台据此将值渲染为可点击链接、大小写敏感；提示行 key 不带 `url` 后缀，避免提示文本被渲染成无效链接）：

| 场景                          | 输出键                  | 值                                  |
| ----------------------------- | ----------------------- | ----------------------------------- |
| detailLink 非空               | `扫描结果（<包名>）url` | 链接                                |
| 未录入（无链接且 tip 非空）   | `扫描结果（<包名>）`    | 提示文案                            |
| 无链接且 tip 为空（异常场景） | —                       | 不输出，仅 `core.info` 记录便于排查 |

仅在上报成功后输出；多产物包按包分别输出，互不合并；每个包固定输出 1 行（detailLink 非空 → 链接行；tip 非空 → 提示行，二者互斥，服务端保证）。5. **鉴权模式保持不变（AK/SK 保留）**：OIDC 与 AK/SK 双模式并存，本次不触及 `CicdUploader` 的鉴权分支、`ApigSigner` 类、`AKSK_REPORT_PATH` 常量、`useOidc`/`apigAppKey`/`apigAppSecret` 构造参数与凭证透传逻辑，`action.yml` 的 `apig-app-key`/`apig-app-secret` 输入项全部保留（部分测试仓不适合纳入 OIDC 认证凭据授权项目）；输出链路改造与鉴权模式正交（两种模式下均正常输出链接/提示）。6. **bundle 双写**：`dist/index.js` 是 ncc 打包产物，内联了 `scanner.js` / `CicdUploader.js` 副本；改动需同步内联副本，或按仓内既有构建方式（`npm run build`）重新打包，保持分发物单文件。7. **README**：输出章节补充双通道链接说明（ATOMGIT_STEP_SUMMARY Markdown 超链接 + ATOMGIT_OUTPUT 概览行）与未录入提示说明及示例；AK/SK 相关说明保持现状。

### 2.3 边界与降级

| 场景                                              | 行为                                                                                                 |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 未纳管仓库（repo_info 无匹配）                    | detailLink 为空 + tip 返回 → 插件输出未录入提示行（不输出链接）                                      |
| 同一 repoUrl 多个项目                             | 服务端取查询第一个项目（SQL `ORDER BY project_id` 第一行）生成单条链接，不返回其他项目链接           |
| 上报的 gitUrl 为空/异常                           | SQL 匹配不到 → 同"未纳管仓库"；不抛异常                                                              |
| repo_info 查询异常                                | 兜底捕获，detailLink 为空、tip 为空 → 插件不输出链接也不输出提示（仅告警日志），上报成功结果不受影响 |
| 上报失败（HTTP/业务失败）                         | 不输出链接（现有失败处理不变）                                                                       |
| 新插件 + 老服务端（无 detailLink/tip）            | 解析为空 → 不输出链接/提示，其余行为不变                                                             |
| 老插件 + 新服务端（data 由数值变对象）            | 老插件解析分支 `data?.recordId` 命中字符串 recordId，行为兼容（recordId 本仅用于日志）               |
| 鉴权模式（OIDC / AK/SK）                          | 两模式均保留、均按现有链路正常上报；本次改造不改变任一模式的报错与回落行为                           |
| 无 ATOMGIT_STEP_SUMMARY / ATOMGIT_OUTPUT 环境变量 | 对应通道跳过输出（两通道独立判定；均缺失时仅 `core.info` 打印）                                      |

## 3. 类设计

### 3.1 服务端（Java，openlibing-cicd）

| 类/文件                                                                       | 操作 | 说明                                                                                                                                                                       |
| ----------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `business/controller/BuildArtifactController.java`                            | 修改 | `reportSecOptionScan` 返回类型改为 `DataResult<SecOptionScanReportVO>`                                                                                                     |
| `business/service/impl/SecOptionScanServiceImpl.java`                         | 修改 | 注入 `PipelineService`；新增私有方法 `buildReportVO` / `resolveProject`（取查询第一个项目解析 projectId，单条链接拼接（recordId + projectId））；`reportScan` 组装 VO 返回 |
| `business/mapper/RepoInfoMapper.java` + `resources/mapper/RepoInfoMapper.xml` | 修改 | 新增 `queryProjectsByUrl`（返回 projectId + platform，参数化 SQL）                                                                                                         |
| `business/vo/secoption/SecOptionScanReportVO.java`                            | 新增 | 响应 VO：`String recordId` + `String detailLink`（固定单条链接，多项目取查询第一个项目；未命中时为空）+ `String tip`（未录入提示，可空）                                   |

### 3.2 插件侧（Node.js，security-compilation-options-action）

| 文件                             | 操作 | 说明                                                                                                                            |
| -------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------- |
| `dist/uploaders/CicdUploader.js` | 修改 | `parseResult` 解析 detailLink/tip；鉴权逻辑不变（AK/SK 保留）                                                                   |
| `dist/scanner.js`                | 修改 | `uploadInfo` 携带 detailLink/tip                                                                                                |
| `dist/index.js`                  | 修改 | 收集各产物链接/提示；双通道输出（ATOMGIT_STEP_SUMMARY Markdown 超链接 + ATOMGIT_OUTPUT 概览行）；`core.info` 打印；内联副本同步 |
| `action.yml`                     | 不改 | `apig-app-key` / `apig-app-secret` 输入项保留                                                                                   |
| `README.md`                      | 修改 | 输出章节补充双通道链接说明；AK/SK 说明保持现状                                                                                  |

## 4. 数据模型设计

**数据库**：无表结构变更。仅新增对共享表 `repo_info` 的只读查询（命中既有索引 `idx_repo_url` / `uk_repo_project`；`GROUP BY project_id ORDER BY project_id` 取第一行），无新增索引、无迁移 SQL。

**响应模型（DataResult\<T\>）**：

改造前：

```json
{ "code": 200, "msg": "success", "data": 2103041785973575680 }
```

改造后：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "recordId": "2103041785973575680",
    "detailLink": "<平台域名>/apps/securityOptions/package-detail?recordId=2103041785973575680&projectId=3"
  }
}
```

（`<平台域名>` 由服务端按环境注入，JSON 样例仅示意。）

未解析到项目（未录入 openLiBing）时：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "recordId": "2103041785973575680",
    "detailLink": null,
    "tip": "当前仓未录入openLiBing平台，无法生成跳转链接，请先联系SRE完成代码仓录入。"
  }
}
```

字段说明：

| 字段         | 类型         | 说明                                                                                                                                            |
| ------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `recordId`   | String       | 扫描记录雪花 ID，字符串化避免 JS 精度丢失（19 位 > 2^53-1）                                                                                     |
| `detailLink` | String       | 固定单条完整平台详情页链接（多项目取查询第一个项目；未命中时为空）；链接含 `recordId` + `projectId`（定位记录与项目上下文）；仅在命中项目时非空 |
| `tip`        | String，可空 | 未录入提示文案；仅"查询成功但未命中项目"时返回，其余场景为 null（不输出提示）                                                                   |

存量数据无需迁移；插件侧不做持久化，链接仅在当次运行输出。

## 5. 性能设计

- 上报链路新增开销：1 次（最多 2 次，含 `.git` 兜底重试）`repo_info` 等值查询，命中 `idx_repo_url` 索引；链接拼接为 O(1)，无额外 HTTP 调用（不跨服务查询）。
- 插件侧新增开销：字符串透传 + 每通道一次 `appendFileSync`（ATOMGIT_STEP_SUMMARY / ATOMGIT_OUTPUT），可忽略。
- 输出行数上限：产物包数（每包固定 1 行，均为小规模），无分页需求。
- 链接构建位于上报事务方法内，异常兜底捕获，不影响入库事务结果与响应时延（单次索引查询量级）。

## 6. API接口设计

| 项              | 说明                                                                                                                                                                                    |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 接口路径        | 不变：OIDC `/action-api/build-artifact/sec-option/report` 与 AK/SK 旧网关路径并存（两模式现状保留）                                                                                     |
| 入参            | 不变（`SecOptionScanReportDTO`，校验注解维持现状）                                                                                                                                      |
| 出参            | `DataResult<Long>` → `DataResult<SecOptionScanReportVO>`（见第 4 节）                                                                                                                   |
| 错误码/失败语义 | 不变：入库失败仍走既有异常处理；业务语义与 msg 维持现状                                                                                                                                 |
| 鉴权            | 维持现状：OIDC 联邦认证（`callApig` 签名）与 AK/SK 旧网关（`ApigSigner` + 静态凭证）双模式并存，本次不改变插件鉴权模式；网关侧配置不变                                                  |
| 前端链接契约    | `/apps/securityOptions/package-detail?recordId=<雪花ID>&projectId=<项目ID>`；页面仅依赖 recordId 取数，projectId 用于项目上下文还原；服务端仅在命中项目时生成链接（未录入时不生成链接） |

## 7. 安全设计

- **无新增凭证与敏感数据**：链接不含 token、不携带平台授权参数，打开时沿用平台既有登录态与页面鉴权；响应不额外暴露仓库归属信息（仅 projectId，不含项目名称）。
- **鉴权模式不变**：保留 AK/SK 与 OIDC 双模式（部分测试仓不适合纳入 OIDC 认证凭据授权项目）；本次不新增、不移除任何凭证输入，凭证面与现状一致。
- **SQL 安全**：新增查询使用 `#{}` 参数化，无 `${}` 拼接，无注入风险。
- **URL 拼接安全**：模板固定 + 纯数字参数（recordId/projectId），无用户可控注入面；不做多余编码（无特殊字符）。
- **异常兜底**：异常日志仅记录 gitUrl 与异常摘要，不打印请求体等数据；异常不阻断上报主流程，不改变事务结果。
- **依赖安全**：无新增依赖（服务端复用现有 Mapper/Service；插件零新增依赖）。

## 8. 需求设计检查清单对照（requirement-design-check）

**适用条目**：

- 第 2 条（二级页面链接直达）：本次为该原则的服务端落地——链接以唯一标识 recordId 定位（非 `repoUrl + runNumber + packageName` 复合键）；projectId 仅作上下文还原；插件以 Markdown 超链接输出（显示文本≠实际链接）；未录入仓库不构造无效链接而是提示用户录入；与前端既有直达能力对齐。
- 第 3 条（ID 接口传递用字符串）：recordId（雪花 ID）按字符串返回；projectId 在 URL 中天然为字符串。
- 第 5 条（可扩展性）：`detailLink` 为固定单条链接（多项目取查询第一个项目，输出形态恒定、不随项目数变化），天然支持后续新增 URL 参数；后续如需多链接可再扩展字段（当前无此需求）。
- 第 6 条（接口精简与复用）：不新增接口，扩展现有上报响应（现有接口加出参分支即可覆盖；无下游调用方的新接口不建）。
- 第 10 条（大小写归一化）：repo_url 匹配沿用现有范式（精确匹配 + 补 `.git` 重试），依赖既有 DB 排序规则行为，本次不做额外归一化改造。
- 第 16 条（重复逻辑下沉单一来源）：平台地址复用 `PipelineService#getOpenlibingHost()`（不新增第二份环境判定）；链接模板与未录入提示文案仅服务端单点定义，插件不做 URL 拼接与文案硬编码。

**不适用条目**：

- 第 1/7/8/9/11 条：本次无列表筛选、排序、分页与时间区间入参。
- 第 4/17 条：无分页接口。
- 第 12/13/14/15/19 条：无表结构/索引变更、无后端管理字段新增、无存量数据迁移、无批量数据变更。
- 第 18 条：上报入参 DTO 的必填/校验维持现状（`@NotBlank` 等），本次不改入参。

## 风险 & 缓解

| #   | 风险                                                                         | 缓解                                                                                                         |
| --- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| R1  | 同一 repoUrl 多项目时仅取查询第一个项目，可能非用户期望的项目                | 按 SQL `ORDER BY project_id` 取第一行（行为确定可预期）；交付说明写明；同 URL 多项目为少数场景               |
| R2  | repoUrl 格式差异（含/不含 `.git`、跨区域域名）导致解析不到项目               | 精确匹配 + 补 `.git` 重试；仍未命中返回未录入提示，提示用户联系 SRE 录入                                     |
| R3  | 响应结构变化影响存量插件（老插件 × 新服务端）                                | 老插件解析分支 `data?.recordId` 命中字符串 recordId，行为兼容；上线前用存量插件版本回归一次上报              |
| R4  | 链接构建异常阻断上报                                                         | 构建逻辑独立兜底捕获，异常仅告警并返回 recordId + 空 detailLink + 空 tip；上报结果与入库不变                 |
| R5  | 未录入提示误导（实际已录入但格式差异未匹配）                                 | 提示文案引导联系 SRE 核实；匹配规则含 `.git` 兜底重试，覆盖主流格式差异                                      |
| R6  | `ATOMGIT_STEP_SUMMARY` 通道不可用（环境变量缺失/平台不渲染）导致超链接不可见 | 双通道兜底：`ATOMGIT_OUTPUT` 概览行与 `core.info` 日志仍输出实际链接（可复制打开）；两通道独立判定、互不影响 |

## 跨仓影响

- **openlibing-cicd**：上报响应结构变化（出参新增 detailLink + tip；链接含 recordId + projectId），需先于或同步插件发布（双向兼容矩阵见 2.3，任一顺序上线均不破坏现状）。
- **security-compilation-options-action**：新增链接双通道输出与响应解析扩展；鉴权模式不变（AK/SK 保留，`action.yml` 不改），分发物（dist）更新。
- **前端**：无改动（依赖既有链接直达能力）。
