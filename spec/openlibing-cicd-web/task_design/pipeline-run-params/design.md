# 流水线运行参数表单优化 - 技术方案

## 涉及文件

| 文件                                       | 说明                       |
| ------------------------------------------ | -------------------------- |
| `src/views/pipeline/pipelineRunDialog.vue` | 流水线运行弹窗，单文件修改 |

## 数据流

### 接口数据获取

`getPipelineDetailAxios` 接口返回 `res.data.variables` 数组，每个元素包含：

| 字段          | 类型     | 说明                                |
| ------------- | -------- | ----------------------------------- |
| `name`        | string   | 参数名称                            |
| `value`       | string   | 参数默认值                          |
| `type`        | string   | 参数类型：enum/string/autoIncrement |
| `is_runtime`  | boolean  | 是否运行时参数                      |
| `description` | string   | 参数描述                            |
| `limits`      | string[] | enum 类型时的可选值列表             |

### 数据转换

```javascript
// 接口返回后映射
const params = res.data.variables.map((item) => ({
  name: item.name,
  type: item.type,
  value: item.value,
  is_runtime: item.is_runtime,
  description: item.description,
  limits: item.limits || [],
}));

// 运行时参数在前，非运行时参数在后
executionParams.value = params.sort((a, b) => {
  return (a.is_runtime === false ? 1 : 0) - (b.is_runtime === false ? 1 : 0);
});
```

## 模板渲染逻辑

```
execution-content-row (v-for)
  ├── name-text-column: 名称文本
  ├── desc-content-column: 描述文本（tooltip 包裹，hover 显示完整内容）
  ├── type-text-column: 类型标签（typeLabelMap 映射）
  └── 默认值列:
       ├── is_runtime === false → 纯文本 + tooltip 提示
       └── is_runtime !== false:
            ├── item.name === 'repo' && isUbmc → el-select (repoList)
            ├── item.type === 'enum' → el-select (item.limits)
            └── else → el-input
```

## 类型映射

```javascript
const typeLabelMap = {
  enum: "枚举",
  string: "字符串",
  autoIncrement: "自增长",
};
```

## 影响范围

- 仅修改 `pipelineRunDialog.vue` 单文件
- 无接口变更，无新增依赖
- 移除：`itemRules` 验证规则、`executionTypeOptions` 类型选项、`CirclePlus`/`Remove` 图标、`addIp`/`subIp` 函数
