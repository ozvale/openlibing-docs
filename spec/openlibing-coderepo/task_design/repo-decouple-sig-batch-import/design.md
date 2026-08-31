# 代码仓管理与项目解耦，实现仓库全局唯一与 SIG 组一键批量录入 — 技术设计

> 详细方案、类/接口/数据模型/性能/安全设计见同目录 [requirement-design.md](./requirement-design.md)，本文为归档用设计摘要。

## 方案概述

repo_info 保持「一项目一行、多行并存」，靠「提示不覆盖 + 开关 OR 聚合（下游约定）」规避配置漂移；新增项目级全局配置表承载 SIG 路径与角色映射；SIG 组通过「一键同步」按平台多路径 sig-info.yaml 批量录入（异步 + 分布式锁）。

## 架构决策

| 决策点                | 选择                                                                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| repo_info 模型        | 一项目一行、多行并存；查重 `(repo_url, project_id)` 唯一                                                                               |
| 配置同步（录入/编辑） | 复制上次配置 + 提示不一致，不覆盖其他项目行                                                                                            |
| 全局配置              | 新增 `project_repo_global_config`（每项目一行 `config_json`）；`sigInfoLocations` 按平台分键 Map；角色映射按平台分键；公共账号仍存原表 |
| sig-info 路径校验     | `validate-sig-path` 批量 paths，返回逐条结果，单条失败不阻断                                                                           |
| SIG 一键同步          | 异步 + 分布式锁 `sig_sync:{projectId}`；默认分支取自平台不可改；任务状态弹窗内轮询展示                                                 |
| 业务日志              | `updateGlobalConfig`→`UPDATE_GLOBAL_CONFIG`、`triggerSigSync`→`SYNC_SIG_REPOS`，独立 operation，记旧 config_json 与返回 data           |
| 开关聚合              | OR（MAX）聚合为下游读取约定；当前无下游调用方，聚合接口不落地                                                                          |
| 下游仓                | repo_info 层面 7 仓零改动；framework 删除级联清理改指新表                                                                              |

## 涉及文件

| 仓        | 文件                                                                                                   | 操作                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| coderepo  | `business/controller/ProjectConfigController.java`                                                     | 改：global-config / validate-sig-path / sig-sync / sig-sync-status                               |
| coderepo  | `business/service/ProjectConfigService(Impl).java`                                                     | 改/新增：getGlobalConfig/updateGlobalConfig/validateSigPath(arr)/triggerSigSync/querySigSyncTask |
| coderepo  | `business/dto/repo/GlobalConfigUpdateDTO.java`、`SigPathValidateDTO.java`、`RepoUrlCheckQueryDTO.java` | 改/新增：sigInfoLocations 为 Map、validate paths 数组                                            |
| coderepo  | `business/vo/{GlobalConfigVO,SigPathValidateVO,RepoUrlCheckVO,SyncSigReposTaskVO}.java`                | 新增                                                                                             |
| coderepo  | `business/entity/space/ProjectRepoGlobalConfigEntity.java`                                             | 新增                                                                                             |
| coderepo  | `business/mapper/{ProjectRepoGlobalConfigMapper,ProjectCommonAccountInfoMapper}.java`(+xml)            | 新增                                                                                             |
| coderepo  | `business/mapper/RepoInfoMapper.java`(+xml)                                                            | 改：新增组查询/移除聚合开关查询                                                                  |
| coderepo  | `business/service/RepoService(Impl).java`                                                              | 改：录入/编辑冲突检测、isParticipateOperation                                                    |
| coderepo  | `common/aop/ProjectLogHandler.java`、`common/constants/LogOperationAndModule.java`                     | 改：新增两个 operation 及日志数据记录                                                            |
| coderepo  | `common/utils/{SigInfoClient,SigDefaultParamBuilder,Github}.java`                                      | 新增                                                                                             |
| coderepo  | `resources/db/changelog/.../repo-decouple-sig-batch-import.xml`                                        | 新增：建表 + 迁移 + 索引                                                                         |
| framework | `business/service/impl/{Project,Product}ServiceImpl.java`、`mapper/ProjectRepoGlobalConfigMapper.java / ProjectRepoGlobalConfigMapper.xml`、`GitcodeRoleMappingMapper`                                                                | 改：删除级联清理改指新表，清理未用注入 |
| web       | `apps/web-openlibing/src/views/Repos/dialog/GlobalConfigDialog.vue` 等                                 | 改：配置弹窗 + 多路径 + 一键同步进度                                                             |

## 风险 & 缓解

- 存量共享仓多行配置漂移 → 提示不覆盖 + OR 聚合约定，不归并。
- 同步并发重复触发 → 分布式锁 + 幂等。
- config_json 整存整取并发丢更新 → global-config POST 对 projectId 加锁。
- 平台 token 泄漏 → header 传递、日志脱敏、全局配置回显仅掩码。
- 切换平台分键后旧版数组数据 → 读取兼容旧版并按域名自动归组。

## 跨仓影响

- openlibing-framework：删除产品/项目级联清理由 `project_gitcode_role_mapping` 改指 `project_repo_global_config`（建议同迭代上线）。
- 其余下游仓（codecheck/cicd/anti-poison/sca/gateway/vulnerability）零改动。
