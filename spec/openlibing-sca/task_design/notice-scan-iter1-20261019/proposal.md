# NOTICE 扫描大版本迭代（20261019 iter1）：多过滤查询 / 批量导出 / 依赖类型 / 下载与 purl 链路强化

## 需求背景

NOTICE（合法合规声明）扫描能力自上线后，用户在实际使用中暴露出批量操作缺失、查询维度不足、下载链路脆弱、purl 解析失败等问题：一次只能导出一个制品、无法按状态批量筛选发起扫描、GitHub 下载在国内链路频繁失败、无版本 purl（version=NOASSERTION）直接导致扫描项无效、超大 Python 包扫描超时等。本迭代为 NOTICE 扫描能力的大版本整合交付，合并交付多个子需求，关联业务 Issue：

- openlibing/openlibing-sca#88 【合法合规】扫描兼容 atomgit.com 域名、审核逻辑及风险看板数据看板优化

## 功能描述

### 1. 新增/增强接口（ProjectNoticeScanController）

| 接口                                                  | 类型 | 说明                                                                                                           |
| ----------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------- |
| `POST /project/notice/scan/scanStatusByMultiFilter`   | 新增 | 按多过滤条件批量查询制品扫描状态（分页）：statuses 本地过滤 + 每条记录附带全量总数/失败数与直接依赖总数/失败数 |
| `POST /project/notice/scan/startBatch`                | 新增 | 按多过滤条件批量发起扫描（异步串行，单制品失败跳过不中断）                                                     |
| `POST /project/notice/scan/exportBatch`               | 新增 | 多制品 NOTICE 批量导出（异步任务，跨乘去重合并为单文件）                                                       |
| `POST /project/notice/scan/clear`                     | 新增 | 异步清空扫描数据（单制品或全量，先删明细后删扫描记录，事务保证两表原子性）                                     |
| `POST /project/notice/scan/dependencyType/supplement` | 新增 | 存量明细依赖类型回填（幂等，可重复执行）                                                                       |
| `POST /project/notice/scan/export`                    | 增强 | 新增 `exportScope` 参数（FULL-全量缺省 / DIRECT-仅直接依赖）                                                   |
| `POST /project/notice/scan/info`                      | 增强 | 明细从列表改分页（pageNum/pageSize），新增 `dependencyTypes` 多选过滤与依赖类型 2×2 拆解统计列                 |

### 2. 依赖类型（dependency_type）

- 明细表新增 `dependency_type`（0-直接，1-间接，2-直接&间接，NULL-未补充，对齐 SBOM package_statistics 口径）。
- SBOM 解析仅展开 externalRefs 中 `referenceCategory=PACKAGE_MANAGER` 的依赖。
- 拆解统计口径：`dependency_type=2` 仅计入直接依赖。
- 支持依赖类型多选过滤与存量回填；回填完成后为制品最新一次扫描重建直接依赖合并 NOTICE。

### 3. 下载链路强化（ProjectNoticeScanExecutor / CGitPackageUrlResolver）

- GitHub 镜像前缀多候选（默认 `gh-proxy.com`、`ghfast.top`，可配置），镜像在前、官方直连兜底，另加 codeload.github.com 直链候选。
- gitee 归档 URL 跨平台误拼纠错：GitHub 形态 `/archive/` 重建为 gitee 原生 `/repository/archive/`（issue #122）。
- 瞬时失败重试：网络类瞬时故障与 HTTP 408/429/5xx 按指数退避重试，404/HTML 壳等确定性失败直接换下一候选。
- OBS 按 objectKey 读缓存（签名 URL 仅 2 周有效期必然过期）；异常消息中签名 URL 脱敏（CWE-532，issue #96 残留面）。
- 批量导出 OBS 并行下载（8 并发、共用 ObsClient、单失败跳过）。
- JVM 代理配置对软件包下载与仓库 API 查询生效（OBS 客户端刻意不走代理）。
- ossinfo 提取超时 20min → 60min（opencv 等超大包曾被熔断）。

### 4. purl 解析（packageurl 各 Resolver）

- 无版本 purl（version=NOASSERTION）拉取最新版本：Go（proxy `@latest`）、Maven（maven-metadata.xml release/latest）、npm（registry latest tarball）、PyPI（JSON API 最新 release）。
- versionless go purl 兜底链：`@latest` 失败后转源码仓库页面 / git clone。
- 无版本明细按最新版本下载成功后，从下载产物反解真实版本回填 DB（issue #123），文档与查询接口不再显示 NOASSERTION。
- 跳过间接依赖与 Python 依赖发起 NOTICE 扫描（Python 依赖不解析、不入库）。

### 5. NOTICE 生成

- 预生成直接依赖合并 NOTICE 并回填 `direct_merged_oss_url`（扫描完成 / 补充重建 / 存量回填三个时机）。
- 新增 `NoticeBatchMerger`：跨制品软件段落去重（同软件同版本保留首次）、License 全文跨制品去重、下载地址表按（名称, 版本）去重。
- 新增 `NoticeExportScope` 枚举（FULL / DIRECT）。

### 6. 工程治理

- license-scanner Dockerfile：钉住 `pluggy<1.7.0`（与 plugincode 32.0.0 不兼容导致 scancode import 即崩）；新增构建期冒烟校验 `pip3 check && scancode --version`，依赖冲突直接让镜像构建失败。
- SpotBugs 修复 3 处；pom.xml 显式引入 `com.rabbitmq:amqp-client:5.34.0`。

## 验收标准

- [ ] 单元测试通过（ProjectNoticeScanServiceImplTest、ProjectNoticeScanAsyncProcessorTest、ProjectNoticeScanControllerTest、ProjectNoticeScanExecutorTest、NoticeBatchMerger 相关、packageurl 各 Resolver 测试）。
- [ ] CI 流水线通过（PR 测试计划勾选项）。
- [ ] 多过滤状态查询结果与制品列表按 productName join 一致，statuses 过滤 / 分页 / 统计列正确。
- [ ] 批量导出产物结构正确：跨制品同软件同版本仅一份、License 全文去重、下载地址表去重。
- [ ] 单制品导出 DIRECT 范围返回直接依赖合并文件；未生成时报业务异常。
- [ ] 无版本 purl 扫描项下载成功后 DB 版本回填为真实版本，不再显示 NOASSERTION。
- [ ] gitee 误拼归档 URL 与 GitHub 直连失败场景均能通过候选链成功下载。
- [ ] Liquibase 两个 changeset 在存量库上执行成功（preConditions 幂等）。
- [ ] license-scanner 镜像构建通过冒烟校验。

## 影响范围

- 仅 `openlibing-sca` 单仓，51 个文件（+6740 / -290，41 commits），主战场为 `dm` 模块（controller / service / executor / packageurl）与 `analysis` 模块（entity / dto / client）。
- **DB schema 变更**：Liquibase 新增 2 个 changeset（`tbl_project_notice_scan_detail.dependency_type`、`tbl_project_notice_scan.direct_merged_oss_url`）。
- **构建/部署影响**：license-scanner Dockerfile 变更（Python 依赖钉住 + 冒烟校验）；新增可选配置项（下载重试 / GitHub 镜像前缀 / ossinfo 超时）均有默认值，不配置不影响启动。
- 对 SBOM 仓新增 internal-api 依赖调用（queryProductNamesByMultiFilter、queryPackageDependencyTypes），契约由对方仓提供。
