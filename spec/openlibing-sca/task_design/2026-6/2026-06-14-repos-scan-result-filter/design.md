## Context

### 调用链

```
GET /open/scan/repos
  → OpenScanController.getScanByCommunity(ScanCommunityReq)
  → OpenScanServiceImpl.getScanByCommunity
      → getCommunityDataFromCacheOrSource (Redis 或 DB)
      → sortAndPaginateData (排序 + 内存分页)
```

现有 `platform` / `repository` 过滤在 `getScanByCommunityJsonObject` 内以 Java stream 实现；`sortColumn` / `pageNo` 在更后置阶段处理。`scanResult` 数据已在 `TblScanMapper.getScanByCommunity` SQL 中映射为 `ScanInfoVO.scanResult`（列 `tbl_scan.scan_result`）。

### 前端契约（已实现）

`openlibing-web/apps/web-openlibing/src/views/sca/softInformation/communityList.vue`：

- 未筛选：不传 `scanResult`
- 多选：`scanResult=1,-1`（逗号分隔）
- 状态值：`1` 成功、`-1` 失败、`0` 执行中

## Goals / Non-Goals

**Goals:**

- 支持 `scanResult` query 参数，行为与前端透传格式一致
- 过滤后 `list` 与 `total` 正确，分页可用
- 筛选可与 `sortColumn` / `sortOrder` 叠加
- 最小改动：2 个 Java 源文件 + 1 个测试类

**Non-Goals:**

- 不改 SQL / Mapper XML
- 不把 `scanResult` 纳入 Redis 缓存 key
- 不修改 `totalCount` / `riskCount` 汇总逻辑
- 不处理 `repositoryType=person` 路径（该 SQL 未查 `scan_result`，与开源片段引用合规场景无关）

## Decisions

### 1. 参数类型：`String scanResult`（逗号分隔）

**选择**：`ScanCommunityReq` 新增 `private String scanResult`。

**理由**：与前端 `join(',')` 对齐；Spring MVC 零配置绑定；项目内有 `split(",")` 先例。

**备选**：`List<String>` — 需自定义 converter，改动更大。

### 2. 过滤位置：缓存后、`sortAndPaginateData` 前

```java
List<ScanInfoVO> list = (List<ScanInfoVO>) jsonObject.get("list");
list = filterByScanResult(list, scanCommunityReq.getScanResult());
if (StringUtils.isNotBlank(scanCommunityReq.getScanResult())) {
    jsonObject.put("total", CollectionUtils.isEmpty(list) ? 0 : list.size());
}
List<ScanInfoVO> page = sortAndPaginateData(list, scanCommunityReq);
jsonObject.put("list", page);
```

**理由**：与 `sortColumn`/`pageNo` 同层后置处理；不同 `scanResult` 可复用同一份 Redis 列表缓存。

### 3. 过滤实现：`filterByScanResult` 私有方法

- 空/blank `scanResult` → 原样返回
- `split(",")` + trim → `Set<String> allowed`
- `vo.getScanResult() != null && allowed.contains(vo.getScanResult())`
- 不匹配 null scanResult 的记录

### 4. `total` 更新策略

有 `scanResult` 筛选时，将 `JSONObject.total` 更新为过滤后列表 size，供前端 `pagesConfig.total` 使用。

`totalCount` / `riskCount` 不随筛选变化（社区级 Redis 汇总，与前端 design Open Question 默认一致）。

### 5. Redis 缓存 key 不变

`buildCacheKey(community, repositoryType, platform)` 不含 `scanResult`。筛选在缓存命中后的 list 上执行，与分页/排序策略一致。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 大社区全量 list 内存过滤性能 | 与现有 platform/repository 策略一致；后续可 SQL 优化 |
| `scanResult` 非法值 | 空 set 视为不过滤；可选 validator.yml 校验 |
| person 扫描路径无 scanResult 字段 | 本需求仅覆盖 openSourceCompliance version 路径 |
| 缓存 JSONObject 被原地修改 | `filterByScanResult` 返回新 list，不 mutate 缓存内对象（或 copy 后再 filter） |

**缓存安全**：从 `jsonObject.get("list")` 取 list 后应在新 list 上操作，避免污染 Redis 中缓存的原始全量 list。实现时使用 `stream().filter().collect(toList())` 产生新列表。

## Migration Plan

1. 后端发版后，前端已有筛选 UI 即可生效
2. 联调验收：未筛选 / 单选 / 多选 / 筛选+排序 / total 正确
3. 回滚：移除 `ScanCommunityReq.scanResult` 与 filter 逻辑，行为恢复现网

## Open Questions

1. 是否在 `validator.yml` 为 `scanResult` 增加白名单校验（`1,-1,0`）——建议联调通过后按需补充
