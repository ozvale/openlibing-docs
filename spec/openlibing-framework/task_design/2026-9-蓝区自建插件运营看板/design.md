# 蓝区自建插件 GitHub & GitCode 使用运营看板 — 技术设计

## 方案概述

在 openlibing-framework 仓建设蓝区自建插件使用度量能力：上报层支持 GitHub 与 GitCode 两渠道的事件上报（安装/卸载/调用/错误），聚合层按渠道+时间+指标类型聚合，查询层提供看板数据查询接口。

## 架构决策

### 决策 1：双渠道共表，channel 字段区分

**选择**：插件使用度量数据表统一存储 GitHub 与 GitCode 数据，通过 `channel` 字段区分。

**原因**：两渠道数据结构一致，共表减少重复建表与维护成本，聚合查询可统一进行。

### 决策 2：事件维度上报 + 时序聚合

**选择**：上报接口按事件维度写入明细，看板查询按时间维度聚合返回。

**原因**：明细写入保证数据可追溯；时序聚合在查询时计算，避免提前物化导致数据不一致。

### 决策 3：指标类型枚举统一

**选择**：指标类型枚举统一为 `INSTALL` / `UNINSTALL` / `INVOKE` / `ERROR` 等。

**原因**：与生态社区特性运营看板指标体系对齐，便于复用聚合逻辑。

## 接口设计

### 上报接口

| 功能 | 接口路径 | 方法 |
|------|----------|------|
| 上报事件 | `/plugin-usage/report` | POST |

**请求示例**：

```json
{
  "channel": "GITHUB",
  "pluginCode": "openlibing-cicd-action",
  "eventType": "INSTALL",
  "userId": "u123",
  "timestamp": "2026-09-23T10:00:00+08:00",
  "extra": "{}"
}
```

### 看板查询接口

| 功能 | 接口路径 | 方法 |
|------|----------|------|
| 按渠道+时间+指标聚合查询 | `/plugin-usage/dashboard?channel=&startTime=&endTime=&metricType=` | GET |

> 接口契约以上线代码为准。

## 数据模型

| 表名 | 关键字段 |
|------|----------|
| `plugin_usage_event` | `id, channel, plugin_code, event_type, user_id, event_time, extra, created_at` |

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 高频上报数据量增长 | 表膨胀 | 按事件时间分区，冷数据归档 |
| 渠道字段缺失/错误 | 聚合偏差 | 上报接口强制校验 channel 枚举 |
| 重复上报 | 指标虚高 | 上报时按 `(channel, plugin_code, user_id, event_type, event_time)` 去重 |

## 关联

- 业务 Issue: openlibing/openlibing-framework#101
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入）
