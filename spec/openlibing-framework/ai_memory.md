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

### 6. 并发重复插入治理

**场景**: 双实例部署下 Check-then-Insert 模式存在并发竞态

**方案**: 优先在数据库层加唯一约束兜底，应用层捕获 `DuplicateKeyException` 返回友好提示。不要仅依赖应用层排他锁或 `SELECT FOR UPDATE`。

**关键点**:

- 数据库唯一约束是根本兜底，不依赖网络/锁服务
- 兼容存量重复数据（新增约束不检查已有数据）
- 异常信息脱敏：使用 `LOG.warn("msg")` 而非 `LOG.error("msg", e)` 避免泄露数据库结构

**来源**: 2026-09-10 duplicate-key-protection

### 7. Maven Liquibase changelog 命名约定

**规则**: 唯一约束的 changelog 文件按 `{table_name}.xml` 命名，放在对应版本的 `vX.Y.Z/` 目录下。主 `db.changelog.xml` 通过 `<include>` 引用。

**来源**: 2026-09-10 duplicate-key-protection

### 8. 防御性拷贝处理集合字段

**场景**: SpotBugs 检测到 DTO/VO 集合字段 `EI_EXPOSE_REP` / `EI_EXPOSE_REP2` 漏洞

**方案**: getter 和 setter 中使用 `new ArrayList<>(field)` 做防御性拷贝，禁止直接返回或赋值内部引用。

```java
public List<String> getUserRoles() {
    return userRoles == null ? null : new ArrayList<>(userRoles);
}

public void setUserRoles(List<String> userRoles) {
    this.userRoles = userRoles == null ? null : new ArrayList<>(userRoles);
}
```

**注意**: `@Data` 生成的 getter/setter 不做防御性拷贝，有集合字段的 DTO 需手动编写 getter/setter。

**来源**: 2026-09-10 PR#436 code review

### 9. SQL 重构等价性测试（无真实库时）

**场景**: 重构 MyBatis SQL（如去 `distinct` / 拆 join）需证明功能零变化，但本仓无真实库连接、无 MyBatis 集成测试基础设施。

**方案**: 用 H2 内存库（MODE=MySQL）播种相同数据，把旧 SQL 以字符串常量作为 oracle，遍历新/旧分支比对完整结果集（含 `is_has_grant_user` 等布尔标志转 0/1）。展开 grantStatus 全分支 + 过滤 + 分页 + 关键脏数据场景。

**关键点**:

- 同账号多授权（2 有效用户 + 2 有效角色）去重用例必须覆盖——`distinct` 移除后行倍增的唯一结构差异点。
- 分页用例必须带与生产一致的确定性 `order by`，否则 H2 行序不定导致偶发红。
- 每用例补绝对期望集合断言（如 resource_id 集合），避免"新旧同错仍通过"。

**来源**: 2026-10-28 iam-account-query-perf

### 10. Liquibase 幂等测试必须重估 preCondition

**场景**: changelog 用 `preConditions`（如 `tableExists`/`indexExists`）做幂等保护，测试要证明 preCondition 真实生效而非 DATABASECHANGELOG 短路。

**方案**: 第二次 `liquibase.update()` 前先 `DELETE FROM DATABASECHANGELOG`，使 changeSet 被真正重新求值——此时索引已存在、`not indexExists` 为 false → onFail=MARK_RAN 跳过，不会重复 createIndex 报错。缺表场景单独用例断言无索引残留。

**来源**: 2026-10-28 iam-account-query-perf

### 11. OR 分支 + 复合索引的优化陷阱

**场景**: WHERE 含 `a.create_by = ? or exists(...) or exists(...)` 的 OR 结构，即使建 `create_by` 单列索引，MySQL 优化器通常仍不走（Index Merge 对多 OR 子查询不生效）。

**方案**: 索引设计以"必然携带的等值过滤字段"为前导列（如前端必传 projectId、DTO `@NotNull`），保证覆盖热点分支；不要为 OR 分支盲目加单列索引（增加写放大、无读收益）。若必优化 OR 分支，优先拆 UNION。

**来源**: 2026-10-28 iam-account-query-perf
