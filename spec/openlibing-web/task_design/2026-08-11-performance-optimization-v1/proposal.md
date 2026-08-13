# 前端性能优化第一版

**Commit**: openlibing/openlibing-web@00a9920987ee6bdad23fa418b3dc0b317a438b3e

## 需求背景

OpenLibing Web 前端在长期迭代中积累了多项性能问题：首屏加载受第三方 SDK 同步脚本阻塞、静态资源缓存策略不完善、部分重型依赖（wangeditor、element-plus）全量打包导致 bundle 体积过大、字体文件缺少 `font-display: swap` 导致文字渲染延迟、构建目标仍为 `es2015` 未充分利用现代浏览器特性、babel-polyfill 冗余依赖等。

本次优化从**构建产物、网络加载、运行时渲染**三个维度入手，系统性提升前端性能。

## 功能描述

### 做什么

#### 1. 构建优化

- **升级 browserslist 与构建目标**：将浏览器兼容目标从 `> 1%` 升级为 `Chrome >= 87, Firefox >= 78, Safari >= 14, Edge >= 87`，构建 target 从 `es2015` 升级为 `es2020`，减少 polyfill 与转译开销
- **移除 babel-polyfill**：现代浏览器已原生支持 ES2020 特性，移除冗余的 `babel-polyfill` 依赖
- **Element-Plus 按需导入**：启用 `unplugin-element-plus/vite` 插件，实现 Element-Plus 组件按需引入，减少样式体积
- **手动分包 (manualChunks)**：在 `vite.config.mts` 中配置 rollup `manualChunks`，将大型依赖拆分为独立 vendor chunk：
  - `vendor-vue`：vue / vue-router / pinia / vue-i18n
  - `vendor-element-plus`：element-plus / @element-plus/icons-vue
  - `vendor-echarts`：echarts
  - `vendor-monaco`：monaco-editor
  - `vendor-codemirror`：codemirror 系列
  - `vendor-wujie`：wujie-vue3 / wujie-polyfill
  - `vendor-utils`：dayjs / lodash / axios / jszip / file-saver / xlsx / html2canvas

#### 2. 网络加载优化

- **华为客服 SDK 按需加载**：将 `index.html` 中的同步 `<script>` 标签移除，改为在 `bootstrap.ts` 首屏渲染完成后通过 `loadHuaweiCS()` 动态创建 async script 标签加载，避免阻塞首屏渲染
- **`_app.config.js` 内联注入**：将 `_app.config.js` 由外部 script 标签引用改为构建时直接内联到 HTML `<head>` 中，消除额外网络请求
- **Nginx 缓存策略优化**：
  - 启用 HTTP/2 协议（gamma/prod 环境）
  - HTML 缓存策略从 `no-cache,no-store,must-revalidate` 改为 `no-cache,must-revalidate`（允许条件请求验证，减少传输量）
  - 新增 `_app.config.js` 长期缓存规则（`max-age=31536000, immutable`）
  - 新增静态资源（图片、字体）长期缓存规则（`max-age=31536000, immutable`）

#### 3. 运行时渲染优化

- **wangeditor 动态导入**：将 4 处 wangeditor 的静态 `import` 改为 `await import()` 动态导入，仅在编辑器初始化时加载，减少首屏 bundle 体积
- **字体加载优化**：为所有 `@font-face` 声明添加 `font-display: swap`，避免字体加载期间文字不可见（FOIT），共涉及 3 个文件 5 处字体声明
- **修复 element-icons 字体声明**：`font-display: 'auto'` 改为 `font-display: swap`（去掉引号，修复语法错误）

### 不做什么

- 不涉及后端接口变更
- 不涉及业务逻辑功能变更
- 不修改路由级别的 lazy loading（已有）
- 不涉及图片压缩或 CDN 迁移

## 验收标准

- [ ] 构建产物中不再包含 `babel-polyfill`
- [ ] 构建 target 为 `es2020`，产物中箭头函数、async/await 等 ES2020 特性不再转译
- [ ] Element-Plus 样式按需加载，未使用的组件样式不打包
- [ ] 构建产物中 7 个 vendor chunk 独立存在
- [ ] 华为客服 SDK 脚本不在 `index.html` 中直接引用，而是在首屏渲染后动态加载
- [ ] `_app.config.js` 内容内联到 HTML `<head>` 中
- [ ] Nginx 配置中 gamma/prod 监听启用 `http2`
- [ ] 静态资源（图片、字体、`_app.config.js`）响应头包含 `Cache-Control: public, max-age=31536000, immutable`
- [ ] HTML 响应头为 `Cache-Control: no-cache,must-revalidate`
- [ ] wangeditor 在编辑器初始化时才加载，首屏不加载
- [ ] 所有 `@font-face` 声明包含 `font-display: swap`
- [ ] element-icons 的 `font-display` 值为 `swap`（无引号）
- [ ] 首屏加载时间（LCP / FCP）有可测量改善
- [ ] 各页面功能正常（编辑器、客服、微前端等）

## 影响范围

- 前端文件：
  - `.browserslistrc`（浏览器兼容目标）
  - `apps/web-openlibing/index.html`（移除客服脚本）
  - `apps/web-openlibing/package.json`（移除 babel-polyfill）
  - `apps/web-openlibing/vite.config.mts`（manualChunks + ElementPlus 插件）
  - `apps/web-openlibing/src/bootstrap.ts`（客服 SDK 动态加载）
  - `apps/web-openlibing/src/utils/loadHuaweiCS.ts`（新增，客服 SDK 加载工具）
  - `apps/web-openlibing/src/components/WangEditor.vue`（动态导入 wangeditor）
  - `apps/web-openlibing/src/majun/src/components/WangEditor.vue`（动态导入 wangeditor）
  - `apps/web-openlibing/src/sca/src/components/wangEditor/index.vue`（动态导入 wangeditor）
  - `apps/web-openlibing/src/views/sca/component/wangEditor/index.vue`（动态导入 wangeditor）
  - `apps/web-openlibing/src/assets/font/iconfont.css`（font-display: swap）
  - `apps/web-openlibing/src/majun/src/assets/font/iconfont.css`（font-display: swap）
  - `apps/web-openlibing/src/majun/src/assets/css/common.less`（font-display: swap）
  - `apps/web-openlibing/src/majun/src/theme/index.css`（修复 font-display）
  - `internal/vite-config/src/config/application.ts`（es2020 target）
  - `internal/vite-config/src/plugins/extra-app-config.ts`（\_app.config.js 内联）
- Nginx 配置：
  - `apps/web-openlibing/nginx/nginx_beta.conf`
  - `apps/web-openlibing/nginx/nginx_gamma.conf`
  - `apps/web-openlibing/nginx/nginx_prod.conf`
- 模块：构建配置、启动入口、富文本编辑器、Nginx 部署
- 数据模型：无变更
