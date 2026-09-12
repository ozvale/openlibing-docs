# 代码仓管理与项目解耦，实现仓库全局唯一与 SIG 组一键批量录入 — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-coderepo/issues/90
- 业务 PR（coderepo）: https://gitcode.com/openlibing/openlibing-coderepo/pulls/152
- 业务 PR（framework）: https://gitcode.com/openlibing/openlibing-framework/pulls/398
- docs PR: https://gitcode.com/openlibing/openlibing-docs/pulls/855

## 交付历程

### openlibing-coderepo-fork（分支 repo-decouple-sig-batch-import）

- `4f00d52` feat(repo-decouple): 实现代码仓解耦 + SIG 仓一键同步
- `0164384` refactor(repo-decouple): 全局配置表主键改雪花算法 + 去软删除字段 + 去重复行清洗
- `96ab4b6` fix(coderepo): 修复 SIG 同步并发锁与多平台细节
- `23797c8` fix(project-config): 修复鉴权/异常兜底/平台校验问题
- `6fdc4d2` chore(project-config): sig同步内层日志补充 projectId/taskId 上下文
- `1950b5c` refactor(repo): 移除无下游调用方的内部聚合开关接口
- `6dc2869` fix(project-config): 修复全局配置NPE并改造公共账号令牌回显
- `99c5c5b` fix: guard jsonObject null in ProjectLogHandler to avoid NPE
- `22fd64c` feat(project-config): batch sig-path validate, platform-keyed sigInfoLocations, add business logs

### openlibing-framework（分支 repo-decouple-sig-batch-import）

- `073565d7` feat(repo-decouple): 级联清理改指 project_repo_global_config 新表

## 用户自测反馈

- 自测暴露 `/project-config/global-config` 在空 `oldDataJsonString` 下 `jsonObject` 为 null 触发 NPE → 修复 `ProjectLogHandler` 判空（commit `99c5c5b`），并在后续日志改造中统一兜底。
- 早期 `sigInfoLocations` 为顶层数组会导致按平台展示时需要重复解析 → 改为按平台分键 Map（commit `22fd64c`）。

## 最终验证

- openlibing-coderepo-fork：全量编译与相关单元测试通过；pre-commit（spotless/checkstyle/spotbugs/PMD）通过。
- openlibing-framework：单元测试（`ProductServiceImplTest`/`ProjectServiceImplTest`）适配通过。
- 设计文档对齐当前实现：sigInfoLocations 按平台分键、validate-sig-path 批量 paths、业务日志独立 operation、移除无下游调用的聚合开关接口。

## 设计偏差与取舍

- 开关 OR 聚合：设计层面纳入，但当前无下游调用方，聚合接口与 `aggregateSwitchByRepoUrl` 查询**未落地**（遵循「无下游调用方即不保留」）。
- `sigInfoLocations` 由「顶层数组 + 域名解析归类」改为「按平台分键 Map」，保留读取侧兼容旧版数组自动归组。
- 业务日志为新增项：为 `updateGlobalConfig`（复用 `GITCODE_ROLE_MAPPING` 语义不符）与 `triggerSigSync` 新增独立 operation。

## 可复用经验

- 优化接口设计：发少数接口承载相近功能，避免冗余；无下游调用方的新接口不保留。
- 全局配置类接口对「整存整取的读-改-写」需加分布式锁防并发丢更新。
- 审计日志切面（AOP `getOldData`/`encapsulatingLogsDetailVO`）解析空串必须判空，避免日志切面阻断业务响应。

## 归档日期

2026-08-27
