# 发布评审单撤回功能 — 任务分解

**日期**: 2026-08-04

## Phase 1: 需求

- [x] brainstorming — 需求澄清（线上/线下评审均支持，不重置评审项）
- [x] proposal.md — 需求背景 + 验收标准
- [x] design.md — 技术方案 + 影响范围

## Phase 2: 开发

- [x] task-1: Controller 新增 `POST /base/withdrawReleaseReview` 接口
- [x] task-2: Service 接口新增 `withdrawReleaseReview` 方法声明
- [x] task-3: Service 实现新增 `withdrawReleaseReview` 方法
  - [x] 存在性校验
  - [x] 权限校验（仅 creatorId）
  - [x] 所有状态回退到 SAVE
  - [x] 不触碰评审项表

## Phase 3: 质量门禁

- [x] pre-commit 全量门禁通过（Spotless/CheckStyle/SpotBugs/PMD）
- [ ] build — `mvn compile`
- [ ] 自测

## Phase 4: 交付

- [x] commit — feat(review): add withdraw release review interface
- [ ] PR — 关联 Issue + ai-assisted 标签
- [ ] Review
- [ ] 归档 — archive/
