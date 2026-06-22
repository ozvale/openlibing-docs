# openLiBing 运营看板项目上下文交接摘要

**会话日期：** 2026-06-05  
**提交分支：** `spec-temp-designs`（openlibing-docs 仓）  
**提交次数：** 11次  

---

## 一、涉及的仓库

| 仓库名称              | 仓库性质         | 作用                                    | Git状态          |
|---------------------|----------------|----------------------------------------|-----------------|
| openlibing-docs     | 组织级文档仓     | 存放设计文档、接口规范、实施计划           | ✅ 已提交到分支   |
| ops-dashboard-demo  | 临时Demo项目     | 运营看板前端静态页面Demo（不属于任何现有仓） | ⚠️ 本地文件，未纳入git |

**仓库路径：**
- openlibing-docs: `D:\Git\openLiBing\openlibing-docs\`
- ops-dashboard-demo: `D:\Git\openLiBing\ops-dashboard-demo\`

---

## 二、本次生成的关键文件路径

### 2.1 设计与文档文件（已提交到 git）

| 文件路径                                                        | 文件类型       | 说明                                    |
|----------------------------------------------------------------|---------------|----------------------------------------|
| openlibing-docs/temp_designs/2026-06-05-ops-dashboard-design.md | 设计文档       | 运营看板完整设计文档（548行）             |
| openlibing-docs/docs/plans/2026-06-05-ops-dashboard.md        | 实施计划       | 运营看板实施计划（14任务，113步骤）        |
| openlibing-docs/temp_designs/dashboard-report-api-spec.md     | 接口规范       | 数据上报与自定义运营指标接口规范（1220行）  |

### 2.2 Demo项目文件（本地文件，未提交 git）

| 文件路径                                        | 文件类型       | 说明                                    |
|------------------------------------------------|---------------|----------------------------------------|
| ops-dashboard-demo/index.html                  | HTML          | 主页面骨架（87行）                        |
| ops-dashboard-demo/styles/main.css            | CSS           | 样式文件（344行）                        |
| ops-dashboard-demo/scripts/data.js            | JavaScript    | Mock数据生成（118行）                    |
| ops-dashboard-demo/scripts/main.js            | JavaScript    | 主逻辑脚本（145行）                      |
| ops-dashboard-demo/README.md                  | 文档          | 项目说明（71行）                        |

**Demo项目统计：**
- 总文件数：5个
- 总代码行数：665行
- 技术栈：HTML5 + CSS3 + JavaScript（原生）

---

## 三、最终方案摘要

### 3.1 运营看板设计方案

**核心定位：**
- 用途：运营跟踪管理工具
- 用户：运营团队（查看各社区对接进展）
- 风格：数据可视化风格，浅色蓝白主题

**页面结构：**
- 表格矩阵布局：9个开源社区 × 11个openLiBing特性
- 状态灯指示：绿色（已使用）、黄色（对接中）、灰色（未使用）
- 详情卡片：点击状态灯展示用户指标 + 业务指标

**开源社区（9个）：**
- MindIE、PTA、MindSpeed、openEuler、HPCkit、UBS Core、openUBMC、CANN、openLiBing

**openLiBing特性（11个）：**
- 门禁检查、接口兼容性、流水线、测试框架、SBOM、漏洞视图、发布评审、工具市场、AI agent、Skill市场、数字化运营看板

**视觉设计：**
- 主背景色：#f0f9ff（浅蓝灰）
- 表格背景：白色
- 状态灯：径向渐变 + 外发光效果
- 响应式：横向滚动 + 社区列固定

### 3.2 运营看板Demo实现方案

**技术栈：**
- HTML5：页面结构
- CSS3：Grid/Flexbox布局、渐变、动画
- JavaScript：原生JS，无依赖

**核心功能：**
- ✅ 表格渲染：动态生成9行×12列矩阵
- ✅ 状态灯：三种颜色（绿/黄/灰）带渐变和光晕
- ✅ 详情卡片：用户指标（UV/PV）+ 业务指标
- ✅ 关闭模态框：4种方式（按钮/图标/遮罩/ESC）
- ✅ Mock数据：99条记录（9×11），随机生成

**文件结构：**
```
ops-dashboard-demo/
├── index.html
├── styles/main.css
├── scripts/data.js
├── scripts/main.js
└── README.md
```

### 3.3 数据上报接口方案

**接口地址：** `POST /api/v1/dashboard/report`

**业务场景：**
- 上报主体：各开源社区业务团队
- 上报内容：前24小时（昨日）推广数据
- 上报频率：每日定时上报一次（建议凌晨01:00）

**请求字段（精简版）：**

| 字段             | 必填 | 说明                                    |
|-----------------|------|-----------------------------------------|
| community       | 否   | 开源社区名称（可选）                     |
| repo            | 否   | 代码仓链接（后端自动关联社区）            |
| feature         | 是   | openLiBing特性名称                      |
| user_metrics    | 是   | 用户指标（UV/PV，支持count/rate两种格式） |
| business_metrics| 是   | 业务指标（key-value，支持count/rate两种格式） |
| timestamp       | 否   | 数据采集时间（ISO 8601）                 |

**关键特性：**
1. **repo字段支持**：可传代码仓链接，后端自动确认community
2. **rate类型指标**：当aggregation_type=rate时，上报格式为 numerator/denominator对象
3. **去掉的字段**：status、reporter、notes、target_value

**请求示例：**
```json
{
  "repo": "https://gitcode.com/mindie/mindie-core",
  "feature": "门禁检查",
  "user_metrics": {
    "uv": 156,
    "pv": 1234
  },
  "business_metrics": {
    "avg_duration": "12.5分钟",
    "success_rate": {
      "numerator": 145,
      "denominator": 150
    }
  }
}
```

### 3.4 自定义运营指标接口方案

**接口地址：** `POST /api/v1/dashboard/metrics`

**使用角色：** 运营团队（需Admin Token）

**请求字段（批量支持）：**

| 字段             | 必填 | 说明                                    |
|-----------------|------|-----------------------------------------|
| feature         | 是   | 特性名称                                |
| metric_type     | 是   | 指标类型（user_metric/business_metric）  |
| metric_name     | 是   | 指标名称                                |
| metric_key      | 是   | 指标标识（对应上报接口的key）             |
| aggregation_type| 是   | 统计方式（count/rate）                   |
| target_value    | 是   | 指标目标值                              |
| description     | 否   | 指标说明（计算公式等）                    |

**关键特性：**
1. **批量支持**：一次定义最多50个指标
2. **aggregation_type枚举**：count（计数统计）、rate（比率计算）
3. **与数据上报联动**：rate类型指标，上报时必须传 numerator/denominator对象

**请求示例：**
```json
{
  "metrics": [
    {
      "feature": "门禁检查",
      "metric_type": "business_metric",
      "metric_name": "成功率",
      "metric_key": "success_rate",
      "aggregation_type": "rate",
      "target_value": "98%",
      "description": "分子：成功次数，分母：总次数"
    }
  ]
}
```

---

## 四、接口关系说明

### 4.1 两接口协同关系

```
运营团队（定义指标配置）
    ↓
POST /api/v1/dashboard/metrics
(aggregation_type: rate, target: "98%")
    ↓
开源社区（每日上报数据）
    ↓
POST /api/v1/dashboard/report
(success_rate: { numerator: 145, denominator: 150 })
    ↓
运营看板前端（查询展示）
    ↓
当前值：145/150 = 96.7%
目标值：98%
达成率：96.7/98 = 98.7%
```

### 4.2 aggregation_type与数据格式对应

| aggregation_type | 数据上报格式                                | 适用指标                                |
|------------------|-------------------------------------------|----------------------------------------|
| count            | 整数或字符串                                | UV、PV、执行次数、平均时长                |
| rate             | numerator/denominator对象                 | 成功率、覆盖率、通过率                    |

---

## 五、后续扩展建议

### 5.1 Demo项目后续

**建议动作：**
1. 在浏览器中打开 `ops-dashboard-demo/index.html` 完整验收
2. 决定归属仓库（建议集成到 `openlibing-ops-web` 或独立仓）
3. 对接真实数据源（替换Mock数据）

### 5.2 接口后续

**建议动作：**
1. 后端实现两个接口（Spring Boot / Express.js）
2. 维护代码仓与社区关联表（repo -> community映射）
3. 实现时间段筛选统计逻辑（count累加、rate分子分母累加）
4. 前端集成：查询配置+数据，展示进度条和达成率

**未来版本（v1.1）：**
- 批量上报接口（一次上报多个特性）
- 查询接口（查询历史数据、指标配置）
- 删除接口（删除指标配置）

---

## 六、Git提交历史

**分支：** `spec-temp-designs`（openlibing-docs 仓）

**提交记录：**

| Commit SHA | 提交说明                                    |
|-----------|-------------------------------------------|
| 1b6abb7   | 新增repo字段，aggregation_type改为count/rate |
| 2abd4d7   | 新增自定义运营指标接口（替换目标值设置接口）   |
| ed20d2d   | 去掉数据上报接口的reporter和notes字段        |
| 34ff3b7   | 去掉数据上报接口的status字段                |
| b9b9345   | 补充每日定时上报业务场景说明                 |
| 09e94ca   | 分离当前值和目标值上报                      |
| 7def087   | 新增数据上报接口规范                        |
| 17159ab   | 新增运营看板实施计划                        |
| 5fe0e98   | 新增运营看板设计文档                        |

---

## 七、关键决策记录

| 决策点                   | 最终决策                                    | 理由                                      |
|-------------------------|--------------------------------------------|------------------------------------------|
| 看板用途                 | 运营跟踪管理                                 | 用于运营团队跟踪各社区对接进展              |
| 技术方案                 | 纯前端静态页面                               | 简单轻量，无需后端，快速Demo              |
| 视觉风格                 | 浅色蓝白主题                                 | 状态灯在白色背景下更醒目                  |
| 状态展示                 | 去掉status字段                               | 状态可由前端根据数据值自动推断              |
| 目标值管理               | 自定义运营指标接口（批量）                     | 支持灵活定义多种指标，包含统计方式          |
| 统计方式                 | count/rate                                  | rate类型支持分子分母计算                  |
| community字段            | 可选，新增repo字段                            | 后端自动关联代码仓与社区                  |

---

## 八、待办事项

**优先级：高**

| 待办事项                   | 负责方       | 说明                                    |
|---------------------------|-------------|----------------------------------------|
| 浏览器验收Demo              | 用户         | 打开index.html完整验收功能               |
| 决定Demo归属仓              | 用户         | 选择集成到现有仓或创建独立仓              |
| 后端接口实现                | 后端团队     | 实现两个接口 + 代码仓关联逻辑             |
| 前端集成                    | 前端团队     | 查询配置+数据，展示进度条                |

**优先级：中**

| 待办事项                   | 负责方       | 说明                                    |
|---------------------------|-------------|----------------------------------------|
| 维护代码仓映射表            | 运营团队     | 配置repo与community关联关系              |
| 对接真实数据源              | 业务团队     | 替换Mock数据，每日定时上报               |

---

**交接完成日期：** 2026-06-05  
**交接人：** Claude Code (AI Assistant)  
**接收人：** 运营团队 + 开发团队