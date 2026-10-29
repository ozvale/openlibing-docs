# Proposal：202610 迭代——发布社区令牌体系、操作日志架构 v2 与发布链路增强

- **仓库**：openlibing/openlibing-platform-release
- **需求 Issue**：[#88 [需求]: openLibing-发布管理：openEuler-update版本发布自动化改造；通用发布流程优化参数填写方案，通用发布流程中完成多个社区发布漏洞公告适配，和关于发布管理增加发布权限的token管理配置以及关于新建tag的命名规范校验](https://gitcode.com/openlibing/openlibing-platform-release/issues/88)
- **交付 PR**：[#230](https://gitcode.com/openlibing/openlibing-platform-release/pull/230)（`disiqi:dsq_202610_iter1-fix` → `release_20261019`，91 文件 +11665/-2167）
- **责任人**：disiqi
- **迭代**：202610

## 1. 需求背景

202610 迭代发布管理面临四类问题：

1. **令牌权限粒度粗**：发布链路（评审单校验、tag 创建、源码包下载、社区发布）共用平台级配置令牌，无法按社区/项目精细化授权，单点泄露影响面大。
2. **操作日志碎片化**：各业务 Handler 各自实现日志采集逻辑，重复代码多；日志快照无上限、批量回查拖垮接口；业务异常被全局处理器误判为系统错误；LTS 日志归属不精确。
3. **发布链路健壮性不足**：tag 命名无规范校验（非法名称在社区发布时才暴露）；源码包误走 HPM 证书验签导致阻断；OBS 公读判断依赖 ACL 接口（已废弃），直链下载失败。
4. **安全整改压力**：送检检出 jackson/jsoup 6 个高危 CVE；权限组 SQL 直查 `user_role_info` 存在越权路径（4 处）。

## 2. 需求范围

| 子需求             | 说明                                                               | 关联 issue 条目  |
| ------------------ | ------------------------------------------------------------------ | ---------------- |
| 发布社区令牌管理   | 社区令牌（GitCode/gitee 等）增删改查配置页面 + 校验                | token 管理配置   |
| 令牌全链路切换     | 评审单创建校验、发布决策、源码包下载、tag 创建统一改用社区令牌新表 | 同上             |
| 操作日志架构 v2    | 统一 Handler 基类、日志快照限量、业务异常标记、LTS 归属精确化      | 通用发布流程优化 |
| tag 命名规范校验   | 评审保存与建 tag 环节前置拦截非法名称                              | tag 命名规范校验 |
| 病毒扫描报告下载   | LTS 扫描报告 Word 版下载                                           | 发布流程优化     |
| 漏洞公告多社区适配 | 多社区（昇腾/openEuler 等）发布漏洞公告适配                        | 漏洞公告适配     |
| 安全整改           | CVE 依赖升级、权限组 SQL 过滤、pre-commit workflow 安全修复        | 安全送检整改     |

## 3. 验收标准

### 功能验收

- [ ] 社区令牌管理页面支持增删改查；gitee 类型令牌新增时必填并校验有效性
- [ ] 创建发布评审单前校验项目 GitCode 令牌，无效令牌拦截并给出明确提示
- [ ] 发布决策、源码包下载、tag 创建统一使用社区令牌表 token，平台配置令牌仅作兜底
- [ ] 非法命名的 tag 在评审保存与建 tag 环节被前置拦截
- [ ] 病毒扫描报告支持 Word 下载
- [ ] 多社区（昇腾/openEuler）漏洞公告按社区格式适配发布

### 质量验收

- [ ] 编译、单测、pre-commit 全链通过
- [ ] jackson/jsoup 升级后无高危 CVE 残留
- [ ] 权限组相关 SQL 全部带 `perm_group_id=0` 过滤（存量 4 处修复）
- [ ] 操作日志快照上限 100 条，批量回查接口无慢查询

## 4. 影响范围

- **代码**：91 文件 +11665/-2167（config/令牌、common/aop/log、safescan、obs、multiarch、perm-group）
- **数据库**：新增 `release_community_token` 表（liquibase changelog）
- **依赖**：openlibing-common SDK 1.0.21.x、jackson/jsoup 升级
- **CI**：`.gitcode/workflows/pre-commit.yaml` 同步 framework 安全修复（permissions + allow-unsafe-pr-checkout）
