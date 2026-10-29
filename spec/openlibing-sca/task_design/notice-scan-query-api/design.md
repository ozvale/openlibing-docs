# notice-scan-query-api — 技术设计

## 方案概述

复用既有 Mapper 查询（`selectLatestByProjectName`、`selectByScanId`），在 Service 层完成实体到新 VO 的字段裁剪（剔除 `mergedOssUrl` / `readmeOssUrl`），Controller 层新增一个 POST 接口，响应中同时包含扫描记录字段与明细列表，沿用现有 try/catch + `ResponseEntity` 风格。

## 架构决策

- **单接口返回记录 + 明细列表**：调用方一次请求同时拿到扫描记录（除 `mergedOssUrl`）和明细列表（每条除 `readmeOssUrl`），避免两次往返。
- **不新增 SQL**：现有 `TblProjectNoticeScanMapper.selectLatestByProjectName` 与 `TblProjectNoticeScanDetailMapper.selectByScanId` 已满足查询需求，字段裁剪在 Java 层做，避免为"剔除单列"维护两套列清单 SQL。
- **新建 VO 而非直接返回实体**：`ProjectNoticeScanInfoVO` 承载总表字段（无 mergedOssUrl）并内嵌 `List<ProjectNoticeScanDetailInfoVO> details`（无 readmeOssUrl）；防止未来实体加字段时把 OBS 地址意外泄漏到响应。
- **查询语义沿用既有约定**：`productName` 只取最新一条扫描记录（与 `queryNotice`/`exportNotice` 一致）；记录存在但无明细时明细为空列表。
- Date 字段在 VO 中做防御性拷贝 getter/setter（与 `TblProjectNoticeScan` 实体一致，规避 SpotBugs EI_EXPOSE_REP）。

## 涉及文件

| 文件                                                      | 操作 | 说明                                         |
| --------------------------------------------------------- | ---- | -------------------------------------------- |
| `analysis/entity/vo/ProjectNoticeScanInfoVO.java`         | 新增 | 扫描总表 VO（无 mergedOssUrl）+ 内嵌明细列表 |
| `analysis/entity/vo/ProjectNoticeScanDetailInfoVO.java`   | 新增 | 扫描明细 VO，无 readmeOssUrl                 |
| `dm/service/ProjectNoticeScanService.java`                | 修改 | 新增 `queryScanInfo(productName)`            |
| `dm/service/impl/ProjectNoticeScanServiceImpl.java`       | 修改 | 实现（含明细 VO 转换私有方法）               |
| `dm/controller/ProjectNoticeScanController.java`          | 修改 | 新增 `/info` 接口                            |
| `src/test/java/.../ProjectNoticeScanServiceImplTest.java` | 修改 | 补充 service 层单测                          |
| `src/test/java/.../ProjectNoticeScanControllerTest.java`  | 修改 | 补充 controller 层单测                       |

## 接口定义

- `POST /project/notice/scan/export`，body：`{"productName": "...", "userId": "..."}` → `ResponseEntity<ProjectNoticeExportVO>`
- `POST /project/notice/scan/info`，body：`{"productName": "..."}` → `ResponseEntity<ProjectNoticeScanInfoVO>`（含 `details` 明细列表）

两个接口的入参均通过请求体传递，不使用 query 参数。

## 风险 & 缓解

- 扫描记录存在但无明细时返回空列表而非报错，前端需按空列表处理（proposal 已写入验收标准）。

## 跨仓影响

无。
