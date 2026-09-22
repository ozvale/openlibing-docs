# #1 代码仓社区issue自动建服务单至uniticket系统相关功能需求设计

## 1. 基础信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/18
* **需求名称**: 【运营】openlibing代码仓社区issue自动建服务单至uniticket系统
* **开发责任人**: lizelin

---

## 2. 需求场景说明

> 在蓝区的GitCode代码仓中，当开发人员或测试人员新建一个Issue（例如：缺陷报告、功能需求）时，需要自动在黄区的UniTicket工单系统中创建一个对应的服务单、事件单。目的是将开发环节中发现的问题或需求，无缝对接到运维或服务管理流程中，实现研发与运维的流程贯通和信息同步。

## 3 需求验收标准

> 用户有权限情况下，在已配置好的GitCode代码仓中新建issue并打上infra-tooling标签，则自动在UniTicket系统创建一个对应的工单。


## 4. 需求设计与分解

### 4.1 核心逻辑方案
#### 4.1.1 架构设计

**架构流程**：
1. 通过libing-framework中机机接口对GitCode代码仓配置webhook，当有Issue事件时触发
2. libing-framework后端服务接收webhook请求，验证事件类型和签名
3. 解析Issue信息，验证操作行为和标签
4. 查询仓库配置信息
5. 验证工单是否已存在
6. 初始化uniportal登录获取Cookie
7. 调用UniTicket系统API创建工单
8. 保存工单任务记录

**组件交互**：
- GitCode平台：触发Issue事件webhook
- 后端服务：处理webhook请求，调用UniTicket API
- UniTicket系统：接收工单创建请求
- 数据库：存储仓库配置和工单任务记录

#### 4.1.2 数据库设计

**表名：ticket_issue_repo_ci**

| 字段名 | 数据类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| id | INT(10) | PRIMARY KEY, NOT NULL | 唯一标识 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| update_time | DATETIME | NOT NULL | 更新时间 |
| del_flag | TINYINT(1) | NOT NULL | 删除标识 (0: 未删除, 1: 已删除) |
| owner | VARCHAR(50) | - | 仓库所属空间地址 |
| repo | VARCHAR(50) | - | 仓库路径 |
| webhook_secret | VARCHAR(255) | - | webhook签名密钥（加密存储） |
| webhook_id | VARCHAR(255) | - | webhook ID |
| system_id | VARCHAR(255) | - | CI/应用/模块ID |
| system_name_zh | VARCHAR(255) | - | 模块名称 (中文名) |
| system_name_en | VARCHAR(255) | - | 模块名称 (英文名) |
| system_type | VARCHAR(255) | - | 提单方式: CI: 按CI提单; MODULE: 按模块提单; TOOL: 按工具提单; HIS_SERVICE: 按HIS应用服务提单 |
| request_user_id | VARCHAR(255) | - | 工单归属人 |

**表名：ticket_ci_supporter**

| 字段名 | 数据类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| id | INT(10) | PRIMARY KEY, NOT NULL | 唯一标识 |
| create_time | DATETIME | NOT NULL | 创建时间 |
| update_time | DATETIME | NOT NULL | 更新时间 |
| del_flag | TINYINT(1) | NOT NULL | 删除标识 (0: 未删除, 1: 已删除) |
| system_id | VARCHAR(255) | - | CI/应用/模块ID |
| supporter | VARCHAR(255) | - | 支持人 |

**表名：ticket_task**

| 字段名 | 数据类型 | 约束 | 描述 |
| :--- | :--- | :--- | :--- |
| id | INT(10) | PRIMARY KEY, NOT NULL | 唯一标识 |
| del_flag | TINYINT(1) | NOT NULL | 删除标识 (0: 未删除, 1: 已删除) |
| create_time | DATETIME | NOT NULL | 创建时间 |
| update_time | DATETIME | NOT NULL | 更新时间 |
| owner | VARCHAR(50) | - | 仓库所属空间地址 |
| repo | VARCHAR(50) | - | 仓库路径 |
| title | VARCHAR(255) | - | 标题 |
| description | VARCHAR(255) | - | 问题描述 |
| issue_id | VARCHAR(255) | - | issueId |
| system_id | VARCHAR(255) | - | CI/应用/模块ID |
| supporter | VARCHAR(255) | - | 支持人 |
| create_service_status | TINYINT(1) | - | 创建服务单状态 (0失败/1成功) |
| task_query_status | TINYINT(1) | - | 查询任务状态 (0待执行, 1执行中, 2执行结束) |
| task_fail_count | TINYINT(1) | - | 失败次数 |
| service_status | VARCHAR(50) | - | 服务单状态 |
| incident_id | VARCHAR(50) | - | 生成的事件单号 |
| solution | VARCHAR(255) | - | 解决方案 |

##### 4.1.3 配置项
| 配置项                             | 说明           | 默认值                                        |
|---------------------------------|--------------|--------------------------------------------|
| issue.webhook.ticket.info       | 工单系统配置信息 | JSON格式，包含addTicketUrl、defaultLabel、uniportalUrl、w3Account、w3Password、gitcodeApiUrl、gitcodeCommonToken、webhookUrl等 |
| security.part1                  | 加密密钥部分1 | -                                          |



##### 4.1.4 实现逻辑

1. **Webhook配置**：通过`addRepoWebhookCi`接口为GitCode仓库配置webhook，设置回调地址和签名密钥
2. **Issue事件处理**：
   - 接收GitCode的Issue事件webhook请求
   - 验证事件类型为"Issue Hook"
   - 验证签名是否正确
   - 解析Issue信息，包括owner、repo、issueId、标题、描述等
   - 验证操作行为为"open"或"update"
   - 验证Issue是否包含指定标签
   - 查询仓库配置信息
   - 验证工单是否已存在
   - 调用UniTicket API创建工单
   - 保存工单任务记录

#### 4.1.5 接口设计

##### 4.1.5.1 处理Issue事件WebHook接口
- **URL**: `/manage/ticketIssue/hooks/gitcode/handleIssueEvent`
- **方法**: POST
- **参数**:
    - 请求头：X-GitCode-Event, X-GitCode-Signature-256
    - 请求体：GitCode Issue事件payload（JSON字符串）
- **返回**: `DataResult<String>` - 返回创建的工单系统ID

##### 4.1.5.2 创建仓库webhook接口
- **URL**: `/manage/ticketIssue/addRepoWebhookCi`
- **方法**: POST
- **参数**:
    - 请求体：`TicketIssueRepoCiDTO`对象，包含仓库URL、系统信息、支持人列表等
- **返回**: `DataResult<Integer>` - 返回仓库配置ID


---

