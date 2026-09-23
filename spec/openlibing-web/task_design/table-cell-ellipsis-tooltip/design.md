# 技术方案

## 变更说明

表格单元格/表头超长文本改为单行省略 + 悬停 tooltip 显示完整内容。分两层实现：全局表格组件 myTable.vue 统一处理四种单元格场景；未走全局组件的局部表格在各自页面内用相同 CSS 手法处理。

## 方案分层

### 1. 全局组件层：myTable.vue

**四种单元格场景统一处理**（新增 ellipsis 类 + el-tooltip）：

| 场景                                  | 类名                   | tooltip                  |
| ------------------------------------- | ---------------------- | ------------------------ |
| 时间列（`item.time`）                 | `time-cell-ellipsis`   | el-tooltip，空值禁用     |
| 链接列（`item.link` + `showToolTip`） | `link-cell-ellipsis`   | el-tooltip，空值禁用     |
| 普通文本列（`item.showToolTip`）      | `text-cell-ellipsis`   | el-tooltip，`0` 视为有值 |
| 普通表头（无筛选/排序）               | `header-cell-ellipsis` | el-tooltip               |

**关键改动**：

1. `:show-overflow-tooltip="item.showToolTip && !item.time"` —— 时间列禁用 Element Plus 原生 tooltip，避免与 el-tooltip 双 tooltip 冲突。
2. 列配置（如 `views/cve/columns.js`）按需追加 `showToolTip: true`。
3. 筛选下拉 filterDropdown.vue：label 包一层 `.filter-dropdown-label` 实现省略 + 原生 title。

**核心 CSS（四个 ellipsis 类共用）**：

```less
span.time-cell-ellipsis,
span.text-cell-ellipsis,
span.link-cell-ellipsis,
span.header-cell-ellipsis {
  display: block !important; // cve.less 将 .cell 内 span 设为 inline-flex（特异性更高），
  // flex 容器上 text-overflow 无效，必须 !important 改回 block
  min-width: 0; // flex 子项默认 min-width: auto 不收缩，置 0 才能出省略号
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

### 2. 页面层：局部表格（未走 myTable 的页面）

统一手法，两类实现：

- **el-tooltip 方案**（内容列）：`el-tooltip` 包 `span.ellipsis-cell`，CSS 为 `display: inline-block / block; max-width: 100%; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle;`
- **原生 title 方案**（表头、简单场景）：`:title="..."` + 同款省略 CSS

覆盖页面：

| 页面       | 文件                                                 | 要点                                                                       |
| ---------- | ---------------------------------------------------- | -------------------------------------------------------------------------- |
| 账号管理   | AccountManage/index.vue                              | IAM用户名列（表头+内容）原生 title                                         |
| 反馈管理   | Feedback/AllFeedback.vue                             | 标题/提单人/评审人/创建时间等列 el-tooltip，表头统一 nowrap 省略           |
| 检测中心   | InspectionCenter/index.vue                           | 局部表格列处理                                                             |
| 制品列表   | Publish/detail/components/releaseArtifacts.vue       | 版本等超长列                                                               |
| 合规规则表 | LegalCompliance/CodeCheckRule/children/RuleTable.vue | 规则列                                                                     |
| 工具管理   | ToolManagement/components/toolTable.vue、config.ts   | 列配置                                                                     |
| 0-day 漏洞 | Vulnerability0Day/components/vulnTable.vue           | 漏洞列表格                                                                 |
| 用户管理   | authorityManagement/user.vue                         | 各账号用户名列 el-tooltip + 表头 title，新增 `formatCreateTime` 复用格式化 |
| 角色管理   | authorityManagement/role.vue                         | 角色名称/描述/类型/创建时间列                                              |
| CVE 列表   | cve/columns.js                                       | 多列追加 `showToolTip: true`（含修复详情、异常/重复表）                    |
| 机器账号   | machineManagement/account/machineAccount.vue         | 机机账号ID（链接列）el-tooltip                                             |
| 机器接口   | machineManagement/machineInterface.vue               | 接口名称/Url 列，tooltip popper 全局限宽 500px 换行                        |
| 公告板     | manageCenter/BulletinBoard/index.vue                 | 标题/生效时间/失效时间列                                                   |
| 用户看板   | manageCenter/UserDashboard/index.vue                 | `dashboard-ellipsis`，show-after 200ms                                     |
| 操作日志   | manageCenter/log/operationLog.vue                    | 操作模块/类型/备注/触发人员等列 el-tooltip + 表头 title                    |

### 3. 关键 CSS 踩坑记录

1. **flex 子项不收缩**：`.cell` 或父容器为 flex 时，子项 `min-width: auto` 导致省略号不生效，必须 `min-width: 0`。
2. **特异性覆盖**：cve.less 将 `.cell` 内 span 设为 `inline-flex`，flex 容器上 `text-overflow: ellipsis` 无效，须 `display: block !important`。
3. **图标防压缩**：筛选图标、排序图标设 `flex: none`，避免与文字竞争宽度。
4. **tooltip 内容超长**：接口 Url 等极长内容用全局 `popper-class`（`.url-tooltip-popper`，max-width 500px + word-break）限宽换行，因 popper 渲染在 body 下需全局样式。
5. **状态标签防变形**：标签类内容需 `display: inline-block; vertical-align: middle` 胶囊样式，避免继承全局 `.cell` 的 block + 40px 行高。

## 影响范围

- **前端**：纯展示层，全局表格组件 + 15 个业务页面
- **后端 / API**：无影响

## 测试建议

1. 各涉及页面：超长内容单行省略，悬停 tooltip 显示完整内容
2. 短内容正常显示、无多余 tooltip；空值显示 `--` 且 tooltip 禁用
3. 时间列与链接列显示正常；带筛选/排序图标的表头省略号不与图标重叠
