# Pipeline Event Menu Refactor Spec

## ADDED Requirements

### Requirement: 流水线事件触发菜单独立

系统 MUST 在流水线编辑中提供独立的“流水线事件触发”菜单。

#### Scenario: 打开流水线编辑

- **Given** 用户打开流水线编辑弹窗
- **When** 用户查看左侧菜单
- **Then** 菜单包含执行计划、并发策略、PR 设置、流水线事件触发

#### Scenario: 离开二级页后返回菜单

- **Given** 用户已进入“流水线事件触发”二级编辑页
- **When** 用户切换到其他左侧菜单，再切回“流水线事件触发”
- **Then** 页面应回到一级列表页，而非停留在之前的二级编辑态

### Requirement: 使用独立数据字段

系统 MUST 通过 `pipelineEventTriggers` 读写流水线事件规则，并与 `eventTriggers` 语义解耦。

#### Scenario: 保存流水线事件

- **Given** 用户在流水线事件触发中编辑一条规则
- **When** 用户点击保存
- **Then** 请求体包含更新后的 `pipelineEventTriggers`
- **And** 旧 `eventTriggers` 语义保持不变

### Requirement: PR设置保存请求行为

系统 MUST 在 `PR设置` 菜单点击保存时发起单次保存请求。

#### Scenario: PR设置菜单有改动

- **Given** 用户在 `PR设置` 菜单修改了任一子模块字段
- **When** 用户点击保存
- **Then** 前端仅发起一次保存请求
- **And** 请求体仅包含该菜单下需要提交的字段

#### Scenario: PR设置菜单无改动

- **Given** 用户在 `PR设置` 菜单未修改任何字段
- **When** 用户点击保存
- **Then** 前端仍发起一次保存请求

### Requirement: 触发条件与事件类型约束

系统 MUST 当前仅支持 `status = "0"`（流水线失败）与 `eventType = "0"`（自动创建 Issue）。

#### Scenario: 展示触发条件

- **Given** 用户打开事件规则详情
- **When** 页面展示触发条件
- **Then** 当前版本固定为流水线失败

### Requirement: 行内校验

系统 MUST 使用行内错误提示进行校验。

#### Scenario: 必填项缺失

- **Given** 必填字段为空
- **When** 用户点击保存
- **Then** 页面展示行内错误并阻止保存

### Requirement: 事件模板接口字段适配

系统 MUST 适配模板接口字段调整：不再依赖 `title` / `titleTemplate`，并支持 `labels[]` 与 `users[]`。

#### Scenario: 模板接口返回新结构

- **Given** 模板接口返回 `descriptionTemplate`、`type`、`labels`、`users`
- **When** 页面加载模板成功
- **Then** 页面仅自动回填 `descriptionTemplate`
- **And** 不再尝试从模板回填标题

#### Scenario: 负责人选项使用 users

- **Given** 模板接口返回 `users: [{ login, name }]`
- **When** 用户在事件详情选择负责人
- **Then** 下拉列表展示 `name`
- **And** 保存值使用 `login`
- **And** 已保存的 `login` 可正确回显与筛选

#### Scenario: Label 选项使用 labels

- **Given** 模板接口返回 `labels` 数组
- **When** 用户编辑 Label
- **Then** 页面将 `labels` 作为可选项来源
- **And** 仍允许自定义创建 Label
