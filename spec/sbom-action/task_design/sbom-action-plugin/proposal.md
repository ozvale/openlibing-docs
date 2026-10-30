# sbom-action 插件全链路实现（插件 + addProduct gitUrl 反查）— sbom-action-plugin

## 业务 Issue

- openlibing/sbom-action#1 — sbom-action 插件
- https://gitcode.com/openlibing/sbom-action/issues/1

> 本需求由原 `sbom-action-init`（插件初始实现）、`sbom-action-addproduct-giturl`（插件侧契约适配）、`sbom-server-addproduct-giturl`（服务端反查改造）三个任务设计合并而成——本质为同一需求，涉及 sbom-action、openlibing-sbom、openlibing-coderepo 三个仓。

## 需求背景

当前 SBOM 上报在 codearts 流水线上实现，后续各产品 nightly 切到 GitCode 流水线，需要适配代码化插件：实现 sbom-action 插件，基于 trivy 离线扫描生成 SBOM，并经 OIDC 联邦认证上传 openlibing-sbom 平台。

同时，`product-type`（社区标识）为平台侧已知信息，不应转嫁给用户配置。addProduct 接口需整体改造为 **gitUrl 反查 productType** 模式：

1. **插件自动采集 gitUrl 上报**：取值三级降级（runner 注入 `ATOMGIT_REPOSITORY_URL`（原样上报）→ `git remote get-url origin`（token 清洗，仅覆盖 `https://user:token@` 形态）→ 空字符串），无需用户配置；清洗覆盖边界见 design.md「9. 遗留项」。
2. **`project-type` 改为可选**：显式传入时以传入值为准（多社区仓逃生口、存量零影响）；未传入时由服务端根据 `gitUrl` 反查。
3. **gitUrl → productType 反查**：openlibing-coderepo 新增内部机机接口，根据 gitUrl 返回所属项目（projectId + projectName，projectName 对应 sbom 的 productType）。
4. **多候选裁决**：反查返回多个候选时，逐候选按现有校验逻辑（product_type 存在 + attribute 覆盖该类型全部配置项）dry-run，第一个合法者自动采用；全部不合法则聚合报错。

## 功能描述

### sbom-action 插件（sbom-action 仓）

- 按当前系统与架构（linux amd/arm、windows、mac amd/arm）从 `openlibing/trivy-sbom-tools` release 下载对应 trivy 工具包，解压并赋可执行权限；版本内置固定 `v1.1.1`，升级由插件发版承载（当前实现无下载完整性校验，见 design.md「9. 遗留项」）
- `trivy fs --format spdx-json --offline-scan` 扫描 `target-dir`（必填），生成 SPDX 2.2 JSON；输出到临时目录按流水线运行 ID 隔离的子目录，文件名固定 `sbom-result.spdx.json`
- 可选参数：`analyze-all-python`（解析 requirements.txt 依赖）、`analyze-dirs`（额外 git 目录作为直接依赖）
- 产品属性按平台 `sbom_new_product_config` 表已录入字段**平铺为独立可选 input**（kebab-case 输入名 + 显式映射表转平台 ConfigValue name，共 15 个，5 个概念重复平台字段不暴露），仅非空项拼入 attribute，全部未填时报错
- 上传链路：单接口 `POST /action-api/sbom/addAndPublishProduct` 一次完成建品+发布（body 同时携带 gitUrl、productName、attribute、sbomContent、`sbomContentType=spdx_2.2_json_sbom`；productType 仅在用户填写 `project-type` 时携带；产品已存在的容忍由服务端 service 层事务内处理，插件仅按 `success` 判定成败）
- `env` 参数切换上报环境（prod / test APIG 网关）
- 认证使用 OIDC 联邦认证（`@openlibing/huaweicloud-oidc-client` 的 `callApig`），workflow 声明 `permissions: id-token: write`，无 AK/SK 入参
- `debug` 输入为 sbom 调试日志开关：开启后打印 gitUrl 解析来源、请求/响应详情、SBOM 内容前 512 字符预览（业务层无脱敏，脱敏边界见 design.md「9. 遗留项」）

### 服务端反查（openlibing-coderepo + openlibing-sbom 仓）

- coderepo：`InternalProjectRepoController` 新增 `POST /project-repo/internal/query-project-names`（复用 `RepoCoordinateResolver` 坐标反查，容忍 `.git` 后缀与跨域名差异）
- sbom：`AddProductRequest` 新增非必填 `gitUrl`；clients 模块新增 `CoderepoClient`（FeignClient）；`SbomServiceImpl.addProduct` 增加 productType 缺省解析分支（双空报错 / 反查失败或空报错 / 逐候选 dry-run 第一个合法者采用 / 全不合法聚合报错）

## 范围

- **sbom-action**：action.yml / index.js / README.md / dist 重建（插件全量实现与契约适配）
- **openlibing-coderepo**：新增内部机机反查接口
- **openlibing-sbom**：addProduct 解析链改造 + Feign 客户端

## 不做

- 不实现 AK/SK 签名双轨兼容（新插件规范禁止新增 AK/SK 凭证参数）
- 不实现 `publishSbomFileWithCompress` 压缩兜底（超大文件问题后续按需反馈平台侧）
- 不涉及 coderepo 前端接口、productName 已存在容忍逻辑（保持不变）

## 验收标准

### sbom-action 插件

- [ ] workflow 声明 `id-token: write` 后，插件可完成 trivy 下载、解压、扫描、建品+发布（单接口 addAndPublishProduct）全流程
- [ ] spdx-json 生成成功且 `sbomContentType=spdx_2.2_json_sbom` 被平台接受（返回 taskId）
- [ ] nightly 重跑（产品已存在）由服务端 service 层事务容忍，插件不因已存在失败
- [ ] `addAndPublishProduct` 请求 body 携带 `gitUrl`（三级降级取值，均失败不阻塞主流程）；`productType` 仅在用户填写 `project-type` 时携带
- [ ] 产品属性输入平铺化后，非空项正确拼入 attribute，全部未填时报错退出
- [ ] `env` 参数可切换 prod / test 网关前缀；未声明 `id-token: write` 时明确报错并给出指引
- [ ] `debug` 开启时打印 sbom 调试日志
- [ ] README 输入表、示例、各社区属性配置说明同步更新（15 个社区属性输入 + 18 个社区 productType 配置对照表）；`dist/index.js` 通过 `npm run build` 重建包含全部改动

### openlibing-coderepo

- [ ] 新增 `POST /project-repo/internal/query-project-names`：入参 `{gitUrl}`，返回 `DataResult<List<ProjectNameVO>>`（projectId + projectName，按 projectId 去重，未命中返回空数组）；匹配容忍 `.git` 后缀与跨域名差异

### openlibing-sbom

- [ ] `AddProductRequest` 新增非必填 `gitUrl` 字段
- [ ] `productType` 显式传入时行为与现状完全一致（存量调用零影响，且不调用 coderepo）
- [ ] `productType` 未传且 `gitUrl` 为空：报错（提示二者至少提供一个）
- [ ] `productType` 未传、`gitUrl` 非空：调 coderepo 反查；返回空或调用失败时报错；返回数组时逐候选按现有校验逻辑 dry-run，第一个合法者采用并继续原有落库链路
- [ ] 全部候选不合法时聚合报错（列出候选与各自失败原因）
- [ ] `productType` 解析结果回填后走完整原有校验（productName 已存在、blank、value/label 冲突、落库），原有报错语义不变
- [ ] 两服务端仓提供单元测试（Full 模式）

## 流程模式

Full 模式：跨仓（sbom-action / openlibing-sbom / openlibing-coderepo），proposal + design + tasks + edevops-design。插件为 Node action 无 UT 框架（以流水线自测验证），两个 Java 仓按 Full 模式补 UT。
