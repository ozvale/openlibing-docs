# Proposal: 项目 NOTICE 扫描（ossinfo-extraction-notice）

> 本文档基于 openlibing-sca `ms_notice` 分支的实现现状（2026-08-31 对齐），替代早期单接口 `POST /open/ossinfo/notice` 版本的 spec。早期设计见文末「演进历史」。

## Summary

项目 NOTICE 扫描功能批量提取产品所含开源软件的版权与许可证信息，并聚合生成一份 Markdown 格式的 `OPEN SOURCE SOFTWARE NOTICE` 文档，供开源合规审计与随产品发布使用。

功能位于 SCA 服务 `dm` 模块，对外提供 `/project/notice/scan` 下 4 个接口：

| 接口 | 路径 | 行为 |
|------|------|------|
| 启动扫描 | `POST /project/notice/scan/start` | 仅传 `productName`；服务端拉取产品 SBOM 自动解析软件清单，落库后经 RabbitMQ 异步执行，立即返回 `scanId` |
| 保存发布名称 | `POST /project/notice/scan/release` | 按 productName 保存/更新发布名称（release_name），支持后续按发布名称查询 |
| 查询结果 | `POST /project/notice/scan/query` | 按 releaseName（优先）或 productName 查询最新扫描：合并 NOTICE 下载地址、扫描状态、失败软件明细 |
| 人工补充 | `POST /project/notice/scan/supplement` | 对扫描失败的软件人工补充 NOTICE 文本，重建合并文档并返回新下载地址与剩余失败明细 |

## Motivation

在开源合规场景中，随产品发布必须附带完整的开源软件声明（版权、许可证全文、下载地址）。该功能提供全自动化能力：

1. **SBOM 驱动**：调用方只需提供产品名，软件清单从产品 SBOM 自动解析（含目录级 SBOM 的 externalRefs 展开），无需人工维护软件列表
2. **多生态下载解析**：依赖下载地址可能是 purl（pkg:maven / pkg:pypi / pkg:npm / pkg:golang / pkg:rpm / git 仓库），由 purl 解析器体系转换为镜像→官方→原始的多候选下载地址依次尝试
3. **异步串行执行**：RabbitMQ 单消费者串行消费，避免 Python 子进程/下载/磁盘重负载并发竞争；手动 ack + 幂等检查 + 死信队列保证可靠消费
4. **状态持久化与可查询**：扫描总表 + 明细表落库，调用方可按产品名/发布名查询扫描状态、合并文档地址与失败明细
5. **人工兜底**：自动提取失败的软件支持人工补充 NOTICE 内容，补充后自动重建合并文档
6. **全局缓存复用**：同一软件（名称+版本+下载地址）在历史扫描中成功过的，直接复用其 OBS 上的 `Readme.opensource`，不重复下载与提取

## Scope

### 涉及文件

| 文件 | 角色 |
|------|------|
| `dm/controller/ProjectNoticeScanController.java` | REST 接口入口（4 个接口） |
| `dm/service/ProjectNoticeScanService.java` | 服务接口定义 |
| `dm/service/impl/ProjectNoticeScanServiceImpl.java` | 服务实现：启动/发布名/查询/人工补充，SBOM 解析 |
| `dm/service/impl/ProjectNoticeScanAsyncProcessor.java` | RabbitMQ 消费者：单包处理、合并上传、结果落库 |
| `dm/util/ProjectNoticeScanExecutor.java` | 执行器：下载、Python 子进程、OBS 上传/下载、合并上传、目录清理 |
| `dm/util/NoticeMerger.java` | 合并文档生成：头部声明 + License 去重 + 下载地址表 |
| `dm/util/packageurl/*.java` | purl 解析器体系（Composite + Pypi/Maven/Npm/Go/CGit/Rpm/Default） |
| `dm/event/ProjectNoticeScanCreatedEvent.java` / `ProjectNoticeScanEventListener.java` | 事务提交后向 RabbitMQ 投递 scanId |
| `common/config/rabbitmq/ProjectNoticeScanRabbitConfig.java` | 手动 ack、单消费者容器工厂 |
| `common/enums/ProjectNoticeScanStatus.java` / `ProjectNoticeScanDetailStatus.java` | 扫描/明细状态枚举 |
| `analysis/entity/TblProjectNoticeScan.java` / `TblProjectNoticeScanDetail.java` | 持久化实体 |
| `analysis/entity/dto/ProjectNoticeScan*Po.java`、`vo/ProjectNoticeScan*VO.java` | 请求/响应 DTO |
| `dm/dao/TblProjectNoticeScan(Detail)Mapper.java` + `mapper/dm/*.xml` | MyBatis 数据访问 |
| `db/changelog/mysql/20260716/create-tbl-project-notice-scan.xml` | Liquibase 建表 |
| `tools/OSSinfo_extraction/` | 本地化的 Python 提取工具（随镜像构建，不再运行时 git clone） |

### 关联改动

- `Dockerfile`：`OSSinfo_extraction` 工具改为 `COPY ./tools/OSSinfo_extraction` 本地复制，`PYTHONPATH` 指向 `ossinfo-extraction/src`
- `analysis/service/impl/OpenScanServiceImpl.java`：提供 `getLicenseFromSbom(productName)` 供扫描启动获取 SBOM
- `dm/service/impl/OpenPersonDMScanDMServiceImpl.java`：兼容 scancode-toolkit 32.x 输出字段（`license_detections` / `license_expression_spdx`），配合工具升级

### 不在范围内

- 不修改 `ossinfo_extraction` Python 工具的提取算法本身（仅随仓本地化维护）
- 不涉及 OBS 文件的清理/过期策略
- 不提供扫描过程的实时进度推送（调用方轮询 query 接口）

## Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│            调用方 POST /project/notice/scan/start { productName }   │
└───────────────────────────┬────────────────────────────────────────┘
                            ▼
              ┌──────────────────────────────┐
              │  startScan (@Transactional)  │
              │  1. getLicenseFromSbom       │  拉取产品 SBOM
              │  2. parseSbomToDetails       │  packages/externalRefs 展开 + 去重
              │  3. 落库 scan(PENDING)+明细  │
              │  4. 发布 CreatedEvent        │  事务内发布
              └──────────────┬───────────────┘
                             ▼  返回 scanId
              ┌──────────────────────────────┐
              │  EventListener (AFTER_COMMIT)│
              │  convertAndSend(scanId)      │  → notice_scan_exchange
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  notice_scan_queue           │  单消费者、手动 ack
              │  AsyncProcessor.onMessage    │  失败 nack → 死信队列
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  processScan(scanId)         │
              │  幂等检查：仅处理 PENDING     │
              │  scan → PROCESSING           │
              │                              │
              │  For each detail:            │
              │  ┌─────────────────────────┐ │
              │  │ 全局缓存命中?           │ │  命中 → 直接下载已有
              │  │ 否 → downloadPackage    │ │  Readme.opensource
              │  │   (purl resolver 多候选)│ │
              │  │   → python 提取         │ │  ossinfo_extraction
              │  │   → 上传单包 Readme     │ │  {productName}/xxx
              │  │ 失败 → 明细 FAILED      │ │
              │  └─────────────────────────┘ │
              │                              │
              │  成功项 > 0:                 │
              │  NoticeMerger 合并 + 上传    │  open-source-notice-*.md
              │  scan → SUCCESS/FAILED       │
              │  finally: cleanupScanDir     │
              └──────────────┬───────────────┘
                             ▼
        ┌─────────────────────────────────────────────┐
        │  调用方 POST /query    → 状态/地址/失败明细  │
        │  调用方 POST /supplement → 人工补充+重建文档 │
        │  调用方 POST /release  → 保存发布名称        │
        └─────────────────────────────────────────────┘
```

## Acceptance Criteria

1. `start` 接口仅传 `productName` 即返回 `scanId`；SBOM 不存在或解析不出软件包时返回明确错误
2. SBOM 中 `downloadLocation` 为 `NOASSERTION`/`NONE` 的包，其 `externalRefs` 中的 purl 被展开为独立扫描明细；跨包按（软件名，版本）去重
3. 落库成功后消息在事务提交后投递；进程重启/消息重投时幂等检查避免重复处理；消费异常进死信队列不堵队列
4. 单包处理失败仅将该明细置为 FAILED（记录失败原因），不影响其他明细；至少 1 个成功即生成合并文档且扫描状态为 SUCCESS
5. purl 下载地址经解析器转换为候选地址依次尝试下载；合并文档下载地址表展示去除镜像后的官方地址
6. 合并文档为 Markdown：头部声明 + 各软件内容（重复 License 全文折叠为 `Please see above`）+ 末尾 GPLv2 声明与下载地址表
7. `query` 接口返回 `scanStatus`/`scanStatusName`（0-待处理/1-处理中/2-成功/3-失败）、`mergedOssUrl` 与失败软件明细
8. `supplement` 接口在扫描完成后接受人工补充，补充项写入合并文档（下载地址表之前），返回重建后的地址；扫描未完成时拒绝补充
9. 历史扫描成功过的同名同版本同地址软件直接复用缓存，不重复下载与执行 Python
10. 临时目录（单包目录、扫描目录）在处理完成后被清理

## 演进历史

- **v1（已废弃）**：单接口 `POST /open/ossinfo/notice`（`analysis` 包 `OssInfoExtractionController`），调用方自带 `repoName + items[]` 下载地址列表，`@Async` 线程池执行，无持久化、无查询、无失败兜底，输出 `{repoName}{timestamp}.opensource`。该版本类在 `ms_notice` 分支已全部移除。
- **v2（当前）**：重构为本文档描述的 `ProjectNoticeScan*` 体系——SBOM 驱动、RabbitMQ 异步、状态持久化、查询/人工补充/发布名称管理、purl 多生态下载解析、Markdown 合并文档。
