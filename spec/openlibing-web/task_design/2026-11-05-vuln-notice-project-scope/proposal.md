# 需求背景

## 业务场景

发布评审 → 评审详情页（`reviewDetail.vue`）→ 漏洞公告区块。当前仅 MindCluster（`projectId = 300038`）与 openLiBing（`projectId = 3`）两个项目的发布评审详情页展示"漏洞公告"表单，其他业务线项目在发布评审时无法维护漏洞公告信息。

## 问题痛点

1. **覆盖项目过少**：MindIE、MindStudio、MindSporeOpenSource、MindSpeed、AscendForPyTorch 等项目同样需要发布漏洞公告，但详情页不展示表单，只能线下维护。
2. **判断逻辑硬编码**：显示条件为 `pid === 3 || pid === 300038` 的双值判断，新增项目需要改动逻辑，易漏改。

## 需求目标

将漏洞公告表单的显示范围扩展为项目白名单，覆盖 MindCluster、openLiBing、MindIE、MindStudio、MindSporeOpenSource、MindSpeed、AscendForPyTorch 共 7 个项目，并将判定方式改为白名单数组匹配，便于后续扩展。

## 验收标准

### 功能验收

1. 使用 `projectId` 为 `300038`、`3`、`300036`、`300037`、`300062`、`300091`、`4` 的项目进入发布评审详情页，均展示"漏洞公告"表单
2. 使用其他项目进入发布评审详情页，不展示"漏洞公告"表单
3. 漏洞公告表单原有填写、保存、提交能力不受影响

### 非功能验收

1. 不改变漏洞公告表单的字段、校验与提交逻辑
2. 代码变更符合项目编码规范，通过 Prettier / ESLint / pre-commit 检查

## 关联 Issue

[openlibing/openlibing-platform-release#88](https://gitcode.com/openlibing/openlibing-platform-release/issues/88)

## 期望交付时间

2026-11-05
