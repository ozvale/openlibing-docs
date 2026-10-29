# Design: 公开漏洞详情内嵌列表同页

## 方案选型

| 方案                      | 说明                                                  | 结论                                                                         |
| ------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------- |
| A. 同路由 query 内嵌      | URL 追加 `?issueNum=...` 区分列表/详情态              | 否决：用户明确不要 URL 带参数                                                |
| **B. 页内内存态（采用）** | 单路由，组件内 `detailRow` ref 切换视图，URL 全程不变 | 与合法合规模块（`sca/componentAnalysis`）模式一致                            |
| C. 父子嵌套路由           | 父路由 `hideChildrenInMenu`，列表/详情为子路由        | 否决：需把 index.vue 改造为 router-view 布局壳，改动量大，且详情仍是独立路由 |

## 核心设计（方案 B）

### 1. 视图切换与状态保留

```
PublicVulnerability/index.vue
├── .tabs（漏洞列表/责任组管理页签）        v-show="!detailRow"
├── .public-vulnerability-view-content      v-show="!detailRow"
│   └── vulnerabilityList  @go-detail="goDetail"
└── detailRow 存在时：
    ├── .breadcrumb-wrapper（面包屑 + 返回箭头）
    └── .public-vulnerability-detail-content
        └── vulnAnalysis :key="detailRow.cveNum" :detail-info="detailRow"
```

- 列表容器用 **`v-show` 而非 `v-if`**：列表 DOM 常驻，过滤条件、分页、请求状态天然保留，**取代原 Pinia store（`stores/publicVulnerability.ts`）暂存/恢复机制，store 整体删除**
- 详情用 `v-if="detailRow"` + `:key="detailRow.cveNum"`：切换不同漏洞时强制重新挂载，避免残留上一条的状态
- 列表 `goPage(row)` 改为 `emit('goDetail', row)`，父组件 `goDetail` 提取 `issueNum/cveNum/software` 存入 `detailRow`
- 责任组管理页签与详情互斥（详情态下页签容器整体 v-show 隐藏）

### 2. 参数传递：props + provide 兼容对象

详情组件链（vulnAnalysis → basicInformation / vulnerabilityImpact / vulnerabilityRepair / impactForm）原有大量 `route.query.issueNum/software` 引用（20+ 处）。为最小化改动：

- `vulnAnalysis/index.vue` 接收 props `detailInfo: { issueNum, cveNum, software }`，并 `provide('publicVulnDetailQuery', props.detailInfo)`
- 各子组件将 `const route = useRoute()` 替换为 `const route = { query: inject('publicVulnDetailQuery', {}) }`——构造一个**仅有 query 属性的兼容对象**，子组件所有 `route.query.xxx` 用法零改动
- 前置校验：grep 确认子组件对 route 的引用全部为 `route.query.*`，无 `path/params/fullPath` 等其他属性依赖

### 3. 面包屑返回

- 详情态顶部：返回箭头（el-icon ArrowLeft）+ `el-breadcrumb`「漏洞列表 / 漏洞分析详情」
- 父级「漏洞列表」可点击（`cursor: pointer`，悬浮 `#5e7ce0`），点击置 `detailRow = null` 回列表
- 面包屑父级文案用「漏洞列表」（列表页首个页签名）而非菜单名「公开漏洞」——指向的是列表视图本身
- 原 vulnAnalysis 顶部「返回」按钮（router.push）删除

### 4. 样式要点（踩坑记录）

- **双倍边距**：外层容器原有 `padding: 20px`，详情组件自身也有 `padding: 16px 20px`，叠加导致详情内容外圈边距过大。修复：详情态容器加 `is-detail` 类将 padding 归零，边距完全由详情组件自身提供；面包屑自身补 `padding: 16px 20px 0` 对齐
- **间隔灰底**：基本信息页签操作历史展开后，左表单与右历史表之间 20px 间隔应透出页面灰底。若父级白底容器包裹详情组件，间隔处会变白色——详情内容容器不得设置 `background-color: #ffffff` / padding
- vulnAnalysis 内容区高度由 `calc(100% - 80px)` 调整为 `calc(100% - 50px)`（返回按钮删除后的布局重算）

### 5. 权限语义变化（安全相关）

| 改造前                                                        | 改造后                                                                                       |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `noMenu` 路由 `meta.auth: 'public_cve:details'`，路由守卫拦截 | 路由已删；列表 cve 编号链接渲染前 `canHandle('public_cve:details')` 校验，无权限降级为纯文本 |

与既有责任组编辑权限（`cve_perosnLabel:manager` 控制编辑图标显隐）做法一致。无权限用户无法触达详情（无入口），但不再有路由级拦截兜底——详情不再是独立可直达的 URL，入口即全部控制点。

## Trade-off（有意接受）

1. **详情态刷新浏览器回到列表态**：内存态无 URL 参数可恢复，与合法合规模块行为一致；原先 query 方案可刷新恢复
2. **详情 URL 不可直接分享/收藏**：同上，URL 全程不变
3. **路由级权限兜底取消**：见上节，入口级控制为唯一控制点

## 影响范围

| 文件                                                                                     | 变更                                                   |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `views/PublicVulnerability/index.vue`                                                    | 新增 detailRow 内存态、面包屑、is-detail 样式          |
| `views/PublicVulnerability/vulnerabilityList.vue`                                        | goPage 改 emit；删 store 暂存/恢复；cve 链接加权限校验 |
| `views/PublicVulnerability/vulnAnalysis/index.vue`                                       | props + provide；删返回按钮；样式调整                  |
| `vulnAnalysis/{basicInformation,vulnerabilityImpact,vulnerabilityRepair,impactForm}.vue` | `useRoute()` → inject 兼容对象                         |
| `router/routes/modules/noMenu.ts`                                                        | 删 `publicVulnerabilityAnalysis` 路由                  |
| `stores/publicVulnerability.ts`                                                          | 整体删除                                               |

接口调用、请求参数、后端契约均无变化（`issueNum/software` 取值来源从 route.query 换成 props，值不变）。
