# 实现任务清单

## 任务分解

### 1. 请求方式手动切换同步

- [x] 请求方式 `el-select` 增加 `@change="getMethodResult"`
- [x] 新增 `getMethodResult` 方法，展开 `...this.data` 后更新 requestMethod 并 emit change

### 2. URL 选择保留请求方式

- [x] `getUrlResult` URL 命中分支：未命中选项时保留 `this.data.requestMethod`（仅无值兜底 GET），不再强制重置
- [x] `getUrlResult` URL 清空分支：同理保留已选请求方式

### 3. 代码质量与交付

- [x] IDE 诊断检查无错误
- [x] 提交代码至 fork 仓并创建业务 PR（openlibing/openlibing-web#756，关联 issue）
- [x] spec 文件归档至 openlibing-docs 仓并创建 docs PR

## 实现优先级

1. **P0（必须完成）**：请求方式 change 同步、URL 未命中保留请求方式
2. **P1（重要）**：URL 清空分支保留请求方式
3. **P2（可选）**：无

## 验证方式

- 本地启动前端服务，打开菜单管理 → 新增/修改菜单弹窗验证：
  - 手动切换 GET/POST 后提交，保存数据为切换后的值
  - 选择 URL 命中选项时请求方式按接口 httpMethod 回填
  - 输入自定义 URL（未命中）时请求方式保留已选值
  - 清空 URL 后提交不报错，请求方式保留
  - URL 远程搜索、懒加载、下线接口标红回归正常

## 负责人

- 开发：AI辅助开发
- 审核：项目团队成员
- 测试：开发自测 + 团队验证
