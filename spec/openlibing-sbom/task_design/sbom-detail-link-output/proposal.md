# 【openlibing-sbom】sbom-action返回产物详情地址 — sbom-detail-link-output

## 业务 Issue

- openlibing/openlibing-sbom#185 — 【openlibing-sbom】sbom-action返回产物详情地址
- https://gitcode.com/openlibing/openlibing-sbom/issues/185

## 需求背景

sbom-action 插件当前输出结果只有任务 ID（taskId），使用者无法从流水线结果直接跳转到 SBOM 产物详情页。需要在输出结果中展示产物详情地址，并展示包的初步分析（包数量、关系数量），提升插件易用性。

输出展示形态对齐 code-metrics-action 的 GitCode 任务结果面板（链接表 + 指标表）。

## 功能描述

- sbom-web `addAndPublishProduct` 响应（`PublishSbomResponse`）新增 `detailLink` 字段，值为平台 SBOM 列表页完整跳转地址：
  `{sbom.service.website.domain}/apps/sbomManage?projectId=<平台项目id>&name=<productName(URLEncode)>`
- `projectId` 为 openlibing 平台项目主数据 id（framework `project_info.project_id`），由 productType（即平台项目名）反查获得：
  - 显式传 productType：sbom-web `FrameworkClient` 新增调用 framework 机机接口 `GET /internal-server/get-project?projectName=<productType>&pageNum=1&pageSize=1`（精确匹配），取 `data[0].projectId`
  - productType 缺省：现有 coderepo `queryProjectNames(gitUrl)` 链路回填 productType 后，同样经 framework 接口按最终 productType 反查
- `projectId` 为硬依赖：反查失败 / 未命中 → 抛 `AddProductException`，上报失败（无降级）
- 域名配置复用既有 `sbom.service.website.domain`（Nacos 配置 `https://www.openlibing.com`）；域名未配置时 `detailLink` 为 null 并 warn（不阻塞上报，projectId 校验已在前）
- 遗留查询接口 `GET /apig-api/querySbomPublishResult` 的 `sbomRef` 同步升级：替换旧 `#/sbomPackages` hash 链接为同一 sbomManage 地址 pattern（复用 projectId 反查）；反查失败 / domain 缺失时 `sbomRef=null` 并 warn（查询接口软降级，`success/finish` 不受影响）
- sbom-action 插件：
  - 新增 outputs：`detail-link` / `package-count` / `relationship-count`（编程取数）
  - GitCode 输出面板（ATOMGIT_OUTPUT，对齐 code-metrics-action）：概览组（任务ID / 包数量 / 关系数量）+ 链接组（`SBOM查询url=<detailLink>`，key 以 url 结尾渲染为可点击链接行）；面板不展示 SBOM 文件路径
  - 包数量 / 关系数量复用插件本地 SPDX JSON 已有统计逻辑（从"仅日志"提升为输出）
  - `detailLink` 输出前过 sanitize 防换行注入
  - STEP_OUTPUT 现有可读行保留不动（向后兼容）
- openlibing-web 前端：SBOM 页（`/apps/sbomManage`，制品信息 + 软件成分数据联动页）支持 URL query 筛选参数并双向同步：
  - 读：进入页面解析 `route.query`——`name`（制品名称单值，detailLink 场景）/ `names`（多值）/ attr 动态字段（branch、softwareName、version 等，key 即后端字段名）/ `scanStatus` / `vulInclude` / `vulExclude`（待闭环漏洞级别包含/排除）——初始化对应筛选并触发查询；单值 `name` 时查询结果匹配制品行自动选中（联动展示该制品的软件成分数据），实现"打开链接即打开某个制品的数据"
  - 写：页面筛选条件变化时通过 `router.replace` 将当前筛选写回 URL（保留 `projectId` 等壳层参数，空筛选删除对应 key），复制 URL 即可分享当前筛选状态
- 平台壳层 `projectId` query 参数由现有 router guard 消费恢复项目上下文，无需改动

## 不做

- 不修改 framework / coderepo 服务端代码（仅 sbom-web 侧新增 feign 方法声明）
- 旧 hash 页 `#/sbomPackages` 前端路由与页面本身不动（仅后端不再生成指向它的链接）
- 不修改前端详情页（列表页点击进详情为现有交互）
- 不修改 sbom-action 的 STEP_OUTPUT 既有输出键
- 软件成分数据区筛选、列表排序、分页状态不做 URL 参数化（URL 只承载制品信息表筛选）

## 验收标准

- [ ] `addAndPublishProduct` 成功响应含 `detailLink`，格式为 `{domain}/apps/sbomManage?projectId=<id>&name=<name>`，name 已 URLEncode
- [ ] 显式 productType 与 productType 缺省两条路径均能返回带 projectId 的 detailLink
- [ ] projectType 反查 framework 未命中或 feign 异常时，`addAndPublishProduct` 抛 `AddProductException` 失败
- [ ] 域名配置缺失时响应 `detailLink=null`，上报流程正常完成
- [ ] `querySbomPublishResult` 任务完成时 `sbomRef` 为新地址格式（含 projectId）；反查失败或 domain 缺失时 `sbomRef=null`，`success/finish` 正常返回
- [ ] 插件任务结果面板展示：链接表（SBOM查询url，可点击/复制）+ 指标表（任务ID、包数量、关系数量），不含 SBOM 文件路径
- [ ] 插件编程 outputs 含 detail-link / package-count / relationship-count
- [ ] 浏览器打开 `{domain}/apps/sbomManage?projectId=3&name=xxx`：项目上下文恢复（壳层 guard），制品表自动过滤并选中对应制品，软件成分数据联动展示；点击行内 name / 其他制品行可切换（现有交互）
- [ ] 打开带扩展筛选参数的 URL（如 `&branch=master&vulInclude=HIGH`）：制品表按参数自动填充筛选并查询；未知字段名/非法枚举参数被忽略
- [ ] 页面筛选条件变化后 URL 同步更新（保留 projectId），复制新 URL 重新打开可复现相同筛选状态
- [ ] 后端新增行为有对应单元测试
