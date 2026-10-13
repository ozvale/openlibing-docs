# 【openLiBing】数据级权限管控能力建设（权限组）— 归档

> 归档性质说明：本文件为 Phase 5 归档（2026-10-13 用户触发）。后端开发已全部完成；业务 MR #453 / #583 合入与 BETA 部署验证进行中（见"最终验证"），前端实施与产品文案终审为后续独立节奏。

## 关联

- 业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/223>
- framework MR #453（基础能力 + 护栏 + 通用端点 + 分页）：<https://gitcode.com/openlibing/openlibing-framework/merge_requests/453>
- cicd MR #583（鉴权适配 + 拆除 + 4030001）：<https://gitcode.com/openlibing/openlibing-cicd/merge_requests/583>
- docs MR #932（本 spec 归档）：<https://gitcode.com/openlibing/openlibing-docs/merge_requests/932>

## 交付历程

### framework 仓（feat/perm-scheme → MR #453，按里程碑）

- commit [`a2e4d558`](https://gitcode.com/openlibing/openlibing-framework/commit/a2e4d558)：Liquibase 加列 `perm_group_id` + 建表 `perm_group` / `perm_group_resource_binding`（F1）
- commit [`9b2f9d65`](https://gitcode.com/openlibing/openlibing-framework/commit/9b2f9d65)：Entity + Mapper + 组过滤成员查询（F2）
- commit [`367b72ac`](https://gitcode.com/openlibing/openlibing-framework/commit/367b72ac) / [`2d2f5ebd`](https://gitcode.com/openlibing/openlibing-framework/commit/2d2f5ebd)：组管理 / 绑定关系 Service（F3/F4）
- commit [`4e43c6b4`](https://gitcode.com/openlibing/openlibing-framework/commit/4e43c6b4)：PermGroupController 9 接口（F5）
- commit [`4af3e369`](https://gitcode.com/openlibing/openlibing-framework/commit/4af3e369) / [`b4380339`](https://gitcode.com/openlibing/openlibing-framework/commit/b4380339)：成员管理复用存量链路 + 一页化增强（2026/09/16 定案落地，平行成员接口净删除）
- commit [`81ebb5d7`](https://gitcode.com/openlibing/openlibing-framework/commit/81ebb5d7) / [`6414cec8`](https://gitcode.com/openlibing/openlibing-framework/commit/6414cec8) / [`39a6a93e`](https://gitcode.com/openlibing/openlibing-framework/commit/39a6a93e) / [`db6472ad`](https://gitcode.com/openlibing/openlibing-framework/commit/db6472ad)：存量 SQL 全量审计整改——8 条 SQL 固定滤组 + 15 处 Java 调用点 `setPermGroupId(0L)`（F6，含复审修复鉴权链 queryInfo 扩权漏洞）
- commit [`a0f3f738`](https://gitcode.com/openlibing/openlibing-framework/commit/a0f3f738)：内部 RPC 查询接口 `InternalPermGroupController`（R1）
- commit [`f671e6e1`](https://gitcode.com/openlibing/openlibing-framework/commit/f671e6e1)：穿透口径扩为三全局角色（admin/super_admin/platform_operater）
- commit [`0f7fae7c`](https://gitcode.com/openlibing/openlibing-framework/commit/0f7fae7c)：update-group 修改组名与说明
- commit [`7a43d6c1`](https://gitcode.com/openlibing/openlibing-framework/commit/7a43d6c1)：bind-resource 支持 permGroupId=0 移回默认组
- commit [`8bd7fc32`](https://gitcode.com/openlibing/openlibing-framework/commit/8bd7fc32)：组内 repo 级行排除护栏（F8，design.md 安全设计 #9）
- commit [`ae91a740`](https://gitcode.com/openlibing/openlibing-framework/commit/ae91a740)：通用资源权限端点 `query-resource-permissions`（F9）
- commit [`8fc4fce7`](https://gitcode.com/openlibing/openlibing-framework/commit/8fc4fce7)：绑定资源列表分页与筛选（F10，含 4 个单测用例）

### cicd 仓（feat/perm-scheme → MR #583，按里程碑）

- commit [`c844e529c`](https://gitcode.com/openlibing/openlibing-cicd/commit/c844e529c)：组鉴权 SQL `hasPermissionByGroup`（最终落点 framework UserRoleMapper，随 RPC 化迁移）
- commit [`3eafd9904`](https://gitcode.com/openlibing/openlibing-cicd/commit/3eafd9904)：AuthInterceptor 资源级鉴权分支（C3）
- commit [`b5f59a7a2`](https://gitcode.com/openlibing/openlibing-cicd/commit/b5f59a7a2)：存量角色过滤查询补 `perm_group_id=0`（C4）
- commit [`804a633b3`](https://gitcode.com/openlibing/openlibing-cicd/commit/804a633b3) / [`be32c5ed1`](https://gitcode.com/openlibing/openlibing-cicd/commit/be32c5ed1)：Feign 客户端 + OkHttp 连接池；组查询全量切换 RPC、本地直查废弃（R2）
- commit [`1e1e6ed8e`](https://gitcode.com/openlibing/openlibing-cicd/commit/1e1e6ed8e)：2 参 `getPipelineDetail` 恢复独立实现（内部 6 处调用方不触发绑定查询）
- commit [`d428f1e6a`](https://gitcode.com/openlibing/openlibing-cicd/commit/d428f1e6a)：拆除内联字段与专用列表端点（C7，已部署 BETA）
- commit [`20ca0829b`](https://gitcode.com/openlibing/openlibing-cicd/commit/20ca0829b)：组拒绝响应改用业务码 4030001（C8，已 merge develop 待部署）

### docs 仓

- commit [`ee7d3d35`](https://gitcode.com/openlibing/openlibing-docs/commit/ee7d3d35)：spec 同步实现定案与审计结果
- commit [`4ae61a26`](https://gitcode.com/openlibing/openlibing-docs/commit/4ae61a26)：护栏定案（design #9 + tasks F8）
- 本归档 commit：三定案补录（通用端点 / 4030001 / 分页）+ api.md + archive.md

## 用户自测反馈

- **组内成员按钮误灰**（chenning 场景）：全局矩阵只认默认组角色，绑定资源按钮需资源级口径 → 定案 framework 通用端点双通道判定，cicd 内联字段拆除（`ae91a740` + `d428f1e6a`）
- **403 提示无法区分权限逻辑**：先定 errorCode 透传方案（common 包 DataResult 加字段），因需蹭 common 发版改为业务码 4030001 纯 cicd 仓方案（`20ca0829b`）；common 仓 feat/dataresult-error-code 分支删除、交还同事，Issue #223 发勘误评论声明方案废弃
- **绑定资源列表千级渲染风险**：趁未上线改服务端分页 + 筛选（framework `8fc4fce7`），resourceName 定案只搜展示名不搜 id
- 审视/评审修复：RPC 缓存与超时配置、半填充不回滚、N+1、查询列缺失、实体映射恒 null 等（见两仓 commit 明细）

## 最终验证

- framework：编译全绿；pre-commit（Spotless/CheckStyle/SpotBugs/PMD）全绿；全量单测 2141 个仅 EmailLimiter 既有失败；分页 4 个新用例全绿
- cicd：编译全绿；16 个存量单测回归 + 绑定分支新增单测全绿
- BETA 部署：`d428f1e6a`（拆除）+ `ae91a740`（通用端点）已部署；`20ca0829b`（4030001）与分页改动已推 develop_202610_iter1，随下次部署验证
- 待完成：业务 MR #453 / #583 合入 `release_20261019_iter1`（#453 需去 WIP 前缀）；BETA 端到端验收（验收清单 P/W 系列）；产品文案终审；前端实施

## 设计偏差与取舍

- **数据供给方案变更**（Phase 1 方案 → 实现偏离，已在 design.md 补录）：cicd 内联字段 / 专用列表端点（C5）→ framework 通用端点（F9），动机：避免模块专用重复实现、后续模块接入免重复开发
- **组拒绝响应方案变更**：common 包 errorCode 透传 → 业务码 4030001，动机：解除 common 发版依赖、纯 cicd 仓随本迭代交付
- **分页为验收期新增增强**：不在 Phase 1 原始范围，属体验/性能优化，已按定案补录 design.md/tasks.md
- 平行成员接口、本地绑定直查 Mapper、`isValidProjectMember` 僵尸标记等早期设计均按定案净删除（v4 → v5 演进，见 design.md 附录）

## 可复用经验

- 通用资源权限端点模式：资源级权限数据供给收敛到 framework 单端点（resourceType 白名单扩展），后续模块（codecheck/coderepo 等）接入免重复开发
- 跨仓字段扩展需蹭他人发版时，优先评估本仓业务码方案（如 403xxxx 家族）解除依赖
- 存量表加列后的混入防护：四层搜索法（表名 / Entity 类名 / MP 泛型签名 / Liquibase changelog）+ 固定滤组写死 0 的等价修复原则（见 design.md 3 章）

## 归档日期

2026-10-13
