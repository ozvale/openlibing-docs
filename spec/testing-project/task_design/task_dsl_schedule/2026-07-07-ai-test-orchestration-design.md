---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 2648868cace9ae6d70a9c2ef0b390e76_542b55d479fe11f182885254006c9bbf
    ReservedCode1: cdQGru/9VUPM/oquRTXv46RcKORziPwdiWcHWWiUxe7N3UuBXAfVcA9nBI9AiWAlyUzUoUXKlkypBbum9Z2eOr5RJLHnyxUK4eQe5523Ff9PoOfLWiYFQVOOdrgFh3jk39rtgvIQIxLesIJn1rQ6shXnkZl5JXmwWvJ/EJVK/rHBCsXzbYSH4l7g8dk=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 2648868cace9ae6d70a9c2ef0b390e76_542b55d479fe11f182885254006c9bbf
    ReservedCode2: cdQGru/9VUPM/oquRTXv46RcKORziPwdiWcHWWiUxe7N3UuBXAfVcA9nBI9AiWAlyUzUoUXKlkypBbum9Z2eOr5RJLHnyxUK4eQe5523Ff9PoOfLWiYFQVOOdrgFh3jk39rtgvIQIxLesIJn1rQ6shXnkZl5JXmwWvJ/EJVK/rHBCsXzbYSH4l7g8dk=
---





# AI 辅助自动化测试编排系统 - 设计文档

> 日期：2026-07-07 | 版本：v1.0

---

## 1. 概述

### 1.1 目标

构建一个 AI 辅助的自动化测试编排系统，支持：

- 多种独立测试业务场景的执行
- 多种故障注入条件的组合
- 通过自然语言描述编排意图，AI 自动生成可执行的编排计划
- 编排方式包括：串行、并行、等待、循环、条件分支、重试

### 1.2 核心原则

**DSL 是 AI 和引擎之间的唯一契约。** AI 只负责产出 DSL，引擎只负责消费 DSL，互不越界。

### 1.3 使用方式

系统同时支持三种入口：

| 入口 | 场景 |
|------|------|
| 自然语言 | 测试人员用自然语言描述编排需求，AI 编译为 DSL |
| CLI/MCP | 用户通过 CLI 或 MCP 直接提交 DSL 或自然语言 |
| 可视化面板 | 拖拽 DAG 节点构建编排，支持从平台资产树选择 scenarios/faults 自动插入声明，支持 loop 结构的简洁表达及与 DAG 的相互转换，导出为 DSL 执行 |

---

## 1.4 术语表

| 术语 | 全称 | 含义 |
|------|------|------|
| DSL | Domain-Specific Language | 领域特定语言，AI 与执行引擎之间的唯一契约 |
| AI | Artificial Intelligence | 人工智能，用于解析用户意图并生成 DSL |
| LLM | Large Language Model | 大语言模型，AI 编译层的核心组件 |
| DAG | Directed Acyclic Graph | 有向无环图，编排计划的内部表示形式 |
| MCP | Model Context Protocol | 模型上下文协议，供 LLM Agent 调用的工具接口 |
| CLI | Command Line Interface | 命令行界面，供用户直接执行编排计划 |
| CI/CD | Continuous Integration / Continuous Deployment | 持续集成/持续部署，自动化流水线 |
| Manifest | - | 清单文件，注册可用的场景和故障定义 |
| Job | - | 作业，一组步骤的集合，可通过 `needs` 声明依赖 |
| Step | - | 步骤，最小执行单元（run/inject/cleanup/loop/condition/parallel/call） |
| Scenario | - | 场景，可执行的测试用例或命令 |
| Fault | - | 故障，混沌工程中的故障注入定义 |
| Inject | - | 故障注入，在执行场景前应用故障条件 |
| Cleanup | - | 故障回收，在执行场景后恢复系统状态 |
| Parallel | - | 并行执行，多个步骤同时运行 |
| Loop | - | 循环控制，重复执行一组步骤 |
| Condition | - | 条件分支，根据表达式结果选择执行路径 |
| Call | - | 调用另一个 job，实现复用和嵌套 |
| Strategy | - | 执行策略，包括 retry、backoff、fail-fast 等 |
| Retry | - | 重试机制，失败后重新执行 |
| Backoff | - | 退避策略，重试间隔时间 |
| Fail-fast | - | 快速失败，步骤失败立即终止整个计划 |
| Adapter | - | 适配器，统一执行接口，支持不同类型的执行器 |
| Executor | - | 执行器，实际执行命令的组件（Python/Shell/JMeter等） |
| Orchestrator | - | 编排器，DSL 解析、DAG 编译、调度执行的核心引擎 |

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                      用户入口层                          │
│   自然语言入口  │  CLI/MCP  │  可视化编排面板             │
│                          │                              │
│                    ┌──────┴──────┐                      │
│                    ▼             ▼                      │
│             ┌──────────┐  ┌──────────────┐             │
│             │ 资产树   │  │ DAG 画布     │             │
│             │ (scenarios│  │ (拖拽编排)   │             │
│             │  faults) │  │             │             │
│             └──────┬──────┘  └──────────────┘             │
│                    │             │                      │
│                    └──────┬──────┘                      │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   AI 编译层                              │
│  · 意图解析（LLM）                                      │
│  · 场景/故障目录匹配                                     │
│  · DSL 生成 + 校验                                      │
└─────────────────────────┬───────────────────────────────┘
                          ▼  (合法 DSL)
┌─────────────────────────────────────────────────────────┐
│                    编排执行层                            │
│  · DSL 解析 → DAG 编译                                  │
│  · 执行调度（拓扑排序 + 并行度计算）                      │
│  · 结果聚合 + 报告生成                                   │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    适配器层                              │
│  PythonExecutor │ ShellExecutor │ JMeterExecutor │ ...  │
└─────────────────────────────────────────────────────────┘
```

自然语言入口走 AI 编译层；API 和可视化面板可直接提交 DSL，旁路 AI 编译层。

可视化面板支持 loop 结构的简洁表达：通过循环节点封装重复执行逻辑，无需展开为多条 DAG 边。系统支持 loop 结构与 DAG 展开形式的相互转换——loop 结构便于用户理解和编辑，DAG 展开形式便于执行引擎调度。

可视化面板支持从平台资产树中选择 scenarios 和 faults 节点，自动插入到 DSL 的声明层（`scenarios` / `faults` 字段），无需手动编写 YAML。资产树按项目/模块/场景层级组织，支持搜索和筛选。

---

## 2.1 前端交互方案

### 2.1.1 资产树组件

资产树分为**业务场景库**和**故障模式库**两个独立管理的模块。公共资产树是完整的资产集合，项目资产树是公共资产树的子集，两者树结构保持一致。

**业务场景库组织结构**：

```
业务场景库（公共资产树）
├── 通用场景
│   └── health_check (scenario)
├── 跨项目场景
│   └── login_common (scenario)
├── 模块A1
│   ├── 场景A1-1 (scenario)
│   └── 场景A1-2 (scenario)
├── 模块A2
│   └── 场景A2-1 (scenario)
├── 模块B1
│   └── 场景B1-1 (scenario)
└── 模块B2
    └── 场景B2-1 (scenario)
```

**项目资产树（公共资产树的子集）**：

```
项目场景（公共资产树子集）
├── 通用场景                    ← 继承自公共
│   └── health_check (scenario)
├── 跨项目场景                  ← 继承自公共
│   └── login_common (scenario)
├── 模块A1                      ← 项目可见
│   ├── 场景A1-1 (scenario)
│   └── 场景A1-2 (scenario)
├── 模块A2                      ← 项目可见
│   └── 场景A2-1 (scenario)
├── 模块B1                      ← 项目可见
│   └── 场景B1-1 (scenario)
└── 模块B2                      ← 项目可见
    └── 场景B2-1 (scenario)
```

**故障模式库组织结构**：

```
故障模式库（公共资产树）
├── 通用故障
│   ├── net_delay_3s (fault)
│   └── packet_loss (fault)
├── 跨项目故障
│   └── db_failure (fault)
├── 模块A1
│   └── 故障A1-1 (fault)
├── 模块A2
│   └── 故障A2-1 (fault)
├── 模块B1
│   └── 故障B1-1 (fault)
└── 模块B2
    └── 故障B2-1 (fault)
```

**项目资产树与公共资产树关系**：

| 关系 | 说明 |
|------|------|
| 树结构一致 | 项目资产树与公共资产树的层级结构保持一致 |
| 子集关系 | 项目资产树是公共资产树的子集 |
| 继承公共 | 项目资产树自动继承公共资产树中的通用场景/故障 |
| 使用隔离 | 编排时只从当前项目的资产树（子集）引用插入 |

**交互方式**：

| 操作 | 说明 |
|------|------|
| 点击展开/折叠 | 展开或折叠节点 |
| 双击选择 | 将选中的场景/故障自动插入到 DSL 声明层（仅本项目资产树） |
| 拖拽到画布 | 将场景/故障作为节点拖拽到 DAG 画布（仅本项目资产树） |
| 搜索框 | 支持按名称搜索场景和故障 |
| 筛选标签 | 按类型（scenario/fault）、项目、模块筛选 |
| 切换库 | 切换业务场景库和故障模式库 |
| 提升为公共 | 将项目专属资产提升为公共资产（需审核） |

### 2.1.2 自动插入机制

当用户从资产树中选择场景或故障时，系统自动将其插入到 DSL 的声明层，并生成对应的引用 ID。

**插入规则**：

| 规则 | 说明 |
|------|------|
| ID 生成 | 自动生成唯一 ID，格式：`<项目>_<模块>_<名称>`（如 `projA_modA1_login`） |
| 去重检查 | 如果相同 ID 已存在，跳过重复插入 |
| 位置保持 | 插入到对应声明列表的末尾，保持用户已有顺序 |
| 自动引用 | 如果拖拽到 DAG 画布，自动创建 `run` 或 `inject` 步骤引用 |
| 项目隔离 | 编排时只从当前项目的资产树（子集）引用插入，其他项目的资产不可直接使用 |
| 公共资产继承 | 公共资产（通用场景/跨项目场景）自动继承到项目资产树，可直接插入 |
| 公共资产 ID | 公共资产插入时，ID 格式：`public_<公共资产ID>`（如 `public_health_check`） |

**示例流程（项目专属资产）**：

1. 用户在项目A资产树中双击 `登录场景`（项目A → 模块A1）
2. 系统自动在 `scenarios` 中添加：
   ```yaml
   - id: projA_modA1_login
     cmd: "pytest tests/login.py"
     params:
       env: "test"
   ```
3. 如果用户将其拖拽到 DAG 画布，自动在对应 job 的 steps 中添加：
   ```yaml
   - run: projA_modA1_login
   ```

**示例流程（继承的公共资产）**：

1. 用户在项目A资产树中双击 `健康检查`（通用场景）
2. 系统自动在 `scenarios` 中添加：
   ```yaml
   - id: public_health_check
     cmd: "curl http://localhost:8080/health"
     params: {}
     source: "public"
   ```
3. 如果用户将其拖拽到 DAG 画布，自动在对应 job 的 steps 中添加：
   ```yaml
   - run: public_health_check
   ```

### 2.1.3 资产树数据模型

资产树分为业务场景库和故障模式库两个独立模块。公共资产树是完整的资产集合，项目资产树是公共资产树的子集视图，两者树结构保持一致。

**业务场景库数据模型（公共资产树）**：

```json
{
  "id": "scenario_library",
  "name": "业务场景库",
  "type": "library",
  "children": [
    {
      "id": "common_scenarios",
      "name": "通用场景",
      "type": "category",
      "visibility": "public",
      "children": [
        {
          "id": "health_check",
          "name": "健康检查",
          "type": "scenario",
          "data": {
            "cmd": "curl http://localhost:8080/health",
            "params": {},
            "description": "服务健康检查",
            "tags": ["common", "health"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "cross_project",
      "name": "跨项目场景",
      "type": "category",
      "visibility": "public",
      "children": [
        {
          "id": "login_common",
          "name": "通用登录",
          "type": "scenario",
          "data": {
            "cmd": "pytest tests/common/login.py",
            "params": {},
            "description": "跨项目通用登录场景",
            "tags": ["common", "auth"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_a1",
      "name": "模块A1",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "scenario_a1_1",
          "name": "场景A1-1",
          "type": "scenario",
          "data": {
            "cmd": "pytest tests/module_a1/scenario1.py",
            "params": {},
            "description": "模块A1场景1",
            "tags": ["module_a1"],
            "owner": "platform"
          }
        },
        {
          "id": "scenario_a1_2",
          "name": "场景A1-2",
          "type": "scenario",
          "data": {
            "cmd": "pytest tests/module_a1/scenario2.py",
            "params": {},
            "description": "模块A1场景2",
            "tags": ["module_a1"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_a2",
      "name": "模块A2",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "scenario_a2_1",
          "name": "场景A2-1",
          "type": "scenario",
          "data": {
            "cmd": "pytest tests/module_a2/scenario1.py",
            "params": {},
            "description": "模块A2场景1",
            "tags": ["module_a2"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_b1",
      "name": "模块B1",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "scenario_b1_1",
          "name": "场景B1-1",
          "type": "scenario",
          "data": {
            "cmd": "pytest tests/module_b1/scenario1.py",
            "params": {},
            "description": "模块B1场景1",
            "tags": ["module_b1"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_b2",
      "name": "模块B2",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "scenario_b2_1",
          "name": "场景B2-1",
          "type": "scenario",
          "data": {
            "cmd": "pytest tests/module_b2/scenario1.py",
            "params": {},
            "description": "模块B2场景1",
            "tags": ["module_b2"],
            "owner": "platform"
          }
        }
      ]
    }
  ]
}
```

**故障模式库数据模型（公共资产树）**：

```json
{
  "id": "fault_library",
  "name": "故障模式库",
  "type": "library",
  "children": [
    {
      "id": "common_faults",
      "name": "通用故障",
      "type": "category",
      "visibility": "public",
      "children": [
        {
          "id": "net_delay_3s",
          "name": "网络延迟3秒",
          "type": "fault",
          "data": {
            "cmd": "tc qdisc add dev eth0 root netem delay 3000ms",
            "params": { "duration": 3 },
            "description": "注入3秒网络延迟",
            "tags": ["network", "chaos"],
            "owner": "platform"
          }
        },
        {
          "id": "packet_loss",
          "name": "网络丢包",
          "type": "fault",
          "data": {
            "cmd": "tc qdisc add dev eth0 root netem loss 10%",
            "params": { "duration": 5 },
            "description": "注入10%网络丢包",
            "tags": ["network", "chaos"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "cross_project_faults",
      "name": "跨项目故障",
      "type": "category",
      "visibility": "public",
      "children": [
        {
          "id": "db_failure",
          "name": "数据库故障",
          "type": "fault",
          "data": {
            "cmd": "systemctl stop mysql",
            "params": { "duration": 30 },
            "description": "停止数据库服务",
            "tags": ["db", "chaos"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_a1",
      "name": "模块A1",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "fault_a1_1",
          "name": "故障A1-1",
          "type": "fault",
          "data": {
            "cmd": "tc qdisc add dev lo root netem delay 500ms",
            "params": { "duration": 5 },
            "description": "数据库网络延迟",
            "tags": ["db", "chaos"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_a2",
      "name": "模块A2",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "fault_a2_1",
          "name": "故障A2-1",
          "type": "fault",
          "data": {
            "cmd": "tc qdisc add dev eth0 root netem delay 2000ms",
            "params": { "duration": 10 },
            "description": "模块A2网络延迟",
            "tags": ["network", "chaos"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_b1",
      "name": "模块B1",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "fault_b1_1",
          "name": "故障B1-1",
          "type": "fault",
          "data": {
            "cmd": "tc qdisc add dev eth0 root netem loss 20%",
            "params": { "duration": 8 },
            "description": "模块B1网络丢包",
            "tags": ["network", "chaos"],
            "owner": "platform"
          }
        }
      ]
    },
    {
      "id": "module_b2",
      "name": "模块B2",
      "type": "module",
      "visibility": "public",
      "children": [
        {
          "id": "fault_b2_1",
          "name": "故障B2-1",
          "type": "fault",
          "data": {
            "cmd": "systemctl stop redis",
            "params": { "duration": 15 },
            "description": "缓存服务故障",
            "tags": ["cache", "chaos"],
            "owner": "platform"
          }
        }
      ]
    }
  ]
}
```

**项目资产树生成规则**：

项目资产树是公共资产树的子集视图，生成规则如下：

1. **公共资产自动继承**：`visibility: "public"` 的节点（通用场景/跨项目场景/各模块）自动包含到所有项目的资产树中
2. **树结构一致**：项目资产树与公共资产树保持相同的层级结构，仅做子集过滤

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 节点类型：`library` / `category` / `module` / `scenario` / `fault` |
| `visibility` | string | 可见性：`public`（公共可见） |
| `owner` | string | 资产归属：`platform`（平台公共） |
| `tags` | array | 标签列表，用于搜索和筛选 |

### 2.1.4 与 DAG 画布的协作

资产树与 DAG 画布双向协作，遵循项目隔离原则。项目资产树是公共资产树的子集视图，自动继承公共资产：

```
┌──────────────────────────────────────────────────────┐
│                    可视化编排面板                       │
│                                                      │
│  ┌─────────────┐         ┌─────────────┐            │
│  │ 业务场景库  │         │ 故障模式库  │            │
│  │ (公共资产树)│         │ (公共资产树)│            │
│  │             │         │             │            │
│  │ 通用场景    │         │ 通用故障    │            │
│  │ 跨项目场景  │         │ 跨项目故障  │            │
│  │ 模块A/B/C   │         │ 模块A/B/C   │            │
│  └──────┬──────┘         └──────┬──────┘            │
│         │                       │                    │
│         └──────────┬────────────┘                    │
│                    ▼  子集过滤                        │
│          ┌──────────────┐                            │
│          │ 当前项目资产树│  ← 公共资产自动继承 + 项目专属 │
│          │ (公共资产树的)│                            │
│          │    子集视图   │                            │
│          └──────┬───────┘                            │
│                 │ 双击/拖拽                          │
│                 ▼                                    │
│          ┌──────────────┐                            │
│          │   DAG画布    │                            │
│          │   节点/连线  │                            │
│          └──────┬───────┘                            │
│                 │ 修改/删除                          │
│                 ▼                                    │
│          ┌──────────────┐                            │
│          │ DSL预览/编辑区│                            │
│          │ (自动同步)   │                            │
│          └──────────────┘                            │
└──────────────────────────────────────────────────────┘
```

| 方向 | 场景 | 行为 |
|------|------|------|
| 资产树 → DAG | 双击场景（项目专属） | 自动创建 `run` 节点并添加到画布 |
| 资产树 → DAG | 双击故障（项目专属） | 自动创建 `inject` 节点并添加到画布 |
| 资产树 → DAG | 双击继承的公共资产 | 自动创建节点，ID 前缀 `public_` |
| 资产树 → DAG | 拖拽到节点 | 自动建立依赖关系 |
| DAG → 资产树 | 删除节点 | 如果无其他引用，提示是否从声明层移除 |
| DAG → 资产树 | 修改引用 ID | 同步更新声明层 ID |
| 项目资产 → 公共 | 提升操作 | 提交审核，审核通过后 `visibility` 改为 `public` |

**项目隔离规则**：

| 规则 | 说明 |
|------|------|
| 可见性 | 资产树默认只显示当前项目的资产树（公共资产树的子集视图） |
| 可操作性 | 只有当前项目资产树中的资产可双击插入或拖拽到画布 |
| 公共资产继承 | 公共资产（`visibility: public`）自动继承到项目资产树，无需手动引用 |
| 数据一致性 | 继承的公共资产与公共资产树保持同步，公共资产更新后自动生效 |
| 子集关系 | 项目资产树是公共资产树的子集，树结构保持一致 |

### 2.1.5 DSL 预览与编辑

可视化面板底部提供 DSL 预览区，实时同步用户操作：

- **实时预览**：用户在资产树或画布的操作实时反映到 DSL
- **手动编辑**：支持直接编辑 YAML，修改后同步到画布和资产树引用
- **语法高亮**：YAML 语法高亮显示
- **错误提示**：校验错误实时标记

---

## 3. DSL 规范

### 3.1 完整示例

```yaml
name: "登录+下单冒烟测试"

scenarios:
  - id: login
    cmd: "pytest tests/login.py"
  - id: create_order
    cmd: "pytest tests/create_order.py"
  - id: check_network
    cmd: "ping 10.0.0.1 -n 3"

faults:
  - id: net_delay_3s
    cmd: "tc qdisc add dev eth0 root netem delay 3000ms"
    params:
      duration: 3

jobs:
  login:
    steps:
      - run: login
        timeout: 30s

  order:
    needs: [login]
    strategy:
      retry: 3
      backoff: 2s
      fail-fast: false
    steps:
      - inject: [net_delay_3s]
      - run: create_order
      - cleanup: [net_delay_3s]

  refund:
    needs: [login]
    strategy:
      fail-fast: false
    steps:
      - run: refund

  check:
    needs: [order, refund]
    steps:
      - loop:
          times: 3
          steps:
            - run: check_network
            - condition:
                if: "${last_step.output.contains('0% loss')}"
                break: true
```

### 3.2 关键词全表

#### 声明层

| 关键词 | 层级 | 含义 | 约束 |
|--------|------|------|------|
| `plan` | 根 | DSL 文档根节点 | 必填，每文件一个 |
| `name` | `plan` 下 | 计划名称 | 必填 |
| `scenarios` | `plan` 下 | 场景声明列表 | 必填，至少一个 |
| `faults` | `plan` 下 | 故障注入声明列表 | 可选，默认空 |
| `id` | 条目 | 全局唯一标识符 | 必填，全文件唯一（场景与故障间也不可重名） |
| `cmd` | 条目 | 执行命令 | 已注册 manifests 时可省略；否则必填 |
| `params` | 条目 | 参数 | 选填，键值对 |

#### 执行层（Job 与 Step 类型）

| 关键词 | 含义 | 子元素 | 约束 |
|--------|------|--------|------|
| `jobs` | 作业定义列表 | 一组 job | 必填，至少一个 job |
| `needs` | 依赖声明 | job id 列表 | 可选，无 `needs` 的 job 立即启动 |
| `strategy` | 执行策略 | `retry` / `backoff` / `fail-fast` | 可选 |
| `steps` | 步骤列表 | step 列表 | 必填，至少一个 step |
| `run` | 执行场景 | 场景 id（引用 `scenarios`） | 单场景，必须引用已声明的 id |
| `inject` | 注入故障 | 故障 id 列表（引用 `faults`） | 按列表顺序注入 |
| `cleanup` | 回收故障 | 故障 id 列表（引用 `faults`） | 按逆序回收；可选，引擎兜底 |
| `parallel` | 并行执行 | `steps` 子步骤列表 | 至少 2 个子步骤 |
| `loop` | 循环控制 | `times` + `steps` 子步骤列表 | 循环内禁嵌套 `loop` |
| `condition` | 条件分支 | `if` / `then` / `else` | `then` 必填，`else` 可选 |
| `call` | 调用另一个 job | job id | 引用的 job 必须已定义在当前 plan 中 |

#### 策略属性

| 关键词 | 适用位置 | 取值 | 含义 |
|--------|---------|------|------|
| `needs` | job | job id 列表 | 依赖的 job 全部完成后才启动 |
| `retry` | strategy | 正整数 | 整个 job 失败后重试次数 |
| `backoff` | strategy | 时间字符串 | 重试间隔 |
| `fail-fast` | strategy | `true` / `false` | 失败是否终止整个 plan，默认 `true` |

#### 步骤属性

| 关键词 | 适用 step | 取值 | 含义 |
|--------|----------|------|------|
| `timeout` | `run` | 时间字符串 | 单步骤超时 |
| `if` | `condition` | 条件表达式 | 判断条件 |
| `then` | `condition` | step 列表 | 条件为真执行 |
| `else` | `condition` | step 列表 | 条件为假执行（可选） |
| `times` | `loop` | 正整数 | 最大循环次数 |
| `break` | `loop` 子步骤 | `true` / 条件表达式 | `true` 立即终止循环 |
| `steps` | `parallel` / `loop` | step 列表 | 子步骤 |

#### 变量插值

| 表达式 | 含义 | 可用范围 |
|--------|------|---------|
| `${last_step.status}` | 上一步状态 | `condition`、`loop.break` |
| `${last_step.exit_code}` | 上一步退出码 | 同上 |
| `${last_step.output}` | 上一步 stdout | 同上 |
| `${parallel.all_passed}` | 当前并行组是否全通过 | 紧邻 `parallel` 之后的 `condition` |
| `${job_id.status}` | 指定 job 的最终状态 | job 间条件判断 |

### 3.4 声明层与执行层关系

- **声明层是"定义"**：告诉引擎存在哪些可执行体
- **执行层是"引用 + 复写"**：通过 `run` / `inject` 引用声明层 id

`cmd` 优先级：`run`/`inject` 中直接写命令（如有）> 声明层 `cmd` > `manifests[id].cmd`

### 3.5 拓扑约束

| 规则 | 说明 |
|------|------|
| 无环 | DAG 编译时通过 `needs` 检测循环依赖 |
| 引用完整性 | `needs` 指向的 job id 必须存在；`run` 引用的场景 id 必须在 `scenarios` 中声明；`inject`/`cleanup` 中的故障 id 必须在 `faults` 中声明；`call` 引用的 job id 必须已定义 |
| 嵌套深度上限 | `loop > parallel` 嵌套上限 5 层 |
| `loop` 内禁嵌套 `loop` | 需嵌套循环用 `call` 引用另一个 job |
| `needs` 缺省语义 | 无 `needs` 的 job 在 plan 启动时立即执行 |
| `parallel` 至少 2 子步骤 | 单一 `run` 直接写在 `steps` 中即可 |
| `fail-fast` 作用域 | `true` 时 job 内任一步骤失败立即终止整个 plan |

---

## 4. 执行引擎

### 4.1 DAG 编译

通过 `needs` 声明构建 DAG：

- 无 `needs` 的 job → 根节点，plan 启动时立即执行
- `needs: [A, B]` → A 和 B 都完成后才执行当前 job
- 多个 job 依赖同一 job → A 完成后并行触发 B 和 C
- `loop` → 展开为循环控制节点，内部子 DAG 每次迭代重新调度。有限次 loop 可展开为 DAG（如 `times: 3` 展开为 3 条串行边），也可保持为循环节点。可视化面板支持 loop 结构与 DAG 展开形式的双向转换：loop 结构便于编辑和理解，DAG 展开形式便于执行引擎调度和可视化渲染。
- `condition` → 提取为带条件表达式的边
- `call` → 将目标 job 的 steps 内联展开到当前执行位置
- `parallel` → 展开为并行组，组内 steps 并发执行

### 4.2 调度模型

两级调度：

| 级别 | 职责 |
|------|------|
| DAG 调度器 | 拓扑排序确定就绪队列；依赖解析；并行组并发发射 |
| 节点执行器 | 每个节点独立线程/协程；状态机管理；超时控制；故障注入生命周期 |

### 4.3 故障注入生命周期

```
inject faults → run scenario → cleanup faults
```

即使用户手动终止执行，引擎保证故障回收。

### 4.4 并行等待策略

| 策略 | 语义 |
|------|------|
| `wait: all` | 所有并行节点完成才继续（默认） |
| `wait: first` | 第一个完成即继续，取消其余 |
| `wait: any` | 任意一个完成即继续，其余继续跑 |

---

## 5. 适配器层

### 5.1 统一接口

```python
class AdapterProtocol:
    supported_types: list[str]
    def inject_fault(fault_def)
    def cleanup_fault(fault_def)
    def execute(node, context) -> Result

    class Result:
        status: SUCCESS | FAIL | TIMEOUT | ERROR
        exit_code: int
        stdout: str
        stderr: str
        metrics: dict
        artifacts: list[str]
        duration_ms: int
```

### 5.2 内置适配器

| 适配器 | 类型 | 实现 |
|--------|------|------|
| PythonExecutor | `python`, `pytest` | subprocess |
| ShellExecutor | `shell`, `bash`, `bat` | subprocess |
| JMeterExecutor | `jmeter` | CLI 模式 + .jtl 解析 |
| FaultInjector | `network_delay`, `packet_loss`, `cpu_stress`, `kill_process` | 对应工具链 |

新增适配器只需实现 `AdapterProtocol` 并注册。

---

## 6. AI 编译层

### 6.1 流程

```
用户自然语言 → LLM 意图解析 → DSL 生成 → 三重校验 → 交付引擎
                                              │
                                         校验失败 → 自动修正（最多 2 次）
                                                    │
                                               仍失败 → 返回用户
```

### 6.2 Prompt 策略

三段式对话：

| 阶段 | 作用 | 内容 |
|------|------|------|
| System | 角色 + DSL 规范 | 编排 DSL 生成器，只输出合法 YAML |
| Context | 环境信息 | 可用场景/故障列表（从 manifests 加载，向量检索裁剪） |
| User | 用户意图 | 自然语言编排需求 |

内置 3-5 个 few-shot 示例覆盖串行/并行/循环/条件/故障注入。

### 6.3 校验规则

| 校验层 | 内容 |
|--------|------|
| 语法校验 | YAML 合法性、缩进、关键词拼写 |
| 引用校验 | 所有 `step_id`、`scenario id`、`fault id` 引用完整性 |
| 拓扑校验 | DAG 无环、嵌套深度 ≤ 5、loop 无嵌套 |

### 6.4 旁路条件

API 和可视化面板直接提交 DSL 时，跳过 LLM，仅走三重校验后交付引擎。

---

## 7. 结果与报告

### 7.1 报告形式

| 格式 | 用途 |
|------|------|
| HTML 报告 | 瀑布图展示节点时间线，失败红色高亮，支持折叠子 DAG |
| JSON 结果 | 结构化数据，供 CI 平台消费做门禁判断 |

### 7.2 聚合维度

- 总步数 / 通过 / 失败 / 超时
- 总耗时
- 成功率
- 每个 step 的详细结果（stdout、stderr、metrics、artifacts）

---

## 8. 技术栈

| 组件 | 技术选型 |
|------|---------|
| DSL 解析/DAG 编译 | Python（pydantic schema 校验） |
| 执行引擎 | Python asyncio / 线程池 |
| AI 编译层 LLM | 现有 LLM API |
| HTML 报告 | Jinja2 模板渲染 |
| 持久化 | SQLite（执行历史、DSL 版本） |
| 适配器 | subprocess + 各工具 CLI |

---

## 9. MCP 与 CLI 封装

### 9.1 封装边界

松耦合设计：MCP 和 CLI 各自独立，MCP 只负责 DSL 的生成与校验，不负责执行。

```
┌──────────────────────────────────────────────┐
│                  MCP Server                   │
│  ┌────────────┐  ┌────────────┐              │
│  │ list_scenarios│ │ generate_dsl│            │
│  │ list_faults  │ │ validate_dsl│            │
│  └────────────┘  └────────────┘              │
│  资源：执行状态推送（streaming Resource）      │
└──────────────────────────────────────────────┘
                      ▲
                      │ LLM 调用
                      │
┌─────────────────────┴────────────────────────┐
│                  CLI (orchestrator)           │
│  run     status   cancel   history   report   │
│  manifest scan / validate                     │
│  adapter list                                 │
└──────────────────────────────────────────────┘
```

| 维度 | MCP | CLI |
|------|-----|-----|
| 调用方 | LLM Agent | 人、CI/CD、可视化面板后台 |
| 交互模式 | 请求-响应 / 流式推送 | 一次性命令 |
| 职责 | 智能编排的"智能"部分 | 确定性执行的"执行"部分 |
| 依赖关系 | 不依赖 CLI | 不依赖 MCP |

用户拿到 MCP 生成的 DSL 后，自行通过 CLI 执行。

### 9.2 MCP 工具定义

| 工具名 | 输入 | 输出 | 说明 |
|--------|------|------|------|
| `list_scenarios` | 无（或目录路径） | `[{id, cmd, type}]` | 返回 manifests 中已注册的场景列表 |
| `list_faults` | 无 | `[{id, cmd, params}]` | 返回 manifests 中已注册的故障列表 |
| `generate_dsl` | `intent: string`（自然语言） | `{dsl: string, warnings: [...]}` | 根据意图生成 DSL YAML |
| `validate_dsl` | `dsl: string` | `{valid: bool, errors: [...]}` | 校验 DSL 合法性（语法+引用+拓扑） |

### 9.3 CLI 命令定义

| 命令 | 说明 |
|------|------|
| `orchestrator run -f <dsl.yaml>` | 执行编排计划 |
| `orchestrator status <run_id>` | 查询执行进度 |
| `orchestrator cancel <run_id>` | 终止执行 |
| `orchestrator history [--limit N]` | 历史记录 |
| `orchestrator report <run_id> [--format html|json]` | 导出报告 |
| `orchestrator manifest scan [--dir <path>]` | 扫描目录生成 manifests |
| `orchestrator manifest validate` | 校验 manifests 完整性 |
| `orchestrator adapter list` | 列出已安装适配器 |

---

## 10. 附录：AI 编译层使用示例

### 示例 1：冒烟测试 + 故障注入

**输入：**
> 先执行登录场景，成功后并行跑下单和退款两个场景，下单的时候注入3秒网络延迟。如果下单失败就重试最多3次，退款失败不影响继续。最后检查一下网络连通性。

**输出 DSL：**

```yaml
name: "冒烟测试"

scenarios:
  - id: login
  - id: create_order
  - id: refund
  - id: check_network

faults:
  - id: net_delay_3s
    cmd: "tc qdisc add dev eth0 root netem delay 3000ms"

jobs:
  login:
    steps:
      - run: login
        timeout: 30s

  order:
    needs: [login]
    strategy:
      retry: 3
      fail-fast: false
    steps:
      - inject: [net_delay_3s]
      - run: create_order
      - cleanup: [net_delay_3s]

  refund:
    needs: [login]
    strategy:
      fail-fast: false
    steps:
      - run: refund

  check:
    needs: [order, refund]
    steps:
      - run: check_network
```

### 示例 2：双环境回归 + 条件判断

**输入：**
> 测试环境A跑登录和商品浏览串行，测试环境B跑下单和支付串行，两边同时开始。都跑完之后，如果两边都成功，再跑一遍全链路压测。

**输出 DSL：**

```yaml
name: "双环境回归"

scenarios:
  - id: login
  - id: browse_product
  - id: create_order
  - id: payment
  - id: full_link_load

jobs:
  env_a:
    steps:
      - run: login
      - run: browse_product

  env_b:
    steps:
      - run: create_order
      - run: payment

  load_test:
    needs: [env_a, env_b]
    steps:
      - condition:
          if: "${env_a.status == 'SUCCESS' && env_b.status == 'SUCCESS'}"
          then:
            - run: full_link_load
```

### 示例 3：嵌套循环（call 拆解）

**输入：**
> 登录后循环5次：每次先注入网络延迟，然后循环3次尝试下单直到成功，最后回收故障并检查网络。

**输出 DSL：**

```yaml
name: "嵌套循环测试"

scenarios:
  - id: login
  - id: create_order
  - id: check_network

faults:
  - id: net_delay_3s

jobs:
  # 内层循环：独立 job
  retry_order:
    steps:
      - loop:
          times: 3
          steps:
            - inject: [net_delay_3s]
            - run: create_order
            - condition:
                if: "${last_step.exit_code == 0}"
                break: true
            - cleanup: [net_delay_3s]

  # 外层循环：调用内层 job
  full_test:
    needs: [login]
    steps:
      - loop:
          times: 5
          steps:
            - call: retry_order
            - run: check_network

  login:
    steps:
      - run: login
```

---

## 11. 附录：Workflow 方案 vs 原始方案对比

以同一复杂业务场景「全链路混沌测试」为例，分别给出两种方案的 DSL，并做逐维度对比。

**场景描述**：先串行检查两个环境的健康状态；然后并行 — 环境A跑登录 + 网络检查循环(直到通) + 商品浏览，环境B注入网络延迟后跑下单(失败重试2次) + 支付(容忍失败)；最后都成功则跑全链路压测。

### 11.1 Workflow 方案（声明层复用 + jobs/needs/steps）

```yaml
name: "全链路混沌测试"

scenarios:
  - id: health_check_a
    cmd: "curl -s http://env-a:8080/health"
  - id: health_check_b
    cmd: "curl -s http://env-b:8080/health"
  - id: login
    cmd: "pytest tests/login.py --env A"
  - id: check_network
    cmd: "ping 10.0.0.1 -n 3"
  - id: browse_product
    cmd: "pytest tests/browse_product.py --env A"
  - id: create_order
    cmd: "pytest tests/create_order.py --env B"
  - id: payment
    cmd: "pytest tests/payment.py --env B"
  - id: full_link_load
    cmd: "jmeter -n -t tests/full_link.jmx"

faults:
  - id: net_delay_3s
    cmd: "tc qdisc add dev eth0 root netem delay 3000ms"
  - id: packet_loss
    cmd: "tc qdisc add dev eth0 root netem loss 10%"

jobs:
  health_a:
    steps:
      - run: health_check_a

  health_b:
    needs: [health_a]
    steps:
      - run: health_check_b

  env_a_flow:
    needs: [health_b]
    steps:
      - run: login
      - loop:
          times: 3
          steps:
            - run: check_network
            - condition:
                if: "${last_step.output.contains('0% loss')}"
                break: true
      - run: browse_product

  env_b_flow:
    needs: [health_b]
    strategy:
      fail-fast: false
    steps:
      - inject: [net_delay_3s, packet_loss]
      - run: create_order
        retry: 2
      - cleanup: [net_delay_3s, packet_loss]
      - run: payment
        on-failure: continue

  load_test:
    needs: [env_a_flow, env_b_flow]
    steps:
      - condition:
          if: "${env_a_flow.status == 'SUCCESS' && env_b_flow.status == 'SUCCESS'}"
          then:
            - run: full_link_load
```

### 11.2 原始方案（scenarios/faults 声明 + flow 树形编排）

```yaml
plan:
  name: "全链路混沌测试"

  scenarios:
    - id: health_check_a
      cmd: "curl -s http://env-a:8080/health"
    - id: health_check_b
      cmd: "curl -s http://env-b:8080/health"
    - id: login
      cmd: "pytest tests/login.py --env A"
    - id: check_network
      cmd: "ping 10.0.0.1 -n 3"
    - id: browse_product
      cmd: "pytest tests/browse_product.py --env A"
    - id: create_order
      cmd: "pytest tests/create_order.py --env B"
    - id: payment
      cmd: "pytest tests/payment.py --env B"
    - id: full_link_load
      cmd: "jmeter -n -t tests/full_link.jmx"

  faults:
    - id: net_delay_3s
      cmd: "tc qdisc add dev eth0 root netem delay 3000ms"
    - id: packet_loss
      cmd: "tc qdisc add dev eth0 root netem loss 10%"

  flow:
    - id: step_health_a
      run:
        scenario: health_check_a
      on_success: step_health_b

    - id: step_health_b
      run:
        scenario: health_check_b
      on_success: step_parallel

    - id: step_parallel
      parallel:
        - id: branch_a
          sequence:
            - run:
                scenario: login
            - id: loop_network
              loop:
                times: 3
                sequence:
                  - run:
                      scenario: check_network
                  - condition:
                      if: "${last_step.output.contains('0% loss')}"
                      break: true
            - run:
                scenario: browse_product
        - id: branch_b
          sequence:
            - inject_faults:
                - net_delay_3s
                - packet_loss
            - run:
                scenario: create_order
                retry:
                  times: 2
              on_failure: continue
            - run:
                scenario: payment
              on_failure: continue
      wait: all
      on_success: step_condition

    - id: step_condition
      condition:
        if: "${step_parallel.all_passed}"
        then:
          - run:
              scenario: full_link_load
```

### 11.3 逐维度对比

| 维度 | Workflow 方案 | 原始方案 |
|------|:------------:|:-------:|
| 代码行数（同等场景） | 73 | 79 |
| 最大嵌套深度 | 5 层 | 5 层 |
| 并行语义表达 | `needs` 隐式：多个 job 依赖同一 job 自动并行 | `parallel` 显式：必须手动把分支包裹进 `parallel` 节点 |
| 故障生命周期显式度 | 高。`inject` / `run` / `cleanup` 三步独立可见，符合混沌工程实践 | 低。`inject_faults` 作为 `run` 属性，引擎内部隐式管理回收 |
| 阅读方式 | 线性。从上到下读 job，`needs` 向上看依赖即可理解全貌 | 跳读。必须跟踪 `on_success` / `on_failure` 链才能梳理执行顺序 |
| 局部修改影响面 | 小。新增 job 只需声明 `needs`，不影响已有 job | 中。在并行组中插入或删除步骤，需调整 `on_success` 指向和 `parallel` 内部结构 |
| 场景/故障复用 | ✓ 声明层复用 | ✓ 声明层复用 |
| CI/CD 社区熟悉度 | 高（GitHub Actions / GitLab CI 风格） | 低（无对标，需学习） |
| AI 生成难度 | 略低。`needs` 是单向依赖边，LLM 无需维护跳转链的连续性 | 略高。LLM 需保证 `on_success` 链无断点和死节点 |
| 方案选型 | **推荐** | 备选 |
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
