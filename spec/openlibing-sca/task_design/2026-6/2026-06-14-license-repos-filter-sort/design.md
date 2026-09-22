## Context

### 调用链

```
GET /license/repos
  → LicenseController.getScanByCommunity(ScanCommunityDto)
  → LicenseServiceImpl.getScanByCommunity
      → tblScanMapper.getLicenseByCommunityWithFilter (SQL)
      → 去重 (repository+platform+branch)
      → [新增] filterByRepoResult
      → [调整] 全量 getStatsBatch + getScanResult
      → [调整] removeIf(repoHasLicense==null)
      → [新增] sortLicenseList + paginateList
```

### 前端契约（已实现）

`openlibing-web/.../communityList.vue` projectCompliance Tab：

| 参数 | 格式 | 示例 |
|------|------|------|
| `repoResult` | 逗号分隔多值 | `success,fail` |
| `sortColumn` | 列 prop | `scanTime`, `fileNum`, `compatibilityNumber`, ... |
| `sortOrder` | Element Plus 值 | `ascending`, `descending` |

状态值域：`success` 成功、`fail` 失败（`ResultType` 枚举，**非** open/scan/repos 的 `1/-1/0`）。

### 参考实现

已归档 `repos-scan-result-filter`（`GET /open/scan/repos`）采用内存 filter → sort → paginate，不改 SQL。本变更镜像该模式，差异在于参数名、值域、排序列集合，以及 license 路径需前移 MongoDB 统计。

### 现状瓶颈

当前 `getScanByCommunity` 在 **分页后** 才调用 `getStatsBatch`，`fileNum` 等字段仅当前页有值，无法实现全量服务端排序。必须将统计加载移到排序前。

## Goals / Non-Goals

**Goals:**

- 支持 `repoResult` query 参数，与前端 `join(',')` 格式一致
- 支持 `sortColumn` / `sortOrder` 服务端排序，覆盖前端五列
- 过滤/排序后 `list` 与 `total` 正确，分页可用
- 筛选可与排序叠加
- 单元测试覆盖 filter、sort、paginate 及组合场景

**Non-Goals:**

- 不改 SQL / Mapper XML
- 不引入 Redis 缓存（license 路径当前无列表缓存）
- 不修改 `open/scan/repos` 逻辑
- 不在本期做 `validator.yml` 白名单（可联调后按需补充）
- 不支持 `repo_result` 为「执行中」等第三状态（DB 枚举仅 success/fail）

## Decisions

### 1. DTO 扩展：`ScanCommunityDto` 新增三个 String 字段

```java
private String repoResult;   // 逗号分隔: success,fail
private String sortColumn;
private String sortOrder;
```

**理由**：与 `ScanCommunityReq` 对齐；Spring MVC query 绑定零配置；参数名 `repoResult` 与 VO 字段一致，区别于 open scan 的 `scanResult`。

### 2. 过滤：`filterByRepoResult` 私有方法

镜像 `OpenScanServiceImpl.filterByScanResult`：

- blank → 返回原 list
- `split(",")` + trim → `Set<String> allowed`
- `vo.getRepoResult() != null && allowed.contains(vo.getRepoResult())`
- 返回新 list，不 mutate 源 list

### 3. 流水线顺序（关键）

```java
List<LicenseInfoVO> list = mapper查询 + 去重;
list = filterByRepoResult(list, dto.getRepoResult());
// 全量统计（排序前）
getStatsBatch(全部 scanId) + getScanResult;
list.removeIf(vo -> vo.getRepoHasLicense() == null);
if (有 repoResult 筛选) { total = list.size(); } else { total = list.size(); }
List<LicenseInfoVO> page = sortAndPaginateLicenseData(list, dto);
```

**理由**：MongoDB 衍生字段排序依赖全量 stats；`removeIf` 在排序前执行，保证 total 与 list 一致。

### 4. 排序：`LicenseColumnList` + comparator Map

新建枚举（参考 `ScanColumnList`）：

| sortColumn (key) | 排序字段 |
|------------------|----------|
| `scanTime` | `licenseCreateTime`（Date，nullsLast） |
| `fileNum` | `fileNum`（Integer，null → 0） |
| `compatibilityNumber` | `compatibilityNumber` |
| `incompatibleNumber` | `incompatibleNumber` |
| `unrecognizedNumber` | `unrecognizedNumber` |

`sortOrder`：`descending` → `comparator.reversed()`（与 open scan 一致）。

**默认排序**（无 sortColumn/sortOrder）：`licenseCreateTime` 降序（替代现网固定 repository 中文升序，与前端「最新扫描时间」语义一致）。

**备选**：保留 repository 中文序为默认——与前端列展示不一致，不采用。

### 5. 分页：`paginateList` 内联或私有方法

与 `OpenScanServiceImpl.paginateList` 相同 subList 逻辑。

### 6. `total` 更新

始终使用经过 filter + removeIf 后的 list size（更准确）。有/无 `repoResult` 筛选均一致。

### 7. 不复用 `ScanColumnList`

openSource 与 projectCompliance 列集合不同，独立 `LicenseColumnList` 避免混淆。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 全量 MongoDB 聚合性能 | 与去重后 scanId 数量线性相关；大社区需联调观察；后续可 SQL/缓存优化 |
| 默认排序变更（repository → scanTime desc） | 无 sort 参数时列表顺序变化；PR 说明；与前端 UX 一致 |
| 历史脏数据（非 success/fail 的 repo_result） | 筛选不匹配则自然排除；可加 debug 日志 |
| `LicenseServiceImplTest` mock 使用 `repoResult("1")` | 测试一并修正为 `success`/`fail` |
| 导出顺序变化 | `fetchLicenseList` 复用同一方法，行为随新排序逻辑 |

## Migration Plan

1. 后端发版后，前端 projectCompliance 筛选/排序 UI 即可生效
2. 联调验收：未筛选 / 单选 / 多选 / 各列排序 / 筛选+排序 / total 正确 / 翻页
3. 回滚：移除 DTO 新字段与 filter/sort 逻辑，恢复 repository 固定排序

## Open Questions

1. 是否在 `validator.yml` 为 `repoResult` 增加白名单（`success,fail`）——建议联调通过后按需补充
2. 全量 MongoDB 聚合耗时是否需加监控阈值——联调阶段观察
