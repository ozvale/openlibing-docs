# Design: review-propagate-person-scan-count

- **业务 Issue**: openlibing/openlibing-sca#87（反馈轮次）
- **业务分支**: `ms_succeed`

## 1. 方案总览

批复/撤销传播已能定位「申请时间之后全部扫描」的继承文档并回写 mongo，缺的是这些扫描在 `tbl_person_scan.un_confirmed_file_num` 上的计数重算。方案：让传播过程中的 scope 解析同时产出 **PR 扫描 scanId 子集**，在 mongo 批量更新落库后按 scanId 逐个重算。

```text
patchReview ─► updateIssueData ─► appendInheritScanPropagation ─┬─ mongoUpdates（继承文档回写，既有）
                                                                └─ affectedPersonScanIds（新增收集）
                              ─► executeUpdate（mongo bulk 落库，既有）
                              ─► refreshPersonScanUnConfirmedNum（新增：逐 scanId 重算）

patchRevoke ─► 循环 propagateRevokeToInheritScans ─┬─ updateMulti（继承文档重置，既有）
                                                   └─ affectedPersonScanIds（新增收集）
            ─► 循环结束后 refreshPersonScanUnConfirmedNum（新增）
```

## 2. 关键设计点

### 2.1 scope 二元组（InheritScanScope record）

`resolveInheritScanIds` 原本只返回合并 scanId 列表（版本扫描 + PR 扫描混排），无法区分哪些是 `tbl_person_scan` 行。引入私有 record：

```java
private record InheritScanScope(List<String> scanIds, List<String> personScanIds) {}
```

- `scanIds`：mongo 传播查询用（`scanId $in` + fileHash + reviewStatus in (10,20)），语义与原实现一致；
- `personScanIds`：仅来自 `tblPersonScanDMMapper.findByRepoIdAndCreatedAfter` 的结果，专供计数刷新，天然不会误刷版本扫描。

缓存 `Map<String, List<String>>` 升级为 `Map<String, InheritScanScope>`，cacheKey 不变（`boundScanId|applyTimeMillis`），批复批次/撤销批次内仍复用。

### 2.2 刷新时机

必须在 mongo 批量更新**之后**（`executeUpdate` / `updateMulti` 返回后），否则 `getPendingRisksNum`（按 reviewStatus != 40 计数）读到旧状态，重算结果错误。

### 2.3 计数口径

复用 `openScanDMService.uploadUnConfirmFileNum(scanId)`（`getPendingRisksNum(scanId, "10")` → mongo count），与页面刷新入口 `/refresh/confirmNum/V2`、`autoPathReview` 的重算语义一致。**不再**使用历史上被移除的 `getDetailByScanId().size()` 口径（f9ec1d40 教训：口径不一致导致数字漂移）。

### 2.4 收集条件与幂等

- 仅当该审核单**实际命中继承文档**（`inheritIds` 非空）时收集 personScanIds——未命中则这些扫描的计数本就不会变化，避免无谓的逐扫描 count 查询；
- 批内多次收集用 `Set` 去重；同一 scope key 的多个审核单共享缓存。

### 2.5 失败语义

`refreshPersonScanUnConfirmedNum` 逐 scanId try/catch：单个失败只记 `LOGGER.error`，继续下一个，不影响批复/撤销事务（传播本身也是 best-effort，见 26ade1f1）。

## 3. 涉及文件（2 个）

| 文件                                                 | 变更                                                                                                                                                                                                                                                                         |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `analysis/service/impl/ConfirmReviewServceImpl.java` | 新增 `InheritScanScope` record、`resolveInheritScanScopeCached`/`buildScanScope`/`refreshPersonScanUnConfirmedNum`；`appendInheritScanPropagation`/`propagateRevokeToInheritScans` 增加 personScanIds 收集参数；`resolveInheritScanIds` 改造为返回 scope；两处调用点接入刷新 |
| `ConfirmReviewServceImplTest.java`                   | 既有批复/撤回传播用例补 verify（刷新命中、版本扫描不刷）；无传播目标用例补 never verify；新增刷新失败不阻断用例                                                                                                                                                              |

## 4. 风险与缓解

| 风险                                    | 缓解                                                                                      |
| --------------------------------------- | ----------------------------------------------------------------------------------------- |
| 申请时间之后扫描数很多时逐个 count 变慢 | 复用 scope 缓存；扫描数受「申请后同仓扫描数」约束，通常个位数；与页面刷新单扫描成本同量级 |
| 刷新失败导致计数仍旧                    | 失败记日志；下次批复/自动批复/页面刷新仍会重算（自愈）                                    |
| 误刷版本扫描                            | personScanIds 仅来源于 tbl_person_scan 查询结果                                           |

## 5. 跨仓影响

无。
