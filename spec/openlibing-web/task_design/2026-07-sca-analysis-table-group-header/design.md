# Design: SCA 分析表二级表头 + nginx /argus 配置缩进统一

## 方案

### 1. 二级表头分组元数据

在 `analysisTable.config.js` 中新增 `columnGroups` 导出，用「分组 label + 列 id 数组」表达二级表头结构，**不改动原 `column` 数组**，避免影响列设置弹框、导出等依赖 `column` 顺序与结构的逻辑。

```js
export const columnGroups = [
  { label: '源代码', ids: ['fileName', 'detail', 'type', 'lines'] },
  { label: '开源软件代码', ids: ['ossLines', 'vendor', 'component', 'version', 'purl', 'file', 'licenses', 'clarifyConfirmType'] },
  { label: '分析及审核结果', ids: ['clarifyType', 'matched', 'reviewStatus', 'riskLevel', 'committerType', 'vulnerLeveList', 'clarifyAuthor', 'applyTime', 'reviewUserName', 'reviewTime'] },
];
```

分组依据用户语义划分：
- 源代码：含「代码行」，到 `lines` 为止
- 开源软件代码：从「开源软件代码行」开始，到「分析结果」之前
- 分析及审核结果：含「分析结果」到末尾

### 2. 模板渲染结构

三个 vue 文件统一改法：在原 `v-for` 列外层包一个父 `el-table-column`：

```html
<el-table-column
  v-for="group in table.columnGroups"
  :key="group.label"
  :label="group.label"
>
  <el-table-column
    v-for="column in table.column.filter((it) => it.show && group.ids.includes(it.id))"
    :key="column.id"
    :label="column.label"
    ...
  >
    <!-- 原 #header / #default 逻辑不变 -->
  </el-table-column>
</el-table-column>
```

要点：
- 父列只给 `label`，不渲染内容；子列继承原所有属性与 slot
- 子列过滤条件在原 `it.show` 基础上加 `group.ids.includes(it.id)`，保证列设置弹框勾选/取消仍生效（`show` 字段控制显隐，分组只决定归属）
- `columnGroups` 通过 `table.columnGroups` 暴露给模板（与 `table.column` 同级挂载）

### 3. nginx /argus 缩进

`/argus` 块原用 16 空格，相邻 `/ai`、`/build`、`/api-management` 用 18 空格。统一为 18 空格，纯格式调整，无语义变化。

## 影响分析

- **列设置弹框**：操作的是 `table.column` 的 `show` 字段，分组不参与，行为不变
- **导出逻辑**：遍历 `table.column`，顺序与字段不变
- **特殊列渲染**：子列 slot 内的 `column.id` 判断逻辑全部保留，无改动
- **未分组列**：`columnGroups` 的 id 并集覆盖全部 22 个列，无遗漏

## 不做的事

- 不调整 `column` 数组顺序
- 不修改列设置弹框 UI
- 不处理 `proxy_cookie_domain` 方向问题（功能性 bug，非本次范围，且其他 location 同样写法）
