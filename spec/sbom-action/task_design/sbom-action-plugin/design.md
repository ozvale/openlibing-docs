# sbom-action 插件全链路实现 — 设计文档

## 1. 总体方案

SBOM 上报从 codearts 流水线迁移到 GitCode 流水线，由"插件扫描上报 + 服务端 gitUrl 反查 productType"三仓联动承接：

```
sbom-action 插件（Node action，ncc 打包 dist/index.js）
  输入校验（fail-fast）
  → 按 platform/arch 下载 trivy-sbom-tools release 包并解压（版本内置 v1.1.1）
  → trivy fs --format spdx-json --offline-scan 扫描 target-dir（输出固定临时目录）
  → addAndPublishProduct 建品+发布单步完成（自动采集 gitUrl 上报；productType 可选；
     产品已存在由服务端 service 层事务容忍）
       └─ productType 缺省时（openlibing-sbom 服务端同一事务内）
            → CoderepoClient 调 openlibing-coderepo POST /project-repo/internal/query-project-names
            → 逐候选 dry-run 校验，第一个合法者回填 productType
       └─ body 含 sbomContent（spdx_2.2_json_sbom，OIDC callApig 认证）
  → 输出 task-id / sbom-file（编程取数 + 可读概览双通道）
  → finally 清理 trivy 临时目录
```

认证从静态凭证改为 OIDC 联邦认证（`@openlibing/huaweicloud-oidc-client` 的 `callApig`：OIDC ID Token → STS 临时凭证 → APIW V11 签名）。

### 关键技术决策

| 决策点             | 选择                                                                                                                                                                                                         | 原因                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| 认证方式           | OIDC 联邦认证（callApig），无 AK/SK 入参                                                                                                                                                                     | 新插件强制规范（gitcode-ci-plugin-development 4.2.4）                                                                 |
| 上传接口           | 仅 `addAndPublishProduct`（建品+发布单接口，非压缩）                                                                                                                                                         | 用户确认；压缩接口 `publishSbomFileWithCompress` 本轮不做兜底                                                         |
| gitUrl 取值        | 三级降级：env `ATOMGIT_REPOSITORY_URL` → `git remote get-url origin`（token 清洗）→ 空串                                                                                                                     | 对齐 code-metrics-action；runner 注入优先，失败不阻塞                                                                 |
| productType 可选化 | 插件 `project-type` 可选 + 服务端 gitUrl 反查                                                                                                                                                                | 平台已知信息不转嫁用户配置；显式传入为多社区仓逃生口                                                                  |
| 多候选裁决         | 逐候选 dry-run 现有校验，第一个合法者自动采用；全不合法聚合报错                                                                                                                                              | 各社区配置项不同，多数多候选场景仅一个能通过 attribute 覆盖校验（用户 2026-10-22 裁定，修订早期"命中 2+ 即报错"方案） |
| trivy 版本         | 移除 `trivy-version` 输入，内置 `DEFAULT_TRIVY_VERSION = 'v1.1.1'`                                                                                                                                           | 版本升级由插件发版承载，消除 TAG 外部输入面                                                                           |
| SBOM 输出          | 移除 `sbom-output` 输入，固定 `os.tmpdir()/sbom-action-output/{ATOMGIT_RUN_ID                                                                                                                                | 时间戳}/sbom-result.spdx.json`                                                                                        | 按流水线运行 ID 隔离，不落入工作区 |
| attribute 入参形态 | 15 个平台 `sbom_new_product_config` 字段平铺为独立可选 input（kebab-case 输入名 + 显式映射表 `ATTRIBUTE_INPUT_TO_FIELD`；component/packageName/arch_type/versionName/service_branch 5 个概念重复字段不暴露） | 消除自由文本双写法解析；映射表替代正则转换（正则漏 camelCase 曾致 9 字段静默丢弃）                                    |
| coderepo 反查接口  | 新增专用 `query-project-names`（不扩展现有 query-repo）                                                                                                                                                      | 现成接口仅返回 projectId 无 projectName，且纯精确匹配对多来源 gitUrl 命中率不足                                       |
| gitUrl 匹配口径    | 复用 `RepoCoordinateResolver.resolveByCoordinate`（URL 全串 + 平台坐标 owner/repo，域名无关）                                                                                                                | 容忍 `.git` 后缀与 gitcode.com ↔ atomgit.com 跨域差异；避免裸 repoName 同名误命中                                     |
| 产品已存在容忍     | 服务端 service 层事务内容忍（视为成功，发布失败回滚新建产品），插件仅按 `success` 判定                                                                                                                       | nightly 重跑产品已注册，失败会中断整条流水线；容忍收敛在服务端避免插件侧字符串判断脆弱性                              |
| 下载方式           | `execFileSync('curl', [...])` 参数数组                                                                                                                                                                       | 外部输入不经 shell 解析，防注入；--fail --retry 3 容错网络抖动                                                        |
| 解压工具           | AdmZip（运行时依赖，ncc 内联）                                                                                                                                                                               | 纯 JS 解压，跨平台无需系统 unzip                                                                                      |
| 输出通道           | setOutput（编程取数）+ STEP_OUTPUT 环境变量文件（可读概览，含中文键，与 pre-commit-action 机制一致）                                                                                                         | 平台双通道规范                                                                                                        |
| env 参数           | prod / test 显式枚举，缺省默认 prod，非法值报错                                                                                                                                                              | 常规场景零配置可用；显式传错值不静默 fallback                                                                         |

## 2. sbom-action 插件设计

### 2.1 输入（action.yml 终态）

| 输入                          | 必填           | 说明                                                                                                                                                                                                                                               |
| ----------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| name                          | 是             | 平台制品名，nightly 重跑需一致                                                                                                                                                                                                                     |
| project-type                  | 否             | 平台 productType；缺省时由服务端按 gitUrl 反查                                                                                                                                                                                                     |
| 15 个属性 input（kebab-case） | 否（全空报错） | `image-format` / `language` / `torch-version` 等，对应平台 `sbom_new_product_config` 表字段，经 `ATTRIBUTE_INPUT_TO_FIELD` 映射表转平台 ConfigValue name 原文（component/packageName/arch_type/versionName/service_branch 5 个概念重复字段不暴露） |
| target-dir                    | 是             | 扫描目标目录/文件                                                                                                                                                                                                                                  |
| analyze-all-python            | 否             | 解析 requirements.txt（pip 下载，增加耗时）                                                                                                                                                                                                        |
| analyze-dirs                  | 否             | 直接依赖 git 目录，逗号分隔                                                                                                                                                                                                                        |
| env                           | 否             | prod / test 网关前缀切换                                                                                                                                                                                                                           |
| debug                         | 否             | sbom 调试日志开关（gitUrl 来源、请求/响应详情、SBOM 预览）                                                                                                                                                                                         |

已移除输入：`product-type`（更名）、`attribute`（平铺化）、`trivy-version`（内置）、`sbom-output`（内置）。

### 2.2 trivy 工具包选择

| platform | arch  | zip                      | binary              |
| -------- | ----- | ------------------------ | ------------------- |
| linux    | x64   | sbom-tools-trivy.zip     | trivy-linux-amd     |
| linux    | arm64 | sbom-tools-trivy.zip     | trivy-linux-amd-arm |
| darwin   | x64   | sbom-tools-trivy-mac.zip | trivy-darwin-amd    |
| darwin   | arm64 | sbom-tools-trivy-mac.zip | trivy-darwin-arm    |
| win32    | *     | sbom-tools-trivy-win.zip | trivy-win.exe       |

下载 URL：`https://gitcode.com/openlibing/trivy-sbom-tools/releases/download/{tag}/{zip}`。解压到 `os.tmpdir()/sbom-action-trivy/{tag}`（执行前清理旧 zip/二进制，避免残留不完整下载）；linux/mac `chmod 0o755`。

### 2.3 扫描命令

```
trivy fs --format spdx-json -o {sbom-output} --offline-scan \
  [--analyze-all-python=true] [--analyze-dir {analyze-dirs}] {target-dir}
```

`analyze-all-python=true` 才追加（默认不追加，避免无谓 pip 下载耗时）；`analyze-dirs` 非空才追加。扫描后校验输出文件存在并打印体积。

### 2.4 addAndPublishProduct 契约（gitUrl + productType 可选）

```js
const body = {
  gitUrl: resolveGitUrl(),
  productName: inputs.productName,
  attribute: attribute, // buildAttribute() 收集非空属性项
  sbomContent: fs.readFileSync(sbomFile, "utf8"),
  sbomContentType: "spdx_2.2_json_sbom",
};
if (inputs.projectType) {
  body.productType = inputs.projectType;
}
```

`resolveGitUrl()` 三级降级：

```js
function resolveGitUrl() {
  const envUrl = (process.env.ATOMGIT_REPOSITORY_URL || "").trim();
  if (envUrl) return envUrl;
  try {
    const remoteUrl = execFileSync("git", ["remote", "get-url", "origin"], {
      encoding: "utf8",
      cwd: process.cwd(),
    }).trim();
    return remoteUrl.replace(/https:\/\/[^@]+@/, "https://"); // token 清洗
  } catch (e) {
    core.warning(`failed to resolve gitUrl via git remote: ${e.message}`);
    return "";
  }
}
```

body 字段名保持 `productType`（后端 DTO 原名）；插件提前携带的 `gitUrl` 为额外字段，Spring Boot 默认 `FAIL_ON_UNKNOWN_PROPERTIES=false`，改造前后端上线顺序解耦。

### 2.5 上传链路（OIDC，单接口）

```
addAndPublishProduct（建品+发布一个 service 事务）:
  POST {base}/action-api/sbom/addAndPublishProduct
  body: {gitUrl, productName, attribute:{k:{value,label}}, sbomContent, sbomContentType, [productType]}
  非 2xx 或 success !== true → 抛错（透出平台错误消息）
  202 + {success:true, taskId} → 成功，输出 task-id
  产品已存在 → 服务端事务内视为成功继续发布；发布失败回滚新建产品（插件无感知）
```

`{base}` 由 env 决定：prod=`https://apig.openlibing.com:443`，test=`https://f209a4ca505e492b96d2dc70f5578641.apic.cn-southwest-2.huaweicloudapis.com`。启动时探测 `ACTIONS_ID_TOKEN_REQUEST_URL`，缺失即报错指引 workflow 声明 `id-token: write`。

### 2.6 模块结构（单文件 index.js）

| 函数                     | 职责                                                                             |
| ------------------------ | -------------------------------------------------------------------------------- |
| `getInput(name)`         | 连字符/下划线 env 兼容读取                                                       |
| `setOutput(k,v)`         | STEP_OUTPUT 环境变量指向的输出文件写入（与 pre-commit-action 机制一致）          |
| `logExec()`              | debug 模式下打印执行命令与输出摘要                                               |
| `resolveGitUrl()`        | gitUrl 三级降级采集 + token 清洗                                                 |
| `buildAttribute()`       | 按映射表收集非空属性 input → ConfigValueLabel；全空报错                          |
| `resolveSbomOutput()`    | 临时目录运行 ID 子目录 + 固定文件名，目录预创建                                  |
| `pickTrivyAsset()`       | platform/arch → {zipName, binaryName}                                            |
| `downloadTrivy()`        | curl 下载 + AdmZip 解压 + chmod（幂等）                                          |
| `buildScanArgs()`        | 组装 trivy fs 参数（可选参数按需追加）                                           |
| `callSbomApi()`          | callApig 封装（签名注入）                                                        |
| `addAndPublishProduct()` | 上传链路单接口调用（非 2xx / success!==true 抛错）                               |
| `extractErrorMsg()`      | 从非 2xx 响应（含纯文本错误体）提取可读错误消息                                  |
| `debugLog()`             | debug 开启时打印调试日志（模块级 `debugEnabled` 开关）                           |
| `cleanupTrivy()`         | finally 清理 trivy 临时目录（zip + 解压产物）                                    |
| `run()`                  | 主流程：校验 → 下载 → 扫描 → addAndPublishProduct 单步上传 → 输出 → finally 清理 |

### 2.7 异常处理

| 场景                                        | 处理                                                                                   |
| ------------------------------------------- | -------------------------------------------------------------------------------------- |
| 未声明 id-token: write                      | 启动即抛错，提示 workflow 声明 permissions: id-token: write                            |
| TAG 无 release / 下载失败                   | curl --fail --retry 3 后抛错，含 URL 便于定位                                          |
| 解压后无对应二进制                          | 抛错（tag 与包内容不匹配）                                                             |
| 属性 input 全空                             | 抛错（attribute 至少填一项）                                                           |
| gitUrl 两种取值方式均失败                   | warning 降级空串，不阻塞主流程                                                         |
| addAndPublishProduct 非 2xx / success=false | 抛错透出平台错误消息（含建品校验失败；产品已存在由服务端事务容忍，插件不会收到该错误） |
| 扫描输出文件缺失                            | 抛错                                                                                   |

### 2.8 性能与安全

性能：trivy 每次全新下载（清旧缓存）；`analyze-all-python` 默认关；全文单次上传（仅 1 次 APIG 调用）。

安全：OIDC 临时凭证无静态入参；curl / trivy / git 均经 `execFileSync` 参数数组（防注入）；gitUrl 回退路径统一 token 清洗（CI 临时凭证不入上报数据与日志）；`ATOMGIT_REPOSITORY_URL` 为 runner 注入的公开地址可直接打印；必填/枚举/路径 fail-fast 校验。

## 3. openlibing-coderepo 设计

### 3.1 新增内部机机接口

`POST /project-repo/internal/query-project-names`

- 入参 body：`{"gitUrl": "..."}`（`@NotBlank`）
- 返回：`DataResult<List<ProjectNameVO>>`，data 为 `{projectId, projectName}` 组合数组（按 projectId 去重、projectName 去重），未命中返回空数组
- 匹配语义：复用 `RepoCoordinateResolver.resolveByCoordinate(gitUrl)`——URL 全串精确匹配快路径 + 平台坐标（repoType + owner + repo，域名无关、忽略大小写）慢路径兜底
- 机机接口：无 userId、不做横向越权校验、网关层完成服务鉴权（与同 Controller 其他端点一致）

### 3.2 文件改动

| 文件                                                         | 改动                                            |
| ------------------------------------------------------------ | ----------------------------------------------- |
| `business/dto/space/QueryProjectNamesDTO.java`               | 新增 DTO：`gitUrl`（`@NotBlank`）               |
| `business/vo/ProjectNameVO.java`                             | 新增 VO：`projectId` + `projectName`            |
| `business/controller/InternalProjectRepoController.java`     | 新增 `queryProjectNames` 端点                   |
| `business/service/RepoService.java` + `RepoServiceImpl.java` | 新增 `internalQueryProjectNames(String gitUrl)` |

```java
List<RepoInfoEntity> repos = repoCoordinateResolver.resolveByCoordinate(gitUrl);
return repos.stream()
    .map(RepoInfoEntity::getProjectId)
    .filter(Objects::nonNull)
    .distinct()                    // 多仓同项目 → projectId 去重
    .map(projectInfoMapper::queryById)
    .filter(Objects::nonNull)      // 项目可能已删
    .filter(p -> StringUtils.isNotBlank(p.getProjectName()))
    .map(p -> new ProjectNameVO(p.getProjectId(), p.getProjectName()))
    .toList();
```

## 4. openlibing-sbom 设计

### 4.1 addProduct 解析链

```
addProduct(req):
  lockTable()
  if productType 非空:
    走现有逻辑（不调 coderepo，存量零影响）
  else:
    gitUrl 为空      → AddProductException（productType 与 gitUrl 至少提供一个）
    调 CoderepoClient 反查:
      调用异常/失败   → AddProductException（透出原因）
      返回空数组      → AddProductException（repo not found in coderepo）
      返回候选数组    → 逐候选 dry-run 现有校验（product_type 存在 + attribute 覆盖
                        findByProductTypeOrderByOrdAsc 全部 config keys + blank +
                        value/label 冲突），捕获 AddProductException 记录原因；
                        第一个通过者回填 req.productType 并采用其 productConfigs
      全部不合法       → AddProductException（聚合候选与失败原因）
  findByName 已存在检查 → addProductInner 落库（均不变）
```

关键约束：`validateProductType(req, productType)` 为现有校验链的逐字参数化抽取，dry-run 与主链路共用同一实现，保证候选判定与真实落库判定一致；锁表仍在最前，解析在锁内完成。

### 4.2 文件改动

| 文件                                                 | 改动                                                                                                                                                                                   |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `model/.../request/sbom/AddProductRequest.java`      | 新增 `gitUrl` 字段 + getter/setter + toString                                                                                                                                          |
| `clients/.../feign/CoderepoClient.java`              | 新增 FeignClient：`@FeignClient(name = "${feign.coderepo.name:openlibing-coderepo}")`，`queryProjectNames(@RequestBody QueryProjectNamesPo po)` 返回 `DataResult<List<ProjectNameVo>>` |
| `sbom-web/src/main/resources/application.properties` | 新增 `feign.coderepo.name: openlibing-coderepo`                                                                                                                                        |
| `sbom-web/.../impl/SbomServiceImpl.java`             | 抽取 `validateProductType(req, productType)`；新增 `resolveProductTypeFromGitUrl(req)` + `queryProjectsViaCoderepo(gitUrl)`；`addProduct` 接入解析分支                                 |

```java
private Map<String, ProductConfig> resolveProductTypeFromGitUrl(AddProductRequest req) {
  if (StringUtils.isBlank(req.getGitUrl())) {
    throw new AddProductException(
        "productType and gitUrl are both empty, please specify at least one");
  }
  List<String> candidates = queryProjectsViaCoderepo(req.getGitUrl()); // 异常/空已抛错
  Map<String, String> failures = new LinkedHashMap<>();
  for (String candidate : candidates) {
    try {
      Map<String, ProductConfig> configs = validateProductType(req, candidate);
      req.setProductType(candidate);
      logger.info("productType [{}] resolved from gitUrl", candidate);
      return configs;
    } catch (AddProductException e) {
      failures.put(candidate, e.getMessage());
    }
  }
  throw new AddProductException(
      "no valid productType resolved from gitUrl [%s], candidates: %s, failures: %s"
          .formatted(req.getGitUrl(), candidates, failures));
}
```

## 5. 数据模型设计

无表结构变更。`product.attribute` JSONB 注入 `productType` key 的落库行为不变（回填后的 req 走 `addProductInner` 原逻辑）。`AddProductRequest` 请求体新增可选 `gitUrl`、`productType` 改可选，响应与错误码语义不变。

## 6. 性能设计

- productType 显式传入路径零额外开销（不调 coderepo）。
- 缺省路径新增一次 Feign 调用（内部服务，同机房）+ 每候选一次 `findByProductTypeOrderByOrdAsc`（候选通常 1~2 个，索引查询）；dry-run 结果复用，不重复查库。
- `resolveByCoordinate` 慢路径有 owner/repo LIKE 预过滤，单次查询毫秒级。

## 7. 安全设计

- coderepo 新端点为内部机机接口，网关服务鉴权，不暴露敏感字段（仅 projectName）。
- gitUrl 来自插件侧 runner 注入/清洗后的值，不参与 SQL 拼接（MyBatis 参数化），无注入面。
- sbom 侧 coderepo 调用失败信息透传时仅含 gitUrl 与候选列表，无凭证类数据。

## 8. 测试设计（Full 模式）

- 插件（Node action 无 UT 框架）：`node --check` 语法校验 + `npm run build` 重建 dist（grep 验证关键点、旧引用清零）+ 流水线自测；本地调试可用 `mock/oidc-mock.js` 预加载 mock（`node --require` 方式，不改动 index.js，不影响真实流水线）。
- coderepo UT：`RepoServiceImpl.internalQueryProjectNames`（坐标命中多项目去重、projectId 缺 projectName 过滤、空 URL、resolveByCoordinate 返回空）+ Controller 参数校验。
- sbom UT：`SbomServiceImpl.addProduct`——显式 productType 不触发 client；缺省 + gitUrl 空报错；反查空/异常报错；多候选第一个合法者采用；全不合法聚合报错；已存在容忍不受影响。`CoderepoClient` 契约（路径/入参/返回类型）。
