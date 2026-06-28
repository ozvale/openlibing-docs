# Design: 测试结果组件新增执行中状态展示与刷新按钮

## 技术方案

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| TestResult.vue | 引入 Refresh 图标，摘要栏新增"执行中"计数与刷新按钮 |
| useTestResultData.ts | 补充 running 状态映射与 getStateDotClass 颜色 |

### 状态映射变更

useTestResultData.ts 中的状态映射新增 running 分支：

```
running -> "执行中"  // 原先缺少此映射，导致执行中的用例状态显示为空
```

getStateDotClass 新增 running 颜色映射，与执行中的语义保持一致。

### UI 变更

摘要栏在"失败数"与"通过率"之间插入"执行中：N"展示：

```
总用例数：X，通过数：Y，失败数：Z，执行中：N，通过率：P%
[刷新] [导出全量用例]
```

刷新按钮：
- 使用 el-button + Refresh 图标
- 绑定 tableLoading 状态，加载中显示 loading 动画
- 点击调用 loadData 方法

### 影响范围

- 仅修改 TestResult 组件内部，不影响外部接口
- 不涉及数据模型变更，running 状态数据由后端已有字段提供
- 无安全影响
