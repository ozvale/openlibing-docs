# Tasks: JwtUtils 构造函数重构任务清单

---

## Task 1: 修改 JwtUtils.java

- **Priority**: High
- **Effort**: 0.5h
- **File**: `src/main/java/com/openlibing/common/utils/JwtUtils.java`

### Steps

1. 新增导入 `jakarta.annotation.PostConstruct`、`lombok.AccessLevel`、`lombok.NoArgsConstructor`
2. 重命名静态变量 `jwtSecret` → `decryptSecret`
3. 新增实例变量：
   - `@Value("${jwt.secret}") private String jwtSecret;`
   - `@Value("${security.part1}") private String part1;`
4. 新增类注解 `@NoArgsConstructor(access = AccessLevel.PRIVATE)`
5. 删除原有手写的空构造函数
6. 新增 `@PostConstruct private void init()` 方法：
   - 调用 `isInitialized()` 复用 CAS 逻辑
   - 设置 `decryptSecret = SecurityUtil.decrypt(jwtSecret, part1)`
7. 修改 `initializeForTest()` 中赋值：`jwtSecret` → `decryptSecret`
8. 修改所有 `Algorithm.HMAC256(jwtSecret)` → `Algorithm.HMAC256(decryptSecret)`（3处）

---

## Task 2: 修改 JwtUtilsTest.java

- **Priority**: High
- **Effort**: 0.1h
- **File**: `src/test/java/com/openlibing/common/utils/JwtUtilsTest.java`

### Steps

1. 修改反射测试字段名：`"jwtSecret"` → `"decryptSecret"`
2. 修改断言描述：`"jwtSecret应为预设值"` → `"decryptSecret应为预设值"`

---

## Task 3: 运行测试验证

- **Priority**: High
- **Effort**: 0.1h
- **Command**: `mvn test -Dtest=JwtUtilsTest`

### Expected Result
- Tests run: 7, Failures: 0, Errors: 0

---

## Task 4: 运行 SpotBugs 验证

- **Priority**: High
- **Effort**: 0.1h
- **Command**: 项目的流水线安全扫描

### Expected Result
- `CT_CONSTRUCTOR_THROW` 警告消除

---

## 任务执行顺序

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         执行顺序                                          │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: Task 1 ──▶ 修改 JwtUtils.java
Step 2: Task 2 ──▶ 修改 JwtUtilsTest.java
Step 3: Task 3 ──▶ 运行测试验证
Step 4: Task 4 ──▶ 运行 SpotBugs 验证

```

---

## Summary

| Task | Priority | Effort | Status |
|------|----------|--------|--------|
| Task 1 | High | 0.5h | ✅ 已完成 |
| Task 2 | High | 0.1h | ✅ 已完成 |
| Task 3 | High | 0.1h | ✅ 已完成 |
| Task 4 | High | 0.1h | ⏳ 待流水线验证 |
| **Total** | - | **0.8h** | **3/4 完成** |