# 实现任务清单

## 任务分解

### 1. tab 改名

- [x] 「已下线接口」→「未匹配接口列表」（tabList label 修改，prop 不变）
- [x] 「误报接口」→「人工配置接口」（tabList label 修改，prop 不变）

### 2. tab 问号提示

- [x] tabList 每项新增 tip 字段（4 个 tab 有值，菜单 tab 为空）
- [x] 模板 tab-item 内增加 el-tooltip + 问号图标（v-if 按 tip 控制）
- [x] 样式新增 .tab-tip-icon（灰默认、蓝 hover、14px 字号、4px 间距）

### 3. 其他

- [x] OfflineInterfaceTab 组件同步修正代码检视问题

### 4. 代码质量与交付

- [x] IDE 诊断检查无错误
- [x] 提交代码至 fork 仓并创建业务 PR（关联 issue）
- [x] spec 文件归档至 openlibing-docs 仓并创建 docs PR

## 实现优先级

1. **P0（必须完成）**：tab 改名、4 个 tab 问号 tooltip
2. **P1（重要）**：问号样式与 hover 交互
3. **P2（可选）**：无

## 验证方式

- 本地启动前端服务，打开菜单管理页验证：
  - 5 个 tab 名称正确显示
  - 4 个 tab 悬停问号显示 tooltip 文案，菜单 tab 无问号
  - tab 切换与各页面功能回归正常

## 负责人

- 开发：AI辅助开发
- 审核：项目团队成员
- 测试：开发自测 + 团队验证
