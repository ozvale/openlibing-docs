# OpenLibing Docs 仓库说明

本文档面向 AI Coding Assistant 和 OpenLibing 开发人员，用来说明 `openlibing-docs` 仓库的结构、使用方式和新增 Spec 工作流。

## 仓库定位

OpenLibing 是公司内部支撑产品代码构建、打包、发布、PR 门禁、Nightly、测试报告、开源合规、安全扫描等研发流程的大型工作流平台。本仓库是 OpenLibing 组织级文档仓库，负责保存跨代码仓的设计、测试、发布和 AI 化研发过程文档。

本仓库不是某一个服务的代码仓，而是 OpenLibing 多代码仓体系的文档中枢。AI 在处理具体代码需求时，应同时参考：

- 当前代码仓的源代码。
- 本仓库 `spec/` 下对应代码仓的系统级设计和需求级设计。
- 本仓库历史 `issue_docs/`、`test_docs/`、`release_docs/` 中与需求相关的文档。

## 目录结构

```text
openlibing-docs/
├── spec/
│   ├── README.md
│   ├── _templates/
│   ├── openlibing-ai-agent/
│   │   ├── system_design/
│   │   ├── task_design/
│   │   └── ai_memory.md
│   └── openlibing-ai-web/
│       ├── system_design/
│       ├── task_design/
│       └── ai_memory.md
├── architecture_desgin/
├── issue_docs/
├── test_docs/
├── release_docs/
└── README.md
```

## 原有目录说明

| 目录 | 用途 | AI 使用建议 |
| --- | --- | --- |
| `architecture_desgin/` | 历史架构设计、威胁分析、系统级方案图和说明。目录名保留历史拼写。 | 做系统级改动前先检索这里，避免重复设计。 |
| `issue_docs/` | 历史需求设计、安全设计、接口设计等需求级文档。 | 分析同类需求时优先检索对应代码仓目录。 |
| `test_docs/` | 测试策略和测试报告，按月份、迭代、代码仓或业务域沉淀。 | 生成测试建议或验收标准时参考。 |
| `release_docs/` | 各代码仓发布报告，通常按代码仓、分支或发布版本保存。 | 判断发布影响面、服务归属和历史变更时参考。 |
| `spec/` | 新增的 AI 化研发 Spec 工作区。 | 新需求优先在这里创建轻量 Spec，再让 AI 依据 `task.md` 开发。 |

## Spec 目录规则

`spec/` 以代码仓为一级归档单位。每个代码仓目录建议保持如下结构：

```text
spec/<repo-name>/
├── system_design/
│   ├── 系统设计索引.md
│   └── <系统级设计文档>.md
├── task_design/
│   ├── README.md
│   └── PR<需求号>_<需求短名>/
│       ├── design.md
│       ├── task.md
│       └── archive.md
└── ai_memory.md
```

说明：

- `system_design/` 保存系统级设计，描述长期稳定的模块职责、接口契约、数据流、部署关系、安全约束等。
- `task_design/` 保存需求级设计，一个需求一个目录，目录名建议使用 `PR<需求号>_<需求短名>`。
- `design.md` 描述需求背景、目标、范围、方案和验收标准。
- `task.md` 描述可执行任务清单，供 AI 和开发人员逐项实现。
- `archive.md` 在需求完成后填写，记录最终交付结果、与原设计偏差、AI 生成过程中的错误和后续规则。
- `ai_memory.md` 保存从多个需求中提炼出来的仓库级 AI 规则，避免相同问题反复出现。

## 轻量工作流

OpenLibing 的需求多数仍走敏捷节奏，因此 Spec 工作流只保留必要动作：

```text
1. 创建需求目录
2. 编写 design.md
3. 编写 task.md
4. 设计评审
5. AI 按 task.md 开发
6. 开发人员修正并验证
7. 编写 archive.md
8. 将可复用经验沉淀到 ai_memory.md
```

小需求可以只写最小版 `design.md` 和 `task.md`，不要求长篇文档。判断标准是：评审人和 AI 能否理解目标、边界、任务和验收方式。

## AI 执行约束

AI 在参与 OpenLibing 开发时必须遵守：

1. 先读取对应代码仓的 `spec/<repo-name>/ai_memory.md`。
2. 再读取对应需求目录下的 `design.md` 和 `task.md`。
3. 涉及系统边界、接口、数据模型、安全或发布影响时，检索 `system_design/` 和历史文档。
4. 实现过程中发现设计遗漏，应先补充到需求目录文档，再继续编码。
5. 完成后在 `archive.md` 记录最终结果、偏差、验证方式、AI 错误和可复用规则。
6. 只有被多次验证有效、或明显会复用的规则，才沉淀到 `ai_memory.md`，避免规则膨胀。

## 新增代码仓的方式

新增一个 OpenLibing 代码仓的 Spec 区域时，复制 `spec/_templates/` 中的模板，建立：

```text
spec/<repo-name>/
├── system_design/
│   └── 系统设计索引.md
├── task_design/
│   └── README.md
└── ai_memory.md
```

如果该代码仓已有历史文档，应在 `系统设计索引.md` 中补充历史文档链接或路径。
