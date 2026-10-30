# sbom-action 插件全链路实现 — EDEVOPS 设计文档

> 变更名称：sbom-action-plugin
> 目标仓库：sbom-action（插件仓）、openlibing-coderepo、openlibing-sbom（跨仓）
> 业务 Issue：https://gitcode.com/openlibing/sbom-action/issues/1
> 设计文档：[design.md](./design.md)
> 说明：本文档由原 sbom-action-init / sbom-action-addproduct-giturl / sbom-server-addproduct-giturl 三个变更的 EDEVOPS 设计合并而成。

## 一、需求背景

SBOM 上报从 codearts 流水线迁移到 GitCode 流水线，需要代码化插件承接"扫描 + 上报"全流程（trivy 离线扫描 + OIDC 联邦认证上传）。同时 productType（社区标识）为平台侧已知信息，不应转嫁给用户配置：插件自动采集 gitUrl 随 addProduct 上报、`project-type` 改可选，服务端经 coderepo 按 gitUrl 反查所属项目名作为 productType，多候选时逐个按现有校验逻辑裁决，第一个合法者采用。

## 二、整体方案

```
sbom-action 插件（Node action，ncc 打包）
  输入校验（fail-fast）
  → 按 platform/arch 下载 openlibing/trivy-sbom-tools release 包并解压（内置 v1.1.1）
  → trivy fs --format spdx-json --offline-scan 扫描 target-dir（输出固定临时目录）
  → addAndPublishProduct 建品+发布单步完成（自动采集 gitUrl；产品已存在由服务端事务容忍）
  │    └─ productType 缺省时（openlibing-sbom 服务端，反查阶段无锁、尚无数据库写入）
  │         → 调 coderepo POST /project-repo/internal/query-project-names（新增机机接口）
  │         ├─ 失败/空 → 报错
  │         └─ projectNames 候选数组 → 逐候选 dry-run 现有校验
  │              （product_type 存在 + attribute 覆盖该类型全部 config keys + blank + value/label 冲突）
  │              ├─ 第一个合法者 → 回填 productType → 原有落库链路
  │              └─ 全部不合法 → 聚合报错（候选 + 各自原因）
  │    └─ body 含 sbomContent（spdx_2.2_json_sbom，OIDC callApig 认证）
  → 输出 task-id / sbom-file（编程取数 + 可读概览双通道）
  → finally 清理 trivy 临时目录（SBOM 输出目录保留，见 design.md「9. 遗留项」）
```

## 三、详细设计

### 3.1 sbom-action 插件

单文件 Node action（`index.js` → ncc 打包 `dist/index.js`）。

**输入（action.yml 终态）**：`name`（必填，平台制品名）、`project-type`（可选，缺省由服务端反查）、15 个平铺属性 input（kebab-case，对应平台 `sbom_new_product_config` 表字段，经显式映射表 `ATTRIBUTE_INPUT_TO_FIELD` 转平台 ConfigValue name；component/packageName/arch_type/versionName/service_branch 5 个概念重复字段不暴露）、`target-dir`（必填）、`analyze-all-python` / `analyze-dirs`（可选）、`env`（prod / test，缺省 prod）、`debug`（sbom 调试日志开关）。已移除：`trivy-version`（内置 v1.1.1）、`sbom-output`（固定 `os.tmpdir()/sbom-action-output/{运行ID}/sbom-result.spdx.json`）、`attribute`（平铺化）。

**gitUrl 自动采集**：三级降级——runner 注入 `ATOMGIT_REPOSITORY_URL`（原样上报，不做凭证清洗，依赖 runner 注入无凭证公开地址）→ 工作区根 `git remote get-url origin`（token 清洗，正则仅覆盖 `https://user:token@host` → `https://host` 形态；http/query/ssh 形态不清洗，见 design.md「9. 遗留项」）→ 空字符串（不阻塞）。body 字段名保持 `productType`（后端 DTO 原名），gitUrl 为提前携带的额外字段（Spring Boot 容忍未知字段），前后端上线顺序解耦。

**trivy 工具包**：platform/arch → 5 二进制映射（linux amd/arm、darwin amd/arm、win）；下载 URL `https://gitcode.com/openlibing/trivy-sbom-tools/releases/download/{tag}/{zip}`；解压至 `os.tmpdir()/sbom-action-trivy/{tag}/{运行 ID}`（执行前清理残留，finally 清理本次运行子目录；目录 TAG + 运行 ID 两级隔离，运行 ID 全程取值一次、与 SBOM 输出目录共用，下载前打印 `trivy workdir`；当前实现无 sha256 完整性校验，见 design.md「9. 遗留项」）。

**上传链路（OIDC，单接口）**：`@openlibing/huaweicloud-oidc-client` 的 `callApig`（OIDC ID Token → STS → APIW V11 签名）；`POST /action-api/sbom/addAndPublishProduct` 建品+发布一个 service 事务完成（body 含 gitUrl/productName/attribute/sbomContent/`sbomContentType=spdx_2.2_json_sbom`/可选 productType；attribute 须覆盖 productType 全部配置项；非 2xx 或 `success!==true` 抛错，202 + `{success, taskId, errorInfo}` 成功输出 taskId；产品已存在由服务端事务内容忍，发布失败回滚新建产品）。网关前缀：prod `https://apig.openlibing.com:443`；test `https://f209a4ca505e492b96d2dc70f5578641.apic.cn-southwest-2.huaweicloudapis.com`。workflow 必须声明 `permissions: id-token: write`，缺失时启动即报错指引。

**插件输出**：编程取数 `steps.<id>.outputs.task-id` / `sbom-file`；可读概览（STEP_OUTPUT 输出文件）`任务ID（taskId）` / `SBOM文件（sbomFile）`。

**实现清单**：index.js（核心逻辑）、action.yml、package.json（构建脚本 package/zip/build/bump/release）、zip.js、eslint.config.mjs、.gitignore、README.md（15 个社区属性输入说明 + 18 个社区 productType 配置对照表）、dist/index.js（ncc 产物）。仓初始化：`.pre-commit-config.yaml`（公共 hooks + gitleaks + markdownlint + prettier + eslint-sarif）、流水线 `pre-commit.yml` / `code-metrics.yml` / `nightly-schedule-scan.yml`。

### 3.2 openlibing-coderepo：新增内部反查接口

`POST /project-repo/internal/query-project-names`，入参 `{"gitUrl": "..."}`，返回 `DataResult<List<ProjectNameVO>>`（projectId + projectName，按 projectId 去重）。

复用 `RepoCoordinateResolver.resolveByCoordinate`：URL 全串精确匹配快路径 + 平台坐标（repoType + owner + repo，域名无关）慢路径，容忍 `.git` 后缀与 gitcode.com ↔ atomgit.com 跨域差异。projectName 经 `projectInfoMapper.queryById` 获取。

不选用现成 `query-repo` 接口：仅返回 projectId 无 projectName，且纯精确匹配对插件上报的多来源 gitUrl 命中率不足。

### 3.3 openlibing-sbom：addProduct 解析链改造

| 文件                                   | 改动                                                                                                                                                                                               |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AddProductRequest`                    | + `gitUrl`（非必填）                                                                                                                                                                               |
| `clients/feign/CoderepoClient`（新增） | FeignClient `openlibing-coderepo`，queryProjectNames                                                                                                                                               |
| `application.properties`               | `feign.coderepo.name: openlibing-coderepo`                                                                                                                                                         |
| `SbomServiceImpl`                      | 抽取 `validateProductType(req, productType)`（现有校验链参数化）；新增 `queryProductCandidatesFromGitUrl` + `resolveProductTypeFromCandidates` + `queryProjectsViaCoderepo`；`addProduct` 接入分支 |

关键约束：`validateProductType` 为现有校验逻辑的逐字参数化抽取，dry-run 与主链路共用同一实现，保证候选判定与真实落库判定一致。gitUrl 反查改造后 `addProduct` 主链路不再调用 `lockTable()`（dao 方法定义保留，生产代码零调用，测试以 `never()` 断言守护）：反查与候选 dry-run 位于判重/落库之前、全程无锁（经 `addAndPublishProduct` 调用时处于外层事务内但尚无写入），coderepo 慢响应只影响本次请求，不会阻塞数据库操作或放大为建品接口整体不可用。

## 四、方案开放问题与决策

| 问题                                 | 决策                                                                                                     | 备注                                                                                                       |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 认证方式                             | OIDC 联邦认证，不做 AK/SK 双轨                                                                           | 新插件规范 4.2.4 硬约束                                                                                    |
| trivy 版本选择                       | 移除 trivy-version 输入，内置 v1.1.1，升级由插件发版承载                                                 | 消除 TAG 外部输入面                                                                                        |
| 大 SBOM 超网关体积上限               | 本轮仅 addAndPublishProduct（非压缩），不做 WithCompress 压缩兜底                                        | 遇超限后续按需反馈平台侧                                                                                   |
| attribute 入参形态                   | 15 字段平铺 input（kebab-case）+ 显式映射表（5 个概念重复平台字段不暴露）                                | 早期多行 key=value / JSON 双写法已废弃；正则转换漏 camelCase 曾致 9 字段静默丢弃，终版用映射表（用户裁定） |
| productType 由用户指定改为服务端反查 | 插件自动采集 gitUrl 上报，服务端经 coderepo 反查                                                         | 显式传入为逃生口，存量零影响                                                                               |
| 多社区仓冲突裁决                     | 逐候选按现有校验逻辑裁决，第一个合法者自动采用；全不合法聚合报错                                         | 修订早期方案（命中 2+ 即报错）；各社区配置项不同，多数场景仅一个候选可通过校验；用户 2026-10-22 指令       |
| 反查失败处理                         | 直接报错（不降级跳过 productType 落库）                                                                  | product_type 校验是现有硬约束，跳过需放宽落库逻辑影响面大；用户确认                                        |
| coderepo 接口形态                    | 新增专用内部接口（不扩展现有 query-repo）                                                                | 语义贴合、不影响既有契约；用户确认                                                                         |
| gitUrl 匹配口径                      | 完整 URL 坐标反查（owner + repo 维度，域名无关）                                                         | 避免裸 repoName 同名误命中                                                                                 |
| productName 已存在（nightly 重跑）   | 容忍逻辑在服务端 service 层事务内（视为成功继续发布，发布失败回滚新建产品），发生在 productType 解析之后 | 插件仅按 success 判定，无插件侧容忍逻辑                                                                    |
| 插件与服务端上线顺序                 | 插件先行携带 gitUrl（后端容忍未知字段），服务端跟进                                                      | Spring Boot `FAIL_ON_UNKNOWN_PROPERTIES=false`，契约演进解耦                                               |

## 五、测试与验证

- 插件本地：`node --check` + `npm install && npm run build`（ncc 编译 + zip 打包，grep 验证 dist 关键点、旧引用清零）
- 单元测试：coderepo `internalQueryProjectNames`（多项目去重/过滤/空场景）；sbom `addProduct` 分支覆盖（显式传入不调 client、双空报错、反查失败/空报错、多候选采纳、全失败聚合、产品已存在容忍不变）
- 流水线自测（test 环境）：
  1. workflow 声明 `permissions: id-token: write` 跑通全流程，平台侧核对产品与 taskId
  2. 去掉 `project-type` 上报 → coderepo 反查 → 平台落库 productType 与 coderepo 项目一致；显式传入回归验证
  3. nightly 重跑验证产品已存在容忍（服务端事务容忍，插件成功输出 taskId）
  4. env=test 切换测试网关；去掉 id-token: write 验证报错指引
- 兼容回归：存量调用（显式 productType、无 gitUrl）行为与报错语义完全不变
