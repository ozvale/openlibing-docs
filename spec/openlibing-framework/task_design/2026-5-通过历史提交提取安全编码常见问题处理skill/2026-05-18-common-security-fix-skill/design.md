## Context

openlibing-framework 项目使用 Java 21，依赖 Lombok、MyBatis、Spring Boot 等框架。FindBugs/SpotBugs 扫描产生的安全编码问题需要人工修复，但当前缺乏统一规范。

通过分析 50+ 次安全编码整改提交，已提取一套经过验证的修复模式。需要将这些模式固化为 opencode skill，使开发者可以一键调用。

**约束条件：**
- 项目使用 Java 21，支持 `List.copyOf()`、`Set.copyOf()`、`Map.copyOf()` 等 Java 9+ API
- MyBatis 作为 ORM 框架，`Optional` 返回值适配不佳，统一使用 `@Nullable`
- Lombok 的 `@Data` 会自动生成 getter/setter，需要通过 `@Getter(AccessLevel.NONE)` 覆盖
- skill 必须支持 XML 日志文件批量输入

## Goals / Non-Goals

**Goals:**
- 覆盖 14 种常见 FindBugs/SpotBugs 问题类型，每种提供 BEFORE/AFTER 模板
- 建立强制约束确保修复质量（追溯调用点、@Nullable 规范等）
- 支持批量日志文件处理，分批执行并反馈进度
- 未覆盖问题类型需用户确认后修改

**Non-Goals:**
- 不自动执行代码编译或测试（由用户手动执行）
- 不修改项目构建配置或 CI/CD 流程
- 不处理非 FindBugs/SpotBugs 类型的代码质量问题

## Decisions

### 1. 按问题类型拆分 reference 文件

每种问题类型一个独立的 `reference/<TYPE>.md` 文件，而非将所有模板放在单个 SKILL.md 中。

**理由：** 14 种问题类型的模板内容较大，拆分后 SKILL.md 保持简洁（仅索引和流程），修改时只需打开对应文件。

**替代方案：** 单文件 + 锚点链接。缺点是文件过长，AI 上下文窗口容易截断。

### 2. Date getter 统一使用 @Nullable，不使用 Optional

Entity 类（如 RepoInfoEntity）的 Date getter 返回 `@Nullable Date` 而非 `Optional<Date>`。

**理由：** Optional 与 MyBatis 等 ORM 框架适配不佳，调用方需要 `.orElse(null)` 转换增加复杂度。`@Nullable` 更直接。

**替代方案：** Entity 用 Optional，VO/Model 用 @Nullable。缺点是风格不统一，增加认知负担。

### 3. @Builder + @Singular 也必须手动写 getter/setter

即使使用 `@Singular` 注解，也必须手动编写 getter/setter 进行防御性复制。

**理由：** `@Singular` 只影响 Builder 的构建方式，`@Data` 生成的 getter 仍然直接返回可变 List，EI_EXPOSE_REP 未被修复。

**替代方案：** 仅对 `private static` 内部类省略 getter/setter。缺点是修复不完整，codecheck 仍会报错。

### 4. 集合 getter 统一使用 Java 9+ API

使用 `List.copyOf()` / `Set.copyOf()` / `Map.copyOf()` 替代 `Collections.unmodifiableXxx()`。

**理由：** 项目使用 Java 21，`copyOf()` 更简洁且性能更好（返回不可变集合而非包装视图）。

### 5. 自定义对象集合使用 BeanUtils.copyProperties()

自定义可变类的防御性复制优先使用 `BeanUtils.copyProperties()`。

**理由：** 项目已有实践（ProjectInfoEntity），团队熟悉此方式，无需引入额外依赖。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `@Nullable` 注解需要 `jakarta.annotation.Nullable` 依赖 | 项目已引入该依赖，无额外依赖风险 |
| 批量处理日志文件时可能超出上下文窗口 | 按 20~40 个 BugInstance 分批执行，每批反馈进度 |
| 未覆盖的问题类型可能被错误处理 | 强制约束 #5：必须先向用户说明并获得确认 |
| `List.copyOf()` 不接受 null 元素 | setter 使用 `new ArrayList<>()` 复制入参，允许 null 元素由调用方保证 |
| `BeanUtils.copyProperties()` 是浅拷贝 | 对于嵌套可变对象需要深拷贝，skill 模板中注明此限制 |
