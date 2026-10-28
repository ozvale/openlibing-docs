# perm-group-postlaunch-fixes: 设计文档

## 1. 方案设计

三项独立修复围绕"权限组上线后遗留问题"展开，互相无耦合：

1. **成员数口径**：所有统计 SQL 统一到成员管理页 `countProjectUser` 口径，不再维护独立去重逻辑。原则：同一数字在权限组列表页与成员管理页必须同源，否则用户视角即认为系统出错。
2. **操作日志**：复用 operation_log_architecture_v2 的 Handler 机制（matches / before / after 三段式），新增 `PermGroupLogHandler`；操作名区分依赖 6 个操作级菜单（identification 带 `:create` / `:update` / `:delete` / `:bind` / `:batch_bind` / `:unbind` 后缀），代码与菜单配置共同生效。
3. **批量绑定契约**：资源展示名由前端随请求传递（id 本就前端传入，名称同源），后端不做跨库反查——为后续分库分表后 framework 与 cicd 数据面分离预留，不依赖 `pipeline_info` 直查。

## 2. 实现逻辑设计

- **countGroupMembersBatch**（列表批量统计）：与 `countProjectUser` 同口径——user 分支按行数统计 PROJECT 类型角色并 INNER JOIN `user_basic_info` 排除孤儿用户行，project 分支把 `project_user_role_info` 仓库外部账号计入默认权限组。
- **countGroupMembers / copyGroupMembers**（复制组对账）：单组统计同口径；复制 SQL 同样 INNER JOIN `user_basic_info`。三者恒闭合：源组可见数 = 已复制数 + 未纳入数。
- **PermGroupLogHandler**：matches 命中 `PermGroupController` + 权限组四个 DTO 或组/资源散参；before 回查组实体（删除场景附成员用户列表）与既有绑定关系；after 按操作类型补数，失败仅影响日志不干扰业务。
- **SpaceUserLogHandler**：失败路径 `fillAddFailureMessage` 把 data.error 逐账号明细按 `[账号] 原因` 拼 ex_message；成功路径 `fillAddAccounts` 把账号清单写 resource_name（登录名优先、邮箱兜底、逗号拼接）；整体成功但存在失败账号时加 `部分失败：` 前缀。
- **批量绑定**：Service 层遍历 `resources` 对象列表，`resourceName` 作为展示信息传入 upsertBinding 落库 `resource_display_info`（为 null 时更新保留原值）；Handler 层 `summarizeResourceNames` 拼接展示名，任一名称缺失回退 `类型×数量`。

## 3. 类设计

| 类                                         | 类型 | 职责                                                                 |
| ------------------------------------------ | ---- | -------------------------------------------------------------------- |
| `PermGroupLogHandler.java`                 | 新增 | 权限组 6 个写接口日志补数（组快照、绑定快照、资源摘要、展示名拼接）  |
| `SpaceUserLogHandler.java`                 | 修改 | 添加成员日志补账号清单、失败明细、部分失败前缀、超长省略             |
| `BatchBindResourceDTO.java`                | 修改 | 内嵌 `ResourceItem`（resourceId + resourceName），替换原 resourceIds |
| `PermGroupResourceBindingServiceImpl.java` | 修改 | bindBatch 遍历 resources、传展示名落库、空白 resourceId 校验         |
| `UserRoleMapper.xml`                       | 修改 | 三条 SQL 口径对齐                                                    |

## 4. 数据模型设计

不涉及表结构变更。既有表语义澄清：

- `user_role_info`：一用户多角色行（项目角色 + repo 级角色），统计成员数必须限定 PROJECT 类型角色行且 join `user_basic_info` 排除孤儿行；`sync_flag` 实际取值 '3'/'4'（自动同步）与 NULL（人工），复制组按 `sync_flag is null or = '0'` 判定可复制。
- `project_user_role_info`：仓库外部账号（gitCode/gitee/openUBMC），恒归默认权限组，计入默认组成员数。
- `perm_group_resource_binding.resource_display_info`（VARCHAR(256)）：批量绑定现在随请求落库，修复此前批量新绑定该列为空的问题。
- 操作日志 resource_name / resource_id 列长度约束：拼接结果超 200 字符回退条数摘要（`共N个资源，明细已省略`）。

## 5. 性能设计

- 批量统计维持一条聚合 SQL（GROUP BY perm_group_id），无 N+1。
- bindBatch 维持一次批量查询既有绑定（queryByResources），循环内无逐资源 SELECT。
- 日志补数发生在操作后异步链路，回查失败仅降级日志字段，不阻塞业务响应。

## 6. API 接口设计

契约变更仅一处（不兼容，需前端同步适配）：

`POST /openlibing-framework/perm-group/batch-bind-resources`

请求体 `resourceIds: string[]` 改为：

```json
{
  "projectId": 3,
  "resourceType": "PIPELINE",
  "permGroupId": 5,
  "resources": [
    { "resourceId": "b97a313d...", "resourceName": "流水线A" },
    { "resourceId": "6e7d1f85...", "resourceName": "流水线B" }
  ]
}
```

- resourceName 可选：缺失时接口不报错，日志回退 `类型×数量`，绑定表展示列保留原值
- resourceId 空白元素返回 400 参数错误
- 响应体不变：`{ "switchedCount": N }`

其余接口（query-groups / create / update / delete / bind / unbind / 查询类）签名无变化。

## 7. 安全设计

- **鉴权**：不涉及新增端点；既有鉴权链路不变，批量绑定新增空白 resourceId 校验防脏数据写入。
- **敏感信息**：日志 resource_name / ex_message 承载用户可见的账号、流水线名称，均为非敏感业务字段；超长省略机制同时防超列长写入失败。
- **硬编码**：不涉及。
- **审计日志**：本次核心交付——6 个写接口全量落审计日志，删除组附成员用户列表，换绑附前后组名，满足权限变更可追溯要求。
