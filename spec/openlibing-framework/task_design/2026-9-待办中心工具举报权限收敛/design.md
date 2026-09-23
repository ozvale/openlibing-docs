# 待办中心工具举报审批权限收敛 — 技术设计

## 方案概述

将 `ToolReportController` 待办中心查询接口的 `userId` 由可选参数改为必填，并在 `ToolReportServiceImpl` 内按维度（待我审批 / 审批历史 / 全部）执行权限判定：非工具管理者在受限维度静默返回空列表，工具管理者保持原查询行为。

## 架构决策

### 决策 1：按维度判定而非全局拦截

**选择**：仅在「待我审批」「审批历史」两个维度做权限收敛，「全部」维度保留原查询行为。

**原因**：「全部」维度用于查询全平台历史举报，存在其他可见性需求；若全局拦截会改变既有可用语义。按维度精确收敛，最小化影响。

### 决策 2：`userId` 必填 + 网关覆盖

**选择**：将 `userId` 由 URL Query 可选参数改为必填，依赖 openlibing-gateway 从 JWT 解析 `userId` 并覆盖 URL Query 中的值。

**原因**：避免前端误传他人 `userId` 造成越权。网关统一覆盖确保 `userId` 来源可信，service 层无需重复鉴权。

### 决策 3：非工具管理者静默返回空列表

**选择**：非工具管理者调用受限维度接口时静默返回空列表，不抛 403/401。

**原因**：与现有审批入口表现一致——无权限用户原本就看不到审批按钮，前端调用方期望空列表而非错误。

## 接口设计

### 待办中心查询接口（ToolReportController）

| 维度 | 接口路径 | 方法 | 必填参数 | 行为 |
|------|----------|------|----------|------|
| 待我审批 | `/tool-report/pending?userId=&dim=pending` | GET | `userId`, `dim` | 工具管理者返回待审批列表；非管理者返回空 |
| 审批历史 | `/tool-report/history?userId=&dim=history` | GET | `userId`, `dim` | 工具管理者返回本人审批历史；非管理者返回空 |
| 全部 | `/tool-report/list?userId=&dim=all` | GET | `userId`, `dim` | 保持原行为，按全平台查询 |

> 维度字段命名以上线代码为准。

### 权限判定流程

```
flow:
  1. controller 接收 userId（来自网关覆盖的 JWT userId）+ dim
  2. service 查询 user 是否为任一工具的「工具管理者」
  3. if (dim in [pending, history]) and (非工具管理者):
        return emptyList
     else:
        return 原查询结果
```

## 关键代码位置

- `ToolReportController`：将 `userId` 由 `@RequestParam(required = false)` 改为 `@RequestParam(required = true)`，新增维度参数
- `ToolReportServiceImpl.queryReportList`：增加按 `dim` + 工具管理者判定的早返回分支
- `ToolReportServiceImplTest`：新增 2 个测试用例覆盖「管理者/非管理者 × 受限维度/全部维度」

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| URL Query 中 `userId` 被前端篡改 | 越权读取他人数据 | 网关已从 JWT 覆盖 `userId`，service 信任网关传值 |
| 已上线前端未传 `dim` 参数 | 接口报 400 | 已与前端协调同步发布；服务端兜底默认 `dim=all` 保持兼容（实现以代码为准） |
| 工具管理者判定接口性能 | 大量请求时延迟上升 | 工具管理者关系表已有索引，判定走缓存命中 |

## 关联

- 业务 Issue: openlibing/openlibing-framework#92
- 安全依据：openlibing-gateway 从 JWT 解析 `userId` 并覆盖 URL Query
