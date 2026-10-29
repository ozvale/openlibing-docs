# Design：202610 迭代——社区令牌体系、操作日志架构 v2 与发布链路增强

## 1. 发布社区令牌体系

### 1.1 数据模型

新增 `release_community_token` 表（liquibase：`release_community_token.xml`，注意 `addIndex` 需写成 `createIndex`，Gitee Liquibase 兼容性）：

| 字段              | 说明                                          |
| ----------------- | --------------------------------------------- |
| 社区类型          | gitcode / gitee / 昇腾 / openEuler 等         |
| token（加密存储） | `SecurityUtil.decrypt(token, part1)` 解密使用 |
| 关联项目/评审单   | 项目级授权粒度                                |

实体四件套：`ReleaseCommunityTokenEntity` / `ReleaseCommunityTokenDTO` / `ReleaseCommunityTokenVo` / `ReleaseCommunityTokenDao`（`business/config` 包）。

### 1.2 令牌获取优先级

```
业务请求（评审校验 / 发布决策 / 源码包下载 / tag 创建）
  → 查 release_community_token 表（项目/社区维度，优先）
  → 未命中或解密失败 → 降级平台配置 token
  → 全空 → 返回 null，业务侧抛明确异常
```

与 openlibing-anti-poison 的 `getPlatformPassworandUserName(platformName, projectId)` 三级降级策略保持同构。

### 1.3 校验逻辑

- **评审单创建前**（`ReleaseBaseServiceImpl`）：遍历制品 repoUrl，按社区类型取 token 并解密校验，无效令牌阻断创建。
- **gitee 类型令牌**：新增时必填 + 有效性校验（防脏配置进库）。

## 2. 操作日志架构 v2

### 2.1 统一 Handler 基类

新增 `OperationLogHandlerSupport`（`common/aop/log/`），收敛各 Handler 重复的模板逻辑（方法匹配、参数快照、异步落库），业务 Handler 只声明差异点。存量 Handler（`ReleaseReviewHandler`、`ReleaseConfigHandler`、LTS 系列等 18 个）按需继承改造。

### 2.2 四项修复

| 问题                       | 方案                                                     | commit     |
| -------------------------- | -------------------------------------------------------- | ---------- |
| 日志快照无上限、批量回查慢 | 快照限量 100 条，批量回查收敛为单条查询                  | `b5924a08` |
| 业务异常被全局处理器误判   | 异常标记机制，业务异常不走系统告警路径                   | `bcdb91e5` |
| LTS 日志归属不精确         | 按请求路径区分删除入口，`LtsLogProjectResolver` 精确归属 | `7c39b92c` |
| paramsMap 为空取不到 DTO   | 从方法实参兜底获取                                       | `219434b8` |

## 3. 发布链路增强

- **tag 命名规范校验**（`5876b3df`）：评审保存与 createTags 环节前置正则拦截，非法名称不再流到社区发布才暴露。
- **源码包发布跳过 HPM 证书验签**（`957988b2`）：源码包类型不走 HPM 验签分支，避免误阻断（与 202609 迭代的 `readAllBytes` 大包内存问题同源，见 [tag-validation-offline-and-token-security](../tag-validation-offline-and-token-security/design.md)）。
- **病毒扫描报告 Word 下载**：LTS 扫描结果导出 Word。
- **提交评审增强**（`f187cd3a`）：分支查重、sha256 按需生成（非全量）、附件上传 2xx 状态码判断。

## 4. OBS 公读与直链修复

问题链：`getObjectAcl`（已废弃接口）判断公读在 bucket policy 场景下失效 → 直链下载 403。

修复序列（`ee205929` → `674bf617`）：

1. 改用 `getObject` 探测 + bucket-level policy 判断公读
2. 解析 bucket policy 支持 object-form Principal
3. 兼容 notice-beta 真实 bucket policy 结构
4. 直链 URL 按候选规则逐级兜底

## 5. 安全整改

| 项                         | 方案                                                                                                                   |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| jackson/jsoup 6 个高危 CVE | 依赖升级（`52a746e4`）                                                                                                 |
| 权限组越权路径             | SQL 直查 `user_role_info` 补 `perm_group_id=0` 过滤（存量 4 处 + 规则固化）                                            |
| pre-commit workflow        | 同步 framework PR #468/#469（permissions 声明 + `allow-unsafe-pr-checkout`），修复 fork PR 的 `CHECKOUT.00010012` 拦截 |
| multiarch                  | `generateIssueByPr` 保留官方 `page++` 写法并豁免 PMD 规则（`f1eba207`）                                                |

## 6. 兼容性

- 平台配置 token 作为降级兜底保留，存量评审单不受影响
- SDK 1.0.21.x 升级伴随 Boot 4.1.1 / Framework 7.0.9 / MP 3.5.17 技术栈适配（`ecd139f9`）
- liquibase index 语法修正（`7ff57044`）

## 7. 风险与回滚

| 风险                          | 缓解                                                    |
| ----------------------------- | ------------------------------------------------------- |
| 社区令牌表数据迁移期令牌缺失  | 平台配置 token 降级兜底，业务不中断                     |
| 操作日志 Handler 改造覆盖不全 | 基类默认行为兜底，逐 Handler 验证 LTS 归属              |
| OBS policy 解析兼容性         | 已用 notice-beta 真实 policy 结构覆盖测试（`674bf617`） |
