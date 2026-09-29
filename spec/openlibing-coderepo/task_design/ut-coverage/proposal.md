# UT 覆盖率上报与分支管理页展示

## 需求背景

平台需要汇总各代码仓分支的 UT（单元测试）覆盖率数据，作为分支质量指标之一。当前 coderepo 只有代码度量（code metrics）指标，缺少 UT 覆盖率数据的接收、存储与展示链路，CI 插件产出的覆盖率结果无法沉淀到平台。

## 功能描述

### 做什么

三仓跨仓需求：

**1. coderepo（后端）**

- 新增机机接口 `POST /coverage/ut/report`：接收 `{gitUrl, branchName, pipelineRunId, obsUrl}`，投递 MQ 异步解析（对齐 code metrics 的 OBS + MQ 模式）
- 新增 MQ 队列 `ut_coverage_import_queue` 与消费者，从 OBS 下载标准格式 JSON，解析后入库
- 存储复用 `code_metrics_record` 表，新增 UT 字段：
  - `record_type` VARCHAR(20)：区分 `code_metrics` / `ut_coverage`
  - `line_coverage` / `branch_coverage` / `method_coverage` / `class_coverage` DECIMAL(5,2)
  - `coverage_file_detail_json` LONGTEXT：文件级明细（供下钻）
- 分支管理接口联动：`/repo/branch/list` 返回各分支最新 UT 覆盖率
- 现有 code metrics 查询（`selectLatestByGitUrl(s)`）加 `record_type` 过滤（兼容存量 `IS NULL`），避免 UT 记录污染现有指标
- ObsBucketService.downloadToTempFile 扩展放行 UT 前缀

**2. web（前端）**

- 分支管理页新增「UT覆盖率」列，显示行覆盖率主指标（如 85.3%）
- 点击下钻弹窗：展示 4 个总体指标（line/branch/method/class）+ 文件级明细列表（分页）

**3. openlibing-ut-coverage-action（新插件仓）**

- 新建独立插件仓，复用 openlibing-upload-sarif 的 OIDC/OBS/APIG 回调基础设施
- 支持工具报告格式解析（用户指定目录自动扫描识别）：gcov/llvm-cov、coverage.py、go test、jacoco、cargo-llvm-cov、c8
- 解析 → 转标准 JSON（4 总体指标 + fileDetails 文件明细数组）→ 上传 OBS → 回调 coderepo `/coverage/ut/report`

### 不做什么

- 不修改 UT 覆盖率之外的其他指标
- 不做覆盖率历史趋势图（当前仅最新值 + 文件明细下钻）
- 不改造现有 code metrics 的 OBS/MQ 链路（仅扩展前缀放行与查询过滤）
- 不建新表（主表复用 + JSON 明细字段）

## 验收标准

- [ ] coderepo 新增机机接口与 MQ 异步消费，UT 覆盖率数据可入库
- [ ] code_metrics_record 新增 UT 字段（record_type + 4 覆盖率 + 明细 JSON），Liquibase 迁移生效
- [ ] 现有 code metrics 查询不受 UT 记录影响（record_type 过滤）
- [ ] `/repo/branch/list` 返回各分支最新 UT 覆盖率（含 pipelineRunId）
- [ ] web 分支管理页展示 UT 覆盖率列，点击下钻可见 4 指标 + 文件级明细
- [ ] 插件可解析 6 种工具报告，转标准 JSON 上传 OBS 并回调 coderepo 接口

## 影响范围

| 仓                            | 模块                                                 | 说明                               |
| ----------------------------- | ---------------------------------------------------- | ---------------------------------- |
| openlibing-coderepo           | controller / service / mapper / mq / obs / liquibase | 新增接口、消费者、表字段、查询过滤 |
| openlibing-web                | Repos/branches.vue + dialog + api                    | 新增列与下钻弹窗                   |
| openlibing-ut-coverage-action | 新插件仓                                             | 报告解析 + 转换 + OBS 上传 + 回调  |
