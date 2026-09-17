# openlibing-framework AI Memory

本文档保存 `openlibing-framework` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-framework` 为现代化开源管理平台后端框架，为 openlibing 生态提供基础服务能力，后续系统级职责、工具边界、任务执行链路、安全约束需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Agent 工具调用、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 常见 AI 错误与规避

| 错误模式                | 规避规则                                                                 | 来源需求                  |
| ----------------------- | ------------------------------------------------------------------------ | ------------------------- |
| 提交前未执行 pre-commit | AI 开发前必须执行 `pre-commit run --all-files`，确保所有检查通过后再提交 | 2026-7-后端下线技术委员会 |
| Spotless 格式化冲突     | 本地与 CI 环境 Spotless 版本不一致时，可恢复到目标分支版本避免冲突       | 2026-7-后端下线技术委员会 |
| 大型代码删除遗漏        | 删除模块后，grep 扫描确认无调用方再删除关联文件，避免遗漏                | 2026-7-后端下线技术委员会 |

## 最佳实践

### 1. pre-commit 优化策略

**场景**: 多个 Maven hooks 串行执行，性能较差

**方案**: 合并为单个 hook，使用 `-T 1C` 启用并行编译

**配置**:

```yaml
- repo: local
  hooks:
    - id: mvn-all-checks
      name: Maven All Checks (Spotless + CheckStyle + SpotBugs + PMD)
      language: system
      entry: python scripts/run-mvn.py -T 1C spotless:apply checkstyle:check compile spotbugs:check pmd:check
      pass_filenames: false
```

**效果**: 减少 JVM 启动次数，编译时间缩短约 30%

**注意**: 资源不足的机器上，`-T 1C` 可能反效果，可改用固定线程数 `-T 2`

### 2. 大型代码删除项目分阶段提交

**场景**: 删除大量文件，需要分阶段提交降低风险

**方案**: 按依赖顺序分阶段提交，每阶段编译验证

**阶段**:

1. Controller 删除
2. Service 接口和实现删除
3. Mapper 接口和 XML 删除
4. Entity/DTO/AOP/常量删除
5. 测试删除
6. 关联 Entity/DTO 删除
7. 引用清理
8. 测试改造和全量编译验证
9. 死代码清理

**收益**: 每阶段编译验证，快速定位问题，降低风险

### 3. 死代码清理策略

**场景**: 删除模块后，关联文件可能成为死代码

**方案**: grep 扫描确认无调用方再删除

**步骤**:

```bash
# 扫描方法调用
grep -r "methodName" src/main/java/ --include="*.java"

# 扫描类引用
grep -r "ClassName" src/main/java/ --include="*.java"

# 扫描 Controller 调用
grep -r "methodName" src/main/java/com/openlibing/framework/business/controller/ --include="*.java"
```

**注意**: 区分同名但不同含义的局部变量，避免误删

### 4. Spotless 格式化冲突处理

**场景**: 本地与 CI 环境 Spotless 版本不一致，import 排序规则不同

**方案**: 恢复到目标分支版本，避免格式化冲突

**步骤**:

```bash
git checkout upstream/target-branch -- path/to/file.java
git commit --no-verify -m "revert: restore file to target branch version"
git push origin branch-name
```

**适用场景**: 非核心文件的格式化冲突，不影响功能逻辑

### 5. 角色下线影响评估

**场景**: 下线模块相关角色，评估对现有系统的影响

**评估维度**:

- 后端代码引用（守卫代码、权限检查）
- 前端硬编码（角色过滤、权限判断）
- 数据库记录（user_role_info 表）
- 用户权限（拥有该角色的用户）

**结论**: 模块专属角色在模块下线后失去管理入口和功能意义，可安全删除

### 6. 权限组滤组整改（resource-permission-scheme）

**场景**: `user_role_info` 加 `perm_group_id` 列后，存量读该表的 SQL/Wrapper 若不滤组，自定义组行会污染接口级鉴权、权限快照（Redis 24h 缓存）、成员查重、IAM 可见性

**已验证规则**（2026/09/17 全量审计，commit `e97ecc5f`/`3a1264c6`）:

- 存量读一律加 `perm_group_id = 0`（SQL WHERE 或 Java 端 `setPermGroupId(0L)`）；`queryInfo` 因编辑查重依赖条件式过滤，只能改调用方不能改 SQL
- 死 SQL 补条件不删（防未来复活踩坑）；P2 展示类（管理端分页/个人中心角色/AOP 日志快照）按定案不动
- 排查必须用四层搜索法：表名字符串 → Entity 类名（Wrapper 在 Java 拼 WHERE，XML 搜不到）→ MP 泛型签名 → Liquibase changelog；"想到哪查到哪"会漏（权限快照、IAM 子查询均不在初期清单上）
- cicd 仓同类整改见该仓 spec；cicd 实体 `UserRoleInfoEntity` 需有 `permGroupId` 字段才能在 Wrapper 中滤组

**成员管理定案**（2026/09/16）: 平行成员接口（`POST/PUT /groups/{id}/members` 等）判定过度设计净删除；成员增删改复用存量项目成员链路 + `permGroupId` 入参（`BatchAddUserDTO`），查重按 `(userId, role, projectId, permGroupId)` 四元组；`copyGroupMembers` 仅复制 `role='committer_project'`、repo 非空、`sync_flag` 有效的记录

**RPC 分阶段定案**（2026/09/17，待实施）: 新增查询（`hasPermissionByGroup`、`queryBoundPermGroup` 等）走 framework 内部 RPC（4 个接口，`InternalPermGroupController`，粗粒度合并——热路径每请求最多 1 次 RPC）；存量热路径维持 cicd 本地直查只补滤组；Feign + OkHttp 连接池、connect 1s/read 2s、键 `(userId, permGroupId, url)` TTL 5s 缓存、fail-closed（失败全拒绝、拒绝结果不缓存）。完整设计见 `openlibing-docs/spec/openlibing-cicd/task_design/resource-permission-scheme/design.md` 4.4
