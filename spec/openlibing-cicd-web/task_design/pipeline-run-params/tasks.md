# 流水线运行参数表单优化 - 实现任务

## 任务列表

- [x] 接口数据映射：增加 `type`、`is_runtime`、`description`、`limits` 字段
- [x] 运行时/非运行时参数排序：is_runtime === false 排在后
- [x] 类型列文本显示：typeLabelMap 映射 enum/string/autoIncrement
- [x] 非运行时参数整行加深背景色（is-disabled-row class）
- [x] 非运行时参数默认值列纯文本 + tooltip 提示"非运行时参数，到华为云流水线修改"
- [x] 运行时参数 enum 类型下拉选择（选项来自 limits）
- [x] 保留已有 repo 下拉选择逻辑（item.name === 'repo' && isUbmc）
- [x] 新增描述列，文本过长省略 + hover tooltip 显示完整内容
- [x] 移除新增/删除参数按钮及相关函数
- [x] 移除 itemRules 验证规则
- [x] 移除 executionTypeOptions 和 type 下拉选择
- [x] 表单样式优化：边框、圆角、行 hover、间距对齐、表头高度