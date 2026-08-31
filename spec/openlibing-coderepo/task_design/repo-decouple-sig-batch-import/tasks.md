# 代码仓管理与项目解耦，实现仓库全局唯一与 SIG 组一键批量录入 — 实现任务

## 进度：已完成（交付/归档）

- [x] `repo_info` 增加 `is_participate_operation` 字段与 `(repo_url, project_id)` 唯一索引（changeLog）。
- [x] 新增 `project_repo_global_config` 表（每项目一行 `config_json`），存量 `project_gitcode_role_mapping` 数据迁移后旧表废弃（Liquibase changeSet，幂等）。
- [x] 全局配置读写：`getGlobalConfig` / `updateGlobalConfig`（唯一写入口，含公共账号更新并入 + projectId 分布式锁）；`sigInfoLocations` 按平台分键 Map，保存校验 URL 域名与平台键一致。
- [x] `validateSigPath` 批量 paths 校验，返回逐条结果，单条失败不阻断。
- [x] SIG 一键同步：`triggerSigSync`（异步 + 分布式锁）+ `querySigSyncTask`（任务状态查询），按平台多路径 sig-info.yaml，默认参数填充。
- [x] repo 录入/编辑冲突检测：`checkRepoUrl`（复制上次配置 + 提示不覆盖）。
- [x] AGENTS：移除无下游调用方的内部聚合开关接口。
- [x] 业务日志：`UPDATE_GLOBAL_CONFIG` / `SYNC_SIG_REPOS` 独立 operation，`ProjectLogHandler` 记录旧配置与返回 data。
- [x] framework：删除产品/项目级联清理改指新表 `project_repo_global_config`，清理未用注入。
- [x] 前端：全局配置弹窗多路径配置 + 批量路径校验 + 一键同步任务状态展示（配套）。
- [x] 需求设计文档/特性规格/front-end api/归档 spec 更新。
