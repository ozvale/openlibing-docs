# Proposal: 修复 JwtUtils CT_CONSTRUCTOR_THROW 安全问题

## Summary

解决 SpotBugs 扫描出的 `CT_CONSTRUCTOR_THROW` 安全警告，将构造函数中的异常抛出移至 `@PostConstruct` 方法。

## Problem

SpotBugs 报告 `JwtUtils` 构造函数在初始化时抛出 `IllegalStateException`：

```
<BugInstance type="CT_CONSTRUCTOR_THROW" priority="2" rank="16">
  <Class classname="com.openlibing.common.utils.JwtUtils">
    <SourceLine start="33" end="166" sourcefile="JwtUtils.java"/>
  </Class>
  <Method name="<init>" signature="(Ljava/lang/String;Ljava/lang/String;)V">
    <SourceLine start="46" end="50"/>
  </Method>
</BugInstance>
```

**问题本质**：构造函数抛出异常可能导致对象处于部分初始化状态，存在安全风险。

## Solution

采用最小改动方案：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      初始化流程变化                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   【改动前】                                                             │
│   Spring 创建 JwtUtils ──▶ 构造函数 ──▶ isInitialized() ──▶ 抛异常风险   │
│                                                                         │
│   【改动后】                                                             │
│   Spring 创建 JwtUtils ──▶ 构造函数(空) ──▶ @PostConstruct init() ──▶ OK │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

核心改动：
1. 构造函数改为空实现
2. 新增 `@PostConstruct` 的 `init()` 方法处理初始化
3. 变量重命名：配置注入变量与实际使用变量分离
4. 复用现有 `isInitialized()` 方法

## Scope

### In Scope
- `JwtUtils.java` 构造函数重构
- `JwtUtilsTest.java` 反射测试字段名适配
- 变量命名优化

### Out of Scope
- `initializeForTest()` 方法逻辑保持不变
- `assertInitialized()` 方法保持不变
- 其他静态方法签名保持不变

## Success Criteria

- SpotBugs `CT_CONSTRUCTOR_THROW` 警告消除
- 所有现有测试通过
- Spring 环境和测试环境初始化流程正常

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| 测试环境不触发 @PostConstruct | 无 | `initializeForTest()` 逻辑不变 |
| Spring 初始化顺序变化 | 低 | @PostConstruct 在依赖注入后执行，符合预期 |

## Dependencies

- `jakarta.annotation.PostConstruct` (已有)
- Spring 依赖注入 (已有)