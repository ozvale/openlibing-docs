# 用户管理新增"普通用户"页签

- 分支：`jzcfork/202610normaluser`
- 核心提交：`74ac5f2e`

## Why

1. 权限管理 - 用户管理左侧组织树原先只有"系统用户"与"黑名单用户"两类视角，缺少对**普通用户**（非系统用户、非黑名单）的独立入口，管理员无法直观查看与检索这部分用户。
2. 普通用户不具备系统用户的管理语义（不归属用户组、不参与用户组筛选、无需用户组维护操作），若直接复用系统用户视图会出现无意义的筛选与操作入口。
3. 组织树展开后内容区高度计算不正确，出现内容溢出白色卡片的问题。

## What Changes

1. **新增普通用户页签**

   - `src/api/url.ts` 新增常量 `GET_GENERAL_USER = FRAME_WORK + '/manage/system/user/query-general-user'`。
   - `src/api/api.ts` 新增 `getGeneralUser = (a, s) => apiClient.post(urls.GET_GENERAL_USER, a, s)`。
   - `src/views/authorityManagement/user.vue` 左侧树在黑名单用户上方新增"普通用户"节点，`currentData.type = 'general'`。

2. **普通用户视角的界面裁剪**

   - 隐藏用户组筛选下拉（`v-if` 排除 `black` 与 `general`）。
   - 隐藏表格"用户组"列。
   - 隐藏操作列（`v-if="!currentData.repo && currentData.type !== 'general'"`）。
   - 隐藏新增/编辑弹窗内的"用户组"表单项。

3. **数据源切换**：`getUsers()` 根据 `currentData.type` 选择 `getGeneralUser` 或 `getSystemUser`；`resMap` 新增 `general: this.getUsers` 映射。

4. **类型注释扩展**：`currentData.type` 取值注释更新为 `'system' // user black system general`。

5. **布局修复**：`.management-content` 增加 `min-height: 0`，修复组织树展开导致内容区溢出白色卡片。

## Capabilities

### New

- 用户管理支持"普通用户"独立视图（独立接口、独立列表）。
- 新增后端接口 `query-general-user` 的前端调用封装。

### Modified

- 用户管理左侧组织树的节点集合（新增普通用户节点）。
- 用户列表在普通用户视角下的列与操作可见性。
- 用户管理内容区高度约束。

### Removed

- 普通用户视角下无意义的用户组筛选、用户组列与操作列。

## Impact

### 受影响代码

| 文件                                                         | 影响                                                  |
| ------------------------------------------------------------ | ----------------------------------------------------- |
| `apps/web-openlibing/src/api/url.ts`                         | 新增 `GET_GENERAL_USER` 常量                          |
| `apps/web-openlibing/src/api/api.ts`                         | 新增 `getGeneralUser`                                 |
| `apps/web-openlibing/src/views/authorityManagement/user.vue` | 新增页签 + 视图裁剪 + 数据源切换 + 样式修复（+31/-7） |

### 明确不受影响

- 系统用户（`type='system'`）、黑名单用户（`type='black'`）、仓库维度的用户视图行为不变。
- 用户组管理页、角色权限分配页不变。

### 风险

- 依赖后端 `/manage/system/user/query-general-user` 接口上线，需与后端同步发布时间；接口未就绪时页签点击会报错。
- 普通用户与系统用户的判定口径由后端决定，前端不做二次过滤，需确认"普通用户"定义（是否包含待审核、已禁用等状态）。

## 同一分支携带的其他 10 月改动（非本 spec 范围）

该分支相对 `jzcfork/202610setup` 还包含以下与本需求无关的提交，归档时请勿计入本 spec：

- 依赖 CVE 修复：`vite 7.3.7`（CVE-2026-112942）、`launch-editor >= 2.14.2`、`mermaid 10.9.3`（GHSA-m4gq-x24j-jpmf）、`d3-color` / `dompurify` / `glob` / `markdown-it` / `follow-redirects`、`pnpm-workspace.yaml` overrides 合并。
- oss-scan CI 工作流：`.gitcode/workflows/oss-pr-scan.yml`、`oss-version-scan.yml`。
- 仓库 token 相关 UI 调整：`fix(repos): include repo-header-with-help in th cell flex selector`、`feat(repos): fill in token member role tooltip content`、`feat(repos): drop token role status column, add member role hint`。
