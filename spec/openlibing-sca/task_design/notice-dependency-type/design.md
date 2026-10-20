# NOTICE 扫描明细依赖类型与按依赖范围导出 — 技术设计

## 1. 方案设计

依赖类型判定**不在 sca 重复实现**，直接消费 SBOM 侧既有结果：新扫描与存量回填统一调用 SBOM internal-api `POST /internal-api/queryPackageDependencyTypes`（入参 productName），返回 `List<PackageDependencyTypeVo>`（name/version/downloadLocation/purl/dependencyType，不去重不归并）。

sca 侧归并规则（同一 (softwareName, version) 命中 SBOM 多行时）：

| SBOM 返回 distinct(dependencyType) | sca 归并结果   |
| ---------------------------------- | -------------- |
| 含 2                               | 2              |
| 同时含 0 和 1                      | 2              |
| 仅 0                               | 0              |
| 仅 1                               | 1              |
| 空 / 全 null                       | NULL（未补充） |

匹配键为 (name, version)。sca 明细侧 version 兜底为 `NOASSERTION`（既有逻辑），SBOM 侧 version 为空时按空串参与匹配，两侧不强行对齐——匹配不上的明细保持 NULL，不猜。

导出按依赖范围过滤采用**预生成 + 新列**（方案 B，2026-10-14 自测阶段评审后由实时重建方案变更而来）：

- `tbl_project_notice_scan` 新增 `direct_merged_oss_url` 列，存储直接依赖合并 NOTICE 的 OBS 地址。
- 扫描完成（processScan）与补充重建（processSupplement）双文件输出：全量合并文件 + 直接依赖合并文件（按 `dependency_type IN (0,2)` 过滤明细）；direct 合并失败仅告警、列保持 NULL，不阻断扫描主流程。
- 导出为纯转存：FULL 转存 `merged_oss_url` 对应文件，DIRECT 转存 `direct_merged_oss_url` 对应文件（objectKey 规则 `<product>/open-source-notice-<product>-direct.md`），文件未生成时报业务异常。
- 存量回填：更新依赖类型后为**最新一次扫描**重建 direct 文件——明细内容经确定性 objectKey（`<product>/<software>-<version>-Readme.opensource`）重签名下载，绕开历史明细签名 URL 过期问题；更早的历史扫描不生成（导出恒定针对最新扫描），如需 DIRECT 导出可重新扫描。

## 2. 实现逻辑设计

1. **迁移**：Liquibase 新 changeset `20261014-add-tbl-project-notice-scan-detail-dependency-type.xml`（detail 表 `ADD COLUMN dependency_type INT NULL`）与 `20261014-add-tbl-project-notice-scan-direct-merged-url.xml`（scan 表 `ADD COLUMN direct_merged_oss_url VARCHAR(1024) NULL`），include 进 `db.changelog.xml`。
2. **扫描填充**：`parseSbomToDetails` 生成明细后，新增私有方法 `fillDependencyTypes(productName, details)`：调 SBOM → 构建 `Map<name+"@"+version, Integer>`（归并规则见上）→ 填充 `detail.dependencyType`。整体 try/catch 降级：SBOM 调用失败仅 WARN 日志，全部置 NULL，扫描继续。
3. **双文件生成**：`ProjectNoticeScanAsyncProcessor` 在 processScan / processSupplement 构建合并条目时同步构建 direct 条目（明细 `dependency_type IN (0,2)`），全量合并成功后生成 direct 合并文件（objectKey `<product>/open-source-notice-<product>-direct.md`）并回填 `direct_merged_oss_url`；direct 生成失败仅 ERROR 日志、列保持 NULL，不影响 scan 终态。
4. **存量回填接口** `POST /project/notice/scan/dependencyType/supplement`：入参 productNames（去空白去重，非空，上限 50）；对每个制品：查全部历史扫描 → 每次扫描的明细按名+版本匹配 SBOM 返回 → 批量 UPDATE（仅更新命中行）；完成后为**最新一次扫描**经确定性 objectKey 重建 direct 文件并回填列。同步执行；返回每制品回填明细数汇总。
5. **导出拆分**：`ProjectNoticeExportPo` / `ProjectNoticeBatchExportPo` 增加 `exportScope`（String，FULL/DIRECT，校验非法值报错，null 兼容为 FULL）。
   - 单制品 DIRECT：校验 `direct_merged_oss_url` 非空 → 按 direct objectKey 转存导出桶，任务置成功（保持同步返回契约）。
   - 批量 DIRECT：异步线程内按 direct objectKey 逐制品下载（缺失制品跳过），再走既有跨制品去重合并。

## 3. 类设计

| 类                                                                 | 操作      | 说明                                                                                                   |
| ------------------------------------------------------------------ | --------- | ------------------------------------------------------------------------------------------------------ |
| `common/enums/ProjectNoticeDependencyType.java`                    | 新增      | DIRECT(0)/INDIRECT(1)/DIRECT_INDIRECT(2)，含 `fromValue`                                               |
| `common/enums/NoticeExportScope.java`                              | 新增      | FULL/DIRECT，含 `parse`（null→FULL，非法→抛 ScaException）                                             |
| `analysis/entity/TblProjectNoticeScanDetail.java`                  | 修改      | 加 `dependencyType` 字段                                                                               |
| `analysis/entity/vo/ProjectNoticeScanDetailInfoVO.java`            | 修改      | 加 `dependencyType` 透出                                                                               |
| `analysis/entity/dto/ProjectNoticeExportPo.java`                   | 修改      | 加 `exportScope`                                                                                       |
| `analysis/entity/dto/ProjectNoticeBatchExportPo.java`              | 修改      | 加 `exportScope`                                                                                       |
| `analysis/entity/dto/ProjectNoticeDependencyTypeSupplementPo.java` | 新增      | 回填入参 productNames                                                                                  |
| `analysis/entity/vo/ProjectNoticeDependencyTypeSupplementVO.java`  | 新增      | 回填结果（每制品回填数/扫描数）                                                                        |
| `analysis/entity/dto/SbomPackageDependencyTypeDto.java`            | 新增      | SBOM 返回行镜像 DTO                                                                                    |
| `common/feign/OpenlibingSbomClient.java`                           | 修改      | 加 `queryPackageDependencyTypes`                                                                       |
| `dm/service/ProjectNoticeScanService.java`                         | 修改      | 加 `supplementDependencyTypes`、export 方法带 scope                                                    |
| `dm/service/impl/ProjectNoticeScanServiceImpl.java`                | 修改      | 回填实现（含最新扫描 direct 文件重建）+ 导出按 scope 转存                                              |
| `dm/service/impl/ProjectNoticeScanAsyncProcessor.java`             | 修改      | processScan / processSupplement 双文件生成（全量 + 直接依赖）                                          |
| `dm/dao/TblProjectNoticeScanDetailMapper.java` + XML               | 修改      | all_column/insert/batchInsert 加列；新增 `batchUpdateDependencyType`                                   |
| `dm/dao/TblProjectNoticeScanMapper.java` + XML                     | 修改      | 新增 `selectAllByProjectName`、`updateDirectMergedOssUrlByScanId`；all_column 加 direct_merged_oss_url |
| `dm/controller/ProjectNoticeScanController.java`                   | 修改      | 新增回填端点；export/exportBatch 传 scope                                                              |
| `resources/db/changelog/mysql/20261014/*.xml` + `db.changelog.xml` | 新增/修改 | 两个迁移脚本                                                                                           |

## 4. 数据模型设计

`tbl_project_notice_scan_detail` 新增：

```sql
ALTER TABLE tbl_project_notice_scan_detail
    ADD COLUMN dependency_type INT NULL COMMENT '依赖类型：0-直接依赖，1-间接依赖，2-直接&间接依赖，NULL-未补充（对齐SBOM package_statistics.dependency_type）';

ALTER TABLE tbl_project_notice_scan
    ADD COLUMN direct_merged_oss_url VARCHAR(1024) NULL COMMENT '直接依赖合并NOTICE文件OBS地址（扫描完成/补充重建/存量回填时生成，NULL-未生成）';
```

- 明细列可空，不破坏既有行与唯一键；scan 列可空，NULL 即"直接依赖文件未生成"语义。
- changeset id：`20261014-add-pnsd-dependency-type-<author>` / `20261014-add-pns-direct-merged-url-<author>`，preConditions `columnExists` MARK_RAN 幂等。

## 5. 性能设计

- SBOM 查询：每次扫描/每制品回填各 1 次 RPC，返回量 = 制品包数（数千级），内存 Map 匹配 O(n)。
- 回填 UPDATE：按扫描分批（每扫描一条批量 UPDATE），避免逐行 N 次往返。
- 双文件生成：direct 条目为全量条目的子集，合并为同一次遍历内的内存过滤，额外成本仅一次 OBS 上传；direct 生成失败不重试（导出时报错提示重新扫描/回填）。
- 存量回填的 direct 文件重建：仅针对最新一次扫描，经确定性 objectKey 逐明细下载（直接依赖量级，数百次小对象读取），同步执行属运维低频操作。
- 不新增高频查询路径，不加索引（无按 dependency_type / direct_merged_oss_url 查询场景）。

## 6. API 接口设计

### 6.1 回填接口（新增）

`POST /project/notice/scan/dependencyType/supplement`

```json
// 请求
{ "productNames": ["product-a", "product-b"] }

// 响应 data
{
  "results": [
    { "productName": "product-a", "scanCount": 3, "updatedCount": 1520 }
  ]
}
```

- 同步执行；productNames 去空白去重、非空校验；单次上限 50 个制品（防误用拖库）。
- SBOM 调用失败：该制品计 updatedCount=0 并在结果中带 reason，不影响其他制品。

### 6.2 导出接口（扩展）

- `POST /project/notice/scan/export`：请求体增加 `"exportScope": "FULL" | "DIRECT"`，可空默认 FULL。DIRECT 要求直接依赖合并文件已生成（未生成报"直接依赖NOTICE文件尚未生成，请先执行依赖类型补充或重新扫描"）。
- `POST /project/notice/scan/exportBatch`：同上，批量异步链路按 scope 转存对应文件（direct 文件缺失的制品跳过）。
- 非法取值返回失败 JSON（沿用 `ResponseEntity.failure` 风格）。

### 6.3 查询接口（透出）

- `POST /project/notice/scan/info`：明细列表每项新增 `dependencyType`（Integer，可空）。

## 7. 安全设计

- 回填接口为内部合规运维动作，与既有 `/supplement` 同级（无新增鉴权模型，沿用服务横向调用约定）。
- productNames 白名单化清洗：去空白、去重、上限 50，超限直接拒绝；无 SQL 拼接（MyBatis 参数化）。
- 导出 scope 仅两个合法枚举值，非法值显式报错，无注入面。
- 不涉及凭证、鉴权、用户输入文件路径，无新增敏感数据（dependency_type 为内部口径字段）。

## 跨仓影响

- `openlibing-sbom`：无改动（internal-api 已就绪，见 `InternalController#queryPackageDependencyTypes`，@since 2026/10/13）。
- 前端（openlibing-web）：/info 明细新增字段展示 + 导出入口增加范围选择（另行跟进，不属本仓）。

## 风险 & 缓解

| 风险                                                            | 缓解                                                                       |
| --------------------------------------------------------------- | -------------------------------------------------------------------------- |
| SBOM 未升级（无该 internal-api）时扫描降级路径                  | 调用异常仅 WARN，依赖类型置 NULL，扫描主流程不受影响；升级后跑回填接口补齐 |
| 存量明细 version=NOASSERTION 与 SBOM 行匹配不上                 | 匹配不上保持 NULL，属预期；不猜匹配避免错误标注                            |
| 历史扫描 direct 文件缺失（旧扫描无直接依赖文件、依赖类型 NULL） | 导出报错提示重新扫描；回填后仅最新扫描重建 direct 文件                     |
| direct 文件生成失败                                             | 仅告警、列保持 NULL、不影响 scan 终态与全量文件；导出侧显式报错            |
| 批量 DIRECT 导出耗时                                            | 复用既有异步批量导出线程池与任务状态机，受理即返回 taskId                  |
