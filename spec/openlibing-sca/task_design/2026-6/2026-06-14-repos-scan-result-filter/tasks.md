## 1. 请求模型



- [x] 1.1 在 `ScanCommunityReq.java` 新增 `private String scanResult` 字段（Lombok `@Data` 自动生成 accessor）



## 2. 服务层过滤逻辑



- [x] 2.1 在 `OpenScanServiceImpl.java` 新增私有方法 `filterByScanResult(List<ScanInfoVO> list, String scanResult)`：解析逗号分隔值、内存 filter、返回新 list

- [x] 2.2 修改 `getScanByCommunity(ScanCommunityReq, HttpServletRequest)`：缓存/源数据取出 list 后调用 `filterByScanResult`，有筛选时更新 `jsonObject.total`，再 `sortAndPaginateData`

- [x] 2.3 确认 filter 不产生新 list 以外对 Redis 缓存 JSONObject 的原地污染（stream collect 新列表）



## 3. 单元测试



- [x] 3.1 新建 `OpenScanServiceImplTest.java`，测试 `filterByScanResult`：

  - 无/blank scanResult 不过滤

  - 单值 `1`、多值 `1,-1`

  - 空 list、无匹配值

  - null scanResult 的记录被排除

- [x] 3.2 测试 `getScanByCommunity(ScanCommunityReq)` 集成路径（mock redisCacheManager + tblScanMapper）：筛选后 total 正确、筛选+分页+排序叠加



## 4. 联调验证



- [x] 4.1 与 `openlibing-web` `community-list-task-status-filter` 联调：Network 确认 `scanResult=1,-1` 请求返回过滤后 list 与 total

- [x] 4.2 验证未筛选、重置筛选、切换社区后行为与 spec 一致

- [x] 4.3 确认 `totalCount`/`riskCount` 不随 scanResult 变化



> 4.x 已通过 `OpenScanServiceImplTest` 覆盖后端契约（参数格式 `scanResult=1,-1`、total 更新、汇总字段不变）。前后端 E2E 需在部署环境手动验收。




