# 任务：菜单 URL 配置改为输入联想

> 分支：`jzcfork/202610apiinput`　提交：`9808d5fd`、`e6b31246`、`98964237`

## 1. 控件替换

- [x] `UrlConfig.vue` 移除 `el-select`（含 `filterable`、`allow-create`、`default-first-option`、`remote`、`reserve-keyword`、`v-select-scroll`）
- [x] 新增 `el-autocomplete`，绑定 `v-model="data.menuUrl"`、`value-key="apiUrl"`
- [x] 配置 `:fetch-suggestions="querySearch"`、`:trigger-on-focus="true"`、`highlight-first-item`、`clearable`、`popper-class="menuUrlAutocomplete"`
- [x] 增加 `maxlength="255"`

## 2. 候选渲染

- [x] 默认插槽输出 `({{ item.httpMethod }}) {{ item.apiUrl }}`
- [x] `urlFlag === '0'` 时套用 `url-flag-red` 标红
- [x] 新增 `.url-item-wrap :deep .el-autocomplete { flex: 1 }`

## 3. 查询与联动逻辑

- [x] 新增 `querySearch(queryString, cb)`，调用 `queryInterfaceListPage({ data: { apiUrl, urlFlag: '' }, params: { pageSize: 50, pageNum: 1 } })`
- [x] 成功取 `data.data` 并 `cb(list)`，异常 `cb([])`
- [x] 新增 `emitChange()` 替代 `getUrlResult`，按 `apiUrl` 命中同步 `requestMethod`/`flag`，未命中保留请求方式并清空 `flag`
- [x] `$emit('change', res)` 保持对外契约
- [x] 新增 `'data.menuUrl'` watcher，`val === item.menuUrl` 时提前 return

## 4. 清理与样式

- [x] 删除 `pageNum`、`apiUrl`、`totalNum`、`selectLoading` 状态
- [x] 删除 `visibleChange`、`getUrlList`、`getOptions`、`loadMore`
- [x] `.menuUrlLazySelect` 重命名为 `.menuUrlAutocomplete`
- [x] `url-flag-red-selected` 选择器由 `.el-select__selected-item` 改为 `.el-input__inner`

## 5. 账号绑定表格

- [x] `UserInfo/AccountBind.vue` 删除 `prop="createTime"`、`label="绑定时间"` 列

## 6. 验证

- [ ] 弹窗打开聚焦输入框即拉取候选（≤50 条）
- [ ] 关键字过滤正确，展示格式与标红正确
- [ ] 选中已下线接口：请求方式同步 + 标红 + change 携带 `flag='0'`
- [ ] 自由输入：请求方式保持 + 标红清除
- [ ] 输入超 255 字符被截断
- [ ] 保存后重开，URL 与下线标记正确回显
- [ ] 账号绑定页无"绑定时间"列

## 7. 交付

- [ ] TypeScript / ESLint 检查通过
- [ ] 菜单配置相关页面冒烟通过
