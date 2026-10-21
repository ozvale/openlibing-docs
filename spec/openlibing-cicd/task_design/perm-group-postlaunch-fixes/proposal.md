# perm-group-postlaunch-fixes: 权限组成员数量统计修正与操作日志接入

## 需求背景

权限组能力（数据级权限管控，spec 见 `task_design/resource-permission-scheme`）合入 release_20261019_iter1 后，BETA 验证期暴露两类遗留问题：

1. **成员数统计失真**：`query-groups` 接口的 `countGroupMembersBatch` 按行数统计（count(1)），而 `user_role_info` 表中一个用户可存在项目角色行 + 多仓库 repo 级角色行等多条记录，默认权限组（id=0，继承项目全部存量角色行）成员数虚高数十倍（project 300044 实测虚报 9287，真实约 97）；且统计口径未计入 `project_user_role_info` 表的仓库外部账号，与成员管理页 `query-project-user` 的显示数字对不上。
2. **操作日志缺失**：operation_log_architecture_v2 初始化清单（223 个 URL）未覆盖后合入的 perm-group 模块，权限组的增删改、资源绑定/解绑等 6 个写操作接口无审计日志；批量添加项目成员日志的失败原因只记占位符 "failure"，账号清单与部分失败明细完全丢失。

## 功能描述

framework 仓（feat/perm-scheme-v2 分支，PR #482）：

1. **成员数口径对齐**：`countGroupMembersBatch` / `countGroupMembers` 重写为与成员管理页 `countProjectUser` 完全同口径（PROJECT 类型角色行数 + INNER JOIN `user_basic_info` 排除孤儿用户行 + 默认组并入仓库外部账号），复制组对账三值恒闭合。
2. **权限组操作日志接入 v2**：新增 `PermGroupLogHandler` 覆盖 6 个写接口，before 回查组实体与既有绑定关系，after 补 projectId/resourceId/resourceName 与前后快照；配合 6 个操作级菜单（identification 带动作后缀）拆分操作名显示。
3. **添加成员日志补全**：`SpaceUserLogHandler` 补账号清单（resource_name）、逐账号失败明细（ex_message）、部分失败前缀与超长省略防护。
4. **批量绑定接口契约变更**：`batch-bind-resources` 请求体 `resourceIds` 改为 `resources` 对象列表（resourceId + resourceName），前端随请求传流水线名称；日志资源名称列显示资源展示名英文逗号拼接，批量绑定落库展示信息到 `resource_display_info`。

不涉及：cicd 仓（无改动）、gateway 仓、前端仓（文案改动另行安排）。

## 验收标准

- [x] `query-groups` 返回的各权限组成员数与成员管理页 `query-project-user` 数值完全相等（BETA 实测 project 3/2/300044 合计 258/437/345 对齐）
- [x] 复制组三者对账闭合：源组可见数 = 已复制数 + 未纳入数（BETA project 3 默认组 253 = 129 + 124）
- [x] 权限组 6 个写操作接口产出操作日志，操作名按"创建/编辑/删除/切换/批量切换/解绑权限组资源"区分显示
- [x] 批量添加成员日志 resource_name 带账号清单、ex_message 带逐账号失败明细，部分成功场景带 `部分失败：` 前缀
- [x] 批量绑定日志资源名称列显示流水线名称英文逗号拼接，绑定表 `resource_display_info` 非空
- [x] 全量单测通过，pre-commit 全链 Passed
- [ ] 前端适配 resources 契约后 BETA 端到端验证批量绑定日志与绑定表展示列

## 影响范围

| 文件                                       | 操作      | 说明                                                |
| ------------------------------------------ | --------- | --------------------------------------------------- |
| `UserRoleMapper.xml`                       | 修改      | 成员数统计与复制 SQL 口径对齐                       |
| `PermGroupLogHandler.java`                 | 新增      | 权限组操作日志 Handler（6 个写接口）                |
| `SpaceUserLogHandler.java`                 | 修改      | 添加成员日志补账号清单、失败明细、超长防护          |
| `BatchBindResourceDTO.java`                | 修改      | resourceIds 改为 resources 对象列表                 |
| `PermGroupResourceBindingServiceImpl.java` | 修改      | 批量绑定遍历 resources、落库展示名、空白 id 校验    |
| 对应测试类 × 3                             | 修改/新增 | 累计新增约 10 个用例                                |
| `menu_url_info` 配置                       | 环境配置  | 6 个操作级菜单 + URL 挂载 + 角色授权（BETA 已完成） |

## 关联 Issue

- openlibing/openlibing-cicd#478（成员数口径）：<https://gitcode.com/openlibing/openlibing-cicd/issues/478>
- openlibing/openlibing-cicd#451（操作日志接入）：<https://gitcode.com/openlibing/openlibing-cicd/issues/451>
- 业务 PR：<https://gitcode.com/openlibing/openlibing-framework/merge_requests/482>
