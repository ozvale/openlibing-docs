# 评论触发 PR 自动评审开放接口 — 技术设计

## 方案概述

新增机机开放接口 `POST /open/review/auto-confirm`，复用既有提审/批复链路（`scanConfirmParseV3` + `autoPathReview`），但去掉 license/copyright 匹配过滤，实现"门禁阻塞 issue 强制提审 → 机器人批量批复 → 既有传播机制同步 → 下次扫描继承批复状态"的闭环，使评论触发的 PR 自动评审真正生效。

## 调用链路

```
sca-action (PR 评论触发)
  → POST /open/review/auto-confirm { prUrl, commentLogin }
    → TblPersonScanDMMapper.findLatestIdByPrUrl(prUrl)      # 仅取 scan_result='1' 的最新扫描
    → ConfirmReviewServce.robotAutoConfirm(scanId, commentLogin)
        → getDetailByScanId(scanId)                          # 全量未确认文档
        → 过滤 reviewStatus ∈ {空, 00(未提审), 10(审核中)}    # 20/30 不重提
        → scanConfirmParseV3(scanId, "person", toSubmit)     # 强制提审：建单或重绑既有待审单
        → autoPathReview(scanId, "person", reposId)          # 机器人批复 + 刷新门禁未确认数
        → 返回 { scanId, total, confirmed, remaining }
```

## 关键决策

1. **机机接口不做登录态鉴权，审核人由服务端固定**：调用方为 sca-action，接口不信任外部传入身份；机器人账号在服务端解密获取，`commentLogin` 仅审计留痕。风险与调用方约束见"风险与缓解"。
2. **不新增审核查询接口，合并为单一自动确认接口**：将原有三个机器接口的能力合并，调用方一次调用即完成提审+批复，避免多轮往返。
3. **按 `scan_result='1'` 过滤最新扫描**（`findLatestIdByPrUrl`）：避免选中进行中（0）或失败（1/失败态）的扫描导致按 scanId 查明细为空。
4. **`repo_id` 未回填时显式中止**：`repo_id` 在扫描行插入后异步回填，评论触发时刻可能尚未就绪；以 null 继续会导致 `selectIdByParam` 丢失仓库条件（跨仓库批复风险）或以 null `repo_id` 落库。抛 `ScaException(60000, ...)` 提示稍后重试。
5. **转审(20)/审核拒绝(30)不重新提审**：重复审核单会让 `autoPathReview` 的批复逻辑产生歧义，且会覆盖人工结论。
6. **N+1 查询修复**：`scanConfirmParseV3` 原先在循环内对每个文档逐条 `selectByParam` 查待审单；改为批量预查仓库全部待审核(10)审核单（`selectPendingByRepoId`），按 `scanFile` 分组后由 `matchPendingReviews` 复刻 `selectByParam` 的动态条件语义（sourceHash/fileHash 仅在文档侧非空时参与匹配）。
7. **避免重复全量查询**：`autoPathReview` 返回值由 `void` 改为 `int`（复用其内部 `getDetailByScanId` 结果返回批复后未确认数），`robotAutoConfirm` 不再第三次全量查询即可统计 `confirmed/remaining`。
8. **`ProcessScanIssueDto` 对 `pendingReviewsByFile` 做防御性拷贝**：setter/getter 均返回副本，避免批量预查结果在提审循环中被意外修改。

## 涉及文件

| 文件                                                   | 操作 | 说明                                                             |
| ------------------------------------------------------ | ---- | ---------------------------------------------------------------- |
| `analysis/controller/OpenConfirmReviewController.java` | 新增 | `POST /open/review/auto-confirm` 机机接口                        |
| `analysis/entity/dto/AutoConfirmPo.java`               | 新增 | 入参 DTO（prUrl + commentLogin）                                 |
| `analysis/service/ConfirmReviewServce.java`            | 修改 | 新增 `robotAutoConfirm`；`autoPathReview` 返回 `int`             |
| `analysis/service/impl/ConfirmReviewServceImpl.java`   | 修改 | `robotAutoConfirm` 实现、`matchPendingReviews`、提审链路批量预查 |
| `analysis/entity/ProcessScanIssueDto.java`             | 修改 | 新增 `pendingReviewsByFile`（防御性拷贝）                        |
| `dm/dao/TblPersonScanDMMapper.java`                    | 修改 | 新增 `findLatestIdByPrUrl`                                       |
| `dm/dao/TblConfirmReviewMapper.java`（+XML）           | 修改 | 新增 `selectPendingByRepoId`                                     |
| `ScanossShiledMapper.xml`                              | 修改 | 屏蔽查询兼容 `_gitcode` 仓库命名变体（附带修复）                 |
| `test/.../OpenConfirmReviewControllerTest.java`        | 新增 | controller 单测                                                  |
| `test/.../ConfirmReviewServceImplTest.java`            | 修改 | service 单测补充                                                 |

## 接口契约

`POST /open/review/auto-confirm`

| 字段         | 类型   | 必填 | 说明                             |
| ------------ | ------ | ---- | -------------------------------- |
| prUrl        | string | 是   | PR 页面 URL                      |
| commentLogin | string | 否   | 触发评论的用户登录名，仅审计留痕 |

返回：`scanId` + `total`（未确认总数）+ `confirmed`（本次批复通过数）+ `remaining`（未被机器人批复的剩余数，含审核人非机器人的待审单）。

## 风险与缓解

| 风险                                      | 缓解                                                                                                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 开放接口无登录态鉴权，可能被滥用批量批复  | 审核人由服务端固定为机器人；需网络层/网关侧限制调用来源（sca-action），后续可加内部 token（参考 `internal-auth-request-interceptor` 方案） |
| 评论触发时扫描尚未完成或 `repo_id` 未回填 | `findLatestIdByPrUrl` 仅取 `scan_result='1'`；`repo_id` 未回填时抛可重试异常                                                               |
| 强制提审可能批量产生大量审核单            | 仅处理空/00/10 状态文档；20/30 不重提；批复结果经既有传播机制同步，后续扫描按「归一化路径\|sourceHash\|fileHash」继承，不重复建单          |
| 越权处理人工审核单                        | `autoPathReview` 仅批复审核人为机器人的审核单，其余计入 `remaining`                                                                        |

## 跨仓影响

- 调用方 `sca-action` 需配合改造：评论触发时调用本接口（原三个机器接口合并为单一接口）。
- 无其他仓代码改动；批复状态同步复用 `openlibing-sca` 既有传播机制。
