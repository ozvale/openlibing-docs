# Tasks: 菜单管理易用性调整

## 实现清单

### 1. 接口列表表头筛选 + 同步弹窗改造（InterfaceListTab.vue）

- [x] 新建 `HeaderRadioFilter.vue`：表头「标题文字+漏斗图标」+ popover 竖排 radio（内置「全部」value=''，点选即生效并收起，无确定/取消按钮）
- [x] 「请求方式」列 `#header` 挂 HeaderRadioFilter，options=httpMethodList（GET/POST/PUT/DELETE，后端已确认）
- [x] 「接口用途/类型」列 `#header` 挂 HeaderRadioFilter，options=typeList（现有 4 项复用）
- [x] `getList` query data 增 `httpMethod`；`urlFlag` 由表头筛选驱动（工具栏类型下拉已按 UX 图示移除）
- [x] 筛选即查（pageNum=1）；两列筛选与 URL 输入筛选叠加生效
- [x] 工具栏按图示：搜索框宽 514px + placeholder「请输入关键词搜索代码仓全路径URL」+ prefix 搜索图标；同步按钮改文字型（蓝色刷新图标 +「同步数据」）
- [x] `ConfirmDialog.vue` 公共组件：内容与底部按钮间距 52px → 30px（全站二次确认弹窗统一生效）
- [x] `handleSync` 改 `confirmDialog.warning({ title: '同步接口数据', message: '将拉取最新接口信息，同步期间列表数据暂不更新。确定开始同步吗？', confirmText: '确定同步' })`（文案按 UX 图示），取消不进 loading

### 2. 菜单页签定位迁移（menu.vue + MenuLocatorPanel.vue）

> 原方案「MenuSearchDialog 弹窗」已废弃（2026-10-26 按定稿 UX 图示重构），实际实现为**表头漏斗图标 + popover 多列级联定位面板**，详见 design.md §3。

- [x] 移除工具栏 `el-select-v2` 搜索入口及关联样式（`.menu-search-wrap` scoped 样式、`menu-search-select-dropdown` 全局样式、`flatMenuOptions` computed）
- [x] menuName 列加 `headerCellRenderer`（⚠️ el-table-v2 无 `headerRenderer` 属性）：「名称」文字 + 漏斗图标（hover/激活态样式，非 scoped 块 `.menu-table-v2` 命名空间）
- [x] 新建 `MenuLocatorPanel.vue`：popover 级联定位面板（多列级联 + 面包屑 + 底部操作区），popper 挂表头漏斗图标下方
- [x] 面板内搜索（2026-10-27）：`el-select-v2` 平铺全量节点（filterable + clearable，label 带祖先路径），选中仅高亮面板内祖先链，手动点「定位到此菜单」才 confirm；下拉 `:teleported="false"` 防止 popover 判外部点击关闭
- [x] 底部操作区规范化（2026-10-27）：顶部分界线（1px #ebeef5）；「取消」按钮 80×32px 次按钮规范；「清除定位」无选中时 disabled
- [x] confirm → 复用 `handleNodeSelect(nodeId)`（祖先链展开、行高亮、滚动居中、清空还原快照全部不变）
- [x] `selectedNodeId` 存在时表头漏斗图标激活态展示
- [x] 弹窗取消/关闭不改变当前定位
- [x] 行状态色定稿：定位行 #FFB85C > 点选行 #E6F6FF > hover #F1F7FE

### 3. 菜单页签视觉与树形对齐（2026-10-26 ~ 10-27 新增）

- [x] 「未匹配接口列表」「人工配置接口」页签隐藏（`hidden: true`，代码分支保留）
- [x] 名称列展开/收起图标改方框 +/-（16px 方框、border #c8ccd4、hover 蓝 #409eff）
- [x] 树形缩进 24px 网格对齐（16px 方框 + 8px 间隙）：子级方框左缘与父级文字左对齐；叶子带特殊图标复刻本级方框几何；叶子无图标文字与父级文字列对齐（图标槽几何用 h() 内联 style 锁死）
- [x] 「新增」按钮 Plus 图标 14px（由 12px 调大）
- [x] 表格外框线移除，仅保留横向行分隔线（项目级规范）

### 4. 附带整改（2026-10-26 ~ 10-27）

- [x] 菜单删除二次弹窗迁移 `confirmDialog.danger`：标题「确认删除」、主文案「确定要删除该条数据吗？」、无 description、红色「删除」按钮
- [x] URL 输入去首尾空格（提交出口 trim）：`AccessWhitelistInterfaceTab.vue` submitEdit 前 `editForm.apiUrl.trim()`；`menu.vue` submit() 组参前对 urlList 每项 menuUrl/availableValue/unavailableValue 逐项 trim

### 5. 访问白名单页签表头筛选与字段提示（2026-10-28 新增，AccessWhitelistInterfaceTab.vue + UrlConfig.vue）

- [x] 「请求方式」列 `#header` 挂 HeaderRadioFilter，options=httpMethodOptions（GET/POST/PUT/DELETE）
- [x] 三个白名单列 `#header` 挂 HeaderRadioFilter，options=yesNoOptions（是 '1' / 否 '0'，内置「全部」''），筛选值 exempFilter / noUsersInfoFilter / unauthenticatedFilter
- [x] 列头结构：标题文字 + el-tooltip 问号图标 + 筛选图标（`.whitelist-header` inline-flex）；⚠️ el-tooltip 仅包住 `el-icon`——首版包「文字+图标」导致表头文字 hover 也触发起泡，2026-10-28 按用户反馈收窄
- [x] `getList` query data 增 httpMethod / exempFlag / noUsersInfoFlag / unauthenticatedFlag（后端已确认 1=是、0=否、''=全部），筛选即查重置第 1 页，与 URL 筛选叠加
- [x] 弹窗三个白名单表单项 `#label` 插槽加同文案问号提示（`.tooltip-label-item` 与 `.api-url-item` 共用 label 样式）
- [x] 弹窗「请求方式」下拉改遍历 `httpMethodOptions`，补齐 GET/POST/PUT/DELETE
- [x] 菜单页签 `UrlConfig.vue` methodList 补齐 GET/POST/PUT/DELETE（同步整改）

### 6. 验证

- [x] ESLint：改动文件 0 新增 error
- [x] 手工回归（接口列表）：两列筛选选择/清空/重置即查、与 URL 筛选叠加、分页正常；同步弹窗确认执行并刷新、取消不执行不进 loading
- [x] 手工回归（菜单页签）：表头图标打开面板、搜索选中高亮、手动定位（展开+高亮+居中）、清除定位还原快照、树形逐级对齐、删除弹窗规范、URL trim
- [x] 手工回归（访问白名单页签）：四列筛选选择/清空/重置即查、与 URL 筛选叠加；列头与弹窗问号提示仅图标触发；弹窗与菜单 URL 配置请求方式均为四项
- [ ] vue-tsc：无本次改动引入的类型错误

## 待办依赖（后端 / 设计稿）

- [x] 后端确认 `queryInterfaceListPage` 支持 `httpMethod` 查询参数（已确认：值域 GET/POST/PUT/DELETE）
- [x] 后端确认 `queryAccessWhitelistInterfaceList`（query-whitelist-page）支持 `httpMethod` / `exempFlag` / `noUsersInfoFlag` / `unauthenticatedFlag` 查询参数（2026-10-28 已确认：1=是、0=否、''=全部）
- [x] UX 设计稿内容 → 定位面板/树形对齐/删除弹窗细节已定稿（2026-10-26 ~ 10-27）

## 交付记录

- 2026-10-23 spec 文档生成，待用户评审后进入编码
- 2026-10-24 需求①②交付：HeaderRadioFilter 表头筛选 + 同步弹窗 confirmDialog 化 + ConfirmDialog 间距 30px
- 2026-10-26 需求③交付（二次重构为 popover 级联面板）：MenuLocatorPanel + 表头漏斗入口 + 行状态色 + 页签隐藏 + 方框 +/-
- 2026-10-27 迭代交付：面板内搜索（teleported=false）+ 底部操作区分界线/按钮规范 + 24px 缩进网格对齐 + 删除弹窗 danger 化 + URL trim + Plus 14px
- 2026-10-27 spec 文档补全（design.md 同步至最新实现，tasks.md 勾选与交付记录更新）
- 2026-10-28 需求⑤交付：访问白名单页签四列表头筛选 + 列头/弹窗问号提示（气泡仅图标触发）+ 弹窗与菜单 URL 配置请求方式补齐 GET/POST/PUT/DELETE（commit b0e08f17、1ae85de6，ESLint 通过，已推送 origin/feat-menu-usability）；spec 文档同步更新（本节）
