# OpenLibing Spec 工作区

`spec/` 用于支撑 OpenLibing 的 AI 化研发。它借鉴 OpenSpec 的“先规格、后实现、再归档”思想，但刻意保持轻量，避免给两三人天的小需求引入过重流程。

## 核心原则

- 一个代码仓一个目录。
- 一个需求一个 `task_design/PR<需求号>_<需求短名>/` 目录。
- 开发前只强制产出 `design.md` 和 `task.md`。
- 开发后补充 `archive.md`。
- AI 过程中的错误和人工修正必须记录，但只把可复用规则提炼到 `ai_memory.md`。

## 推荐流程

```text
create task spec -> review design/task -> AI implement -> human correct -> archive -> extract memory
```

## 文档粒度

小需求可以保持短文档：

- `design.md` 写清楚目标、范围、方案、验收。
- `task.md` 写清楚任务拆分和检查项。
- `archive.md` 写清楚最终交付、偏差、验证、AI 错误和修正规则。

中大型需求需要补充接口、数据模型、安全、兼容性、灰度、回滚等内容。

## 目录模板

模板位于 `_templates/`：

- `system_design_template.md`：系统级设计模板。
- `design_template.md`：需求设计模板。
- `task_template.md`：任务拆分模板。
- `archive_template.md`：完成归档模板。
- `ai_memory_template.md`：仓库级 AI 记忆模板。
