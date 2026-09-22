## Why

FindBugs/SpotBugs 扫描产生的安全编码问题（如 EI_EXPOSE_REP、DM_DEFAULT_ENCODING 等）在 openlibing-framework 项目中频繁出现。当前修复这些问题的方式缺乏统一规范，不同开发者的修复风格不一致，导致代码审查成本高、修复质量参差不齐。

本项目已通过分析历史提交（50+ 次安全编码整改提交），提取了一套经过验证的修复模式。需要将这些模式固化为可复用的 opencode skill，使任何开发者调用该 skill 时都能按照统一标准自动修复问题。

## What Changes

- 新增 `common-security-fix` skill，覆盖 14 种常见 FindBugs/SpotBugs 问题类型
- 每种问题类型提供独立的 reference 模板文件，包含 BEFORE/AFTER 代码示例
- 建立强制约束：方法修改后必须追溯调用点、统一使用 `@Nullable` 而非 `Optional`、`@Nullable` 注解位置规范
- 支持日志文件（XML）批量输入，按 `<BugInstance>` 实例逐个处理，分批执行并反馈进度
- 未覆盖的问题类型需向用户说明成因和危害，获得确认后才能修改

## Capabilities

### New Capabilities
- `security-fix-patterns`: 安全编码问题的修复模式库，包含 14 种问题类型的 BEFORE/AFTER 模板
- `skill-automation`: skill 的自动化执行流程，包括日志解析、分批处理、约束强化循环

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- 新增 `.opencode/skills/common-security-fix/` 目录结构（SKILL.md + 14 个 reference 文件）
- 影响所有需要修复 FindBugs/SpotBugs 问题的开发者工作流
- 不改变现有业务代码或 API
