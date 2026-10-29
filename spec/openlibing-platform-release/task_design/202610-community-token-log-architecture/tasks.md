# Tasks：202610 迭代——社区令牌体系、操作日志架构 v2 与发布链路增强

- **仓库**：openlibing/openlibing-platform-release
- **分支**：`dsq_202610_iter1-fix`（fork：disiqi）
- **交付 PR**：[#230](https://gitcode.com/openlibing/openlibing-platform-release/pull/230) → `release_20261019`
- **需求 Issue**：[#88](https://gitcode.com/openlibing/openlibing-platform-release/issues/88)

## 实现步骤

### 发布社区令牌体系

- [x] 新增 `release_community_token` 表与实体四件套（Entity/DTO/Vo/Dao）
- [x] 社区令牌管理增删改查接口与页面（`56fc74a8`）
- [x] gitee 类型令牌新增必填 + 有效性校验（`6b1bcbcf`）
- [x] 创建发布评审单前校验项目 GitCode 令牌（`1f048f56`）
- [x] 发布决策改用社区令牌表 token（`d919bffe`）
- [x] 提交评审校验 / tag 创建 / 源码包下载切换到社区令牌新表（`d0001dc1`）
- [x] liquibase `release_community_token.xml` addIndex → createIndex 修正（`7ff57044`）

### 操作日志架构 v2

- [x] 引入 `OperationLogHandlerSupport` 统一处理器基类（`b977b822`）
- [x] 日志快照限量 100 条并收敛批量回查（`b5924a08`）
- [x] 业务异常标记 + 全局异常处理适配（`bcdb91e5`）
- [x] 按请求路径区分删除入口、LTS 日志归属精确化（`7c39b92c`）
- [x] paramsMap 为空时从方法实参兜底获取 DTO（`219434b8`）

### 发布链路增强

- [x] tag 命名规范校验：评审保存与建 tag 环节拦截（`5876b3df`）
- [x] 源码包发布跳过 HPM 证书验签（`957988b2`）
- [x] 病毒扫描报告 Word 下载（`56fc74a8`）
- [x] 提交评审分支查重、sha256 按需生成、附件上传 2xx 判断（`f187cd3a`）

### OBS 公读与直链修复

- [x] `getObjectAcl` → `getObject` + bucket policy 判断公读（`ee205929` / `eb7e65d2`）
- [x] bucket-level 公读检查接入直链下载（`41caa4bf`）
- [x] 支持 object-form Principal（`8cc88e19`）
- [x] notice-beta 真实 policy 覆盖测试（`674bf617`）
- [x] 直链检查补诊断日志（`726d9969`）

### 多架构适配与权限组

- [x] startModule / collectBugfix / saveCveCallbackResult 接口适配（`b8e6f11e` / `a7ace9c8`）
- [x] `generateIssueByPr` 官方 page++ 写法保留并豁免 PMD（`f1eba207`）
- [x] 权限组 SQL 直查 `user_role_info` 补 `perm_group_id=0` 过滤（4 处，`08ace17c` 等）

### 安全与依赖

- [x] 升级 jackson/jsoup 修复 6 个高危 CVE（`52a746e4`）
- [x] SDK 升级 1.0.21.x + Boot 4.1.1 / Framework 7.0.9 / MP 3.5.17 适配（`ecd139f9`）
- [x] pre-commit workflow 同步 framework 安全修复（`55c2250a`）

### 验证

- [ ] 编译 + 单测 + pre-commit 全链通过（CI 验证中）
- [ ] 社区令牌管理 + 令牌校验流程回归
- [ ] 发布决策 → tag 创建 → 社区发布全链路回归
- [ ] OBS 直链下载回归
- [ ] PR CI 流水线通过后评审合入

## 提交记录

- PR：[#230](https://gitcode.com/openlibing/openlibing-platform-release/pull/230)（ai-assisted，关联 #88）
- 分支合并自 master（含 `176a5e7b` pre-commit 修复），base `release_20261019`

## 关联文档

- 上一迭代 spec：[tag-validation-offline-and-token-security](../tag-validation-offline-and-token-security/proposal.md)（202609，issue #79）
