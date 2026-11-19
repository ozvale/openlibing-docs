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
                                         └─ publishSbom(...) → taskId           （现有）
                                     ◀── PublishSbomResponse{success,taskId,detailLink}
  输出:
    core.setOutput detail-link/package-count/relationship-count
    ATOMGIT_OUTPUT 概览组 + 链接组(产物详情url=…) ← GitCode 结果面板
    sanitize(detailLink) 防换行注入

openlibing-web(零服务端改动)
  /apps/sbomManage?projectId=3&name=xxx
    ├─ 壳层 guard 消费 projectId 恢复项目上下文        （现有）
    └─ sbomManage 页 onMounted 读 route.query.name
        → 初始化名称筛选 → 触发查询 → 用户点击行内 name 进详情   （新增）
```

## 3. 关键设计决策

| #   | 决策                                         | 结论                                                                                                                                                                                                                                           | 依据                                                                                                                                                                                                                                                                                                                                             |
| --- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | projectId 获取（统一时机 + 来源 + 失败语义） | `addProduct` 完成（确定最终 productType）后，统一调用 framework 机机接口 `GET /internal-server/get-project?projectName=<productType>&pageNum=1&pageSize=1`（精确匹配）反查 projectId；失败/未命中 → 抛 `AddProductException`，上报失败，无降级 | framework 是平台项目主数据权威源（coderepo 反查返回的 projectId 与 framework `project_info.project_id` 同源性无契约保证）；显式 productType / 缺省回填 / already-exists 容忍三条路径在 addProduct 返回后收敛：productType 必非空且与存量产品类型一致；`/internal-server` 与 sbom-web 现有 feign 调用同鉴权域；硬失败与 coderepo 反查现有语义一致 |
| D2  | 域名配置                                     | 复用 `sbom.service.website.domain`（Nacos 配 `https://www.openlibing.com`），不新增 `openlibing.domain`                                                                                                                                        | 该配置项已被 UrlUtil 声明使用，避免两套域名配置；域名缺失属环境配置问题，detailLink 置 null + warn，不阻塞上报（projectId 硬校验在前已保证 id 可得）                                                                                                                                                                                             |
| D3  | 落地页形态                                   | 列表页 `/apps/sbomManage?projectId=&name=` + name 参数定位，点击行内 name 进详情                                                                                                                                                               | 详情直连页 `/apps/sbomManageDetail` 需 packageId 且路由当前不存在；对齐用户指定交互                                                                                                                                                                                                                                                              |
| D4  | 插件面板机制                                 | ATOMGIT_OUTPUT 分组（概览组：任务ID/包数量/关系数量 + 链接组：产物详情url）对齐 code-metrics-action；面板不输出 SBOM 文件路径（仅编程 outputs 与日志保留）；STEP_OUTPUT 既有 4 行保留                                                          | 用户指定展示效果对齐 code-metrics 截图；key 以 `url` 结尾由 GitCode 渲染为链接行；保留 STEP_OUTPUT 向后兼容                                                                                                                                                                                                                                      |
| D5  | 返回值承载                                   | `SbomService.addAndPublishProduct` 返回类型 UUID → `AddAndPublishResult(UUID taskId, String detailLink)`（新 record，model 模块）；`PublishSbomResponse` 新增 `detailLink` 字段                                                                | service 层持有 projectId/productName，URL 在 service 层拼好传出；调用方仅 ApigController 一处                                                                                                                                                                                                                                                    |

## 4. 修改清单（按模块）

### openlibing-sbom（后端）

| 文件                                                    | 变更                                                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `clients/.../feign/FrameworkClient.java`                | 新增 `getProject(projectName, pageNum, pageSize)` → `GET /internal-server/get-project`                  |
| `model/.../pojo/response/sbom/PublishSbomResponse.java` | 新增 `detailLink` 字段（getter/setter/toString）                                                        |
| `model/.../pojo/response/sbom/AddAndPublishResult.java` | 新增 record（taskId + detailLink）                                                                      |
| `model/.../constants/SbomConstants.java`                | 新增 `SBOM_DETAIL_PAGE_URL_PATTERN = "%s/apps/sbomManage?projectId=%s&name=%s"`                         |
| `sbom-web/.../service/sbom/SbomService.java`            | `addAndPublishProduct` 返回类型改为 `AddAndPublishResult`                                               |
| `sbom-web/.../service/sbom/impl/SbomServiceImpl.java`   | `addAndPublishProduct`：注入 domain 配置；新增 `resolvePlatformProjectId` / `buildDetailLink`；组装返回 |
| `sbom-web/.../controller/ApigController.java`           | `addAndPublishProduct` 端点：响应填充 `detailLink`                                                      |
| `sbom-web/src/test/.../SbomServiceImplTest.java`        | 新增 detailLink 场景 UT                                                                                 |

### sbom-action（插件）

| 文件            | 变更                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `index.js`      | 响应解析 detailLink；统计变量提升；新增 outputs（编程取数 + ATOMGIT_OUTPUT 分组）；`sanitize` 复刻；`appendAtomgitOutput` 复刻 |
| `dist/index.js` | ncc 重新打包                                                                                                                   |

### openlibing-web（前端）

| 文件                                                                         | 变更                                                                                                                                                                                        |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue` | 引入 `useRoute`；onMounted 读 `route.query.name` → 写入 `productFilters.names` → `handleProductFilterChange()` 查询 → 结果返回后匹配行自动选中（selectedProduct 联动成分数据 + 行高亮定位） |

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

## 6. 测试策略

- **UT（sbom-web）**：`SbomServiceImplTest` 新增用例——两路径 detailLink 组装、URLEncode、framework 未命中抛异常、feign 异常传播、domain 缺失 detailLink=null、already-exists 容忍路径仍返回 detailLink。
- **插件**：`node --check`；本地模拟响应断言输出行；`ncc build` 后 diff dist。
- **前端**：ESLint；浏览器手工验证 query 参数定位（design-review.html 提供 mockup 预演）。
- **联调**：test 环境配置 Nacos `sbom.service.website.domain=https://www.openlibing.com` 后端到端验证（链接可打开、项目上下文正确、列表定位、点击进详情）。

## 7. 风险

| 风险                                                                     | 等级 | 缓解                                                                    |
| ------------------------------------------------------------------------ | ---- | ----------------------------------------------------------------------- |
| `/internal-server/get-project` 对 feign 直连的鉴权拦截（现网拦截器行为） | 低   | 与现有 `checkPermissionByProductType` 同前缀同鉴权域；联调首验此调用    |
| project_info 存在同名重复项目（无唯一约束）                              | 低   | 精确匹配 + pageSize=1 取首条；出现重复属平台数据治理问题，warn 日志暴露 |
| Nacos 域名配置缺失/错误导致链接不可用                                    | 中   | detailLink=null 不阻塞上报；发布检查项加入配置核对                      |
| GitCode 面板对 ATOMGIT_OUTPUT 渲染分组规则变化                           | 低   | 行为对齐 code-metrics-action 线上实际效果，随其回归                     |
| `addAndPublishProduct` 签名变更影响未知调用方                            | 低   | 全仓检索仅 ApigController 一处调用                                      |
