# 需求背景

## 业务场景

发布评审 → 评审详情页 → 基本信息组件（`basicInformation.vue`）中的"评审专家"下拉选项通过 `getUserOptions` 接口获取用户列表，展示 `userName` 供评审组织者选择。

## 问题痛点

1. **重名用户无法区分**：下拉选项仅展示 `userName`，当组织内存在同名用户时，评审组织者无法通过姓名区分目标用户，可能选错评审专家

## 需求目标

在用户列表接口返回后，将 `userName` 格式化为 `userName（userId）`，使评审专家下拉选项同时展示用户名和用户 ID，便于精确识别。

## 验收标准

### 功能验收

1. **下拉选项展示格式**
   - 评审专家下拉选项显示为 `用户名（用户ID）` 格式
   - 用户 ID 来自接口返回的 `userId` 字段

2. **过滤逻辑不受影响**
   - 当前登录用户仍被正确过滤排除，不出现在评审专家候选列表中

### 非功能验收

1. 不影响 `getUserOptions` 接口调用和返回数据的其他字段
2. 不影响基本信息组件中其他表单项的正常交互
3. 代码变更符合项目编码规范

## 关联Issue

[openlibing/openlibing-platform-release#79](https://gitcode.com/openlibing/openlibing-platform-release/issues/79)

## 期望交付时间

2026-09-10
