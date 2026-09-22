## ADDED Requirements

### Requirement: EI_EXPOSE_REP 修复模式
skill 必须提供 EI_EXPOSE_REP（暴露内部可变表示）的修复模板，覆盖 Date、集合类、自定义可变类、基本类型数组四种类型。getter 必须返回防御性副本或不可变视图，setter 必须对入参做防御性复制。

#### Scenario: Date 字段修复
- **WHEN** 用户需要修复 Date 字段的 EI_EXPOSE_REP 问题
- **THEN** skill 将字段标记 `@Getter(AccessLevel.NONE) @Setter(AccessLevel.NONE)`，手动编写 getter 返回 `new Date(date.getTime())` 防御性副本，setter 同样做防御性复制

#### Scenario: 集合字段修复
- **WHEN** 用户需要修复 List/Set/Map 字段的 EI_EXPOSE_REP 问题
- **THEN** skill 将 getter 改为返回 `List.copyOf()` / `Set.copyOf()` / `Map.copyOf()`，setter 改为 `new ArrayList<>()` / `new HashSet<>()` / `new HashMap<>()` 防御性复制

#### Scenario: 自定义对象字段修复
- **WHEN** 用户需要修复自定义可变类字段的 EI_EXPOSE_REP 问题
- **THEN** skill 使用 `BeanUtils.copyProperties()` 在 getter 和 setter 中做深拷贝

#### Scenario: 数组字段修复
- **WHEN** 用户需要修复 byte[]/int[] 等数组字段的 EI_EXPOSE_REP 问题
- **THEN** skill 使用 `Arrays.copyOf(arr, arr.length)` 在 getter 和 setter 中做防御性复制

### Requirement: 其他 13 种问题修复模板
skill 必须为以下每种问题类型提供独立的 reference 模板文件，包含 BEFORE/AFTER 代码示例：DM_DEFAULT_ENCODING、DM_BOXED_PRIMITIVE_FOR_PARSING、STCAL_INVOKE_ON_STATIC_DATE_FORMAT_INSTANCE、SF_SWITCH_NO_DEFAULT、NM_CLASS_NAMING_CONVENTION、NM_SAME_SIMPLE_NAME_AS_SUPERCLASS、SIC_INNER_SHOULD_BE_STATIC、RCN_REDUNDANT_NULLCHECK、DLS_DEAD_LOCAL_STORE、UC_USELESS_OBJECT、GC_UNRELATED_TYPES、REC_CATCH_EXCEPTION、UCF_USELESS_CONTROL_FLOW。

#### Scenario: 模板文件存在性
- **WHEN** skill 被调用
- **THEN** 14 个 reference 文件全部存在于 `.opencode/skills/common-security-fix/reference/` 目录下

#### Scenario: DM_DEFAULT_ENCODING 修复
- **WHEN** 用户需要修复 DM_DEFAULT_ENCODING 问题
- **THEN** skill 将 `new String(bytes)` 改为 `new String(bytes, StandardCharsets.UTF_8)`

### Requirement: @Nullable 统一规范
所有可能返回 null 的方法必须使用 `@Nullable` 注解，不得使用 `Optional` 作为返回值。`@Nullable` 必须单独一行放在方法声明上方。

#### Scenario: Date getter 使用 @Nullable
- **WHEN** skill 修改 Date 字段的 getter
- **THEN** getter 返回 `@Nullable Date` 而非 `Optional<Date>`，注解单独一行在方法声明上方

#### Scenario: 自定义对象 getter 使用 @Nullable
- **WHEN** skill 修改自定义可变类字段的 getter
- **THEN** getter 返回 `@Nullable CustomType` 而非 `Optional<CustomType>`

### Requirement: @Builder + @Singular 必须搭配手动 getter/setter
即使集合字段使用了 `@Singular` 注解，也必须手动编写 getter/setter 进行防御性复制。

#### Scenario: @Builder 内部类集合字段
- **WHEN** skill 处理 `@Builder` 内部类中的 List 字段
- **THEN** 添加 `@Singular` 注解的同时，也添加 `@Getter(AccessLevel.NONE) @Setter(AccessLevel.NONE)` 并手动编写 getter/setter

### Requirement: @AllArgsConstructor 处理
修改可变字段后，skill 必须处理失效的 `@AllArgsConstructor`。未使用全参构造的类改为 `@AllArgsConstructor(access = AccessLevel.PRIVATE)`（Entity）或 `AccessLevel.NONE`（其他），或删除该注解。已使用全参构造的类必须手动重写构造方法并包含防御性复制。

#### Scenario: Entity 类未使用全参构造
- **WHEN** skill 修改 Entity 类的可变字段且代码中未使用全参构造
- **THEN** 将 `@AllArgsConstructor` 改为 `@AllArgsConstructor(access = AccessLevel.PRIVATE)`

#### Scenario: VO 类已使用全参构造
- **WHEN** skill 修改 VO 类的可变字段且代码中已使用全参构造
- **THEN** 删除 `@AllArgsConstructor`，手动重写全参构造方法，在构造方法中对可变字段做防御性复制

### Requirement: 附加代码规范清理
每次修改必须同时执行：Javadoc 格式统一（去掉冒号）、Copyright 年份更新到当前年份、import 语句整理、长方法签名参数换行对齐。

#### Scenario: Javadoc 格式清理
- **WHEN** skill 修改任意文件
- **THEN** 将 `@author:` 改为 `@author`，`@version:` 改为 `@version`，`@since:` 改为 `@since`

#### Scenario: Copyright 年份更新
- **WHEN** skill 修改任意文件
- **THEN** 将 Copyright 年份范围更新到当前年份（如 2024-2026）
