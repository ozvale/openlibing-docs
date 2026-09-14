# 代码仓管理与项目解耦，实现仓库全局唯一与 SIG 组一键批量录入

## 需求背景

同一代码仓被多个项目各自录入、各自维护，导致配置漂移；SCA 等下游仓按 `(project_id, repo_url)` 反查 `repo_info`，要求每项目必须存在独立行。同时缺少批量录入手段：SIG 组的新增仓库需要逐仓手工录入，效率低、易漏。本次将「代码仓管理」从「项目」维度解耦为「仓库全局唯一 + 按平台分组」模型，并提供 SIG 组一键批量录入能力。

## 功能描述

做什么：

- `repo_info` 保持「一项目一行、多行并存」现状模型；同一 repo_url 可跨项目多行。
- 录入时检测到同 repo_url 已在其他项目录入 → 复制上次录入配置到表单（可修改），提交时提示与之前项目配置不一致、**不覆盖**。
- 编辑时检测到同 repo_url 跨项目配置不一致 → 提示性告警、**不自动覆盖**。
- 开关类配置 OR 聚合作为下游读取约定（当前无下游调用方则不下发聚合接口）。
- 新增 `project_repo_global_config` 全局配置表（每项目一行，`config_json` 承载 sig-info 路径 + 角色映射），存量 `project_gitcode_role_mapping` 迁移后废弃。
- SIG 组一键同步：全局配置弹窗内「一键同步」异步执行 + 分布式锁，支持按平台多路径 sig-info.yaml，任务状态在弹窗内展示。
- 默认分支直接从代码托管平台获取、不可修改。

不做什么：

- 不归并存量共享仓多行（Phase 1 只清洗同项目重复行 + 加唯一索引）。
- 不改动 codecheck 下 `sig_rule_set` 等规则集表。
- repo_info 层面下游 7 仓零改动（framework 因全局配置表迁移需将删除级联清理改指新表）。

## 验收标准

- [ ] 同一 repo_url 跨项目多行并存，`(repo_url, project_id)` 唯一。
- [ ] 录入命中多行时复制上次录入配置、提交提示不一致且不覆盖其他项目行。
- [ ] 编辑命中跨项目配置不一致时提示性告警、不覆盖其他项目行。
- [ ] 项目级全局配置集中读写：sig-info 路径按平台分组、角色映射按平台分键；公共账号仍存原表。
- [ ] validate-sig-path 支持批量 paths，返回每条校验结果，单条失败不阻断。
- [ ] SIG 一键同步异步 + 分布式锁，任务状态在弹窗内可见。
- [ ] framework 删除产品/项目时级联清理改指 `project_repo_global_config`。
- [ ] `updateGlobalConfig` / `triggerSigSync` 有独立业务日志 operation 并正确记录旧/新数据。

## 影响范围

- openlibing-coderepo-fork：全局配置表与接口、SIG 一键同步、repo 录入/编辑冲突检测、业务日志。
- openlibing-framework：删除产品/项目级联清理改指新表。
- openlibing-docs：本 spec 包 + 需求设计/特性规格文档。
- （前端 openlibing-web 涉及配置弹窗与批量校验，属配套改动）
