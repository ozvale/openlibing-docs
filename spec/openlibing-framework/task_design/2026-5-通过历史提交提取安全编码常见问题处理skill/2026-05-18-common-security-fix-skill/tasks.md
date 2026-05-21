## 1. Skill 目录结构

- [x] 1.1 创建 `.opencode/skills/common-security-fix/` 目录
- [x] 1.2 创建 `reference/` 子目录
- [x] 1.3 创建 SKILL.md 主文件（包含 frontmatter、概述、强制约束、执行流程、问题类型索引、附加规范）

## 2. Reference 模板文件

- [x] 2.1 创建 `reference/EI_EXPOSE_REP.md`（覆盖 Date、集合、自定义类、数组四种类型，含 @Singular 规则、@AllArgsConstructor 规则）
- [x] 2.2 创建 `reference/DM_DEFAULT_ENCODING.md`
- [x] 2.3 创建 `reference/DM_BOXED_PRIMITIVE_FOR_PARSING.md`
- [x] 2.4 创建 `reference/STCAL_INVOKE_ON_STATIC_DATE_FORMAT.md`
- [x] 2.5 创建 `reference/SF_SWITCH_NO_DEFAULT.md`
- [x] 2.6 创建 `reference/NM_CLASS_NAMING_CONVENTION.md`
- [x] 2.7 创建 `reference/NM_SAME_SIMPLE_NAME_AS_SUPERCLASS.md`
- [x] 2.8 创建 `reference/SIC_INNER_SHOULD_BE_STATIC.md`
- [x] 2.9 创建 `reference/RCN_REDUNDANT_NULLCHECK.md`
- [x] 2.10 创建 `reference/DLS_DEAD_LOCAL_STORE.md`
- [x] 2.11 创建 `reference/UC_USELESS_OBJECT.md`
- [x] 2.12 创建 `reference/GC_UNRELATED_TYPES.md`
- [x] 2.13 创建 `reference/REC_CATCH_EXCEPTION.md`
- [x] 2.14 创建 `reference/UCF_USELESS_CONTROL_FLOW.md`

## 3. 规范约束实现

- [x] 3.1 在 SKILL.md 中实现强制约束 #1：修改方法后必须追溯所有调用点
- [x] 3.2 在 SKILL.md 中实现强制约束 #2：统一使用 @Nullable 而非 Optional
- [x] 3.3 在 SKILL.md 中实现强制约束 #3：@Nullable 注解位置规范
- [x] 3.4 在 SKILL.md 中实现强制约束 #4：日志文件输入处理与分批执行机制
- [x] 3.5 在 SKILL.md 中实现强制约束 #5：未覆盖类型需用户确认

## 4. OpenSpec 工件

- [x] 4.1 创建 proposal.md
- [x] 4.2 创建 design.md
- [x] 4.3 创建 specs/security-fix-patterns/spec.md
- [x] 4.4 创建 specs/skill-automation/spec.md
- [x] 4.5 创建 tasks.md
