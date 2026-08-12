## 1. 状态字段适配与标签拆分

- [x] 1.1 修改数量接口字段映射：`unresolvedCount` → `pendingCount`，`closedCount` 拆分为 `ignoredFalsePositiveCount`/`ignoredTestUsageCount`/`ignoredWontFixCount`/`resolvedAutoCount`
- [x] 1.2 拆分状态标签：将"已关闭" el-tab-pane 拆分为"已修复"和"已忽略"两个独立标签
- [x] 1.3 更新各标签状态值映射：待处理→PENDING、已修复→RESOLVED、已忽略→IGNORED
- [x] 1.4 计算 `ignoredCount = ignoredFalsePositiveCount + ignoredTestUsageCount + ignoredWontFixCount` 用于展示

## 2. 接口参数适配

- [x] 2.1 修改 `buildParams`：删除 `closed` 和 `statuses` 字段，新增 `tab` 字段（值取 `query.status`）
- [x] 2.2 确认 `tab` 字段取值：PENDING（待处理）、IGNORED（已忽略）、RESOLVED（已修复）

## 3. 状态值同步

- [x] 3.1 将全局所有 `RESOLVED_AUTO` 替换为 `RESOLVED`（类型定义、状态映射、模板判断等）
- [x] 3.2 更新搜索框 `GithubIssueSearch` 中的状态筛选选项映射
- [x] 3.3 更新 `GithubHeaderFilter` 中的状态标签渲染逻辑

## 4. 忽略原因筛选

- [x] 4.1 在 `searchQualifiers` 中新增"忽略原因"筛选条件，`visible: query.status === 'IGNORED'`
- [x] 4.2 忽略原因选项从 `options.shieldTypes` 获取，label 后拼接 `(数量)`
- [x] 4.3 实现 `shieldTypeCount(code)` 方法，根据 `code` 映射到对应数量字段
- [x] 4.4 切换状态时重置 `shieldTypes` 选中值
- [x] 4.5 列表接口请求参数中包含 `shieldTypes` 字段

## 5. 数据来源筛选改为单选

- [x] 5.1 将 `StaticAlarmFilter.sources` 类型从 `string[]` 改为 `string`
- [x] 5.2 从 `MULTI_FILTER_KEYS` 中移除 `sources`
- [x] 5.3 修改解析逻辑：`case 'source'` 中直接赋值单值
- [x] 5.4 修改序列化逻辑：`sources` 直接输出单值字符串
- [x] 5.5 在 `searchQualifiers` 和 `GithubHeaderFilter` 中设置 `multiple: false`

## 6. 测试更新

- [x] 6.1 更新 `staticAlarmSearchQuery.spec.ts` 中状态值断言（`OPEN` → `PENDING` 等）
- [x] 6.2 更新 `sources` 相关测试用例（从多值改为单值）
