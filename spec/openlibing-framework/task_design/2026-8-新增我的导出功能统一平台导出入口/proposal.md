# 新增《我的导出》功能，统一平台导出入口

## 需求背景

当前各业务仓（cicd、codecheck 等）的导出能力各自为战：导出任务记录、文件上传下载、状态查询、过期清理等逻辑分散在各仓实现，缺少统一入口与统一的任务记录管理，维护成本高、体验不一致。

本需求在 openlibing-framework 仓建设统一的《我的导出》能力：提供统一的导出任务创建/查询/更新/下载签名接口与 OBS 文件记录管理，供 codecheck、cicd 等业务仓通过 Feign 复用，实现平台导出入口统一。

## 功能描述

### 做什么

1. **framework 建设统一导出能力**：新增 `/export/*` 接口群（list/detail/download-url 对外，internal-server create/update/query 对内），新增 `obs_file` 导出记录表（Liquibase changelog 落库）与过期清理任务，导出状态统一由 `ExportStatus` 枚举管理。
2. **codecheck 静态告警导出适配**：删除本地导出记录表、状态枚举与桶配置，改为调用 framework 统一导出接口，XxlJob 批量导出改造。
3. **cicd 流水线/测试用例导出迁移**：删除本地 `FileExportLog` 导出记录表与下载/状态刷新接口，导出文件上传改为分片上传并回填 framework 状态。
4. **工程改造**：common-sdk 升级至 1.0.20.4，配置中心 Apollo → Nacos 迁移。

### 不做什么

1. 不改造导出文件内容本身的生成逻辑（各业务仓自行负责业务数据组装）。
2. 不迁移历史已存在的导出记录数据（各仓本地导出表下线后不再保留）。
3. 不做前端《我的导出》页面的具体交互实现（本需求为后端能力建设与接口收敛）。
4. 不改变 OBS 依赖（复用既有华为云 OBS，仅收敛接入方式）。

## 验收标准

- [x] framework 提供统一导出任务创建/查询/下载签名等接口
- [x] `obs_file` 表结构通过 Liquibase changelog 落库
- [x] 导出任务记录支持按过期时间定时清理（含 OBS 对象文件）
- [x] codecheck 静态告警导出、cicd 流水线/测试用例导出均改为调用 framework 统一导出
- [x] codecheck、cicd 删除本地导出记录表及下载/状态刷新接口
- [x] 各环境（beta/gama/prod）配置迁移至 Nacos，移除 Apollo 依赖
- [x] common-sdk 升级至 1.0.20.4，编译与单元测试通过

## 影响范围

- **openlibing-framework**：统一导出能力建设（新增 6 接口 + obs_file 表 + 清理任务 + Nacos 迁移）
- **openlibing-codecheck**：静态告警导出适配（删除本地导出表/状态枚举，改用框架）
- **openlibing-cicd**：流水线/测试用例导出迁移（删除 FileExportLog 系列，改用框架）
- **数据库**：新增 `obs_file` 表（Liquibase changelog `20260820_create_table_obs_file`）

## 关联

- 业务 Issue: openlibing/openlibing-framework#94（需求总锚点）、openlibing/openlibing-codecheck#177、openlibing/openlibing-cicd#213
- 业务 PR: openlibing/openlibing-codecheck#318（已合入 release_20260831_iter2）、openlibing/openlibing-cicd#553
