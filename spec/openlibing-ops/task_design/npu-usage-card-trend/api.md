# 卡数趋势 — 前端接口文档

> 后端 commit：`713f8938`（申请卡数）/ `b1b48add`（等待卡数口径修正）/ `672c960c`（新增接口）/ `f499cc46`（使用卡数改取运行任务真实申请卡数）/ `0e23ebaf`（三条曲线统一数据源，总卡数 = 使用卡数 + 等待卡数），openlibing-ops 分支 `usage_analyse_1030`
> 关联 Issue：[#300](https://gitcode.com/openlibing/openlibing-ops/issues/300)（父需求 [#208](https://gitcode.com/openlibing/openlibing-ops/issues/208) 第三点「使用率页面」）

## 1. 接口

| 项 | 值 |
|------|------|
| 路径 | `POST /common/chart`（网关前缀 `/gateway/openlibing-ops`） |
| Content-Type | `application/json` |
| 用途 | 「卡数趋势」单张图：总卡数 / 使用卡数 / 等待卡数三条曲线 |

与「趋势分析」走同一个通用图表接口，仅 `category` 不同；请求/响应结构与既有 `ops-npu-usage-trend` 完全一致。

## 2. 请求

```json
{
  "category": "ops-npu-usage-card-trend",
  "startTime": "2026-09-02 00:00:00",
  "endTime": "2026-09-04 23:55:00",
  "projectId": 123,
  "resourcePoolIds": [1, 2]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category` | string | 是 | 固定 `ops-npu-usage-card-trend` |
| `startTime` | string | 是 | `yyyy-MM-dd HH:mm:ss` |
| `endTime` | string | 是 | `yyyy-MM-dd HH:mm:ss`，与 `startTime` 间隔 **≤ 72 小时** |
| `projectId` | number | 否 | 项目 ID，为空统计全部 |
| `resourcePoolIds` | number[] | 否 | 资源池多选，为空统计全部 |

## 3. 响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "title": "流水线NPU卡数趋势",
    "xAxis": [
      "2026-09-02 00:00",
      "2026-09-02 00:05",
      "2026-09-02 00:10",
      "2026-09-02 00:15",
      "2026-09-02 00:20"
    ],
    "series": [
      { "name": "总卡数", "data": [3592.0, 3745.0, 3754.0, 3770.0, 3819.0] },
      { "name": "使用卡数", "data": [474.0, 503.0, 433.0, 455.0, 424.0] },
      { "name": "等待卡数", "data": [3118.0, 3242.0, 3321.0, 3315.0, 3395.0] }
    ]
  }
}
```

（以上为 2026-09-02 00:00~00:20 的**实测返回（新口径）**：三条曲线**同源同集合**，都来自同一份任务数据 `dwr_rd_efc_resource_npu_detail_5m` 的同一条 5 分钟切片时间轴；逐切片严格满足 **总卡数 = 使用卡数 + 等待卡数**）

### 结构说明

- `data.xAxis`：时间切片标签，格式 `yyyy-MM-dd HH:mm`，**粒度固定 5 分钟**，无数据的切片也会占位
- `data.series`：**固定 3 条、顺序固定**，按下标取值即可，不要按 `name` 匹配（见下）
- `series[i].data`：长度与 `xAxis` 严格一致，**无 null**，无数据补 `0`，可直接喂给 ECharts

| 下标 | `name` | 单位 | 口径 |
|------|------|------|------|
| 0 | 总卡数 | 张 | 该切片**全部活跃任务**（等待任务 ∪ 运行任务）的申请卡数之和。任务集合 = 该切片 `job_current_slot_pending_seconds > 0 OR job_current_slot_running_seconds > 0`；与使用卡数 / 等待卡数**同源同集合**，恒有 总卡数 = 使用卡数 + 等待卡数。**不再是静态维表的机器容量水平线** |
| 1 | 使用卡数 | 张 | 该切片**归为运行**的任务的申请卡数之和（互斥归类：`job_current_slot_running_seconds >= job_current_slot_pending_seconds` 归运行）；申请卡数取平台任务事实表（三张平台事实表 UNION 后与活跃任务集合 join）的 `npu_second / job_duration`，job 级去重、四舍五入、下限 1；codearts 历史整点记账数据（`npu_second % 3600 == 0`）直接 `÷ 3600`；**不按机器容量封顶**；与「运行任务明细抽屉」的申请卡数同源 |
| 2 | 等待卡数 | 张 | 该切片**归为等待**的任务的申请卡数之和（互斥归类：`job_current_slot_running_seconds < job_current_slot_pending_seconds` 归等待），即队列需求，数值上属数千量级。申请卡数算法与使用卡数完全一致（job 级去重、四舍五入、下限 1；codearts 历史整点记账数据直接 `÷ 3600`）；与「排队任务明细抽屉」的申请卡数同源，且**同一切片的取值与查询窗口无关** |

> **互斥归类**：每个 (切片, 任务) 在该切片只归一类——running 秒数 ≥ pending 秒数记「运行」，否则记「等待」。因此三条曲线是同一任务集合的互斥切分，既无重复计数、也不漏计。

## 4. 前端接入要点

1. **双 Y 轴**：总卡数（约 3600~3800）与等待卡数（约 3100~3400）都是数千量级且彼此接近，使用卡数（约 420~500）小一个数量级；应给**使用卡数单独一个轴**（`yAxisIndex: 1`），总卡数与等待卡数共用另一个轴，否则使用卡数会被压进不足 20% 的高度。
2. **配色建议**：总卡数灰蓝 `#64748b`、使用卡数紫 `#7c3aed`、等待卡数橙 `#f97316`（等待卡数可加半透明面积区分）。
3. **右轴不画网格线**：左轴保留网格作为主参照，避免两套网格造成读数混乱。
4. **不要读两条轴的交叉点**：左右轴量纲不同，交叉点无业务含义；务必用 axis 触发的 tooltip 同时展示三条曲线的真实数值。
5. **下钻**：点击曲线上任一点 → 用该点对应的 `xAxis[dataIndex]` 拼成 `slotTime`（`yyyy-MM-dd HH:mm:00`）打开时段任务明细抽屉，行为与「趋势分析」一致。
6. **缩放**：图表内的 `dataZoom` 是前端本地缩放，不会触发重新请求；只有页面级筛选（项目 / 资源池 / 时间范围）变化才重新请求。

## 5. 约束与注意事项

- **时间窗口超过 72 小时会报错**，前端需在筛选处限制，或对报错做提示兜底
- **三条曲线同源同集合**：都来自 `dwr_rd_efc_resource_npu_detail_5m` 的同一条 5 分钟切片时间轴，任务集合 = 该切片**活跃任务 = 等待任务 ∪ 运行任务**（`job_current_slot_pending_seconds > 0 OR job_current_slot_running_seconds > 0`）
- **恒等式 总卡数 = 使用卡数 + 等待卡数 逐切片严格成立**：每个 (切片, 任务) 按 `job_current_slot_running_seconds >= job_current_slot_pending_seconds` 互斥归为运行 / 等待，同一集合互斥切分，不存在重复计数或漏计
- 等待卡数是**队列需求**，数值上属数千量级；图上已无机器容量线，不再与机器容量做对比说明
- 等待卡数取**平台任务事实表**口径（按 `platform + job_id` 取 job 级常量，事实表不做时间过滤），因此**同一切片的取值不随查询窗口变化**：实测 72h 与 20min 窗口下 00:00~00:20 五个切片三条曲线逐个相同（等待卡数 3118 / 3242 / 3321 / 3315 / 3395）。原先「窗口越短、等待卡数偏低」的偏差已消除
- 使用卡数与等待卡数**同源同算法**（都是 job 级申请卡数换算），只是归属由该切片的 running / pending 秒数孰大决定；因此同一切片的取值同样与查询窗口无关
- **三条卡数曲线与「使用率」不同源**：使用率（趋势分析曲线 / 热力图 / KPI）仍为分配卡时口径（`Σ assign_npu_hours / Σ total_npu_num`），而三条卡数曲线都是「申请卡数」口径，因此 `使用卡数 ÷ 总卡数 ≠ 使用率`（**总卡数现在也是申请卡数口径，不能写成「使用率 = 使用卡数 / 总卡数」**）
- **机器容量已不在本图展示**：旧版「总卡数」是静态维表 `sdi_rd_efc_server_machine_hidevlab` 的机器容量水平线（实测恒 1316），新口径下总卡数是活跃任务的申请卡数之和；容量基准请看同页 KPI 卡与热力图（那两处仍为机器容量 / 分配卡时口径，本次未改动）
- 接口耗时参考：本地实测 457~1008ms，与同页其它曲线同量级。若你在 Doris 控制台里量到「4 秒」，那是控制台固定开销（`SELECT 1` 同样是 4 秒），与接口无关

## 6. 关联改动：任务明细下钻新增「申请卡数」

同一需求（#300）的「点击下钻时，job 任务增加使用卡数的数据展示」对应**切片任务明细接口新增响应字段 `applyNpuNum`**，后端 commit `713f8938`，**前端需要适配**。

| 项 | 值 |
|------|------|
| 路径 | `POST /common/detail`（网关前缀 `/gateway/openlibing-ops`） |
| category | `ops-npu-slot-queue-detail`（排队 tab）/ `ops-npu-slot-running-detail`（运行 tab） |
| 用途 | 点击卡数趋势 / 趋势分析 / 热力图后打开的任务明细抽屉 |

### 请求

在原有 `category` / `startTime` / `endTime` 基础上，按点击来源传（均为可选）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `slotTime` | string | 5 分钟切片 `yyyy-MM-dd HH:mm`，趋势点 / 热力图格子点击时传 |
| `serverIp` | string | 机器 IP，热力图机器行点击时传 |
| `projectId` | number | 项目 ID，为空统计全部 |
| `resourcePoolIds` | number[] | 资源池多选，为空统计全部 |
| `platform` / `pipelineId` | string | 每日分层抽屉下钻时传，为空统计全部 |

### 响应

`data.records[]` 为**按资源池分组**的 `OpsNpuSlotTaskGroupResp`（含 `resourcePoolId` / `resourcePoolName` / `records[]`），分组内每个任务记录**新增字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `applyNpuNum` | number \| null | **任务实际申请卡数**。任务事实表 NPU 总量 ÷ 运行时长四舍五入、下限 1；codearts 历史整点记账数据（NPU 总量为 3600 整数倍）直接 ÷ 3600；取不到时为空 |

### 前端适配要点

1. 任务明细表新增「申请卡数」列，直接取 `applyNpuNum`。
2. `applyNpuNum` 可能为 `null`（该任务在平台事实表无数据），展示用 `--` 占位，不要按 0 处理。
3. 与卡数趋势的「等待卡数」**同源同口径**（都是 job 级申请卡数换算），同一切片 / 同一任务两处取值应一致。
