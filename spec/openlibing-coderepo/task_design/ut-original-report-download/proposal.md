# UT 覆盖率原始报告下载

| 项          | 内容                                                                |
| ----------- | ------------------------------------------------------------------- |
| FE 需求名称 | 【openLiBing】UT原始报告下载能力建设                                |
| 业务 Issue  | https://gitcode.com/openlibing/openlibing-coderepo/issues/276       |
| 改动范围    | openlibing-coderepo（后端）、openlibing-web（前端）                 |
| 详细设计    | [design.md](./design.md)（2026-11-02 评审通过，D1–D5 决策全部采纳） |

## 需求背景

UT 覆盖率插件上报的原始报告 JSON 存放在 OBS 桶 `openlibing-gitcode-action/ut-coverage-action/` 下，但 `/ut/coverage/report` 仅把 `obsUrl` 用作一次性入参（下载解析后即丢弃），**未持久化**；`/ut/coverage/file-detail` 只能看到解析入库后的文件级明细。痛点：

1. 明细页仅展示 filePath/lineCoverage/lineCovered/lineTotal 四列，解析入库丢掉的字段无法回看；
2. 问题排查（如"明细与总量对不上"）需要原始 JSON 比对，目前只能找运维捞 OBS；
3. 离线分析、审计无原始数据入口。

## 功能描述

上报时多落一列原始报告位置（`code_ut_record.original_report_obs_url`）；下载时把"原始报告从源桶转存到导出桶"做成一次**幂等的导出任务**，任务登记与状态托管全部复用 framework 导出中心（`/export/internal-server/create|update|query` + 导出桶 `obs.export.bucket` + 签名 URL），前端轮询拿到签名 URL 触发下载。

- 详情页新增"下载原始报告"按钮：无原始报告（历史记录）置灰带提示；提交即返回，进度与下载由框架全局「导出任务」浮层托管（自动下载 / 重新下载 / 失败原因透出）
- 幂等：`identifier = ut-original-report:{recordId}`，未完成任务复用、已完成复用返回原 ID，仅 FAILED 允许重建
- 权限：复用 `UT_COVERAGE_FILE_DETAIL` 权限点，不新增权限项

**不做什么**：不回溯补齐历史记录的原始报告 URL；coderepo 不新建轮询接口（前端直轮 framework `/export/detail`）；不重新打包/压缩原始文件（byte-for-byte 原样转存）。

## 验收标准

- [ ] 新上报一条 UT 覆盖率 → `code_ut_record.original_report_obs_url` 非空且等于插件传的 obsUrl
- [ ] 历史记录（列为 NULL）：按钮置灰带提示；接口提交返回「无原始报告」明确文案
- [ ] 点击下载：任务创建 → 框架「导出任务」浮层呈现进度 → 成功自动下载，文件内容与源桶对象 byte-for-byte 一致
- [ ] 连续快速点击 N 次：同 identifier 仅 1 条进行中任务，无重复转存执行
- [ ] 人工删除源对象后再点击：任务 FAILED 且前端展示失败原因
- [ ] 无明细查看权限的用户调提交接口：被拒绝

## 影响范围

| 仓                  | 改动摘要                                                                                                                                                                                                                         |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| openlibing-coderepo | db.changelog 加列；上报落库 1 行；`UtOriginalReportExportService`/`ExportProducer`/MQ 消费者/`FrameworkExportClient`（唯一 contextId）+ 4 个导出 DTO + `ExportStatus` 枚举；Controller 1 个提交端点；file-detail VO 加字段；单测 |
| openlibing-web      | UT 覆盖率详情页新增"下载原始报告"按钮 + 提交调用（状态呈现复用框架导出浮层，页面不自建轮询）                                                                                                                                     |
