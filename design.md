# OpenLibing AI 化研发 Spec 体系设计方案

## 1. 背景与目标

OpenLibing 是支撑产品代码构建、打包、发布、PR 门禁、Nightly、测试、安全扫描、开源合规等研发流程的大型平台。随着 AI Coding Assistant 进入日常研发，团队需要把“系统知识、需求设计、AI 修正经验”转化为可被 AI 和评审组共同读取的结构化资产。

本方案目标不是引入重流程，而是在现有敏捷开发节奏上增加一层轻量 Spec 机制：

- 让 AI 在开发前读得到需求上下文和系统约束。
- 让设计评审聚焦 `design.md` 和 `task.md` 两个文件。
- 让需求完成后通过 `archive.md` 记录最终结果和 AI 修正经验。
- 让可复用经验进入 `ai_memory.md`，减少同类错误反复发生。

## 2. 设计原则

### 2.1 轻量优先

OpenSpec 的完整流程适合复杂需求，但 OpenLibing 中存在大量两三人天的小需求。如果每个需求都强制 proposal、delta spec、design、task、verify、archive，会降低团队接受度。

本方案只保留四类必要信息：

- `design.md`：做什么、为什么做、边界是什么、怎么验收。
- `task.md`：AI 和开发人员按什么步骤执行。
- `archive.md`：最终做成什么、哪里偏离原设计、AI 犯了什么错。
- `ai_memory.md`：从多个需求中提炼出来的长期规则。

### 2.2 与多代码仓结构对齐

OpenLibing 是多代码仓系统，因此 Spec 按代码仓归档：

```text
spec/<repo-name>/
+-- system_design/
+-- task_design/
+-- ai_memory.md
```

AI 处理某个代码仓时，可以直接定位该仓的系统设计、需求设计和长期规则。

### 2.3 设计评审前置，归档面向复盘

需求开发前只评审 `design.md` 和 `task.md`。评审通过后，AI 可以依据任务清单开始开发。

`archive.md` 不只是记录最终结果，还必须记录 AI 生成过程中发生的错误、人工修正和后续规避规则。这一点是对 OpenSpec archive 的增强：OpenSpec 更关注最终规格归档，本方案额外关注 AI 过程改进。

### 2.4 规则少而准

`ai_memory.md` 不能变成流水账。只有稳定、可复用、能减少未来错误的经验才进入仓库级记忆。单次需求的临时决策保留在 `archive.md`，不污染长期规则。

## 3. 目录方案

仓库最终保留一个总说明 `README.md`，并将设计汇报材料 `design.md` 一起入库：

```text
openlibing-docs/
+-- README.md
+-- design.md
+-- spec/
|   +-- _templates/
|   |   +-- system_design_template.md
|   |   +-- design_template.md
|   |   +-- task_template.md
|   |   +-- archive_template.md
|   |   +-- ai_memory_template.md
|   +-- openlibing-ai-agent/
|   |   +-- system_design/
|   |   |   +-- 系统设计索引.md
|   |   +-- task_design/
|   |   |   +-- .gitkeep
|   |   +-- ai_memory.md
|   +-- openlibing-ai-web/
|       +-- system_design/
|       |   +-- 系统设计索引.md
|       +-- task_design/
|       |   +-- .gitkeep
|       +-- ai_memory.md
+-- architecture_desgin/
+-- issue_docs/
+-- test_docs/
+-- release_docs/
```

后续每个 OpenLibing 代码仓都可以按同样结构扩展。

## 4. 需求目录格式

每个需求一个目录：

```text
spec/<repo-name>/task_design/PR<需求号>_<需求短名>/
+-- design.md
+-- task.md
+-- archive.md
```

`design.md` 用于设计评审，建议包含：

- 背景
- 目标
- 非目标
- 影响范围
- 方案设计
- 验收标准
- AI 开发提示

`task.md` 用于执行，建议包含：

- 开发任务
- 测试与验证
- 文档与发布
- AI 执行检查项

`archive.md` 用于完成后归档，建议包含：

- 最终交付
- 与原设计的偏差
- 验证结果
- AI 错误与人工修正记录
- 可沉淀到 `ai_memory.md` 的规则
- 后续事项

## 5. 推荐工作流

```text
开发人员创建需求目录
        |
        v
编写 design.md + task.md
        |
        v
设计评审组评审两个文件
        |
        v
AI 按 task.md 开发
        |
        v
开发人员修正、验证、补充上下文
        |
        v
完成 archive.md
        |
        v
提炼稳定经验到 ai_memory.md
```

## 6. 与原敏捷流程的关系

本方案不替代原有需求、迭代、PR、测试、发布流程，只是在开发前后增加轻量文档节点：

- 原需求管理系统仍是需求入口。
- 原代码仓 PR 仍是代码评审入口。
- 原测试策略和测试报告仍放在 `test_docs/`。
- 原发布报告仍放在 `release_docs/`。
- 新增 `spec/` 只负责 AI 可读的设计、任务和经验沉淀。

## 7. AI 修正经验的沉淀机制

AI 犯错通常有三类：

1. 缺少系统上下文，例如不知道某个接口有兼容约束。
2. 缺少团队规范，例如不知道某类前端交互或后端异常处理的固定写法。
3. 错误推理或过度实现，例如把小需求做成大改造。

处理方式：

- 单次错误记录在需求 `archive.md`。
- 如果该错误未来可能复现，把“规避规则”提炼到 `ai_memory.md`。
- 如果规则涉及系统架构，把长期事实补充到 `system_design/`。
- 如果规则只适用于当前需求，不进入 `ai_memory.md`。

这样可以在“知识复用”和“规则膨胀”之间保持平衡。

## 8. 预期收益

- 设计评审更聚焦：评审两个固定文件即可。
- AI 开发更稳定：开发前有明确任务和上下文。
- 知识沉淀更连续：需求设计、最终结果、AI 经验形成闭环。
- 团队迁移成本低：小需求可以短文档，大需求再扩展。
- 多代码仓更清晰：每个仓的系统设计和 AI 规则独立维护。

## 9. 推进建议

第一阶段建议只在 `openlibing-ai-agent` 和 `openlibing-ai-web` 试点。

试点期间关注三件事：

- `design.md` 和 `task.md` 是否足够支撑评审和 AI 开发。
- `archive.md` 是否真实记录了 AI 错误和人工修正。
- `ai_memory.md` 是否能减少下一次同类需求的返工。

试点稳定后，再推广到 OpenLibing 其他核心代码仓。
