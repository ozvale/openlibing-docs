# 任务：SCA 遗留 Vue2 SFC 迁移至 `<script setup>`

> 分支：`jzcfork/202610setup`　提交：`d09b04fe`、`1801cedd`
> 路径统一前缀 `apps/web-openlibing/`

## 1. 基础组件

- [x] `src/sca/src/components/BaseComponents/Pagination/index.vue`
- [x] `src/sca/src/components/BaseComponents/ReturnIcon/index.vue`
- [x] `src/sca/src/components/BaseComponents/TitleIcon/index.vue`
- [x] `src/sca/src/components/BaseComponents/tabs/index.vue`
- [x] `src/sca/src/components/Pagination/index.vue`
- [x] `src/sca/src/components/SvgIcon/index.vue`
- [x] `src/sca/src/components/Hamburger/index.vue`
- [x] `src/sca/src/components/TextTooltip/index.vue`
- [x] `src/sca/src/components/DeleteMessage.vue`

## 2. 业务组件

- [x] `src/sca/src/components/BaseComponents/RepoSelect/index.vue`
- [x] `src/sca/src/components/BaseComponents/PrRepoSelect/index.vue`
- [x] `src/sca/src/components/BaseComponents/communityRepoSelect/index.vue`
- [x] `src/sca/src/components/BaseComponents/batchUpdate/index.vue`
- [x] `src/sca/src/components/BaseComponents/combinationCondition/index.vue`
- [x] `src/sca/src/components/wangEditor/index.vue`

## 3. 业务页面

- [x] `src/sca/src/codeTree/ztreeCompent.vue`
- [x] `src/sca/src/codeTree/index.vue`

## 4. 布局

- [x] `src/sca/src/layout/index.vue`
- [x] `src/sca/src/layout/components/AppMain.vue`
- [x] `src/sca/src/layout/components/Navbar.vue`
- [x] `src/sca/src/layout/components/Sidebar/index.vue`
- [x] `src/sca/src/layout/components/Sidebar/Item.vue`
- [x] `src/sca/src/layout/components/Sidebar/Link.vue`
- [x] `src/sca/src/layout/components/Sidebar/Logo.vue`
- [x] `src/sca/src/layout/components/Sidebar/SidebarItem.vue`
- [x] `src/sca/src/layout/components/TagsView/index.vue`

## 5. 特殊处理

- [x] `src/sca/src/components/Empty.vue` 回退为 Options API，并加注释说明"有意保持未迁移"

## 6. 验证

- [ ] `src/sca` 下 `this.` 引用清零（`Empty.vue` 除外）
- [ ] `pnpm build` 通过，无未解析导入
- [ ] ESLint 通过
- [ ] 分页组件页码/页大小事件参数正确
- [ ] 仓库选择三件套远程搜索、分页、回填、清空正确
- [ ] 组合条件增删/嵌套/提交载荷正确
- [ ] 批量更新表单校验与提交正确
- [ ] 代码树展开/选中/搜索正常，ztree 实例销毁无泄漏
- [ ] 富文本初始化/取值/销毁正常
- [ ] 布局菜单渲染、折叠、页签切换/关闭正常
- [ ] `Empty.vue` 默认图与自定义描述正常
- [ ] 反复进出 ztree/wangEditor 页面无实例堆积

## 7. 交付

- [ ] 迁移清单与本文档 27 个文件逐一对齐
- [ ] 发布说明注明 `src/sca` 内部实现调整（对外无接口变化）
