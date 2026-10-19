# notice-scan-batch-export

## 需求背景

NOTICE 单制品导出（`/export`）一次只能导出一个制品的声明文件。用户需要一次选中多个制品，把各制品已生成的 NOTICE 文件从 OBS 下载后合并为一个文件导出，避免逐个导出再手工拼接；不同制品包含相同软件时需去重。

## 功能描述

在 `ProjectNoticeScanController` 新增接口 `POST /project/notice/scan/exportBatch`：

1. 入参：`productNames` 集合（body）+ `userId`（query，导出任务创建者，与 `/export` 一致）。
2. 入参去空白、去重；逐制品查 `tbl_project_notice_scan` 最新记录获取下载地址（按既有 `/export` 的对象 key 规则定位 NOTICE 桶对象，`merged_oss_url` 为带时效签名 URL 仅作存在性判断）。
3. 未发起过扫描或 NOTICE 未生成的制品跳过继续；全部缺失时拒绝导出（不创建任务）。
4. **异步**：创建 framework 统一导出任务后立即返回 `taskId`；后台线程逐制品下载 OBS 文档 → 按 `Software: <名> <版本>` 段落解析 → 跨制品段落去重（同软件同版本保留首次出现）→ License 全文跨制品去重（复用 `NoticeMerger.collapseDuplicateLicenses`）→ 尾部下载地址表按（名称,版本）去重合并 → 写临时文件上传导出桶 → 任务置导出成功/失败。
5. 不设制品数量上限（已确认，内存风险记录于 design）。

不做的事情：

- 不修改既有 `/export`、`/supplement`、`/info` 接口行为。
- 不新增数据库表/字段、不修改 Liquibase。
- 不做 markdown 解析以外的内容改写（各软件段落内容原样保留，仅做去重）。

## 验收标准

- [ ] 传入多个 productName，返回 `{exportTaskId, fileName, message="导出任务已创建"}`；任务完成后《我的导出》可下载合并文件。
- [ ] 合并文件结构 = 头部声明 + 各制品软件段落（跨制品同软件同版本仅一份）+ GPLv2 声明 + 去重后的下载地址表。
- [ ] 跨制品相同 License 的 Full License Text 仅首次保留，后续替换为 `Please see above`。
- [ ] 未扫描/未生成 NOTICE 的制品被跳过，成功任务信息注明跳过数量；全部缺失时业务失败且不产生导出任务。
- [ ] 后台失败时导出任务置为失败，不留下"成功但无文件"的任务。
- [ ] 单测覆盖合并器（段落/表格去重、License 去重、异常文档跳过）与服务层（校验/部分跳过/全部缺失/后台成功与失败路径）；全量测试通过。

## 影响范围

- 业务仓：`openlibing-sca`（dm 模块 controller/service/impl + dm/util 新增合并器 + executor 增强下载/上传方法 + analysis dto），约 300 行（含单测）。
- 不涉及其他仓、数据库迁移、部署配置变更（新增可选配置项 `sca.notice.export.*` 如需要再补）。
