# 设计：菜单 URL 配置改为输入联想

## Context

菜单/权限配置页的 `UrlConfig.vue` 负责维护"菜单地址 + 请求方式 + 是否下线"三元信息，`menuUrl` 既可能取自已登记接口，也可能由管理员自由填写。原实现用 `el-select`：

- `remote` + `filterable` + `allow-create` + `default-first-option` + `reserve-keyword`
- `v-select-scroll` 绑定 `visibleChange` / `loadMore`，按 `pageNum` 累加、`totalNum` 判停，`selectLoading` 控制 loading

问题在于：分页状态与选择语义互相污染——用户下拉翻页会改变 `urlOptions` 集合，`getUrlResult` 依据集合做 `find`，一旦父组件回写 `menuUrl` 就可能误判"未命中"从而清掉 `flag`。

## Goals / Non-Goals

### Goals

1. 输入即联想，减少查找路径长度。
2. 选中项与自由输入的语义边界清晰：选中 -> 同步请求方式与下线标记；自由输入 -> 保留请求方式、清空标记。
3. 父组件回传 `menuUrl` 不触发 change，避免误清下线标记。
4. 输入长度受控（255）。

### Non-Goals

- 不改造 `queryInterfaceListPage` 后端接口与分页契约。
- 不引入本地缓存或全量接口预加载。
- 不改动 `UrlConfig` 对外 props / 事件契约。

## Decisions

### D1：用 `el-autocomplete` 而非保留 `el-select`

`el-autocomplete` 天然表达"输入 + 联想 + 可自由填写"，无需 `allow-create` 这类补丁式能力；`value-key="apiUrl"` 让 v-model 直接承载 URL 字符串，与现有 `data.menuUrl` 语义一致。

### D2：单次取 50 条，不做滚动加载

原 `v-select-scroll` 无限滚动在 autocomplete 的下拉结构下难以复用，且联想输入的场景是"缩小候选"而非"浏览全集"，故固定 `pageSize: 50`、`pageNum: 1`。删除 `pageNum/totalNum/selectLoading` 三个状态。

### D3：候选渲染保留 method 与下线标红

默认插槽输出 `({{ item.httpMethod }}) {{ item.apiUrl }}`；当 `item.urlFlag === '0'` 时套用 `url-flag-red`。使管理员在不选中前即可识别下线接口。

### D4：`emitChange` 区分命中/未命中

```js
emitChange() {
  const tmp = this.urlOptions.find((item) => item.apiUrl === this.data.menuUrl);
  const res = { ...同步 requestMethod / flag... };
  this.$emit('change', res);
}
```

- 命中：`requestMethod = tmp.httpMethod`，`flag = tmp.urlFlag`。
- 未命中：`requestMethod` 保持当前值（缺省 `'GET'`），`flag = ''`。

### D5：watcher 守卫父组件回写

```js
'data.menuUrl'(val) {
  if (val === this.item.menuUrl) return;
  this.emitChange();
}
```

父组件把已保存值写回 `data.menuUrl` 时值与 `item.menuUrl` 相同，直接返回，避免"未命中 -> 清空 flag"，从而不丢失下线标记。

## 交互矩阵

| 场景                   | menuUrl 变化来源 | 命中 urlOptions | requestMethod        | flag             | 是否触发 change |
| ---------------------- | ---------------- | --------------- | -------------------- | ---------------- | --------------- |
| 用户从下拉选中一项     | 用户输入/点选    | 是              | 取 `httpMethod`      | 取 `urlFlag`     | 是              |
| 用户手工输入未登记 URL | 用户输入         | 否              | 保持现值（缺省 GET） | `''`             | 是              |
| 父组件回写已保存值     | props 同步       | 不判断          | 不变                 | 不变             | 否              |
| 打开弹窗初始化         | 初始化赋值       | 不判断          | 由初始化数据决定     | 由初始化数据决定 | 否              |

## 后端接口契约

沿用现有接口，不新增、不改字段：

```http
POST {FRAME_WORK}/.../interface/queryInterfaceListPage
data:   { "apiUrl": "<keyword>" }
params: { "pageSize": 50, "pageNum": 1 }
```

响应取 `data.data` 作为候选数组（元素含 `apiUrl`、`httpMethod`、`urlFlag`）。请求异常时 `cb([])`，下拉为空且不阻塞自由输入。

## 涉及文件

| 文件                                                                         | 操作 | 说明                                                                                                |
| ---------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/authorityManagement/components/UrlConfig.vue` | 修改 | select -> autocomplete；新增 `querySearch`/`emitChange`/watcher；删除分页方法与状态；样式选择器适配 |
| `apps/web-openlibing/src/views/UserInfo/AccountBind.vue`                     | 修改 | 删除"绑定时间"列                                                                                    |

## 风险与兼容性

| 风险                                       | 影响 | 应对                                                                                     |
| ------------------------------------------ | ---- | ---------------------------------------------------------------------------------------- |
| 候选只取 50 条，长尾接口需更精确关键字     | 中   | 联想语义可接受；如有反馈可调大 `pageSize`                                                |
| autocomplete 标红态依赖 `.el-input__inner` | 低   | 已在样式改为 `.el-input__inner`；需回归已下线接口展示                                    |
| 父组件回写路径依赖 `item.menuUrl` 存在     | 低   | `item` 为必传 prop，编辑场景恒有值；新增场景 `item.menuUrl` 为空，回写也不等价于用户输入 |
| 删除 `visibleChange` 等方法后有无外部引用  | 低   | 方法为组件内部私有，无外部调用                                                           |

## 验证策略

1. 打开菜单配置弹窗，聚焦 URL 输入框应自动拉取候选（最多 50 条）。
2. 输入关键字后候选按 `apiUrl` 过滤，格式为 `(METHOD) url`。
3. 选中已下线接口 -> 请求方式同步、URL 标红、change 事件携带 `flag='0'`。
4. 手工输入未登记 URL -> 请求方式保持、标红消失。
5. 输入超过 255 字符应被截断。
6. 保存后重新打开，已保存 URL 与下线标记应原样回显（不被 watcher 清空）。
7. 账号绑定页不再出现"绑定时间"列。
