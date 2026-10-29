# 设计：用户管理新增"普通用户"页签

## Context

`authorityManagement/user.vue` 通过左侧组织树切换数据源，`currentData.type` 决定列表来源：

| type     | 含义                 | 数据源方法                 |
| -------- | -------------------- | -------------------------- |
| `system` | 平台用户（系统用户） | `getSystemUser`            |
| `black`  | 黑名单用户           | `getBlackUsers`            |
| `user`   | 全部用户             | `getSystemUserAll`         |
| `repo`   | 仓库维度用户         | 由 `currentData.repo` 驱动 |

左侧树当前顺序为：平台用户 -> 黑名单用户。产品需要在此之外提供"普通用户"视图，用于查看既非系统用户也非黑名单的用户。

## Goals / Non-Goals

### Goals

1. 用户管理左侧树新增"普通用户"节点，位置在黑名单用户之前。
2. 普通用户走独立后端接口 `query-general-user`，不与系统用户共用查询。
3. 普通用户视角下不展示与"用户组"相关的筛选/列/表单项，也不展示行操作列。
4. 修复组织树展开后内容区溢出白色卡片的布局问题。

### Non-Goals

- 不改变系统用户、黑名单用户、全部用户、仓库用户的既有行为。
- 不新增普通用户的编辑/删除等写操作能力（本视图只读）。
- 不做"普通用户"与"系统用户"的判重或迁移逻辑。

## Decisions

### D1：新增独立接口而非复用 `query-system-user`

普通用户与系统用户在数据归属上不同（不属用户组），复用系统用户接口会带来权限过滤与分页语义的混淆。新增：

```
GET_GENERAL_USER = FRAME_WORK + '/manage/system/user/query-general-user'
getGeneralUser = (a, s) => apiClient.post(urls.GET_GENERAL_USER, a, s)
```

### D2：复用 `getUsers()`，仅切换请求函数

```js
async getUsers() {
  const requestFn = this.currentData.type === 'general' ? getGeneralUser : getSystemUser;
  const { code, data } = await requestFn({ data: { pageSize, pageNum, ... } });
}
```

好处：分页、查询条件、错误处理路径完全复用，改动面最小。`resMap` 中 `general: this.getUsers` 与 `system: this.getUsers` 指向同一方法，由方法内部按类型分流。

### D3：以 `type !== 'general'` 显式裁剪，而非新建页面

新增页面会重复约 800 行模板与脚本。选择在同一组件内按类型裁剪：

| 元素               | 裁剪条件                                                         |
| ------------------ | ---------------------------------------------------------------- |
| 用户组筛选下拉     | `currentData.type !== 'black' && currentData.type !== 'general'` |
| 用户组表格列       | 同上                                                             |
| 操作列             | `!currentData.repo && currentData.type !== 'general'`            |
| 弹窗内用户组表单项 | 同上（排除 `black`/`general`）                                   |

### D4：`type` 枚举注释显式扩展

`currentData.type` 注释更新为 `// user black system general`，避免后续维护者遗漏该分支。注意 `repo` 维度通过 `currentData.repo` 表达，不在 `type` 枚举内。

### D5：布局修复用 `min-height: 0`

`.management-content` 是 flex 容器子项，默认 `min-height: auto` 会阻止内部滚动容器收缩，导致组织树展开后内容溢出白色卡片。补 `min-height: 0` 即可让子项在 flex 中正确收缩。

## 交互矩阵

| 当前页签            | 数据源             | 用户组筛选 | 用户组列 | 操作列             | 弹窗用户组项 |
| ------------------- | ------------------ | ---------- | -------- | ------------------ | ------------ |
| 平台用户（system）  | `getSystemUser`    | 显示       | 显示     | 显示（非仓库维度） | 显示         |
| 普通用户（general） | `getGeneralUser`   | 隐藏       | 隐藏     | 隐藏               | 隐藏         |
| 黑名单用户（black） | `getBlackUsers`    | 隐藏       | 隐藏     | 显示（非仓库维度） | 隐藏         |
| 全部用户（user）    | `getSystemUserAll` | 显示       | 显示     | 显示（非仓库维度） | 显示         |

## 后端接口契约

```http
POST {FRAME_WORK}/manage/system/user/query-general-user
data: {
  "pageSize": <number>,
  "pageNum": <number>,
  "userRole": <string?>,
  "accountLogin": <string?>,
  "accountPlatform": <string?>
}
```

响应结构与 `query-system-user` 对齐（`{ code, data: [...] }`），前端直接复用同一套表格列渲染。接口需由后端同步上线。

## 涉及文件

| 文件                                                         | 操作 | 说明                                            |
| ------------------------------------------------------------ | ---- | ----------------------------------------------- |
| `apps/web-openlibing/src/api/url.ts`                         | 修改 | 新增 `GET_GENERAL_USER`                         |
| `apps/web-openlibing/src/api/api.ts`                         | 修改 | 新增 `getGeneralUser`                           |
| `apps/web-openlibing/src/views/authorityManagement/user.vue` | 修改 | 新增页签、视图裁剪、数据源分流、`min-height: 0` |

## 风险与兼容性

| 风险                                              | 影响               | 应对                                                  |
| ------------------------------------------------- | ------------------ | ----------------------------------------------------- |
| 后端 `query-general-user` 未上线                  | 高（页签点击报错） | 前后端同版本发布；或先隐藏页签待接口就绪              |
| 普通用户定义与前端预期不一致（是否含禁用/待审核） | 中                 | 与产品/后端确认口径，前端不做二次过滤                 |
| 用户组相关元素裁剪遗漏                            | 低                 | 以 `type !== 'general'` 为统一开关，逐项核对 4 处     |
| `min-height: 0` 影响其他页签布局                  | 低                 | 该样式仅作用于 `.management-content`，需回归 4 个页签 |

## 验证策略

1. 点击"普通用户"页签，列表数据来自 `query-general-user`（Network 校验），分页正常。
2. 普通用户视图下无用户组筛选下拉、无用户组列、无操作列。
3. 打开新增/编辑弹窗，无"用户组"表单项。
4. 切回平台用户/黑名单用户，上述元素按原规则显示。
5. 展开组织树至深层级后，内容区不溢出白色卡片，滚动正常。
6. 普通用户视图的搜索条件（账号、平台等）与分页组合查询结果正确。
