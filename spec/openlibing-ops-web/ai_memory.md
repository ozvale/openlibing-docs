# openlibing-ops-web AI Memory

本文档保存 `openlibing-ops-web` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-ops-web` 负责 OpenLibing AI 能力的 Web 侧交互。后续系统级职责、页面边界、接口契约、权限控制和用户体验规范需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及页面路由、权限、接口字段、用户可见交互时，必须在需求设计中说明影响范围。
- 前端需求完成后，必须在 `archive.md` 记录最终交互、验证方式、AI 错误和人工修正。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| -------- | -------- | -------- |
| 待补充   | 待补充   | 待补充   |

## 前端编码规范

### 项目结构

```
src/
├── api/                  # API 接口层
├── assets/               # 静态资源（样式、图标等）
├── components/           # 公共组件
├── hooks/                # 组合式函数
├── plugins/              # 插件
├── router/               # 路由配置
├── stores/               # Pinia 状态管理
├── types/                # TypeScript 类型定义
├── utils/                # 工具函数
├── views/                # 页面组件
└── 根级文件               # App.vue、main.ts 等入口文件
```

- 禁止在 `src` 下新建非标准目录。
- 状态 `src/stores/` 按业务模块划分，暴露 `useXxxStore` Hook。
- 工具 `src/utils/`、接口类型 `src/types/`、组件 `src/components/`、页面 `src/views/` 均按业务模块/页面组织。
- 公共部分复用：`base-table.vue`、`src/plugins/chart/`、`base-column-settings.vue`、`time-range-filter.vue`、`src/utils/`。无特殊要求必须复用，禁止重复造轮子。
- 业务页面代码保持简洁、易读，避免过度复杂。

### 编码规范

- 所有代码必须使用 TypeScript，禁止使用 JavaScript；禁止使用 `any`（除非有明确理由并加注释）。
- 接口、类型定义必须使用 PascalCase 命名；组件 Props 必须定义清晰的 TypeScript 接口。
- 命名：文件夹/文件 kebab-case、变量/函数 camelCase、常量 UPPER_CASE、枚举及属性 PascalCase/UPPER_CASE、接口/类 PascalCase、自定义 Hooks 以 `use` 开头。
- 业务函数：事件处理 `onXxx`（如 `onBannerClick`）、内部处理 `handleXxx`（如 `handleSubmit`）。

### 组件规范

- 组件目录在 `src/components` 下，每个组件单独文件（有子组件则新建目录）。
- 组件文件名使用多个单词的 kebab-case；交互组件库二次封装必须使用 Element Plus。
- 单个 `.vue` 文件建议不超过 400 行（拆分参考阈值）；遵循单一职责。
- 页面级组件（仅当前页面使用）→ `src/views/<type>/<page>/<name>.vue`；通用组件（跨页面复用）→ `src/components/<name>.vue`。
- `src/components/` 中的组件必须真正通用，业务耦合组件禁止放入。

### API 规范

- 使用 `axios` 封装的 `http` 请求；页面接口集中在 `src/api/<type>/<name>.ts`；TS 类型定义放 `src/types/<name>.ts`。
- 接口函数命名（NON-NEGOTIABLE）：`getXxxList` / `getXxxDetail` / `createXxx` / `updateXxx` / `deleteXxx`。禁止 `fetch` 前缀或匈牙利命名。
- 业务代码通过 `src/utils/promise.ts` 的 `to` 函数处理 Promise，避免过多 try-catch。
- 接口错误由 HTTP 拦截器统一处理，业务代码禁止重复添加错误提示、禁止直接处理 `http` 错误码；前端表单验证错误和业务逻辑检查错误可保留；成功提示可保留。

### 样式复用与去重（强制）

- 铁律：样式不允许重复。只要两个 class 的 CSS 规则集合实质相同就必须合并。
- 落点：全局公共 → `src/assets/style/common.less`（跨模块复用）；模块内公共 → `src/views/<module>/style.less`（仅本模块多个组件复用）；组件私有 → 组件 `<style lang="less" scoped>`（仅本组件一处）。
- 判定流程：跨 ≥2 个模块抽到 common.less；仅本模块 ≥2 处抽到 `<module>/style.less`；仅本组件 1 处留在 scoped。
- 引入方式：模块入口用非 scoped `<style lang="less">@import "./style.less";</style>`；全局公共由 `main.ts` 引一次 `import "@/assets/style/common.less"`。

### 工程约束

- mock 数据必须放在根目录 `/mock` 文件夹下（不存在则创建），必须使用 `vite-plugin-mock` 配置，禁止手动写在 `src/api/**` 下；`/mock` 文件夹禁止提交（保持 .gitignore 规则）。
- 代码中不能写任何注释。
- 自动导入（`unplugin-auto-import` / `unplugin-vue-components` / `unplugin-icons`，配置见 `vite.config.ts`）：
  - Vue / vue-router / pinia / @vueuse/core 的 API（`ref`、`computed`、`watch`、`defineStore`、`storeToRefs` 等）自动导入。
  - `src/api/**`、`src/hooks/**`、`src/types/**`、`src/utils/**`、`src/stores/**` 导出的函数、常量、类型自动导入。
  - `src/components/**` 组件在模板中直接用组件名，不手动 import。
  - Element Plus 组件 `el-*` 标签直接用。
  - 图标：`<i-ep-xxx />`（Element Plus 图标集合）并用 `<el-icon>` 包裹，无需显式 import。
- 提交前质量门禁：每次 commit 前必须运行 `npm run lint`、`npm run format`、`npm run test:unit`、`npm run type-check`，全部无问题才能提交。
