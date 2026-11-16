# 流水线任务明细增加机器/资源池（Issue #343）

## 需求背景

工程能力运营看板 →「流水线执行明细」→ 行下钻的「任务明细」当前只展示任务名称、时长、状态、排队时长、调度时间、NPU 卡时，无法定位任务实际占用的机器与资源池；排障、资源核算与容量分析需要另行查询数仓。

## 功能描述

- 在任务明细接口（category `ops-pr-pipeline-job-detail`）的每条任务上新增 `machines` 成对数组：`[{serverIp, resourcePoolName}]`，一个任务可对应多台机器。
- IP 与资源池必须成对返回，多机场景下不得错位；数组为空表示无资源记录。
- 数据源：`dwi_rd_efc_resource_apply_info`，并限定 **`npu_num > 0`**，仅统计 NPU 申请，纯 CPU 构建/检查机器不再出现在该列。
- codearts 的申请 `job_id` 与统一 `job_id` 口径不同，需经 `sdi_rd_efc_pipeline_run_clean_codearts` 反查；gitcode/github 直接使用统一 `job_id`。
- 资源池名称来自机器静态维表 `sdi_rd_efc_server_machine_hidevlab`（同一 `server_ip` 可能多行，按 IP 去重取一个池名）。
- 机器查询与分页主查询解耦：按当页 jobIds 批量查询，不改变任务明细行数/总数/分页。
- 不做：历史数据回填、快照/实时值、权限与脱敏、筛选/排序/导出、华为云/实验室标签。

## 验收标准

- [x] 多机跨池时每条 IP 与其自身资源池配对正确、无错位
- [x] 同 job 同 IP 多条申请记录去重后只出现一次
- [x] 无资源记录的任务返回 `machines: []`
- [x] 有 IP 但机器维表查不到资源池时返回 `resourcePoolName: null`，不隐藏 IP
- [x] 改造前后任务明细行数与 `total` 完全一致
- [x] 同一任务多次请求、翻页后顺序一致（IPv4 四段数值序）
- [x] `server_ip` 为 null/空串/纯空格的记录被过滤
- [x] `npu_num > 0` 生效：纯 CPU 构建/检查机器不再出现在机器列

## 影响范围

- `openlibing-ops`：任务明细响应 DTO、Mapper 接口与 XML、Service、单元测试
- `openlibing-ops-web`：「机器/资源池」列需在包含 #294 任务明细组件的前端仓版本中补充（本次未落地，见 archive.md）
