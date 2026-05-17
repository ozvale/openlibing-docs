# openlibing-docs

本文档面向 OpenLibing 开发人员、设计评审人员和 AI Coding Assistant，用来说明 `openlibing-docs` 仓库的结构、使用方式，以及轻量级 Spec 工作流。

## 1. 仓库定位

OpenLibing 是公司内部支撑产品代码构建、打包、发布、PR 门禁、Nightly、测试报告、开源合规、安全扫描等研发流程的大型工作流平台。

`openlibing-docs` 是 OpenLibing 组织级文档仓库，负责沉淀跨代码仓的系统设计、需求设计、测试策略、测试报告、发布报告，以及面向 AI 辅助研发的 Spec 文档。

本仓库不是某一个服务的代码仓，而是 OpenLibing 多代码仓体系的文档中枢。AI 处理具体代码需求时，应同时参考：

- 当前代码仓的源代码。
- `spec/<repo-name>/` 下对应代码仓的系统级设计、需求级设计和 AI 记忆。
- `architecture_desgin/`、`issue_docs/`、`test_docs/`、`release_docs/` 中与需求相关的文档。

## 2. 仓库目录

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

说明：

- `README.md`：本仓库唯一总说明，给人和 AI 共同阅读。
- `design.md`：OpenLibing AI 化研发 Spec 体系设计方案，可用于汇报和决策。
- `spec/`：AI 化研发 Spec 工作区。
- `architecture_desgin/`：架构设计、威胁分析、系统级方案图和说明。
- `issue_docs/`：需求设计、安全设计、接口设计等需求级文档。
- `test_docs/`：测试策略和测试报告。
- `release_docs/`：各代码仓发布报告。

## 3. Spec 工作区

`spec/` 用于支撑 OpenLibing 的 AI 化研发。它借鉴 OpenSpec “先设计、后实现、再归档”的思想，并采用轻量流程，不要求每个小需求都写完整的大型规格包。

每个代码仓一个目录：

```text
spec/<repo-name>/
+-- system_design/
|   +-- 系统设计索引.md
|   +-- <系统级设计文档>.md
+-- task_design/
|   +-- PR<需求号>_<需求短名>/
|       +-- design.md
|       +-- task.md
|       +-- archive.md
+-- ai_memory.md
```

目录职责：

- `system_design/`：保存系统级设计，描述长期稳定的模块职责、接口契约、数据流、部署关系、安全约束等。
- `task_design/`：保存需求级设计，一个需求一个目录。
- `design.md`：开发前编写，用于设计评审，说明背景、目标、非目标、影响范围、方案和验收标准。
- `task.md`：开发前编写，用于 AI 和开发人员执行，说明任务拆分、验证动作和完成标准。
- `archive.md`：开发完成后编写，说明最终交付、与原设计偏差、验证结果、AI 错误和人工修正。
- `ai_memory.md`：保存从多个需求中提炼出来的仓库级 AI 规则，避免同类问题反复出现。

## 4. 轻量工作流

OpenLibing 的需求仍然沿用原敏捷研发流程，Spec 只增加必要的设计和经验沉淀动作：

```text
1. 在 spec/<repo-name>/task_design/ 下创建需求目录
2. 编写 design.md
3. 编写 task.md
4. 设计评审组评审 design.md 和 task.md
5. AI 按 task.md 开发
6. 开发人员修正、验证并补充上下文
7. 编写 archive.md
8. 将可复用经验提炼到 ai_memory.md
```

小需求可以写短文档，判断标准是：评审人和 AI 能否理解目标、边界、任务和验收方式。中大型需求再补充接口、数据模型、安全、兼容性、灰度、回滚等内容。

## 5. AI 使用规则

AI 参与 OpenLibing 开发时必须遵守：

1. 先读取对应代码仓的 `spec/<repo-name>/ai_memory.md`。
2. 再读取对应需求目录下的 `design.md` 和 `task.md`。
3. 涉及系统边界、接口、数据模型、安全或发布影响时，检索 `system_design/` 和相关文档。
4. 实现过程中发现设计遗漏，应先补充到需求目录文档，再继续编码。
5. 完成后在 `archive.md` 记录最终结果、偏差、验证方式、AI 错误和可复用规则。
6. 只有被验证有效、或明显会复用的规则，才沉淀到 `ai_memory.md`，避免规则膨胀。

## 6. 代码仓 Spec 目录约定

每个 OpenLibing 代码仓在 `spec/` 下按以下结构维护：

```text
spec/<repo-name>/
+-- system_design/
|   +-- 系统设计索引.md
+-- task_design/
|   +-- .gitkeep
+-- ai_memory.md
```

可以从 `spec/_templates/` 复制模板：

- `system_design_template.md`：系统级设计模板。
- `design_template.md`：需求设计模板。
- `task_template.md`：任务拆分模板。
- `archive_template.md`：完成归档模板。
- `ai_memory_template.md`：仓库级 AI 记忆模板。

如果该代码仓存在相关架构、需求、测试或发布文档，应在 `系统设计索引.md` 中补充文档路径。
