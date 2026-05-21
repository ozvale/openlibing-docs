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
+-- system_design/                         # 系统级设计：长期稳定的模块职责、接口契约、数据流、部署关系、安全约束
|   +-- 系统设计索引.md                    # 系统设计入口和文档清单
|   +-- <系统级设计文档>.md                # 单个系统级主题设计
+-- task_design/                           # 需求级设计：每一个子文件夹就是一个独立需求，禁止在根目录散落需求文件
|   +-- PR<需求号>_<需求短名>/             # 单个需求目录，也可用 <change-id> 或 YYYY-M-<需求短名>
|       +-- changes/                       # OpenSpec 变更区
|       |   +-- <change-id>/               # 当前进行中的变更
|       |   |   +-- proposal.md            # 目标、非目标、影响、风险
|       |   |   +-- design.md              # 完整级需求的技术方案、替代方案、架构决策；轻量或标准级可省略
|       |   |   +-- tasks.md               # 任务拆分、验证动作、完成标准
|       |   |   +-- specs/                 # 可测试的能力规格
|       |   |       +-- <capability>/
|       |   |           +-- spec.md         # GIVEN/WHEN/THEN 场景
|       |   +-- archive/                   # 归档区
|       |       +-- <change-id>/           # 已完成变更的归档副本
|       |           +-- proposal.md
|       |           +-- design.md
|       |           +-- tasks.md
|       +-- docs/                          # AI 协作过程产物
|       |   +-- superpowers/
|       |       +-- brainstorming/         # 头脑风暴记录
|       |       +-- plans/                 # 显式实现计划
|       +-- specs/                         # 归档后合并出的稳定规格
|       |   +-- <capability>/
|       |       +-- spec.md
|       +-- light-dev-record.md            # 轻量级任务的设计偏差、验证结果、可复用经验记录（按需）
+-- ai_memory.md                           # 仓库级 AI 记忆：跨多个需求验证过的可复用规则
```

需求目录命名建议使用 `<change-id>` 或 `YYYY-M-<需求短名>`，但同一个需求必须只占用一个目录。该目录是需求生命周期的唯一容器，从提案、设计、任务、计划、实现验证到归档都在目录内完成。

## 4. 轻量工作流

OpenLibing 的需求仍然沿用原敏捷研发流程，Spec 只增加必要的设计和经验沉淀动作：

```text
1. 在 spec/<repo-name>/task_design/ 下创建单独需求目录：<change-id>/
2. 在需求目录内编写 changes/<change-id>/proposal.md
3. 按需求等级编写 changes/<change-id>/design.md（完整级必需，标准级可省略）
4. 编写 changes/<change-id>/specs/*/spec.md 和 changes/<change-id>/tasks.md
5. 设计评审组评审 proposal.md、design.md、specs 和 tasks.md
6. AI 按 tasks.md 和 specs 场景开发
7. 开发人员修正、验证并补充上下文
8. 将 changes/<change-id>/ 归档到 changes/archive/<change-id>/，并合并稳定规格到 specs/
9. 将可复用经验提炼到 ai_memory.md
```

小需求可以写短文档，判断标准是：评审人和 AI 能否理解目标、边界、任务和验收方式。中大型需求再补充接口、数据模型、安全、兼容性、灰度、回滚等内容。

## 5. AI 使用规则

AI 参与 OpenLibing 开发时必须遵守：

1. 先读取对应代码仓的 `spec/<repo-name>/ai_memory.md`。
2. 再读取对应需求目录下的 `changes/<change-id>/proposal.md`、`design.md`、`tasks.md` 和 `specs/*/spec.md`。
3. 涉及系统边界、接口、数据模型、安全或发布影响时，检索 `system_design/` 和相关文档。
4. 实现过程中发现设计遗漏，应先补充到需求目录文档，再继续编码。
5. 完成后在 `changes/archive/<change-id>/` 或需求目录记录最终结果、偏差、验证方式、AI 错误和可复用规则。
6. 只有被验证有效、或明显会复用的规则，才沉淀到 `ai_memory.md`，避免规则膨胀。

## 6. 代码仓 Spec 目录约定

每个 OpenLibing 代码仓在 `spec/` 下按以下结构维护：

```text
spec/<repo-name>/
+-- system_design/
|   +-- 系统设计索引.md
+-- task_design/
|   +-- <需求目录>/
|       +-- changes/
|       |   +-- <change-id>/
|       |   +-- archive/
|       +-- docs/
|       |   +-- superpowers/
|       +-- specs/
+-- ai_memory.md
```

可以从 `spec/_templates/` 复制模板：

- `system_design_template.md`：系统级设计模板。
- `design_template.md`：需求设计模板。
- `task_template.md`：任务拆分模板。
- `archive_template.md`：完成归档模板。
- `ai_memory_template.md`：仓库级 AI 记忆模板。

如果该代码仓存在相关架构、需求、测试或发布文档，应在 `系统设计索引.md` 中补充文档路径。
