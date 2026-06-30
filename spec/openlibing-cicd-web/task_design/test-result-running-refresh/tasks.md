# Tasks: 测试结果组件新增执行中状态展示与刷新按钮

## 实现步骤

- [x] 1. useTestResultData.ts：补充 running 状态映射，文案为"执行中"
- [x] 2. useTestResultData.ts：补充 getStateDotClass 中 running 状态的圆点颜色映射
- [x] 3. TestResult.vue：引入 Refresh 图标
- [x] 4. TestResult.vue：摘要栏新增"执行中：{{ summary.runningCount }}"显示
- [x] 5. TestResult.vue：摘要栏新增刷新按钮，绑定 tableLoading + loadData
