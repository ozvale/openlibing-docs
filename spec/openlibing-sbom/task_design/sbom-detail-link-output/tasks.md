# 实现任务 — sbom-detail-link-output

## Phase 3 编码

### 后端 openlibing-sbom

- [ ] 1. `FrameworkClient` 新增 `getProject(projectName, pageNum, pageSize)` feign 方法（`GET /internal-server/get-project`）
- [ ] 2. `SbomConstants` 新增 `SBOM_DETAIL_PAGE_URL_PATTERN`
- [ ] 3. model 新增 `AddAndPublishResult` record（taskId + detailLink）；`PublishSbomResponse` 新增 `detailLink` 字段
- [ ] 4. `SbomService` 接口 `addAndPublishProduct` 返回类型改 `AddAndPublishResult`
- [ ] 5. `SbomServiceImpl`：注入 `sbom.service.website.domain`；新增 `resolvePlatformProjectId`（framework 反查，硬失败）与 `buildDetailLink`（URLEncode + domain 空判）；改造 `addAndPublishProduct`
- [ ] 6. `ApigController.addAndPublishProduct` 响应填充 `detailLink`
- [ ] 7. UT：`SbomServiceImplTest` 补 detailLink 场景（两路径 / 未命中抛异常 / feign 异常 / domain 缺失 / already-exists 容忍）

### 插件 sbom-action

- [ ] 8. `index.js`：`addAndPublishProduct` 解析响应 `detailLink`；包/关系统计变量提升作用域
- [ ] 9. `index.js`：复刻 `sanitize` / `appendAtomgitOutput`；新增 outputs（core.setOutput 三项 + ATOMGIT_OUTPUT 概览组[任务ID/包数量/关系数量]/链接组[产物详情url]，面板不含 SBOM 文件路径）；STEP_OUTPUT 既有行不动
- [ ] 10. `ncc build` 重新打包 dist 并 diff 确认

### 前端 openlibing-web

- [ ] 11. `CompositionAnalysis/index.vue`：读 `route.query.name` → 初始化名称筛选 → 触发查询

## Phase 3 自检

- [ ] 12. sbom-web：`mvn -pl sbom-web -am compile` + 相关 UT 通过
- [ ] 13. sbom-action：`node --check index.js` + ncc 打包成功
- [ ] 14. openlibing-web：lint 通过

## Phase 4 后续（用户自测确认后）

- [ ] 15. 业务 PR（openlibing-sbom / sbom-action / openlibing-web 三仓，标题与 Issue 一致，ai-assisted 标签，关联 #185）
- [ ] 16. test 环境 Nacos 配置 `sbom.service.website.domain` 后端到端联调
- [ ] 17. docs PR 归档 spec + design-review.html
