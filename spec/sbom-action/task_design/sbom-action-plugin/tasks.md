# sbom-action 插件全链路实现 — 实现任务

> 原 `sbom-action-init` / `sbom-action-addproduct-giturl` / `sbom-server-addproduct-giturl` 三份任务清单合并。

## sbom-action（插件仓）

### 初始实现

- [x] Task 1: 创建插件骨架 — `action.yml`（inputs，runs 固定 node16 + dist/index.js）、`package.json`（@actions/core / huaweicloud-oidc-client / adm-zip，ncc 编译）、`zip.js`（输出 openlibing-sbom-action.zip）、`.gitignore`
- [x] Task 2: `index.js` 工具层 — getInput 连字符/下划线兼容、setOutput 双通道输出（setOutput 编程取数 + STEP_OUTPUT 输出文件可读概览）
- [x] Task 3: `index.js` trivy 层 — pickTrivyAsset（platform/arch → 5 二进制映射）、downloadTrivy（curl 参数数组 + AdmZip 解压 + chmod，执行前清理旧 zip/二进制）、buildScanArgs（--offline-scan + 可选 --analyze-all-python / --analyze-dir）
- [x] Task 4: `index.js` 上传层 — OIDC 探测（ACTIONS_ID_TOKEN_REQUEST_URL）、addAndPublishProduct 单接口（body 含 attribute 扁平 JSON → ConfigValueLabel + sbomContent spdx_2.2_json_sbom；非 2xx / success!==true 抛错；产品已存在容忍在服务端 service 层事务内）
- [x] Task 5: README.md — 简介、工作流程、输入/输出参数表、使用示例（permissions: id-token: write）、注意事项
- [x] Task 6: 仓初始化补齐（gitcode-openlibing-repo-init Step 2）— `.pre-commit-config.yaml` 补 eslint-sarif 钩子、`eslint.config.mjs` + devDeps、`nightly-schedule-scan.yml`、`.gitignore` 补 tmp_pre-commit-reports/

### addProduct 契约适配（gitUrl + productType 可选）

- [x] action.yml：`product-type` 输入更名为 `project-type`，`required` 改为 `false`，描述与校验文案更新
- [x] index.js：输入读入改为 `getInput('project-type')`，内部变量更名 `projectType`；删除 `productType` 必填校验
- [x] index.js：新增 `resolveGitUrl()`（env 优先 → `git remote get-url origin` 回退 + token 清洗 → 空串），`addProduct` body 的 `gitUrl` 改为调用该函数，`productType` 非空才写入
- [x] trivy 版本内置固定：移除 `trivy-version` 输入，`downloadTrivy` / `cleanupTrivy` / 日志统一改用 `DEFAULT_TRIVY_VERSION`（v1.1.1）
- [x] SBOM 输出内置固定：移除 `sbom-output` 输入，新增 `resolveSbomOutput()`（`os.tmpdir()/sbom-action-output/{ATOMGIT_RUN_ID|时间戳}/sbom-result.spdx.json`，目录预创建）
- [x] debug 输入重构为 sbom 调试日志：模块级开关 `debugEnabled` + `debugLog()`（gitUrl 解析来源、请求响应详情、SBOM 前 512 字符预览）
- [x] attribute 输入平铺化：移除 `attribute` 输入与 `parseAttribute()`，新增 `ATTRIBUTE_INPUT_TO_FIELD` 显式映射表（终态 15 字段，component/packageName/arch_type/versionName/service_branch 5 个概念重复平台字段不暴露）+ `buildAttribute()`（收集非空项，全空报错）；产品名输入为 `name`，属性输入含 `product-name`；README 新增「各社区属性配置」章节（18 社区映射表）
- [x] 修复 camelCase 字段输入名映射：字段名转输入名同时处理 snake_case 与 camelCase，原 `replace(/_/g,'-')` 漏掉 camelCase 致 9 个字段取不到 input 静默丢弃
- [x] 输入名方案终版（用户裁定）：action.yml 对外统一 kebab-case，index.js 用显式映射表 `ATTRIBUTE_INPUT_TO_FIELD`（kebab-case 输入名 → 平台 ConfigValue name 原文）替代正则转换；脚本验证 15 字段 kebab 归一化两两不同（早期中间态曾为 20 字段全量，后裁剪 5 个概念重复字段）
- [x] README.md：输入表 `project-type` 可选化、使用示例更名、注意事项新增 gitUrl 自动上报说明
- [x] `node --check` 语法校验通过；`rm -rf dist && npm run build` 重建产物，grep 验证 dist 关键点齐全、旧引用清零

## openlibing-coderepo

- [x] 新增 `QueryProjectNamesDTO`（`gitUrl`，`@NotBlank`）+ `ProjectNameVO`（projectId + projectName）
- [x] `RepoService` / `RepoServiceImpl` 新增 `internalQueryProjectNames(String gitUrl)`（resolveByCoordinate → projectId 去重 → queryById → projectName 过滤，返回 `List<ProjectNameVO>`）
- [x] `InternalProjectRepoController` 新增 `POST /project-repo/internal/query-project-names`
- [x] UT：多项目命中去重 / projectName 缺失过滤 / 空 gitUrl / 未命中返回空（3 个用例通过）

## openlibing-sbom

- [x] `AddProductRequest` 新增 `gitUrl` 字段（getter/setter/toString）
- [x] clients 模块新增 `CoderepoClient`（`${feign.coderepo.name:openlibing-coderepo}`）+ `QueryProjectNamesPo` + `ProjectNameVo`（返回反序列化）
- [x] `application.properties` 新增 `feign.coderepo.name: openlibing-coderepo`
- [x] `SbomServiceImpl`：抽取 `validateProductType(req, productType)`（现有校验链参数化）
- [x] `SbomServiceImpl`：新增 `resolveProductTypeFromGitUrl(req)` + `queryProjectsViaCoderepo(gitUrl)`（gitUrl 空报错 / 反查失败与空报错 / 逐候选 dry-run 第一个合法采用 / 全失败聚合报错）
- [x] `addProduct` 主流程接入解析分支（显式传入零影响）
- [x] UT：显式 productType 不调 client / gitUrl 空报错 / 反查空与异常报错 / 多候选采纳第一个合法 / 全不合法聚合报错（6 个用例通过，already exists 容忍由既有用例覆盖）

## 收尾

- [x] 两服务端仓 `mvn test` 相关模块通过（coderepo：3 UT；sbom：-pl sbom-web -am 全模块编译 + 6 UT）
- [ ] 用户自测（test 环境联动验证：sbom-action 不带 project-type 上报 → coderepo 反查 → 落库 productType 正确；nightly 重跑产品已存在由服务端事务容忍；env=test 切换；去掉 id-token: write 报错指引）
- [ ] 业务 PR（sbom-action、openlibing-sbom、openlibing-coderepo 三仓，均关联 https://gitcode.com/openlibing/sbom-action/issues/1 + `ai-assisted` 标签）
