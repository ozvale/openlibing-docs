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

### 1.2 接口二：目标值设置接口

运营人员通过此接口设置各指标的年度目标值，包括：
- 社区和特性信息
- 用户指标目标值（UV/PV）
- 业务指标目标值（key-value 形式）

**接口地址：** `/api/v1/dashboard/targets`

### 1.3 接口信息对比

| 属性         | 数据上报接口                            | 目标值设置接口                          |
|-------------|----------------------------------------|----------------------------------------|
| 接口地址     | `/api/v1/dashboard/report`            | `/api/v1/dashboard/targets`           |
| 请求方法     | POST                                  | POST                                  |
| 数据格式     | application/json                      | application/json                      |
| 认证方式     | Bearer Token (JWT)                    | Bearer Token (JWT)                    |
| 编码格式     | UTF-8                                 | UTF-8                                 |
| 使用角色     | 各开源社区                             | 运营团队                               |

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
  "reporter": {
    "type": "object",
    "required": false,
    "properties": {
      "name": {
        "type": "string",
        "description": "上报负责人姓名"
      },
      "email": {
        "type": "string",
        "format": "email",
        "description": "上报负责人邮箱"
      },
      "organization": {
        "type": "string",
        "description": "上报组织/团队"
      }
    },
    "description": "上报负责人信息（可选）"
  },
  "notes": {
    "type": "string",
    "required": false,
    "max_length": 500,
    "description": "备注信息（可选，最大500字符）"
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
| data.status       | string   | 接收的推广状态                           |
| data.received_at  | string   | 接收时间（ISO 8601格式）                 |
| data.updated_fields | array   | 本次更新的字段列表                       |
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
  "reporter": {
    "name": "张三",
    "email": "zhangsan@example.com",
    "organization": "MindIE Team"
  },
  "notes": "已完成门禁规则配置，支持PR自动检查和质量门禁",
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
    "received_at": "2026-06-05T14:30:25.123Z",
    "updated_fields": [
      "user_metrics",
      "business_metrics",
      "reporter",
      "notes"
    ]
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
  "business_metrics": {},
  "notes": "暂未对接，如有需求请联系运营团队"
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
    "received_at": "2026-06-05T14:30:26.456Z",
    "updated_fields": [
      "user_metrics",
      "business_metrics",
      "notes"
    ]
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
        "timestamp": yesterday_end.isoformat()  # 昨日结束时间
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

## 13. 接口二：目标值设置接口

### 13.1 接口信息

| 属性         | 值                                    |
|-------------|---------------------------------------|
| 接口名称     | 目标值设置接口                         |
| 接口地址     | `/api/v1/dashboard/targets`           |
| 请求方法     | POST                                  |
| 数据格式     | application/json                      |
| 认证方式     | Bearer Token (JWT, Admin权限)         |
| 编码格式     | UTF-8                                 |
| 使用角色     | 运营团队                               |

### 13.2 认证要求

运营团队需要申请 **Admin权限** Token：
- Token权限：可设置任意社区的目标值
- Token有效期：永久（需定期审计）
- Token绑定：运营团队成员身份

### 13.3 请求 Headers

与数据上报接口相同（见3.1节），但需使用 Admin Token。

### 13.4 请求 Body（JSON Schema）

```json
{
  "community": {
    "type": "string",
    "required": true,
    "enum": [
      "MindIE", "PTA", "MindSpeed", "openEuler", 
      "HPCkit", "UBS Core", "openUBMC", "CANN", "openLiBing"
    ],
    "description": "开源社区名称"
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
  "user_targets": {
    "type": "object",
    "required": true,
    "properties": {
      "uv_target": {
        "type": "integer",
        "required": true,
        "min": 0,
        "description": "用户数年度目标值"
      },
      "pv_target": {
        "type": "integer",
        "required": true,
        "min": 0,
        "description": "访问量年度目标值"
      }
    },
    "description": "用户指标年度目标值"
  },
  "business_targets": {
    "type": "object",
    "required": true,
    "additionalProperties": {
      "type": "string",
      "description": "业务指标年度目标值（可包含单位）"
    },
    "description": "业务指标年度目标值（key-value 形式）"
  },
  "year": {
    "type": "integer",
    "required": false,
    "description": "目标年份（默认为当前年份）"
  },
  "notes": {
    "type": "string",
    "required": false,
    "max_length": 500,
    "description": "备注信息（可选）"
  }
}
```

### 13.5 响应格式（HTTP 200）

```json
{
  "code": 200,
  "message": "目标值设置成功",
  "data": {
    "target_id": "660e8400-e29b-41d4-a716-446655440000",
    "community": "MindIE",
    "feature": "门禁检查",
    "year": 2026,
    "user_targets": {
      "uv_target": 200,
      "pv_target": 1500
    },
    "business_targets": {
      "avg_duration": "10分钟",
      "block_rate": "20%",
      "success_rate": "98%"
    },
    "created_at": "2026-06-05T14:30:25.123Z"
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

### 13.6 完整请求示例

**请求 Headers:**
```
POST /api/v1/dashboard/targets
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (Admin Token)
Content-Type: application/json
X-Reporter-ID: ops-team
X-Request-ID: 660e8400-e29b-41d4-a716-446655440000
User-Agent: openLiBing-Ops/1.0
```

**请求 Body:**
```json
{
  "community": "MindIE",
  "feature": "门禁检查",
  "user_targets": {
    "uv_target": 200,
    "pv_target": 1500
  },
  "business_targets": {
    "avg_duration": "10分钟",
    "block_rate": "20%",
    "success_rate": "98%"
  },
  "year": 2026,
  "notes": "2026年度推广目标"
}
```

**成功响应（HTTP 200）:**
```json
{
  "code": 200,
  "message": "目标值设置成功",
  "data": {
    "target_id": "660e8400-e29b-41d4-a716-446655440000",
    "community": "MindIE",
    "feature": "门禁检查",
    "year": 2026,
    "user_targets": {
      "uv_target": 200,
      "pv_target": 1500
    },
    "business_targets": {
      "avg_duration": "10分钟",
      "block_rate": "20%",
      "success_rate": "98%"
    },
    "created_at": "2026-06-05T14:30:25.123Z"
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

### 13.7 错误码定义

| HTTP状态码 | 错误码 | 错误消息                                | 原因                                      |
|-----------|-------|----------------------------------------|------------------------------------------|
| 400       | 40001 | 缺少必填字段                             | 请求体缺少 required 字段                  |
| 400       | 40002 | 字段类型错误                             | 字段类型不符合 JSON Schema 定义           |
| 400       | 40003 | 目标年份无效                             | 年份不在合理范围（2020-2030）            |
| 401       | 40101 | 缺少认证信息                             | Header 中未包含 Authorization             |
| 401       | 40102 | Token 无效                              | Token 格式错误或已被撤销                  |
| 403       | 40303 | 无权限设置目标值                         | Token 不是 Admin 权限                    |
| 409       | 40901 | 目标值已存在                             | 该年份的目标值已设置，需先删除            |
| 500       | 50001 | 内部服务错误                             | 服务器处理异常                            |

### 13.8 目标值管理规则

**存储策略：**
- 按 (community, feature, year) 组合作为唯一键
- 每年只能设置一次目标值
- 目标值一经设置，不可修改（需先删除再重新设置）

**查询接口（v1.1计划）：**
- 查询某社区某特性当前目标值
- 查询某社区全部目标值
- 查询某年份全平台目标值

**删除接口（v1.1计划）：**
- 删除某社区某特性某年目标值
- 仅 Admin 权限可删除

### 13.9 目标值生效规则

运营看板展示时：
- 当前值与目标值对比
- 计算达成率：`当前值 / 目标值 × 100%`
- 显示进度条（绿色表示达成，黄色表示进展中）
- 未设置目标值时，不显示对比和进度条

---

**文档维护：** openLiBing 运营团队  
**联系方式：** dashboard-support@openlibing.com  
**更新日期：** 2026-06-05