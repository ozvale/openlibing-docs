# 版本扫描批量操作 - 技术设计

## 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                    openlibing-sca                         │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │          ManualVersionScanController                 │ │
│  │  POST /version/scan/startVersionScan                │ │
│  │     Body: List<ManualVersionScanStartPo>             │ │
│  │     Response: List<ManualVersionScanStartResultVO>   │ │
│  │                                                     │ │
│  │  POST /version/scan/deleteByIds                     │ │
│  │     Body: List<String>                              │ │
│  │     Response: int (deleted count)                   │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │          ManualVersionScanServiceImpl                │ │
│  │  startScan(List<StartPo>) → List<ResultVO>:          │ │
│  │    for each startPo:                                 │ │
│  │      try startSingleScan(startPo)                    │ │
│  │      → ResultVO { success=true, scanId }             │ │
│  │      catch ScaException                              │ │
│  │      → ResultVO { success=false, errorMsg }          │ │
│  │      catch Exception                                 │ │
│  │      → ResultVO { success=false, errorMsg }          │ │
│  │                                                     │ │
│  │  startSingleScan(startPo):                           │ │
│  │    1. 校验 repoId/branchId 非空                      │ │
│  │    2. 查 tbl_manual_version_scan                     │ │
│  │    3. 查 repo_info                                   │ │
│  │    4. 调 integrationApiService.startVersionScan      │ │
│  │    5. 更新 scan_status=SCANNING                      │ │
│  │                                                     │ │
│  │  deleteByIds(List<String>):                          │ │
│  │    空/null → return 0                                │ │
│  │    非空 → mapper.deleteByIds(ids)                    │ │
│  └──────────────────────┬──────────────────────────────┘ │
│                         │                                │
│  ┌──────────────────────▼──────────────────────────────┐ │
│  │          TblManualVersionScanMapper                  │ │
│  │  + deleteByIds(@Param("ids") List<String>)           │ │
│  │    DELETE FROM tbl_manual_version_scan               │ │
│  │    WHERE id IN (?, ?, ...)                           │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 模块设计

### 1. 变更文件清单

| 文件                                    | 变更类型    | 职责                                                                     |
| --------------------------------------- | ----------- | ------------------------------------------------------------------------ |
| `ManualVersionScanController.java`      | 修改 + 新增 | startScan 入参改为 List；新增 deleteByIds 端点                           |
| `ManualVersionScanService.java`         | 修改 + 新增 | startScan 签名改为批量；新增 deleteByIds 方法声明                        |
| `ManualVersionScanServiceImpl.java`     | 修改 + 新增 | 批量 startScan 逐条执行+异常隔离；提取 startSingleScan；新增 deleteByIds |
| `ManualVersionScanStartResultVO.java`   | 新增        | 批量触发单条结果 VO（repoId, branchId, scanId, success, errorMsg）       |
| `TblManualVersionScanMapper.java`       | 新增        | 新增 deleteByIds 方法                                                    |
| `TblManualVersionScanMapper.xml`        | 新增        | 新增 deleteByIds SQL（MyBatis foreach IN）                               |
| `ManualVersionScanControllerTest.java`  | 修改 + 新增 | 批量/空列表/异常测试；新增 deleteByIds 测试                              |
| `ManualVersionScanServiceImplTest.java` | 修改 + 新增 | 批量部分失败；空/null 列表；deleteByIds 测试                             |

### 2. ManualVersionScanStartResultVO

```java
@Data
@NoArgsConstructor
public class ManualVersionScanStartResultVO {
    private Integer repoId;      // 仓库ID
    private Integer branchId;    // 分支ID
    private String scanId;       // 扫描ID（成功时返回）
    private Boolean success;     // 是否成功
    private String errorMsg;     // 错误信息（失败时返回）
}
```

### 3. startScan 批量触发核心逻辑

```
startScan(List<ManualVersionScanStartPo> startPoList):
  1. 初始化 results = empty List
  2. if startPoList == null || isEmpty: return empty results
  3. for each startPo in startPoList:
     3.1 创建 ResultVO, set repoId, branchId
     3.2 try:
         scanId = startSingleScan(startPo)   // 复用原单条逻辑
         result.setScanId(scanId)
         result.setSuccess(true)
     3.3 catch ScaException:
         result.setSuccess(false)
         result.setErrorMsg(errorMsg + ": " + adviceMsg)  // 拼接建议
         LOG.warn(...)
     3.4 catch Exception:
         result.setSuccess(false)
         result.setErrorMsg(ex.getMessage())
         LOG.error(...)
     3.5 results.add(result)
  4. return results
```

### 4. startSingleScan 单条触发逻辑（从原 startScan 提取）

```
startSingleScan(startPo):
  1. if repoId == null || branchId == null:
       throw ScaException("仓库ID和分支ID不能为空")
  2. existing = mapper.selectByRepoIdAndBranchId(repoId, branchId)
     if null: throw ScaException("该仓库分支未添加，请先添加仓库")
  3. repoInfo = repoInfoMapper.queryById(repoId)
     if null: throw ScaException("仓库信息不存在")
  4. 构建 VersionScanPo { repoUrl, branch, projectName }
  5. scanId = integrationApiService.startVersionScan(versionScanPo, true)
  6. 更新 scanStatus = SCANNING, scanTime = now
  7. return scanId
```

### 5. deleteByIds 批量删除逻辑

```
deleteByIds(List<String> ids):
  1. if ids == null || isEmpty: return 0
  2. deleted = mapper.deleteByIds(ids)
  3. LOG.info("deleteByIds success, requested={}, deleted={}")
  4. return deleted
```

### 6. MyBatis SQL

```xml
<delete id="deleteByIds">
    DELETE FROM tbl_manual_version_scan
    WHERE id IN
    <foreach collection="ids" item="id" open="(" close=")" separator=",">
        #{id}
    </foreach>
</delete>
```

## 关键设计决策

| 决策点                    | 方案                                              | 原因                                                          |
| ------------------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| 批量失败隔离              | 单条 catch 异常后继续，不抛全局异常               | 批量操作中单条失败不应阻断其他条                              |
| 单条逻辑复用              | 提取 `startSingleScan` 私有方法                   | 避免重复代码，单条逻辑仍是异常抛出语义，批量层做异常转 Result |
| 错误信息拼接              | ScaException 时拼接 `errorMsg + ": " + adviceMsg` | 给调用方提供完整的失败原因和修复建议                          |
| 空/null 列表处理          | 空/null 直接返回空结果/0，不抛异常                | 前端可能传入空选择，应静默处理                                |
| 接口入参从单对象改为 List | 不新开批量端点，直接改造原端点                    | 保持接口简洁，前端传单对象时包装为单元素 List 即可            |

## 影响范围

- **接口变更**（破坏性）：
  - `POST /version/scan/startVersionScan` 入参从 `ManualVersionScanStartPo` 变为 `List<ManualVersionScanStartPo>`，返回从 `String` 变为 `List<ManualVersionScanStartResultVO>`
- **MySQL 表**: `tbl_manual_version_scan`（新增 `DELETE` 操作）
- **新增 VO**: `ManualVersionScanStartResultVO`
- **Mapper**: 新增 `deleteByIds` 方法和对应 SQL
- **单元测试**: 覆盖批量多条目、空列表、部分失败、批量删除等场景
