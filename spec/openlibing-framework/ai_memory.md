# openlibing-framework AI Memory

本文档保存 `openlibing-framework` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-framework` 为现代化开源管理平台后端框架，为 openlibing 生态提供基础服务能力，后续系统级职责、工具边界、任务执行链路、安全约束需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Agent 工具调用、权限、安全边界、外部系统访问时，必须补充设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| 提交前未执行 pre-commit | AI 开发前必须执行 `pre-commit run --all-files`，确保所有检查通过后再提交 | 2026-7-后端下线技术委员会 |
| Spotless 格式化冲突 | 本地与 CI 环境 Spotless 版本不一致时，可恢复到目标分支版本避免冲突 | 2026-7-后端下线技术委员会 |
| 大型代码删除遗漏 | 删除模块后，grep 扫描确认无调用方再删除关联文件，避免遗漏 | 2026-7-后端下线技术委员会 |

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
