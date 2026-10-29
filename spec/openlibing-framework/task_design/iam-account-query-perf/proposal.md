# iam-account-query-perf — 账号纳管页面 LCP 性能优化（后端）

## 需求背景

账号纳管页面（`openlibing-web` `AccountManage/index.vue`）LCP 存在偶发性 >3s 的情况。前端已完成资源加载侧的优化，需要后端在**不改变接口契约、不改变返回结构、不影响功能语义**的前提下，对首屏链路做性能优化。

## 功能描述

- **做什么**：
  1. 重构 `IAMAccountMapper.selectIAMAccounts` SQL（去 `distinct` 全表 join 膨胀、模糊匹配改可走索引写法、优化排序分页）
  2. 通过 Liquibase 为 `iam_account` / 授权表补充缺失索引
- **不做什么**：
  1. 不加 Redis 缓存层（避免一致性风险）
  2. 不改 `/iam/account/query` 接口契约与返回结构
  3. 不涉及 `grants/query` 抽屉查询（本次不覆盖）
  4. 不新增/删除任何接口

## 验收标准

- [x] `selectIAMAccounts` 重构后返回结果与重构前一致（等价性回归，11 项 H2 用例覆盖 5 分支 + 过滤 + 分页 + 脏数据）
- [ ] EXPLAIN / 慢查询日志确认主查询避免全表扫描（按条件命中索引）——**未完成：需真实库（beta/prod）补 EXPLAIN 复测**
- [x] Liquibase changelog 合法、可重复执行，测试库可正常迁移（含幂等重估验证）
- [x] 工程编译通过、相关单元测试通过（等价性 11 + 迁移 2 + IAM 相关 89 项）
- [x] 接口契约（入参 `QueryAccountRequest`、出参 `IamAccountsDTO`）零变化
- [ ] 基线与优化后同一数据量下查询耗时对比有明确下降——**未完成：需真实库埋点/压测**

## 影响范围

- `openlibing-framework`：`IAMAccountMapper.xml`、`src/main/resources/db/changelog/`（新增索引）
- `openlibing-docs`：本 proposal/tasks/archive
- 关联业务 Issue：https://gitcode.com/openlibing/openlibing-framework/issues/116（子项）
