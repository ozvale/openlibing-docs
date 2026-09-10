# ms-notice-20260910 — notice 生成优化与 Copyright 归一化

> 对应 openlibing-sca PR [#304](https://gitcode.com/openlibing/openlibing-sca/pull/304)（`ms_notice_20260910` → `release_20260910`，已合并），38 文件，+3622 / -576。Fixes #75、#76。

## 需求背景

项目 NOTICE 扫描链路存在两个缺陷，同时叠加一批工程化增强需求：

1. **#75 人工修正下载地址不跨扫描继承**：软件包下载地址错误时由人工补充修正，但同产品再次发起扫描时，SBOM 解析出的原始地址仍会覆盖人工成果，导致同一软件反复下载失败、反复人工补充，且修正后的地址无法命中全局缓存。
2. **#76 Copyright 归一化不兼容导致误告警**：版本扫描与 PR 扫描对 Copyright 字段的归一化口径不一致（`copyright` 前缀、`(c)` 标记剥离方式不同），同一版权声明在不同来源下归一化结果不同，对比时误报不匹配。
3. 人工补充接口为同步长事务（补充时同步重建合并 NOTICE 文档），多调用方并发补充时行为不可预期。
4. 缺少面向调用方的扫描详情查询 API（现有 `/query` 暴露 OBS 内部地址且字段不全）。
5. NOTICE 导出为直接返回 OBS 签名 URL，未接入平台统一导出入口（「我的导出」），且文件名可控性差。
6. purl 解析对 git host 主页 URL、归档/ref URL、Maven 镜像 URL 的路由存在缺陷，下载到 HTML 网页时未判定失败。

## 变更内容

### 缺陷修复

- **#75 人工修正跨扫描继承**：`tbl_project_notice_scan_detail` 新增 `manual_url` / `manual_content` 两个 TINYINT 标记列（Liquibase changeset 含 preConditions 与 rollback）；新扫描解析 SBOM 生成明细后，按 `(software_name, version)` 查询最近一条「人工干预且 SUCCESS」的历史明细——`manual_content=1` 时内容继承优先（明细落库即 SUCCESS 并回填 OBS 地址，跳过下载提取）；否则 `manual_url=1` 时以人工修正地址覆盖 SBOM 原始地址，天然命中 `(name, version, url)` 全局缓存。
- **#75 补充受理状态管理**：补充受理时主表经 CAS 置为 PROCESSING（仅允许终态或 PROCESSING 翻转）；`processScan` 状态检查由「仅 PENDING」放宽为「PENDING 或 PROCESSING」，消息重投 / 进程重启后恢复孤儿 PROCESSING 扫描（已 SUCCESS 明细复用 OBS 内容，仅重扫未完成明细）。
- **#76 Copyright 归一化**：`replaceSpecialCharsCopyright` 归一化时先以 `(?i)copyright` 剥离前缀单词，`©`、`(c)`、`(C)` 整体移除且排在 `(`、`)` 单字符之前，避免 `(c)` 被拆散残留孤立 `c`，修复版本扫描 / PR 扫描 Copyright 对比不兼容导致的误告警。

### 功能增强

- **补充接口异步化**：`/supplement` 仅做受理（content 与 downloadUrl 二选一），content 项受理时上传 OBS 并 CAS 回填地址，两类明细均置 PENDING；事务提交后投递补充消息（`msgType=supplement` header + JSON body），由既有单消费者串行处理——重扫 rescan 明细、重读 DB 全量明细重建合并 NOTICE 文档，合并成功后才统一置明细成功；多调用方补充结果累积互不覆盖。
- **扫描详情查询 API**：新增 `POST /info`（`productName` + 可选明细状态过滤），返回 `tbl_project_notice_scan` 除 `merged_oss_url` 外全部字段及其明细列表（每条除 `readme_oss_url` 外全部字段）；产品尚未发起过扫描时返回 null 而非抛异常。
- **统一平台导出**：`/release`、`/query` 下线，新增 `POST /export`（body 传 `productName`，query param 传 `userId`）——在 openlibing-framework 创建统一导出任务（Feign `/export/internal-server/create|update`），NOTICE 文件转存至导出桶（objectKey 随机化为 `yyyy-MM-dd/UUID`），下载文件名通过对象元数据 `Content-Disposition`（RFC 5987 `filename*`）指定；用户在平台「我的导出」按 taskId 获取下载链接。
- **NOTICE 文档格式统一**：`NoticeMerger` 软件段分隔前缀与人工补充项头部统一为 ossinfo-extraction 产物（`readme_opensource.py`）的 `Software: <名称> <版本>` 行，去掉自造的 `====` 边框与 `(manually supplemented)` 标注。

### purl 解析修复

- `CGitPackageUrlResolver`：引入 git host 白名单（gitcode/github/gitee/atomgit/gitlab/bitbucket 含子域），支持识别不带 `.git` 后缀的仓库主页 URL 走 git clone；归档 / 发布资产 URL（`/archive/`、`/releases/download/`、归档后缀等）路由到 HTTP 下载；网页版 ref 页面（`/commit/<sha>`、`/tree/<ref>` 等）归一化为平台归档下载地址（github/gitee/bitbucket/gitlab 已知格式，其余回退仓库基址由 clone 兜底）。
- `MavenPackageUrlResolver`：镜像 URL 去掉 `maven2/` 路径前缀（镜像根路径已等价于 Central 的 `/maven2/`），官方 URL 保留前缀。
- `ProjectNoticeScanExecutor` 下载响应 `Content-Type` 为 `text/html` 时判定下载失败（SPA 平台对未匹配路径返回 200 + HTML 首页壳），避免网页被当软件包静默落盘后交给 scancode 扫出空结果。

### 依赖

- `openlibing-common-sdk` 升级 1.0.20.4 → 1.0.20.6。

## 验收标准

- [x] 人工修正地址重扫成功后，同产品再次扫描明细自动继承修正地址并命中缓存，不重新下载提取
- [x] `manual_content=1` 的历史明细被新扫描继承时，明细落库即 SUCCESS 并直接纳入合并文档
- [x] 人工修正但重扫失败（FAILED）的地址不被继承；无修正记录的软件行为不变
- [x] 补充受理后主表置 PROCESSING，调用方可通过 `/info` 感知处理中；合并成功后明细才统一置成功
- [x] 同一软件在途补充期间（PENDING）重复提交被拒绝受理；任一项受理失败整批回滚
- [x] Copyright 含 `copyright` / `(c)` / `©` 前缀变体时归一化结果一致，不再误告警
- [x] `/info` 支持按状态过滤明细，未扫描产品返回 null；响应不含 OBS 内部地址字段
- [x] `/export` 在 framework 创建导出任务，转存成功后任务置成功，用户可从「我的导出」下载且文件名正确
- [x] Liquibase changeset 可正确执行（幂等 preConditions）并可回滚
- [x] 相关单元测试通过（AsyncProcessor / ServiceImpl / EventListener / Controller / CGit & Maven resolver / Copyright 归一化等）

## 影响范围

- 业务仓：`openlibing-sca`（dm 模块为主 + analysis 实体/VO + common Feign + Liquibase），38 文件。
- 数据库：`tbl_project_notice_scan_detail` 新增 2 列（含 NOT NULL DEFAULT 0 约束，存量数据自动补 0）。
- 外部依赖：openlibing-framework 统一导出接口（`/export/internal-server/create|update`）、`obs.export.bucket` 配置项（默认 `openlibing-export-prod`，各环境配置中心需确认）。
- 接口契约：`/release`、`/query` 下线，`/supplement` 语义变更为异步受理，调用方（openlibing-web 等）需同步适配。
