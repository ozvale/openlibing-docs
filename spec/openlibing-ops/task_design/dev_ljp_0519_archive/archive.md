# dev_ljp_0519 — 归档

## 关联
- 业务 Issue: https://gitcode.com/openlibing/openlibing-ops/issues/32
- 业务 PR: https://gitcode.com/openlibing/openlibing-ops/merge_requests/90
- 合并 commit: `2eec897` !90 merge dev_ljp_0519 into release_20260611_iter1

## 需求概述
【PR门禁看板】社区运营指标建设 — 新增 PR E2E时长、PR 流水线启动时长、PR 合入时长、Workflow端到端时长、E2E达标率等运营指标。同步建设资源消耗看板（CPU/NPU 多级钻取）。

## 交付历程

### PR 看板新增指标
- `5a872ee` PR看板新增指标实体类修改
- `b95a79b` PR看板新增指标UT修改
- `70c95ad` PR看板新增指标service修改
- `aec6692` PR看板新增指标 codecheck 问题解决
- `d98534f` PR看板新增指标 联调问题解决
- `cdb2b2a` fix(repo): add prE2eTime sort support for PR detail query

### 资源消耗看板
- `0ac10e7` 测试资源缺少用例成功数、总npu消耗
- `4930edd` 测试资源缺少用例成功数、总npu消耗
- `d2efc08` 导出Excel顺序调整

### 代码仓 CI 配置
- `1ca4971` 代码仓CI时间配置

### 质量修复
- `7ab4091` codecheck问题修复
- `f435e95` codecheck问题修复

## 最终验证
- PR CI 通过（ci-pipeline-passed、approved、lgtm）
- 已合入 release_20260611_iter1（commit `2eec897`）

## 设计文档（本地）
归档阶段的设计文档位于 `openlibing-ops/docs/202605/`：
- `E2E目标配置开发方案.md` — E2E 目标时长配置表设计、分层架构
- `E2E目标配置API接口文档.md` — 前端 API 说明
- `PR_E2E时长和达标率开发方案.md` — E2E 时长 & 达标率计算方案（ETL+Java）
- `PR看板新增指标开发方案.md` — 4 个新指标的 DDL/实体/响应/XML 设计
- `PR看板新增指标.md` — 早期需求笔记
- `resource-dashboard-api-design.md` — 资源消耗看板后端接口方案
- `resource-dashboard-api-doc.md` — 资源消耗看板前端 API 接口文档

## 可复用经验
- 无

## 归档日期
2026-06-15
