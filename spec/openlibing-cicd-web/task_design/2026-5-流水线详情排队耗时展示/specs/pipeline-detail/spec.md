# Pipeline Detail Queue Time Display Spec

## ADDED Requirements

### Requirement: 在流水线详情展示任务排队时长

系统 MUST 在流水线详情页展示任务（Job）级排队时长。

#### Scenario: 任务存在排队时长

- **Given** `detail` 返回 `stages[].jobs[].job_queue_time`
- **When** 用户查看任务卡片
- **Then** 页面展示可读格式的排队时长

#### Scenario: 任务无排队时长

- **Given** `job_queue_time` 缺失或为空
- **When** 用户查看任务卡片
- **Then** 页面不渲染排队时长项

### Requirement: 在任务抽屉展示步骤排队时长

系统 MUST 在任务抽屉中展示步骤（Step）级排队时长。

#### Scenario: 步骤存在排队时长

- **Given** `detail` 返回 `stages[].jobs[].steps[].job_queue_time`
- **When** 用户打开任务抽屉
- **Then** 每个步骤展示对应排队时长

#### Scenario: 步骤无排队时长

- **Given** 步骤 `job_queue_time` 缺失或为空
- **When** 用户查看步骤行
- **Then** 页面不渲染排队时长项

### Requirement: 任务抽屉全屏按钮状态可辨识

系统 MUST 在任务抽屉头部根据全屏状态展示不同图标。

#### Scenario: 非全屏状态

- **Given** 任务抽屉当前为非全屏状态
- **When** 用户查看头部全屏按钮
- **Then** 显示进入全屏图标

#### Scenario: 全屏状态

- **Given** 任务抽屉当前为全屏状态
- **When** 用户查看头部全屏按钮
- **Then** 显示退出全屏图标

### Requirement: 排队与执行时长并列展示

系统 MUST 保留执行时长展示，并与排队时长并列呈现。

#### Scenario: 两项时长都存在

- **Given** 排队时长与执行时长同时存在
- **When** 用户查看时长区域
- **Then** 页面清晰展示两者

#### Scenario: 展示顺序与图标

- **Given** 排队时长与执行时长同时存在
- **When** 页面渲染紧凑时长
- **Then** 顺序为 `排队 / 执行`
- **And** 排队使用 `Timer`，执行使用 `Clock`

#### Scenario: 时长为 0

- **Given** 排队或执行时长格式化后为 `0s`
- **When** 页面渲染时长
- **Then** 该项不渲染

#### Scenario: tooltip 与对齐

- **Given** 页面展示时长区域
- **When** 用户悬浮时长块
- **Then** tooltip 以两行显示排队与执行时长（仅存在项）
- **And** 主视图时长块右对齐
