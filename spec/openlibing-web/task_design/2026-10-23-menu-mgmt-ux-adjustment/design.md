# Design: 菜单管理易用性调整

## 1. 接口列表表头筛选（需求①）

**现状**（`components/InterfaceListTab.vue`）：

- 工具栏 L3-32：URL 输入框 + 类型 `el-select`（`typeList` 4 项，L152-157）+ 同步按钮
- 「请求方式」列 L46-50（`prop="httpMethod"`，width 200）、「接口用途/类型」列 L56-60（`getTypeLabel(row.urlFlag)`）均无表头筛选
- `getList` query data 仅 `apiUrl` + `urlFlag`（L195-197），**无 httpMethod**
- 表头筛选范式参照：`views/Repos/branches.vue` L231-238（`#header` 插槽挂 ColumnFilter + confirm/reset 即查）

**改动**（表头筛选 UI 已按 UX 图示定稿：轻量 radio 面板，含「全部」选项、点选即生效并收起，无确定/取消/清除按钮）：

1. **新建轻量表头筛选组件** `views/authorityManagement/components/HeaderRadioFilter.vue`（替代原 ColumnFilter 方案——CategorySearchEditor 面板含标题栏与底部按钮，与图示不符）：
   - 表头渲染「列标题文字 + 漏斗图标」（图标 hover 蓝色，已选非空值时激活态填充）
   - 点击图标弹 el-popover（宽 160，bottom-start），内容为竖排 el-radio-group：内置「全部」（value=''，默认选中）+ options
   - 点选任一项 → `update:modelValue` + `change` → 关闭面板（即选即查，无确认按钮）
   - popper 挂 body，样式走 popper-class 全局块；radio 行样式（32px 高、hover #f4f6fa）参照 CategorySearchEditor
2. 两列 `#header` 插槽挂 HeaderRadioFilter：
   - 请求方式：`options = httpMethodList`（GET/POST/PUT/DELETE，后端已确认支持 `httpMethod` 查询参数）
   - 接口用途/类型：`options = typeList`（未配置接口 '0' / 人机接口 '1' / 机机接口 '2' / 服务内接口 '3'，复用现有定义）
3. `getList` query data 增补 `httpMethod`；`urlFlag` 由表头筛选驱动（工具栏类型下拉**已按 UX 图示移除**，表头筛选为该维度唯一入口）
4. 工具栏按 UX 图示调整：搜索框固定宽 514px、placeholder「请输入关键词搜索代码仓全路径URL」、prefix 搜索图标（灰 #a8abb2）；同步按钮改为文字型 `el-button text`——蓝色刷新图标（#409eff，loading 时隐藏由 loading 态替代）+「同步数据」，margin-left:auto 靠右
5. 筛选变化 → `pagination.pageNum = 1` → `getList()`（复用 `handleSearch`）

query 结构（唯一变化为新增 `httpMethod`）：

```ts
{
  apiUrl: this.url,
  urlFlag: this.type,           // 工具栏下拉与表头筛选共用的筛选值，'' 为全量
  httpMethod: this.httpMethodFilter, // 新增，后端已确认支持
}
```

## 2. 同步数据二次弹窗改造（需求②）

**现状**：`handleSync`（L165-186）用 `this.$confirm('是否确定同步接口数据?', '提示', { type: 'warning' })`。

**改造**为公共 `confirmDialog.warning`（文案按 UX 图示定稿）：

```js
import { confirmDialog } from '@/components/ConfirmDialog/use-confirm-dialog';

async handleSync() {
  try {
    await confirmDialog.warning({
      title: '同步接口数据',
      message: '将拉取最新接口信息，同步期间列表数据暂不更新。确定开始同步吗？',
      confirmText: '确定同步',
    });
  } catch {
    return; // 用户取消，不进入 loading
  }
  this.syncLoading = true;
  // 原 syncInterfaceList 成功刷新逻辑不变
}
```

注意：`confirmDialog` 取消时 reject（`use-confirm-dialog.ts` L48-50），必须 try/catch；`syncLoading` 只在确认后置 true（当前实现取消分支也会 finally 复位，改造后语义更干净）。

**公共组件样式调整**：`ConfirmDialog.vue` 内容与底部按钮间距由 `padding-top: 52px` 改为 `30px`（UX 图示 2026-10-23 定稿，全站二次确认弹窗统一生效）。

## 3. 菜单页签节点搜索迁移（需求③）

**现状**（`menu.vue`）：

**页签隐藏（2026-10-26 新增需求）**：「未匹配接口列表」（offline）与「人工配置接口」（falseReport）两个页签隐藏——`tabList` 对应项加 `hidden: true`（代码保留，恢复只需去掉该字段），模板 `v-for` 过滤 `!item.hidden`；内容区 `v-if="activeTab === 'offline' / 'falseReport'"` 渲染分支保留（不可达但不动），ESLint 通过。

**菜单页签视觉调整（2026-10-26 UX 图示，2026-10-27 对齐模型定稿）**：

- 名称列展开/收起图标由 `CaretRight` 旋转改为**方框 +/-**：`.menu-tree-arrow` 16px 方框（border #c8ccd4、圆角 2px），`::before` 横线 + `::after` 竖线（#909399），`is-expanded` 隐藏竖线变减号，hover 变蓝 #409eff；点击链路 `toggleTreeExpand` 不变
- **树形缩进对齐网格（踩坑多轮后定稿）**：每级缩进 = 图标槽总宽 **24px**（16px 方框 + 8px 间隙）。三类节点统一几何：
  - 带子节点：缩进 `depth×24` + 方框 + 8px 间隙，文字 `depth×24+24` → **子级方框左缘与父级文字左对齐**
  - 叶子无图标：缩进 `depth×24`，文字 = 父级文字列
  - 叶子带特殊图标（前台界面/管理中心/通用配置）：缩进 `depth×24` + 图标复刻本级方框几何（16px 图标 + 8px 间隙），文字与本层级带方框兄弟节点文字对齐
  - ⚠️ 踩坑：叶子图标槽位几何不要用 CSS 类覆盖实现（.menu-leaf-icon-slot 曾因覆盖不生效导致文字右偏 ~12px），必须用 `h()` 内联 style 锁死 `width:16px + marginRight:8px`；曾按 16px 缩进 + 22px 槽位的多轮修补均错位，根因是**缩进步长必须严格等于图标槽总宽**，父级文字 = (depth-1)×24+24 = depth×24
- 「新增」按钮：失效的 `<i class="el-icon-plus">`（element-ui 旧类名）替换为 `el-icon + Plus`（**14px**，2026-10-27 由 12px 调大），margin-right 4px，组件注册 `Plus`，移除不再使用的 `CaretRight` import

**定位入口迁移（2026-10-26 已实现，按 UX 图示）**：

- **移除**：工具栏 `el-select-v2` 搜索定位框（`.menu-search-wrap` 模板块与 scoped 样式、`menu-search-select-dropdown` 全局样式、`flatMenuOptions` computed 一并移除；`menu-search-highlight-row` 行高亮类保留复用）
- **新增组件** `components/MenuLocatorPanel.vue`（Options API；2026-10-26 二次重构：~~el-dialog 居中弹窗~~ → 纯面板 + el-popover 挂表头图标下方，`placement: bottom-start`、width 900、`:persistent="false"`（每次打开重建实例，`data()` 内按 selectedId 回显路径）、popper 隐藏箭头去 padding；⚠️ 踩坑：Options API 中 emit 必须用 `this.$emit`/模板 `$emit`，`this.emit` 会报 `TypeError: this.emit is not a function`）：
  - 弹窗 900px，标题「选择菜单位置」；搜索框（prefix 搜索图标，按名称过滤，命中节点保留完整子树、未命中但后代命中的保留祖先链）
  - 多列级联面板：第 1 列为根层，列头（「N级菜单」，14px）背景 #F1F3F6 / 字体 #191919；点击节点即选中（背景 #E6F6FF / 字体 #006BE6 / 箭头 #006BE6，2026-10-26 色值定稿）并自动产出下一列；最终选中项色值相同（背景 #E6F6FF / 字体 #006BE6）无箭头、保留 #006BE6 边框区分；列高 380px 横向滚动、列内纵向滚动
  - 面包屑（选中后显示，14px）：祖先路径链——最后一级之前背景 #F3F4F6 / 字体 #575D6C，分隔符 #575D6C；最后一级背景 #E6F6FF / 字体 #006BE6
  - 底部：左提示（未选中「点击菜单名称选择，带箭头可展开下级」/选中后「已选路径：…」，14px / 字体 #AEAEAE）；右侧「清除定位」（emit clear）「取消」（emit close，两者默认字色 #575D6C 与 ConfirmDialog 次按钮规范一致）「定位到此菜单」（primary，无选中 disabled，emit confirm(id)）
  - 打开时按 `selectedId` 回显完整选中路径
  - **面板内搜索（2026-10-27 定稿）**：搜索框为 `el-select-v2` 平铺全量节点（filterable + clearable，label 带祖先路径区分同名节点，超长省略 + title），选中后**不直接定位**——仅更新 `selectedPath` 使面板内祖先链高亮（`is-active`/`is-final`）、面包屑同步、自动滚动选中项到可视区，需手动点「定位到此菜单」才 emit confirm；清空下拉还原为打开时初始路径。⚠️ 踩坑：el-select-v2 下拉必须 `:teleported="false"` 渲染在 popover 内容内——teleport 到 body 的下拉面板 DOM 在 popover 外，点击选项被 el-popover 的 onClickOutside 判定为外部点击直接关闭弹窗
  - **底部操作区（2026-10-27 规范化）**：操作区顶部加横向分界线（1px #ebeef5，与上下各 12px 间距）；「取消」按钮按公共弹窗次按钮规范 **80×32px**（默认边框 #E5E7EB/字色 #575D6C）；「清除定位」在无选中节点时 disabled
  - **popover 箭头**：通过 `!important` 覆盖 popper.js 自动 clamp 的 inline 定位（left 固定 17px），箭头对准表头漏斗触发图标
- **表头入口**：menuName 列 `headerCellRenderer`（⚠️ 踩坑：el-table-v2 列**不存在** `headerRenderer` 属性——会被静默忽略导致表头渲染不出来，必须用 `headerCellRenderer`，已从 node_modules 源码 use-columns.d.ts 证实）渲染 `.menu-name-header`（名称文字 + ElPopover；⚠️ 二次踩坑：headerCellRenderer 返回值会**整体替换**默认表头内容，漏包名称文字会导致表头只剩图标）。ElPopover reference=漏斗图标 SVG polygon（⚠️ 三次踩坑：CSS 选择器必须写 `svg polygon`——渲染的 svg 内无 g 包裹层，写 `svg g` 样式不命中，polygon 默认黑色实心与设计图线框漏斗不符）；已有定位时图标激活态蓝色填充
- **定位链路复用**：confirm → `handleLocatorConfirm(id)` → `handleNodeSelect(id)`（expandToNode + 高亮 + scrollToRow 不变）；清除定位 → `handleLocatorClear()` → `handleNodeSelect(null)`（快照还原展开状态）

- 工具栏 ~~L35-52：`el-select-v2`（680px，filterable，options=`flatMenuOptions` 带祖先路径 label），change → `handleNodeSelect`~~（已移除，见上）
- 定位链路：`handleNodeSelect`（L757）→ `expandToNode`（L767，祖先链展开 + `preSelectExpandedIds` 快照）→ `scrollToSelectedRow`（L786，虚拟滚动居中）；`tableRowClass` 高亮选中行；清空 → `restoreExpandSnapshot`（L780）还原展开快照
- 行状态色（2026-10-26 定稿）：定位行 #FFB85C（优先级最高）> 点选行 #E6F6FF（`rowEventHandlers.onClick` 记录 `clickedNodeId`，回调参数为 `{ event, rowData, rowIndex, rowKey }`）> 行 hover #F1F7FE
- el-table-v2 列定义 `buildTableColumns`（L526-576）：menuName 列（width 320）通过 **`headerCellRenderer`** 自定义表头（不存在 `headerRenderer`，见上方踩坑）

**改动**：

1. **移除**工具栏搜索入口：模板 L35-52（`.menu-search-wrap` / `el-select-v2`）、scoped 样式 L1054-1067、全局样式 `menu-search-select-dropdown` L1150-1159；「新增」按钮保留
2. menuName 列增加 `headerRenderer`：渲染「名称」文字 + 搜索图标按钮（视觉参照 ColumnFilter 表头图标：16px svg、hover 高亮、`selectedNodeId` 存在时激活态填充色）
3. **节点搜索弹窗**（新组件 `components/MenuSearchDialog.vue`，暂名 [TBD]，具体以 UX 稿为准）：
   - `el-dialog`，标题「搜索并选择节点」，宽度默认 480px [TBD]
   - 内容：搜索输入框（关键字过滤，匹配名称与祖先路径，复用 `flatMenuOptions`）+ 节点选项列表（展示「祖先路径 / 节点名」区分同名节点，单选高亮）
   - 底部「确定 / 取消」按钮，主按钮确定在左（UI 规范）[TBD 文案]
   - 确定 → 关闭弹窗 + 调用既有 `handleNodeSelect(nodeId)`；取消/关闭 → 不改变当前定位
   - 菜单节点量级为数百，普通列表即可；若 UX 稿要求树形展示/虚拟滚动再扩展 [TBD]
4. `selectedNodeId` / `preSelectExpandedIds` / `restoreExpandSnapshot` / `getMenuList(keepState)` 逻辑全部保留，仅入口控件形态变化
5. headerRenderer 内 `h()` 渲染的元素不带 scopeId，样式放非 scoped 块并以 `.menu-table-v2` 命名空间隔离（既有约定见 L1160-1161 注释）

### 入口形态备选

| 方案                       | 说明                                                           | 结论                             |
| -------------------------- | -------------------------------------------------------------- | -------------------------------- |
| A. el-dialog 弹窗（默认）  | 「弹窗形式」的字面语义，内容布局自由度高，可承载搜索+列表+按钮 | **采用**，细节待 UX 稿确认       |
| B. el-popover 内嵌选择列表 | 更轻量，与 ColumnFilter 漏斗范式一致                           | 备选，若 UX 稿实为轻量浮层再切换 |

## 4. 附带整改（2026-10-26 ~ 10-27，按弹窗规范/用户反馈）

1. **菜单删除二次弹窗迁移（menu.vue `deleteRow`）**：存量 `this.$confirm`（ElMessageBox）迁移至公共 `confirmDialog.danger`——标题「确认删除」、主文案「确定要删除该条数据吗？」（无 description 副说明）、红色 ❌ 图标、确认按钮红色「删除」、取消灰边框，80×32 按钮规范、align-center 居中、禁点遮罩关闭。原 i18n key（ruleConfigure.confirmDelete/tipTitle）不再用于此弹窗，删除成功提示保留原 i18n 文案。
2. **URL 输入去首尾空格（提交出口 trim，勿流入接口参数）**：
   - `AccessWhitelistInterfaceTab.vue`：`submitEdit` 前 `editForm.apiUrl.trim()` 再校验/组参（trim 先于校验——纯空格会被 required 拦截）
   - `menu.vue`：`submit()` 组参前对 `urlList` 每项的 `menuUrl` / `availableValue` / `unavailableValue` 逐项 trim（URL 配置字段不参与 el-form 校验，仅在提交出口统一处理）
3. **表格外框线**：菜单表格默认无外边框，仅保留横向行分隔线（项目级规范，见 project_memory）。

## 5. 访问白名单页签表头筛选与字段提示（2026-10-28，需求⑤）

**现状**（`components/AccessWhitelistInterfaceTab.vue`）：「请求方式」列与三列白名单列（exempFlag / noUsersInfoFlag / unauthenticatedFlag，width 250）均无表头筛选、无字段释义；新增/修改弹窗请求方式下拉仅 GET/POST 两项。

**改动**：

1. **四列表头筛选**（复用 HeaderRadioFilter，范式同需求①）：
   - 「请求方式」：`options = httpMethodOptions`（GET/POST/PUT/DELETE，与接口列表页签语义一致）
   - 三个白名单列：`options = yesNoOptions`（是 '1' / 否 '0'，组件内置「全部」''）；筛选值 `exempFilter` / `noUsersInfoFilter` / `unauthenticatedFilter`
   - `getList` query data 增补 `httpMethod` / `exempFlag` / `noUsersInfoFlag` / `unauthenticatedFlag`（后端 query-whitelist-page 已确认支持，2026-10-28：1=是、0=否、''=全部）；筛选即查（pageNum=1，复用 `handleSearch`），与 URL 输入筛选叠加
2. **列头字段提示**：三列 `#header` 结构为「标题文字 + el-tooltip 问号图标（QuestionFilled 16px #a7a8bc）+ HeaderRadioFilter（不传 title，仅渲染漏斗图标）」，外层 `.whitelist-header` inline-flex（gap 4px，图标与文字间距 5px 与弹窗 label 一致）。⚠️ 踩坑：el-tooltip 必须只包住 `el-icon`——首版包住「文字+图标」整个 label，气泡在表头文字上也会触发（2026-10-28 用户反馈后收窄到图标）
3. **弹窗表单项提示**：三个白名单 `el-form-item` 用 `#label` 插槽渲染「文字 span.tooltip-label + el-tooltip 问号图标」（同列头文案、同样仅图标触发）；新增 `.tooltip-label-item` 类与既有 `.api-url-item` 共用 label flex / 图标间距样式（选择器合并 `.api-url-item, .tooltip-label-item`）
4. **请求方式选项补齐**：弹窗下拉改遍历 `httpMethodOptions`（GET/POST/PUT/DELETE）；菜单页签 `UrlConfig.vue` 的 `methodList` 同步补齐（同步整改）

## 影响范围

| 文件                                                                   | 变更                                                                                                                                                                                |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `views/authorityManagement/components/InterfaceListTab.vue`            | 两列表头筛选（HeaderRadioFilter）；query 增 httpMethod；同步确认 confirmDialog 化                                                                                                   |
| `views/authorityManagement/components/HeaderRadioFilter.vue`           | 新建：轻量 radio 表头筛选组件（标题+漏斗图标+popover 单选面板，含「全部」）                                                                                                         |
| `views/authorityManagement/menu.vue`                                   | 移除顶部搜索下拉；menuName 列 headerCellRenderer + 定位面板接入；方框 +/- 与 24px 缩进网格；删除确认 confirmDialog.danger 化；urlList 提交 trim；新增按钮 Plus 14px；表格外框线移除 |
| `views/authorityManagement/components/MenuLocatorPanel.vue`            | 新建：popover 级联定位面板（多列级联 + el-select-v2 搜索 + 面包屑 + 底部操作区）                                                                                                    |
| `views/authorityManagement/components/AccessWhitelistInterfaceTab.vue` | 新增/编辑提交前 apiUrl trim；四列表头筛选（httpMethod + 三个白名单 全部/是/否）；列头/弹窗表单项问号提示；弹窗请求方式选项补齐 GET/POST/PUT/DELETE                                  |
| `views/authorityManagement/components/UrlConfig.vue`                   | 请求方式下拉 methodList 补齐 GET/POST/PUT/DELETE                                                                                                                                    |
| `components/ConfirmDialog.vue`                                         | 内容与底部按钮间距 52px → 30px（全站生效）                                                                                                                                          |

## Trade-off（有意接受）

1. `httpMethod` 筛选后端已支持（GET/POST/PUT/DELETE），无联调阻塞
2. 菜单弹窗视觉/交互细节在拿到 UX 稿前按默认方案开发，设计稿到位后可能有一次调整返工
3. ColumnFilter 局部副本方案已废弃（UX 图示为轻量 radio 面板，与 CategorySearchEditor 结构不符），改为专用 HeaderRadioFilter 组件，不引入第三份 ColumnFilter 副本
