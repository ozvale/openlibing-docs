# 【openlibing-sbom】sbom-action返回产物详情地址 — 技术设计

关联 Issue: https://gitcode.com/openlibing/openlibing-sbom/issues/185

## 1. 现状与问题

- sbom-action 调 `addAndPublishProduct` 后仅拿到 `taskId`（导入任务 UUID），无法拼出平台详情地址：详情落地页 `/apps/sbomManage` 需要平台项目 id（projectId）定位项目上下文，产品名（name）定位列表行。
- sbom-web `Product` 实体无 projectId 概念，SBOM 服务自身不知道平台项目 id。
- 平台前端 `/apps/sbomManage`（CompositionAnalysis/index.vue，制品信息 + 软件成分数据联动页）当前不读 URL query 参数；壳层 router guard 已支持 `projectId` query 恢复项目上下文（guard.ts 现有能力）；制品行选中机制已有（`@current-change` → selectedProduct → 成分数据联动 + 行高亮滚动定位）。
- projectType 与平台项目名的对应关系：`validateProductType` 校验 productType 必须是平台已配置的合法类型，即 productType == 平台项目名（project_info.project_name）。

## 2. 方案架构

```
sbom-action(CI)                      sbom-web                             framework(零改动)
──────────────                       ──────────                           ─────────────
addAndPublishProduct ──────────────▶ ApigController
  请求: productName/sbomContent      └▶ SbomServiceImpl.addAndPublishProduct
                                         ├─ addProduct(req)               （现有）
                                         │   ├─ 显式 productType: 直接校验采用
                                         │   └─ 缺省: coderepo queryProjectNames(gitUrl)
                                         │        候选裁决回填 req.productType   （现有）
                                         ├─ resolvePlatformProjectId(productType) （新增）
                                         │   └─ FrameworkClient.getProject─────▶ GET /internal-server/get-project
                                         │        ?projectName=<productType>&pageNum=1&pageSize=1
                                         │        精确匹配 → data[0].projectId
                                         │        失败/未命中 → AddProductException
                                         ├─ buildDetailLink(projectId, productName) （新增）
                                         │    {sbom.service.website.domain}/apps/sbomManage
                                         │      ?projectId=<id>&name=<URLEncode(name)>
                                         ├─ publishSbom(...) → taskId           （现有）
                                         └─ getSbomPublishResult(遗留查询)：sbomRef
                                              同步升级同一 pattern（projectId 软反查，
                                              失败 → sbomRef=null，不阻塞查询）
                                     ◀── PublishSbomResponse{success,taskId,detailLink}
  输出:
    core.setOutput detail-link/package-count/relationship-count
    ATOMGIT_OUTPUT 概览组 + 链接组(SBOM查询url=…) ← GitCode 结果面板
    sanitize(detailLink) 防换行注入

openlibing-web(零服务端改动)
  /apps/sbomManage?projectId=3&name=xxx
    ├─ 壳层 guard 消费 projectId 恢复项目上下文        （现有）
    └─ sbomManage 页 onMounted 解析 route.query 筛选参数集   （新增）
        name/names/attr 动态字段(branch、softwareName…)/scanStatus/vulInclude/vulExclude
        → 初始化 productFilters → 触发查询 → 单值 name 匹配时自动选中制品行
        筛选变化时 router.replace 写回 URL（保留 projectId 等壳层参数）
```

## 3. 关键设计决策

| #   | 决策                                         | 结论                                                                                                                                                                                                                                                                                                                                                                  | 依据                                                                                                                                                                                                                                                                                                                                             |
| --- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | projectId 获取（统一时机 + 来源 + 失败语义） | `addProduct` 完成（确定最终 productType）后，统一调用 framework 机机接口 `GET /internal-server/get-project?projectName=<productType>&pageNum=1&pageSize=1`（精确匹配）反查 projectId；失败/未命中 → 抛 `AddProductException`，上报失败，无降级                                                                                                                        | framework 是平台项目主数据权威源（coderepo 反查返回的 projectId 与 framework `project_info.project_id` 同源性无契约保证）；显式 productType / 缺省回填 / already-exists 容忍三条路径在 addProduct 返回后收敛：productType 必非空且与存量产品类型一致；`/internal-server` 与 sbom-web 现有 feign 调用同鉴权域；硬失败与 coderepo 反查现有语义一致 |
| D2  | 域名配置                                     | 复用 `sbom.service.website.domain`（Nacos 配 `https://www.openlibing.com`），不新增 `openlibing.domain`                                                                                                                                                                                                                                                               | 该配置项已被 UrlUtil 声明使用，避免两套域名配置；域名缺失属环境配置问题，detailLink 置 null + warn，不阻塞上报（projectId 硬校验在前已保证 id 可得）                                                                                                                                                                                             |
| D3  | 落地页形态                                   | 列表页 `/apps/sbomManage?projectId=&name=` + name 参数定位，点击行内 name 进详情                                                                                                                                                                                                                                                                                      | 详情直连页 `/apps/sbomManageDetail` 需 packageId 且路由当前不存在；对齐用户指定交互                                                                                                                                                                                                                                                              |
| D4  | 返回值承载                                   | `SbomService.addAndPublishProduct` 返回类型 UUID → `AddAndPublishResult(UUID taskId, String detailLink)`（新 record，model 模块）；`PublishSbomResponse` 新增 `detailLink` 字段                                                                                                                                                                                       | service 层持有 projectId/productName，URL 在 service 层拼好传出；调用方仅 ApigController 一处                                                                                                                                                                                                                                                    |
| D5  | URL 筛选参数化                               | 制品表筛选参数 URL 化并双向同步。读：onMounted 解析 `name`（单值，detailLink 场景）/`names`/attr 动态字段名（branch、softwareName、version 等）/`scanStatus`/`vulInclude`/`vulExclude` 初始化 productFilters 后统一触发查询；写：筛选变化时 `router.replace` 写回 query（保留 projectId 等壳层参数，空筛选删除对应 key）；多值逗号分隔，scanStatus 组值内逗号冲突用 ` | ` 分隔多组；names 多值时仅筛选不自动选中                                                                                                                                                                                                                                                                                                         | 用户提出的额外增强：分享/跳转可携带筛选状态（分支、待闭环漏洞级别等）；detailLink 生成侧仍只带 projectId+name 保持最简；软件成分数据区筛选、排序、分页不 URL 化（避免状态爆炸） |
| D6  | 遗留 querySbomPublishResult 的 sbomRef 升级  | `sbomRef` 换用 `SBOM_DETAIL_PAGE_URL_PATTERN` 新地址，projectId 复用 `resolvePlatformProjectId` 反查，但采用**软降级**（反查失败/domain 缺失 → `sbomRef=null` + warn，`success/finish` 不受影响）；删除旧常量 `PACKAGE_LIST_PAGE_URL_PATTERN`（唯一调用方即该路径）                                                                                                   | 查询接口主 payload 是 success/finish，sbomRef 为辅助信息，硬失败会把 framework 故障放大到存量流水线结果查询；与发布路径「projectId 硬依赖」的差异：publish 必须保证链接可得才允许上报成功，查询允许无链接降级                                                                                                                                    |

## 4. 修改清单（按模块）

### openlibing-sbom（后端）

| 文件                                                    | 变更                                                                                                                                                                             |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `clients/.../feign/FrameworkClient.java`                | 新增 `getProject(projectName, pageNum, pageSize)` → `GET /internal-server/get-project`                                                                                           |
| `model/.../pojo/response/sbom/PublishSbomResponse.java` | 新增 `detailLink` 字段（getter/setter/toString）                                                                                                                                 |
| `model/.../pojo/response/sbom/AddAndPublishResult.java` | 新增 record（taskId + detailLink）                                                                                                                                               |
| `model/.../constants/SbomConstants.java`                | 新增 `SBOM_DETAIL_PAGE_URL_PATTERN = "%s/apps/sbomManage?projectId=%s&name=%s"`；删除 `PACKAGE_LIST_PAGE_URL_PATTERN`（唯一调用方升级后无引用）                                  |
| `utils/.../UrlUtil.java`                                | `generateSbomUrl` 改用新 pattern 并增加 projectId 参数；productName 先 URLDecoder.decode（兼容存量库内编码值）再 URLEncoder.encode                                               |
| `sbom-web/.../service/sbom/SbomService.java`            | `addAndPublishProduct` 返回类型改为 `AddAndPublishResult`                                                                                                                        |
| `sbom-web/.../service/sbom/impl/SbomServiceImpl.java`   | `addAndPublishProduct`：注入 domain 配置；新增 `resolvePlatformProjectId` / `buildDetailLink`；组装返回。`getSbomPublishResult`：完成分支 sbomRef 接入 projectId 软反查 + 新链接 |
| `sbom-web/.../controller/ApigController.java`           | `addAndPublishProduct` 端点：响应填充 `detailLink`                                                                                                                               |
| `sbom-web/src/test/.../SbomServiceImplTest.java`        | 新增 detailLink 场景 UT + `getSbomPublishResult` 升级场景 UT（新链接格式 / 软降级 sbomRef=null）                                                                                 |

### sbom-action（插件）

| 文件            | 变更                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `index.js`      | 响应解析 detailLink；统计变量提升；新增 outputs（编程取数 + ATOMGIT_OUTPUT 分组）；`sanitize` 复刻；`appendAtomgitOutput` 复刻 |
| `dist/index.js` | ncc 重新打包                                                                                                                   |

### openlibing-web（前端）

| 文件                                                                         | 变更                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue` | 引入 `useRoute`；onMounted 解析 route.query 筛选参数集（name/names/attr 动态字段/scanStatus/vulInclude/vulExclude）→ 初始化 productFilters → `handleProductFilterChange()` 查询 → 单值 name 匹配行自动选中（selectedProduct 联动成分数据 + 行高亮定位）；`handleProductFilterChange` 中 `router.replace` 把当前筛选写回 URL（保留 projectId 等既有参数，空筛选删除 key） |

## 5. 边界与异常场景

| 场景                                              | 行为                                                                       |
| ------------------------------------------------- | -------------------------------------------------------------------------- |
| 显式 productType，framework 反查未命中（total=0） | 抛 `AddProductException("platform project not found by productType: xxx")` |
| framework feign 调用异常                          | 同上抛 AddProductException（携带原因）                                     |
| productType 缺省 + coderepo 候选裁决成功          | 回填 productType 后统一走 framework 反查                                   |
| 同名产品已存在（类型一致容忍）                    | 容忍路径继续发布，framework 反查按本次 productType 执行                    |
| 同名产品已存在（类型不一致）                      | 现有行为不变（抛 not match 中断）                                          |
| `sbom.service.website.domain` 未配置              | projectId 校验通过，domain 为 blank → warn 日志，detailLink=null，上报成功 |
| productName 含特殊字符                            | URLEncoder.encode（UTF-8），与现有 exportUrl 编码方式一致                  |
| 插件读取 detailLink 为 null                       | 面板不输出链接行，仅概览组（对齐 code-metrics「无链接不输出」约定）        |
| URL 筛选参数含未知字段名 / 非法枚举值             | 忽略该参数（不进入筛选），页面正常加载                                     |
| URL 筛选参数与首屏默认查询并发                    | onMounted 解析完成后仅触发一次查询，不重复请求                             |
| querySbomPublishResult：framework 反查失败/未命中 | `sbomRef=null` + warn，`success/finish` 正常返回（软降级，不阻塞查询）     |
| querySbomPublishResult：domain 未配置             | 同上 `sbomRef=null`                                                        |
| 存量 productName 在库内为 URL 编码值              | generateSbomUrl 先 decode 再 encode，链接 name 形态与 detailLink 一致      |

## 6. 测试策略

- **UT（sbom-web）**：`SbomServiceImplTest` 新增用例——两路径 detailLink 组装、URLEncode、framework 未命中抛异常、feign 异常传播、domain 缺失 detailLink=null、already-exists 容忍路径仍返回 detailLink；另补 `getSbomPublishResult` 升级用例（新链接格式 / 反查失败软降级 / success·finish 不受影响）。
- **插件**：`node --check`；本地模拟响应断言输出行；`ncc build` 后 diff dist。
- **前端**：ESLint；浏览器手工验证 query 参数筛选定位与写回（name 单值选中联动；branch/vulInclude 多参数组合筛选；筛选变化后 URL 同步且保留 projectId；design-review.html 提供 mockup 预演）。
- **联调**：test 环境配置 Nacos `sbom.service.website.domain=https://www.openlibing.com` 后端到端验证（链接可打开、项目上下文正确、列表定位、点击进详情；`querySbomPublishResult` 返回新 sbomRef 且可打开）。

## 7. 风险

| 风险                                                                     | 等级 | 缓解                                                                                                                             |
| ------------------------------------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------------------- |
| `/internal-server/get-project` 对 feign 直连的鉴权拦截（现网拦截器行为） | 低   | 与现有 `checkPermissionByProductType` 同前缀同鉴权域；联调首验此调用                                                             |
| project_info 存在同名重复项目（无唯一约束）                              | 低   | 精确匹配 + pageSize=1 取首条；出现重复属平台数据治理问题，warn 日志暴露                                                          |
| Nacos 域名配置缺失/错误导致链接不可用                                    | 中   | detailLink=null 不阻塞上报；发布检查项加入配置核对                                                                               |
| GitCode 面板对 ATOMGIT_OUTPUT 渲染分组规则变化                           | 低   | 行为对齐 code-metrics-action 线上实际效果，随其回归                                                                              |
| `addAndPublishProduct` 签名变更影响未知调用方                            | 低   | 全仓检索仅 ApigController 一处调用                                                                                               |
| querySbomPublishResult sbomRef 链接形态变化（旧 hash 链接失效）          | 低   | 全仓检索未发现 sbomRef 的程序化消费方（sbom-tools 仅消费 success/finish/taskId）；旧 hash 页路由保留，历史消息中的旧链接仍可访问 |
