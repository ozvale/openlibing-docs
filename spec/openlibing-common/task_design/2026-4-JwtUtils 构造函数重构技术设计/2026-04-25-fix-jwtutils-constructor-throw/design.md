# Design: JwtUtils 构造函数重构技术设计

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      改动前后对比                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   【改动前】                                                             │
│                                                                         │
│   @Component                                                            │
│   public class JwtUtils {                                               │
│       private static String jwtSecret;                                  │
│       private static final AtomicBoolean INITIALIZED = ...;             │
│                                                                         │
│       private JwtUtils(@Value("${jwt.secret}") String jwtSecret,        │
│                         @Value("${security.part1}") String part1) {     │
│           isInitialized();  // ← 构造函数中抛异常，触发安全警告           │
│           JwtUtils.jwtSecret = SecurityUtil.decrypt(jwtSecret, part1);  │
│       }                                                                 │
│   }                                                                     │
│                                                                         │
│   ──────────────────────────────────────────────────────────────────    │
│                                                                         │
│   【改动后】                                                             │
│                                                                         │
│   @Component                                                            │
│   @NoArgsConstructor(access = AccessLevel.PRIVATE)                      │
│   public class JwtUtils {                                               │
│       private static String decryptSecret;     // 解密后用于签名         │
│       private static final AtomicBoolean INITIALIZED = ...;             │
│                                                                         │
│       @Value("${jwt.secret}")                                          │
│       private String jwtSecret;                // 配置注入原始值         │
│                                                                         │
│       @Value("${security.part1}")                                      │
│       private String part1;                    // 配置注入原始值         │
│                                                                         │
│       @PostConstruct                                                    │
│       private void init() {                                            │
│           isInitialized();              // ← 复用现有方法                │
│           decryptSecret = SecurityUtil.decrypt(jwtSecret, part1);       │
│       }                                                                 │
│   }                                                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Technical Decisions

### 1. 变量命名分离

**Decision**: 配置注入变量与实际使用变量分开命名

**Rationale**:
- `jwtSecret` / `part1` - 从 Apollo 配置注入的原始加密值
- `decryptSecret` - 解密后实际用于 JWT 签名的密钥
- 命名更清晰，职责更明确

### 2. 复用 isInitialized() 方法

**Decision**: `@PostConstruct init()` 方法调用现有的 `isInitialized()` 而不是重复 CAS 逻辑

**Rationale**:
- 避免代码重复
- `isInitialized()` 已实现 `compareAndSet(false, true)` + 抛异常逻辑
- 保持一致性

### 3. @PostConstruct 方法私有化

**Decision**: `init()` 方法使用 `private` 修饰符

**Rationale**:
- `@PostConstruct` 方法不应对外暴露
- Spring 框架会通过反射调用
- 符合最小暴露原则

### 4. 使用 Lombok @NoArgsConstructor

**Decision**: 使用 `@NoArgsConstructor(access = AccessLevel.PRIVATE)` 替代手写空构造函数

**Rationale**:
- 私有构造函数明确表达"不要手动实例化"
- 符合原静态类的设计意图
- Spring 5+ 可反射调用私有构造函数，正常工作
- Lombok 注解比手写更简洁

## Initialization Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      初始化流程                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   【Spring 环境】                                                        │
│                                                                         │
│   1. Spring 容器创建 JwtUtils Bean                                      │
│      │                                                                  │
│      ▼                                                                  │
│   2. 构造函数执行（空实现，无异常）                                       │
│      │                                                                  │
│      ▼                                                                  │
│   3. @Value 注入 jwtSecret, part1                                       │
│      │                                                                  │
│      ▼                                                                  │
│   4. @PostConstruct init() 执行                                         │
│      │                                                                  │
│      ├── isInitialized() → CAS 设置 INITIALIZED                         │
│      │                                                                  │
│      └── decryptSecret = SecurityUtil.decrypt(jwtSecret, part1)         │
│                                                                         │
│   【测试环境（无 Spring）】                                               │
│                                                                         │
│   1. @BeforeAll                                                         │
│      │                                                                  │
│      ▼                                                                  │
│   2. JwtUtils.initializeForTest("test_sign")                            │
│      │                                                                  │
│      ├── isInitialized() → CAS 设置 INITIALIZED                         │
│      │                                                                  │
│      └── decryptSecret = "test_sign"                                    │
│                                                                         │
│   注：@PostConstruct 不会被调用（无 Spring 容器）                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `JwtUtils.java` | Modify | 构造函数重构 + 变量重命名 |
| `JwtUtilsTest.java` | Modify | 反射测试字段名适配 |

### JwtUtils.java Detailed Changes

```java
// 新增导入
import jakarta.annotation.PostConstruct;
import lombok.AccessLevel;
import lombok.NoArgsConstructor;

// 变量变更
private static String decryptSecret;  // 原 jwtSecret 重命名

@Value("${jwt.secret}")
private String jwtSecret;             // 新增：配置注入

@Value("${security.part1}")
private String part1;                 // 新增：配置注入

// 类注解变更
@NoArgsConstructor(access = AccessLevel.PRIVATE)  // 私有构造函数

// 新增方法
@PostConstruct
private void init() {
    isInitialized();
    decryptSecret = SecurityUtil.decrypt(jwtSecret, part1);
}

// 签名方法变更
Algorithm.HMAC256(decryptSecret)      // 使用 decryptSecret
```

### JwtUtilsTest.java Detailed Changes

```java
// 反射测试字段名变更
if (field.getName().equals("decryptSecret")) {  // 原 jwtSecret
    // ...
    assertEquals("test_sign", secretValue, "decryptSecret应为预设值");
}
```