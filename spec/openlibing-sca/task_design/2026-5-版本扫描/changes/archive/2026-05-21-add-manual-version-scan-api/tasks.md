# Tasks: Add Manual Version Scan API

## Task 1: Create TblManualVersionScan Entity ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/entity/TblManualVersionScan.java`

- [x] 创建实体类，字段与 `tbl_manual_version_scan` 表对应
- [x] 使用 `@Data` + `@NoArgsConstructor`
- [x] Date 字段加 `@JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")`
- [x] 字段：id(Integer), communityId(String), repoUrl(String), repoName(String), repoId(String), branch(String), scanResult(Integer), platform(String), scanId(String), isScan(Integer), created(Date), modified(Date), scanTime(Date)

## Task 2: Create TblManualVersionScanMapper Interface ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/dao/TblManualVersionScanMapper.java`

- [x] 创建 Mapper 接口，标注 `@Mapper`
- [x] 方法：insert, deleteByPrimaryKey, selectByPrimaryKey, selectByCondition, updateByPrimaryKey, updateScanResult, updateByScanId
- [x] `updateByScanId` 为新增方法，需在 XML 中同步添加

## Task 3: Add updateByScanId to Mapper XML ✅

**文件**: `src/main/resources/mapper/analysis/TblManualVersionScanMapper.xml`

- [x] 新增 `updateByScanId` SQL：通过 scan_id 更新 scan_result 和 modified
- [x] SQL: `UPDATE tbl_manual_version_scan SET scan_result = #{scanResult}, modified = NOW() WHERE scan_id = #{scanId}`

## Task 4: Create ManualVersionScanService Interface ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/ManualVersionScanService.java`

- [x] 接口方法：
  - `void add(TblManualVersionScan record)`
  - `List<TblManualVersionScan> list(TblManualVersionScan condition)`
  - `void deleteById(Integer id)`
  - `String startScan(Integer id, String repoUrl, String branch, String projectName)`

## Task 5: Create ManualVersionScanServiceImpl ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/ManualVersionScanServiceImpl.java`

- [x] `@Service("manualVersionScanService")`
- [x] 注入 `TblManualVersionScanMapper` 和 `IntegrationApiService`
- [x] `add()`: 设置 created/modified 为当前时间，调用 mapper.insert
- [x] `list()`: 调用 mapper.selectByCondition
- [x] `deleteById()`: 调用 mapper.deleteByPrimaryKey
- [x] `startScan()`:
  1. 构建 `VersionScanPo(repoUrl, branch, projectName)`
  2. 调用 `integrationApiService.startVersionScan(po)` 获取 scanId
  3. 查询记录，设置 scanId、scanResult=0、modified=now、scanTime=now
  4. 调用 mapper.updateByPrimaryKey 更新
  5. 返回 scanId

## Task 6: Create ManualVersionScanController ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/controller/ManualVersionScanController.java`

- [x] `@RestController` + `@RequestMapping("/manual/version/scan")`
- [x] 注入 `ManualVersionScanService`
- [x] 4 个接口，均遵循 try-catch 三段式（ScaException + Exception）
- [x] POST `/add` → add
- [x] POST `/list` → list
- [x] POST `/delete` → delete
- [x] POST `/start` → startScan

## Task 7: Modify saveVersionScanResult for Callback ✅

**文件**: `src/main/java/com/openlibing/sca/dm/service/impl/IntegrationApiServiceImpl.java`

- [x] 注入 `TblManualVersionScanMapper`
- [x] 在 `saveVersionScanResult` 方法中，`tblScanDMMapper.upload(scan)` 之后，新增：
  - 调用 `tblManualVersionScanMapper.updateByScanId(scanRequestVO.getScanId(), 1)`
  - 更新 `tbl_manual_version_scan` 中 scan_id 匹配的记录：scanResult=1, modified=NOW()

## Task 8: Modify IntegrationApiListener for Error Callback ✅

**文件**: `src/main/java/com/openlibing/sca/common/config/rabbitmq/IntegrationApiListener.java`

- [x] 注入 `TblManualVersionScanMapper`
- [x] 在异常处理路径中（设置 scanResult=-1 的位置），新增：
  - 调用 `tblManualVersionScanMapper.updateByScanId(scanId, -1)`
  - 同步更新 `tbl_manual_version_scan` 的 scanResult=-1, modified=NOW()
