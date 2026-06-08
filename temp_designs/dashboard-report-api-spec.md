# openLiBing 运营看板接口规范

**版本：** v1.0  
**状态：** Draft  
**日期：** 2026-06-05

---

## 1. 接口概述

本规范定义了两个 REST API 接口：

### 1.1 接口一：数据上报接口

各开源社区通过此接口上报推广数据的当前值，包括：
- 社区和特性信息
- 用户指标当前值（UV/PV）
- 业务指标当前值（key-value 形式）

**接口地址：** `/api/v1/dashboard/report`

### 1.2 接口二：自定义运营指标接口

运营人员通过此接口定义运营看板的指标配置，包括：
- 特性名称
- 指标类型（用户指标、业务指标）
- 指标名称和标识（key）
- 指标统计方式（累加、平均）
- 指标目标值
- 指标说明（计算公式等）

**接口地址：** `/api/v1/dashboard/metrics`  
**支持批量：** 一次请求可定义多个指标

### 1.3 接口信息对比

| 属性         | 数据上报接口                            | 自定义运营指标接口                       |
|-------------|----------------------------------------|----------------------------------------|
| 接口地址     | `/api/v1/dashboard/report`            | `/api/v1/dashboard/metrics`           |
| 请求方法     | POST                                  | POST                                  |
| 数据格式     | application/json                      | application/json                      |
| 认证方式     | Bearer Token (JWT)                    | Bearer Token (JWT, Admin权限)         |
| 编码格式     | UTF-8                                 | UTF-8                                 |
| 使用角色     | 各开源社区                             | 运营团队                               |
| 批量支持     | 不支持                                 | 支持（一次定义多个指标）                |

---

## 2. 认证机制

### 2.1 认证方式

采用 Bearer Token (JWT) 认证：

```
Authorization: Bearer <token>
```

### 2.2 Token 获取

各社区需向 openLiBing 运营团队申请专属 Token：
- Token 有效期：90 天
- Token 绑定：社区身份（防止跨社区上报）
- Token 权限：仅允许上报数据，不允许查询或修改其他社区数据

### 2.3 Token 验证规则

- Header 中必须包含 `Authorization` 字段
- Token 格式必须符合 JWT 规范
- Token 必须未过期
- Token 绑定的社区必须与上报数据中的 `community` 字段一致

---

## 3. 请求参数定义

### 3.1 请求 Headers

| Header 名称       | 必填 | 说明                                    | 示例值                          |
|------------------|------|-----------------------------------------|--------------------------------|
| Authorization    | 是   | Bearer Token 认证凭证                   | Bearer eyJhbGciOiJIUzI1NiIs...  |
| Content-Type     | 是   | 请求体格式                              | application/json                |
| X-Reporter-ID    | 是   | 上报方身份标识（社区ID）                 | mindie-community                |
| X-Request-ID     | 否   | 请求唯一ID（用于追踪）                   | uuid-v4-format                  |
| User-Agent       | 否   | 上报方客户端信息                         | MindIE-Reporter/1.0             |

### 3.2 请求 Body（JSON Schema）

```json
{
  "community": {
    "type": "string",
    "required": true,
    "enum": [
      "MindIE", "PTA", "MindSpeed", "openEuler", 
      "HPCkit", "UBS Core", "openUBMC", "CANN", "openLiBing"
    ],
    "description": "开源社区名称（必须与Token绑定的社区一致）"
  },
  "feature": {
    "type": "string",
    "required": true,
    "enum": [
      "门禁检查", "接口兼容性", "流水线", "测试框架", "SBOM",
      "漏洞视图", "发布评审", "工具市场", "AI agent", 
      "Skill市场", "数字化运营看板"
    ],
    "description": "openLiBing 特性名称"
  },
  "user_metrics": {
    "type": "object",
    "required": true,
    "properties": {
      "uv": {
        "type": "integer",
        "required": true,
        "min": 0,
        "description": "当前用户数"
      },
      "pv": {
        "type": "integer",
        "required": true,
        "min": 0,
        "description": "当前访问量"
      }
    },
    "description": "用户指标当前值数据"
  },
  "business_metrics": {
    "type": "object",
    "required": true,
    "additionalProperties": {
      "type": "string",
      "description": "业务指标当前值（可包含单位）"
    },
    "description": "业务指标当前值数据（key-value 形式）"
  },
  "timestamp": {
    "type": "string",
    "format": "date-time",
    "required": false,
    "description": "数据采集时间（ISO 8601 格式，默认为当前时间）"
  }
}
```

---

## 4. 业务指标定义

### 4.1 各特性专属业务指标

| 特性名称        | 业务指标 Key 名称（建议）                | 数据类型     | 单位示例        |
|---------------|----------------------------------------|------------|----------------|
| 门禁检查        | avg_duration, block_rate, success_rate | string      | 12.5分钟, 23.4% |
| 接口兼容性      | managed_count, test_coverage, change_count | string      | 45个, 89.2%    |
| 流水线         | execution_count, avg_duration, success_rate | string      | 234次, 5.2分钟 |
| 测试框架        | test_count, coverage_rate, automation_rate | string      | 1560个, 87.3%  |
| SBOM          | component_count, compliance_rate, vulnerability_count | string | 89个, 95.6%  |
| 漏洞视图        | vulnerability_count, fix_rate, high_risk_count | string      | 12个, 83.3%    |
| 发布评审        | release_count, review_duration, pass_rate | string      | 45次, 2.5天    |
| 工具市场        | tool_count, download_count, active_tool_count | string      | 23个, 1560次   |
| AI agent       | agent_count, task_count, success_rate  | string      | 8个, 450次     |
| Skill市场       | skill_count, usage_count, top_skill_rank | string      | 12个, Top 5    |
| 数字化运营看板   | dashboard_access_count, update_frequency, satisfaction_score | string | 2340次, 4.5星 |

### 4.2 业务指标值格式规范

- **计数类指标**：数字 + 单位（如 "1560个", "234次"）
- **百分比指标**：百分比数值 + % 符号（如 "87.3%"）
- **时长类指标**：数字 + 时间单位（如 "12.5分钟", "2.5天"）
- **排名类指标**：排名文本（如 "Top 5"）
- **评分类指标**：数字 + 星级符号（如 "4.5星"）
- **频率类指标**：频率文本（如 "每日", "每周", "每月"）

---

## 5. 响应格式定义

### 5.1 成功响应（HTTP 200）

```json
{
  "code": 200,
  "message": "数据上报成功",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "community": "MindIE",
    "feature": "门禁检查",
    "status": "active",
    "received_at": "2026-06-05T14:30:25.123Z",
    "updated_fields": [
      "user_metrics",
      "business_metrics"
    ]
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

### 5.2 响应字段说明

| 字段               | 类型     | 说明                                    |
|-------------------|----------|-----------------------------------------|
| code              | integer  | 响应状态码（200=成功）                   |
| message           | string   | 响应消息                                 |
| data.report_id    | string   | 本次上报的唯一ID（UUID格式）              |
| data.community    | string   | 接收的社区名称                           |
| data.feature      | string   | 接收的特性名称                           |
| data.received_at  | string   | 接收时间（ISO 8601格式）                 |
| timestamp         | string   | 响应生成时间                             |

---

## 6. 错误码定义

### 6.1 常见错误码

| HTTP状态码 | 错误码 | 错误消息                                | 原因                                      |
|-----------|-------|----------------------------------------|------------------------------------------|
| 400       | 40001 | 缺少必填字段                             | 请求体缺少 required 字段                  |
| 400       | 40002 | 字段类型错误                             | 字段类型不符合 JSON Schema 定义           |
| 400       | 40003 | 字段值不合法                             | 字段值不在 enum 列表或超出范围            |
| 400       | 40004 | JSON 格式错误                            | 请求体不是有效的 JSON                     |
| 401       | 40101 | 缺少认证信息                             | Header 中未包含 Authorization             |
| 401       | 40102 | Token 无效                              | Token 格式错误或已被撤销                  |
| 401       | 40103 | Token 已过期                            | Token 有效期已超过 90 天                  |
| 403       | 40301 | 无权限上报此社区数据                     | Token 绑定的社区与上报数据不一致          |
| 403       | 40302 | 无权限上报此特性数据                     | Token 权限不包含该特性                    |
| 429       | 42901 | 请求频率超限                             | 同一社区上报频率超过限制（每分钟10次）    |
| 500       | 50001 | 内部服务错误                             | 服务器处理异常                            |
| 503       | 50301 | 服务暂时不可用                           | 服务正在维护或过载                        |

### 6.2 错误响应格式

```json
{
  "code": 40001,
  "message": "缺少必填字段",
  "errors": [
    {
      "field": "community",
      "reason": "required field missing"
    },
    {
      "field": "user_metrics.uv.current",
      "reason": "required field missing"
    }
  ],
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

---

## 7. 请求频率限制

### 7.1 频率限制规则

| 维度         | 限制                                    | 说明                                      |
|-------------|-----------------------------------------|------------------------------------------|
| 单社区上报   | 10 次/分钟                              | 防止数据刷量                              |
| 单特性上报   | 1 次/分钟                               | 同一特性避免重复上报                      |
| 全局上报     | 100 次/分钟                             | 全平台总限制                              |

### 7.2 频率限制响应（HTTP 429）

```json
{
  "code": 42901,
  "message": "请求频率超限",
  "data": {
    "limit": 10,
    "remaining": 0,
    "reset_at": "2026-06-05T14:31:00Z"
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

---

## 8. 完整请求示例

### 8.1 示例 1：门禁检查特性上报

**请求 Headers:**
```
POST /api/v1/dashboard/report
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
X-Reporter-ID: mindie-community
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
User-Agent: MindIE-Reporter/1.0
```

**请求 Body:**
```json
{
  "community": "MindIE",
  "feature": "门禁检查",
  "user_metrics": {
    "uv": 156,
    "pv": 1234
  },
  "business_metrics": {
    "avg_duration": "12.5分钟",
    "block_rate": "23.4%",
    "success_rate": "96.7%"
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

**成功响应（HTTP 200）:**
```json
{
  "code": 200,
  "message": "数据上报成功",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "community": "MindIE",
    "feature": "门禁检查",
    "received_at": "2026-06-05T14:30:25.123Z"
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

### 8.2 示例 2：未对接特性上报

**请求 Body:**
```json
{
  "community": "MindIE",
  "feature": "Skill市场",
  "user_metrics": {
    "uv": 0,
    "pv": 0
  },
  "business_metrics": {}
}
```

**成功响应（HTTP 200）:**
```json
{
  "code": 200,
  "message": "数据上报成功",
  "data": {
    "report_id": "550e8400-e29b-41d4-a716-446655440001",
    "community": "MindIE",
    "feature": "Skill市场",
    "received_at": "2026-06-05T14:30:26.456Z"
  },
  "timestamp": "2026-06-05T14:30:26.456Z"
}
```

### 8.3 示例 3：错误响应示例

**请求 Body（缺少必填字段）:**
```json
{
  "community": "MindIE",
  "feature": "门禁检查",
  "status": "active"
}
```

**错误响应（HTTP 400）:**
```json
{
  "code": 40001,
  "message": "缺少必填字段",
  "errors": [
    {
      "field": "user_metrics",
      "reason": "required field missing"
    },
    {
      "field": "business_metrics",
      "reason": "required field missing"
    }
  ],
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

---

## 9. 数据存储与更新规则

### 9.1 数据存储策略

| 策略         | 规则                                    |
|-------------|-----------------------------------------|
| 数据唯一性   | 按 (community, feature) 组合作为唯一键  |
| 更新模式     | 全量更新（每次上报覆盖之前的数据）        |
| 历史记录     | 保留历史上报记录（report_id + timestamp）|
| 数据有效期   | 数据默认有效期 30 天，超期显示为灰色      |

### 9.2 更新逻辑

1. 收到上报请求后，验证 Token 和数据格式
2. 根据 (community, feature) 查询现有数据
3. 如果存在：更新现有记录 + 保存历史版本
4. 如果不存在：创建新记录
5. 返回 report_id 和更新结果

---

## 10. 实施建议

### 10.1 业务场景说明

**上报主体：** 各开源社区业务团队  
**上报内容：** 前24小时（昨日）的推广数据  
**上报频率：** 每日定时上报一次  
**上报时间：** 建议在每日 00:00-02:00 之间（避开业务高峰期）

### 10.2 定时上报机制

**数据时间范围定义：**
- 上报数据时间范围：前24小时（昨日 00:00-23:59）
- 数据采集周期：每日一次，聚合昨日全天数据
- 上报时间窗口：每日固定时间段（建议 00:00-06:00）

**定时任务配置（示例）：**

```yaml
# 定时任务配置示例
schedule:
  cron: "0 0 1 * * ?"  # 每日凌晨1点执行
  task: "DailyReportTask"
  parameters:
    time_range: "yesterday"  # 前24小时
    communities: ["MindIE", "PTA", "MindSpeed", ...]
```

**定时任务实现流程：**

```
每日凌晨1点
    ↓
业务团队定时任务启动
    ↓
采集昨日数据（前24小时）
    ↓
聚合计算指标值
    ↓
调用 POST /api/v1/dashboard/report
    ↓
数据入库 + 保存历史记录
```

### 10.3 数据聚合逻辑

**用户指标聚合：**

| 指标   | 聚合方式     | 计算说明                                |
|-------|-------------|----------------------------------------|
| UV    | 累加计数     | 昨日新增用户数（去重后）                 |
| PV    | 累加计数     | 昨日总访问量（所有请求次数）              |

**业务指标聚合：**

| 指标类型     | 聚合方式        | 示例                                      |
|------------|----------------|------------------------------------------|
| 计数类       | 累加求和         | 执行次数：昨日总执行次数                  |
| 百分比类     | 平均值/加权平均   | 成功率：昨日所有任务成功率平均值          |
| 时长类       | 平均值           | 平均时长：昨日所有任务耗时平均值          |
| 状态类       | 当前状态快照     | 排名：昨日结束时排名状态                  |

**聚合示例代码：**

```python
# 示例：计算昨日门禁检查指标
def aggregate_yesterday_metrics():
    # 时间范围：昨日 00:00-23:59
    yesterday_start = get_yesterday_start()
    yesterday_end = get_yesterday_end()
    
    # 聚合用户指标
    uv = db.query_unique_users(start=yesterday_start, end=yesterday_end)
    pv = db.query_total_requests(start=yesterday_start, end=yesterday_end)
    
    # 聚合业务指标
    avg_duration = db.query_avg_duration(start=yesterday_start, end=yesterday_end)
    block_rate = db.query_block_rate(start=yesterday_start, end=yesterday_end)
    success_rate = db.query_success_rate(start=yesterday_start, end=yesterday_end)
    
    # 组装上报数据
    report_data = {
        "community": "MindIE",
        "feature": "门禁检查",
        "user_metrics": {
            "uv": uv,
            "pv": pv
        },
        "business_metrics": {
            "avg_duration": f"{avg_duration}分钟",
            "block_rate": f"{block_rate}%",
            "success_rate": f"{success_rate}%"
        },
        "timestamp": yesterday_end.isoformat()
    }
    
    return report_data
```

### 10.4 客户端实施建议

**上报时机：**
- **定时上报（强制）：** 每日固定时间上报昨日数据
- 推荐时间：每日凌晨 01:00（避开业务高峰）
- 最晚时间：每日 06:00 前完成上报

**上报频率：**
- 正常频率：每日 1 次（上报昨日全天数据）
- 不允许高频上报（频率限制生效）
- 延迟上报：如遇网络故障，可在当日 06:00-12:00 补报

**数据采集要求：**
- 数据时间范围：严格限制为前24小时（昨日）
- 数据完整性：确保昨日数据完整采集后再上报
- 数据准确性：聚合计算需去重、校验、过滤异常值

**错误处理：**
- 网络超时：重试 3 次，间隔 5 秒
- 认证失败：重新申请 Token
- 频率超限：等待 reset_at 时间后重试
- 上报失败：记录日志，次日补报

**客户端定时任务实现：**

```python
# Python 示例：定时任务框架
import schedule
import time

def daily_report_job():
    """每日数据上报任务"""
    try:
        # 1. 采集昨日数据
        data = aggregate_yesterday_metrics()
        
        # 2. 上报到运营看板
        response = report_to_dashboard(data)
        
        # 3. 记录上报日志
        log_report_result(response)
        
    except Exception as e:
        # 4. 异常处理：记录日志，次日补报
        log_error(e)
        schedule_retry_job()

# 配置定时任务：每日凌晨1点执行
schedule.every().day.at("01:00").do(daily_report_job)

# 启动定时任务
while True:
    schedule.run_pending()
    time.sleep(60)
```

### 10.5 服务端实施建议

**技术选型：**
- REST API：Spring Boot / Express.js
- 数据存储：MongoDB（文档存储，适合 key-value 业务指标）
- 认证：JWT（jsonwebtoken库）
- 频率限制：Redis + Lua脚本
- 日志：结构化日志（JSON格式）
- 定时任务监控：可选（监控上报延迟、失败情况）

**性能优化：**
- 批量上报接口：支持一次上报多个特性（可选）
- 数据缓存：Redis 缓存热点数据
- 异步处理：上报数据异步写入数据库
- 数据压缩：历史数据定期归档（超过30天）

**数据校验：**
- 时间戳校验：验证 timestamp 是否在昨日范围内
- 数据合理性校验：UV/PV 不能为负数，百分比不能超过100%
- 重复上报检测：同一 (community, feature, timestamp) 只接受一次

### 10.6 运营看板展示逻辑

**数据展示策略：**

| 数据来源         | 展示逻辑                                |
|-----------------|----------------------------------------|
| 最新上报数据      | 展示当前值（来自最近一次上报）            |
| 目标值           | 展示年度目标值（来自目标值设置接口）      |
| 达成率           | 当前值 / 目标值 × 100%                   |
| 进度条           | 根据达成率显示进度（<50%黄色，≥50%绿色）  |

**数据时效性：**
- 最新数据时间：显示最后一次上报的 timestamp
- 数据过期判断：超过 48 小时未上报，显示灰色（inactive）
- 数据过期提醒：运营看板前端显示"数据已过期，请及时上报"

**数据对比功能：**
- 昨日 vs 今日对比（需前端实时计算）
- 本周 vs 上周对比（需历史数据支持）
- 本月 vs 上月对比（需历史数据支持）

---

## 11. 接口版本管理

### 11.1 版本演进规则

- 接口路径包含版本号：`/api/v1/`
- 向后兼容：新版本必须兼容旧版本字段
- 弃用策略：旧版本保留 180 天后弃用
- 变更通知：接口变更需提前 30 天通知各社区

### 11.2 未来版本规划

**v1.1（计划）：**
- 批量上报接口（一次上报多个特性）
- 数据查询接口（查询历史上报记录）
- 数据导出接口（CSV/Excel格式）

**v2.0（远期）：**
- 实时推送（WebSocket）
- 数据订阅机制
- 数据质量评分

---

## 12. 附录

### 12.1 JSON Schema 完整定义

完整的 JSON Schema 定义可从以下地址获取：
- URL: `/api/v1/schema/report.json`
- 格式: JSON Schema Draft 07

### 12.2 Postman 测试集合

提供 Postman 测试集合：
- URL: `/api/v1/postman/collection.json`
- 包含: 认证测试、上报测试、错误场景测试

### 12.3 SDK 提供

提供多语言 SDK：
- Python SDK: `pip install openlibing-dashboard-reporter`
- Java SDK: Maven依赖
- Node.js SDK: npm包

---

## 13. 接口二：自定义运营指标接口

### 13.1 接口信息

| 属性         | 值                                    |
|-------------|---------------------------------------|
| 接口名称     | 自定义运营指标接口                     |
| 接口地址     | `/api/v1/dashboard/metrics`           |
| 请求方法     | POST                                  |
| 数据格式     | application/json                      |
| 认证方式     | Bearer Token (JWT, Admin权限)         |
| 编码格式     | UTF-8                                 |
| 使用角色     | 运营团队                               |
| 批量支持     | 支持（一次定义多个指标）                |

### 13.2 认证要求

运营团队需要申请 **Admin权限** Token：
- Token权限：可定义任意特性的运营指标
- Token有效期：永久（需定期审计）
- Token绑定：运营团队成员身份

### 13.3 请求 Headers

与数据上报接口相同（见3.1节），但需使用 Admin Token。

### 13.4 请求 Body（JSON Schema）

**批量上报结构：**

```json
{
  "metrics": {
    "type": "array",
    "required": true,
    "items": {
      "type": "object",
      "properties": {
        "feature": {
          "type": "string",
          "required": true,
          "enum": [
            "门禁检查", "接口兼容性", "流水线", "测试框架", "SBOM",
            "漏洞视图", "发布评审", "工具市场", "AI agent", 
            "Skill市场", "数字化运营看板"
          ],
          "description": "openLiBing 特性名称"
        },
        "metric_type": {
          "type": "string",
          "required": true,
          "enum": ["user_metric", "business_metric"],
          "description": "指标类型：user_metric=用户指标, business_metric=业务指标"
        },
        "metric_name": {
          "type": "string",
          "required": true,
          "max_length": 50,
          "description": "指标名称（如：用户数、平均时长、成功率）"
        },
        "metric_key": {
          "type": "string",
          "required": true,
          "max_length": 50,
          "description": "指标标识（对应数据上报接口中的key，如：uv、avg_duration、success_rate）"
        },
        "aggregation_type": {
          "type": "string",
          "required": true,
          "enum": ["sum", "avg"],
          "description": "指标统计方式：sum=累加, avg=平均（支持时间段筛选时的统计）"
        },
        "target_value": {
          "type": "string",
          "required": true,
          "description": "指标目标值（可包含单位，如：200、10分钟、98%）"
        },
        "description": {
          "type": "string",
          "required": false,
          "max_length": 500,
          "description": "指标说明（说明指标计算公式等，如：昨日新增用户数（去重））"
        }
      }
    },
    "description": "运营指标配置数组（批量定义）"
  },
  "year": {
    "type": "integer",
    "required": false,
    "description": "目标年份（默认为当前年份）"
  }
}
```

### 13.5 响应格式（HTTP 200）

```json
{
  "code": 200,
  "message": "运营指标定义成功",
  "data": {
    "batch_id": "770e8400-e29b-41d4-a716-446655440000",
    "year": 2026,
    "total_metrics": 3,
    "created_metrics": [
      {
        "metric_id": "770e8400-e29b-41d4-a716-446655440001",
        "feature": "门禁检查",
        "metric_type": "user_metric",
        "metric_name": "用户数",
        "metric_key": "uv",
        "aggregation_type": "sum",
        "target_value": "200",
        "description": "昨日新增用户数（去重后）",
        "created_at": "2026-06-05T14:30:25.123Z"
      },
      {
        "metric_id": "770e8400-e29b-41d4-a716-446655440002",
        "feature": "门禁检查",
        "metric_type": "business_metric",
        "metric_name": "平均时长",
        "metric_key": "avg_duration",
        "aggregation_type": "avg",
        "target_value": "10分钟",
        "description": "昨日所有任务耗时平均值",
        "created_at": "2026-06-05T14:30:25.123Z"
      },
      {
        "metric_id": "770e8400-e29b-41d4-a716-446655440003",
        "feature": "门禁检查",
        "metric_type": "business_metric",
        "metric_name": "成功率",
        "metric_key": "success_rate",
        "aggregation_type": "avg",
        "target_value": "98%",
        "description": "昨日所有任务成功率平均值",
        "created_at": "2026-06-05T14:30:25.123Z"
      }
    ]
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

### 13.6 完整请求示例

**请求 Headers:**
```
POST /api/v1/dashboard/metrics
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (Admin Token)
Content-Type: application/json
X-Reporter-ID: ops-team
X-Request-ID: 770e8400-e29b-41d4-a716-446655440000
User-Agent: openLiBing-Ops/1.0
```

**请求 Body（批量定义3个指标）:**
```json
{
  "metrics": [
    {
      "feature": "门禁检查",              // 特性名称
      "metric_type": "user_metric",       // 指标类型（user_metric/business_metric）
      "metric_name": "用户数",             // 指标名称
      "metric_key": "uv",                 // 指标标识（对应上报接口的key）
      "aggregation_type": "sum",          // 统计方式（sum累加/avg平均）
      "target_value": "200",              // 指标目标值
      "description": "昨日新增用户数（去重后）"  // 指标说明（可选）
    },
    {
      "feature": "门禁检查",
      "metric_type": "business_metric",
      "metric_name": "平均时长",
      "metric_key": "avg_duration",
      "aggregation_type": "avg",
      "target_value": "10分钟",
      "description": "昨日所有任务耗时平均值"
    },
    {
      "feature": "门禁检查",
      "metric_type": "business_metric",
      "metric_name": "成功率",
      "metric_key": "success_rate",
      "aggregation_type": "avg",
      "target_value": "98%",
      "description": "昨日所有任务成功率平均值"
    }
  ],
  "year": 2026
}
```

**成功响应（HTTP 200）:**
```json
{
  "code": 200,
  "message": "运营指标定义成功",
  "data": {
    "batch_id": "770e8400-e29b-41d4-a716-446655440000",
    "year": 2026,
    "total_metrics": 3,
    "created_metrics": [
      {
        "metric_id": "770e8400-e29b-41d4-a716-446655440001",
        "feature": "门禁检查",
        "metric_type": "user_metric",
        "metric_name": "用户数",
        "metric_key": "uv",
        "aggregation_type": "sum",
        "target_value": "200",
        "description": "昨日新增用户数（去重后）",
        "created_at": "2026-06-05T14:30:25.123Z"
      },
      {
        "metric_id": "770e8400-e29b-41d4-a716-446655440002",
        "feature": "门禁检查",
        "metric_type": "business_metric",
        "metric_name": "平均时长",
        "metric_key": "avg_duration",
        "aggregation_type": "avg",
        "target_value": "10分钟",
        "description": "昨日所有任务耗时平均值",
        "created_at": "2026-06-05T14:30:25.123Z"
      },
      {
        "metric_id": "770e8400-e29b-41d4-a716-446655440003",
        "feature": "门禁检查",
        "metric_type": "business_metric",
        "metric_name": "成功率",
        "metric_key": "success_rate",
        "aggregation_type": "avg",
        "target_value": "98%",
        "description": "昨日所有任务成功率平均值",
        "created_at": "2026-06-05T14:30:25.123Z"
      }
    ]
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

### 13.7 错误码定义

| HTTP状态码 | 错误码 | 错误消息                                | 原因                                      |
|-----------|-------|----------------------------------------|------------------------------------------|
| 400       | 40001 | 缺少必填字段                             | 请求体缺少 required 字段                  |
| 400       | 40002 | 字段类型错误                             | 字段类型不符合 JSON Schema 定义           |
| 400       | 40003 | 指标标识重复                             | 同一特性的同一metric_key已存在            |
| 400       | 40004 | JSON 格式错误                            | 请求体不是有效的 JSON                     |
| 400       | 40005 | 批量指标数量超限                         | metrics数组超过50个                       |
| 401       | 40101 | 缺少认证信息                             | Header 中未包含 Authorization             |
| 401       | 40102 | Token 无效                              | Token 格式错误或已被撤销                  |
| 403       | 40303 | 无权限定义运营指标                       | Token 不是 Admin 权限                    |
| 409       | 40901 | 指标已存在                               | 该特性的该指标已定义，需先删除            |
| 500       | 50001 | 内部服务错误                             | 服务器处理异常                            |

### 13.8 运营指标管理规则

**存储策略：**
- 按 (feature, metric_key) 组合作为唯一键
- 每个特性可定义多个指标（用户指标 + 业务指标）
- 指标定义支持批量（一次最多50个）

**查询接口（v1.1计划）：**
- 查询某特性的所有指标配置
- 查询全平台所有指标配置

**删除接口（v1.1计划）：**
- 删除某特性的某个指标
- 仅 Admin 权限可删除

### 13.9 指标统计方式说明

**统计方式定义：**

| 统计方式     | 说明                                    | 适用指标                                |
|------------|----------------------------------------|----------------------------------------|
| sum（累加）  | 时间段内的数值累加求和                   | UV、PV、执行次数、下载次数                |
| avg（平均）  | 时间段内的数值平均值                     | 平均时长、成功率、覆盖率                  |

**时间段筛选统计示例：**

**场景：查询过去7天的数据**

| 指标       | 统计方式 | 计算逻辑                                | 示例                                      |
|-----------|---------|----------------------------------------|------------------------------------------|
| UV        | sum     | 过去7天每日UV累加                        | Day1:100 + Day2:120 + ... = 780          |
| PV        | sum     | 过去7天每日PV累加                        | Day1:500 + Day2:600 + ... = 3500         |
| avg_duration | avg   | 过去7天每日平均值再平均                  | (10+12+8+11+9+13+10) / 7 = 10.4分钟       |
| success_rate | avg   | 过去7天每日成功率平均值                  | (96+98+95+97+96+98+97) / 7 = 96.7%        |

### 13.10 指标配置与数据上报的对应关系

**配置 -> 上报 -> 展示流程：**

```
运营团队                指标配置数据库              开源社区                运营看板前端
    |                         |                        |                        |
    |--POST /metrics---------->| (定义指标配置)          |                        |
    |   {                     |                        |                        |
    |     metric_key: "uv",   |                        |                        |
    |     aggregation: "sum", |                        |                        |
    |     target: "200"       |                        |                        |
    |   }                     |                        |                        |
    |                         |                        |                        |
    |                         |                        |                        |
    |                         |<---POST /report---------| (每日上报当前值)        |
    |                         |   {                    |                        |
    |                         |     uv: 156            |                        |
    |                         |   }                    |                        |
    |                         |                        |                        |
    |                         |                        |                        |
    |                         |                        |<----GET (查询)----------|
    |                         |                        |   {                    |
    |                         |                        |     uv_current: 156,   |
    |                         |----------------------->|     uv_target: 200,    |
    |                         |   (返回配置+数据)       |     aggregation: "sum" |
    |                         |                        |   }                    |
    |                         |                        |                        |
    |                         |                        |   前端展示：            |
    |                         |                        |   - 当前值：156         |
    |                         |                        |   - 目标值：200         |
    |                         |                        |   - 达成率：78%         |
    |                         |                        |   - 统计方式：累加      |
```

### 13.11 指标字段使用规范

**metric_key 唯一性：**
- 同一特性内，metric_key 必须唯一
- metric_key 与数据上报接口中的 key 保持一致
- 例如：上报接口用 `uv`，配置接口也必须用 `uv`

**target_value 格式：**
- 用户指标：纯数字（如："200"）
- 业务指标：数字 + 单位（如："10分钟"、"98%"）
- 单位必须与上报数据单位一致

**description 内容建议：**
- 说明指标计算公式
- 说明数据来源和采集方式
- 说明数据时间范围定义
- 例如："昨日新增用户数（去重后），来源于访问日志统计"

---

**文档维护：** openLiBing 运营团队  
**联系方式：** dashboard-support@openlibing.com  
**更新日期：** 2026-06-05