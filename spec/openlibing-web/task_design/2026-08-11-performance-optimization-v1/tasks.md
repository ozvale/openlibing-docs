# 前端性能优化第一版 实现任务清单

## 任务分组

### 第一组：构建目标与依赖优化

- [x] 1.1 升级 browserslist 浏览器兼容目标
  - 文件：`.browserslistrc`
  - 将 `> 1%` 改为 `> 0.5%`，删除 `not ie 11`
  - 新增明确的浏览器版本：`Chrome >= 87, Firefox >= 78, Safari >= 14, Edge >= 87`
- [x] 1.2 升级构建 target 为 es2020
  - 文件：`internal/vite-config/src/config/application.ts`
  - `target: 'es2015'` → `target: 'es2020'`
- [x] 1.3 移除 babel-polyfill 依赖
  - 文件：`apps/web-openlibing/package.json`
  - 删除 `"babel-polyfill": "catalog:"` 依赖项

### 第二组：Element-Plus 按需导入

- [x] 2.1 启用 Element-Plus 按需导入插件
  - 文件：`apps/web-openlibing/vite.config.mts`
  - 取消注释 `import ElementPlus from 'unplugin-element-plus/vite'`
  - 在 plugins 数组中添加 `ElementPlus({})`

### 第三组：手动分包 (manualChunks)

- [x] 3.1 配置 rollup manualChunks
  - 文件：`apps/web-openlibing/vite.config.mts`
  - 在 `build.rollupOptions.output` 中配置 `manualChunks`：
    - `vendor-vue`：vue / vue-router / pinia / vue-i18n
    - `vendor-element-plus`：element-plus / @element-plus/icons-vue
    - `vendor-echarts`：echarts
    - `vendor-monaco`：monaco-editor
    - `vendor-codemirror`：codemirror / @codemirror/state / @codemirror/view / @codemirror/commands
    - `vendor-wujie`：wujie-vue3 / wujie-polyfill
    - `vendor-utils`：dayjs / lodash / axios / jszip / file-saver / xlsx / html2canvas

### 第四组：华为客服 SDK 按需加载

- [x] 4.1 创建 loadHuaweiCS 工具函数
  - 文件：`apps/web-openlibing/src/utils/loadHuaweiCS.ts`（新增）
  - 实现 `loadHuaweiCS()` 函数：动态创建 async script 标签加载华为客服 SDK
  - 包含防重复加载判断（检查 `ihelp_component_script` id 是否已存在）
- [x] 4.2 从 index.html 中移除客服脚本
  - 文件：`apps/web-openlibing/index.html`
  - 删除 `<script id="ihelp_component_script" ...>` 标签
- [x] 4.3 在 bootstrap 中调用按需加载
  - 文件：`apps/web-openlibing/src/bootstrap.ts`
  - 导入 `loadHuaweiCS`
  - 在 `app.mount('#app')` 之后调用 `loadHuaweiCS()`

### 第五组：_app.config.js 内联注入

- [x] 5.1 改造 extra-app-config 插件为内联注入
  - 文件：`internal/vite-config/src/plugins/extra-app-config.ts`
  - 移除 `generatorContentHash` 导入
  - 将外部 script 标签引用改为 `injectTo: 'head-prepend'` 的内联 `children` 方式
  - 读取配置源文件内容直接注入

### 第六组：wangeditor 动态导入

- [x] 6.1 主应用 WangEditor 组件动态导入
  - 文件：`apps/web-openlibing/src/components/WangEditor.vue`
  - 移除顶层 `import WangEditor from 'wangeditor'`
  - 在 `wangEditorInit` 函数内使用 `await import('wangeditor')` 动态导入
  - 函数改为 `async`
- [x] 6.2 马军模块 WangEditor 组件动态导入
  - 文件：`apps/web-openlibing/src/majun/src/components/WangEditor.vue`
  - 移除顶层 `import WangEditor from 'wangeditor'`
  - 在 `wangEditorInit` 方法内使用 `await import('wangeditor')` 动态导入
  - `wangEditorInit` 和 `mounted` 改为 `async`
- [x] 6.3 SCA 模块 wangEditor 组件动态导入
  - 文件：`apps/web-openlibing/src/sca/src/components/wangEditor/index.vue`
  - 移除顶层 `import WangEditor from 'wangeditor'`
  - 在 `creatEditor` 方法内使用 `await import('wangeditor')` 动态导入
- [x] 6.4 SCA views 模块 wangEditor 组件动态导入
  - 文件：`apps/web-openlibing/src/views/sca/component/wangEditor/index.vue`
  - 移除顶层 `import WangEditor from 'wangeditor'`
  - 在 `creatEditor` 方法内使用 `await import('wangeditor')` 动态导入

### 第七组：字体加载优化

- [x] 7.1 主应用 iconfont 字体声明优化
  - 文件：`apps/web-openlibing/src/assets/font/iconfont.css`
  - 在 `@font-face` 声明中添加 `font-display: swap;`
- [x] 7.2 马军模块 iconfont 字体声明优化
  - 文件：`apps/web-openlibing/src/majun/src/assets/font/iconfont.css`
  - 在 `@font-face` 声明中添加 `font-display: swap;`
- [x] 7.3 马军模块自定义字体声明优化
  - 文件：`apps/web-openlibing/src/majun/src/assets/css/common.less`
  - 在 Lato 和 PangMenZhengDao 两个 `@font-face` 声明中各添加 `font-display: swap;`
- [x] 7.4 修复 element-icons 字体声明
  - 文件：`apps/web-openlibing/src/majun/src/theme/index.css`
  - `font-display: 'auto'` → `font-display: swap`（去掉引号）

### 第八组：Nginx 缓存与协议优化

- [x] 8.1 Beta 环境 Nginx 优化
  - 文件：`apps/web-openlibing/nginx/nginx_beta.conf`
  - HTML 缓存策略：`no-cache,no-store,must-revalidate` → `no-cache,must-revalidate`
  - 新增 `_app.config.js` 长期缓存 location 块
  - 新增静态资源（图片、字体）长期缓存 location 块
- [x] 8.2 Gamma 环境 Nginx 优化
  - 文件：`apps/web-openlibing/nginx/nginx_gamma.conf`
  - 监听启用 `http2`
  - HTML 缓存策略：`no-cache,no-store,must-revalidate` → `no-cache,must-revalidate`
  - 新增 `_app.config.js` 长期缓存 location 块
  - 新增静态资源（图片、字体）长期缓存 location 块
- [x] 8.3 Prod 环境 Nginx 优化
  - 文件：`apps/web-openlibing/nginx/nginx_prod.conf`
  - 监听启用 `http2`
  - HTML 缓存策略：`no-cache,no-store,must-revalidate` → `no-cache,must-revalidate`
  - 新增 `_app.config.js` 长期缓存 location 块
  - 新增静态资源（图片、字体）长期缓存 location 块

## 任务依赖关系

- 第一组、第七组无依赖，可优先并行
- 第二组、第三组无依赖，可并行
- 第四组无依赖，可独立
- 第五组无依赖，可独立
- 第六组无依赖，可独立
- 第八组无依赖，可独立（但建议在构建验证后执行）

## 执行顺序建议

1. 第一组 + 第七组（并行）
2. 第二组 + 第三组 + 第四组 + 第五组 + 第六组（并行）
3. 第八组
4. 构建验证 + 功能回归测试

## 当前状态

- [x] 全部完成
- 19 个文件变更，+113 行 / -33 行