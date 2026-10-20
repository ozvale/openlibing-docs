# perm-group-postlaunch-fixes — 归档

> 归档性质说明：本文件为 Phase 5 归档（2026-10-20 用户触发）。后端开发与 BETA 验证完成（业务 PR #482 待合入）；前端两处配套改动（批量绑定契约适配、复制来源文案）为后续独立节奏。

## 关联

- 业务 Issue（成员数口径）：<https://gitcode.com/openlibing/openlibing-cicd/issues/478>
- 业务 Issue（操作日志接入）：<https://gitcode.com/openlibing/openlibing-cicd/issues/451>
- 业务 PR（framework #482）：<https://gitcode.com/openlibing/openlibing-framework/merge_requests/482>
- 权限组整体方案 spec：`task_design/resource-permission-scheme`（本变更为其上线后修复增强）
- docs PR（本 spec 归档）：创建后回填

## 交付历程

framework 仓（feat/perm-scheme-v2 → PR #482，7 个 commit）：

- commit [`d0a51807`](https://gitcode.com/openlibing/openlibing-framework/commit/d0a51807)：query-groups 成员数按用户去重修正（count(1) → count(distinct user_id)，BETA 实测 9287 → 97）
- commit [`bbcd73de`](https://gitcode.com/openlibing/openlibing-framework/commit/bbcd73de)：成员数口径对齐成员管理页 countProjectUser（PROJECT 角色行数 + join user_basic_info 排除孤儿行 + 默认组并入 project_user_role_info 外部账号）
- commit [`4179f477`](https://gitcode.com/openlibing/openlibing-framework/commit/4179f477)：接入 operation_log v2，新增 PermGroupLogHandler 覆盖权限组 6 个写接口
- commit [`e0e1548b`](https://gitcode.com/openlibing/openlibing-framework/commit/e0e1548b)：添加成员日志记录逐账号失败明细（fillAddFailureMessage，`[账号] 原因` 格式）
- commit [`89bec5f4`](https://gitcode.com/openlibing/openlibing-framework/commit/89bec5f4)：添加成员日志补账号清单与部分失败前缀（fillAddAccounts，登录名优先邮箱兜底）
- commit [`47bb09d1`](https://gitcode.com/openlibing/openlibing-framework/commit/47bb09d1)：评审意见修复——复制组口径对账三值闭合、批量绑定日志补资源摘要、账号清单超长省略
- commit [`29a590ec`](https://gitcode.com/openlibing/openlibing-framework/commit/29a590ec)：批量绑定契约改为 resources 对象列表（id+name），日志展示名拼接、resource_display_info 落库、空白 id 校验

环境配置（menu_url_info，BETA 已完成并核验）：

- 6 个操作级菜单（identification 带 `:create` / `:update` / `:delete` / `:bind` / `:batch_bind` / `:unbind` 后缀）+ URL 挂载（write_log=1）+ 角色授权 + 旧菜单重复 URL 清理，操作日志操作名按动作区分显示

## 用户自测反馈

- 权限组成员数与成员管理页对不上（300044 虚报 9287）→ 第一版 distinct 去重后仍差外部账号，最终对齐列表页口径（d0a51807 → bbcd73de）
- 日志操作名统一显示"权限组操作" → 拆分 6 个操作级菜单（先角色授权后清理旧 URL，顺序颠倒会全员 403）
- 复制组提示与可见人数对不上 → countGroupMembers/copyGroupMembers 同口径重写，三者恒闭合（47bb09d1）
- 批量绑定日志资源名称 PIPELINE×2 可读性差 → 契约改为前端传名称（29a590ec），拒绝后端反查（分库分表后不可依赖直查 pipeline_info）
- 批量绑定后绑定表 resource_display_info 为空 → 随 29a590ec 一并修复（resourceName 落库）

## 最终验证

- 单测：PermGroupLogHandlerTest 19/19、SpaceUserLogHandlerTest 15/15、PermGroupResourceBindingServiceImplTest 15/15；全量 2212 例仅 EmailLimiterTest 存量失败（基线复现，与本变更无关）
- pre-commit 全链（Spotless + CheckStyle + SpotBugs + PMD）Passed
- BETA 只读库实测成员数对齐：project 3/2/300044 权限组合计 258/437/345，与成员管理页完全一致
- BETA 只读库实测复制对账：默认组可见 253 = 可复制 129 + 未纳入 124（112 自动同步行 + 12 外部账号）；自定义组见数 = 复制数
- 待前端适配后：BETA 批量绑定端到端验证日志名称列与绑定表展示列（PR #482 测试计划留档未勾选项）

## 设计偏差与取舍

- 成员数口径两步走：distinct 去重（数字仍不一致）→ 列表页行数口径（最终方案），中间版本保留在 commit 历史供追溯
- 批量绑定名称来源：曾评估后端反查 pipeline_info（framework 与 cicd 同库可直查），因分库分表规划放弃，改前端传名——契约不兼容变更趁接口未全量上线时点落地
- resource_name 兜底策略：任一名称缺失整体回退 `类型×数量` 而非部分拼接，避免日志列出现混合格式

## 可复用经验

- 成员统计类数字必须与用户可见页面同源同口径，独立口径必然漂移（已沉淀 ai_memory）
- 操作级菜单拆分配置顺序：先角色授权再清理旧菜单 URL，颠倒直接全员 403（已沉淀 ai_memory）
- 列表类字段（账号清单/资源名）拼接进定长列时统一 200 字符上限 + 条数摘要回退模式

## 归档日期

2026-10-20
