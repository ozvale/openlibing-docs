# API 扫描集成需求拆解

## 1. 需求描述优化

在用户 CodeArts / CodeBuild 流水线完成业务构建后，openLibing 提供扫描脚本接入 API 检测步骤。对于 C/C++ 项目，用户构建阶段需产出 `compile_commands.json`，扫描脚本调用 APIInfoGenTool 和 api-parser，将 `func_export.json` 等产物转换为 openLibing 统一 `result.json`，并上传到 api-management。

api-management 保存 PR 扫描快照，与 `master` 基线对比，生成接口变更记录、门禁结论和详情链接。第一版不做 PR 评论机器人，PR 状态评论由用户 webhook / 流水线完成。

第一版核心口径：

```text
func_export.json：核心必需输入，用于函数级 API 增删改检测
data_export.json：增强输入，用于数据定义记录，后续支持结构体字段差异
func_call.json：增强输入，用于调用关系记录，后续支持影响面分析
```

第一版扫描路径口径：

```text
api-parser / 执行机：全量扫描源码、全量生成 result.json、全量上报 api-management。
api-management：保存 PR 全量扫描快照后，读取扫描路径配置，同时过滤 PR 全量快照和 master 全量基线，再做增删改对比和门禁判断。
扫描路径配置：统一推荐 regex，兼容 glob 写法；逗号分隔的多路径由后端拆成多条规则。
```

## 2. FE-US-TASK 拆解

### 2.1 模块归属口径

| 模块 | 负责范围 |
| --- | --- |
| api-parser | 用户执行机上的 `openlibing_scan.sh`、Python 依赖安装、APIInfoGenTool / `api_analysis` 工具定位、C/C++ 扫描、`result.json` 生成、流水线报告输出 |
| api-management | 扫描结果接收接口、PR 扫描快照存储、与 `master` 基线对比、接口变更记录、审批状态、门禁结论、详情页数据 |
| 用户流水线 | 拉业务代码、执行业务构建、产出 `compile_commands.json`、调用 api-parser 提供的扫描脚本、根据脚本退出码决定流水线状态 |

执行机脚本归属 api-parser。用户流水线只负责调用脚本和提供必要参数，不负责理解 APIInfoGenTool 产物目录，也不负责上传流水线本地文件地址。

## FE1：CodeArts 流水线 API 扫描接入（归属模块：api-parser）

[特性背景]

用户希望在现有业务构建流水线后增加 API 扫描步骤，本地和 CodeArts 上都能跑通。

[特性价值]

让 C/C++ API 扫描成为流水线的一部分，避免人工执行，保证 PR 都能产生标准扫描结果。

[特性范围]

提供扫描脚本、参数校验、Python 依赖安装、`api_analysis` 预编译工具定位、阶段日志、退出码和 `result.json` 产物。

[特性验收标准和交付件]

交付 `openlibing_scan.sh` 或等价脚本；支持 `SOURCE_DIR`、`OUTPUT_JSON`、`COMPILE_COMMANDS` 等核心参数；随 api-parser 仓库交付 `requirements.txt` 和预编译 `api_analysis` 工具包；扫描失败返回明确错误码。扫描路径配置不作为第一版执行机必传参数，由 api-management 在基线对比阶段读取。

### US1：流水线执行 API 扫描（归属模块：api-parser）

[需求背景]

作为项目管理员，我需要在现有构建流水线后接入 openLibing 扫描步骤。

[需求价值]

这样 PR 每次构建后都能自动生成接口扫描结果。

[需求详情]

扫描脚本校验源码目录、`compile_commands.json`、APIInfoGenTool、`api_analysis` 是否可用，并负责调用 api-parser 全量生成 `result.json` 后上报 api-management。

[验收标准和交付件]

构建后能执行脚本；缺少关键条件时流水线失败并输出错误原因；成功时生成 `result.json`。

#### TASK1：实现扫描脚本参数校验（归属模块：api-parser）

[任务详情]

校验源码目录、`compile_commands.json`、工具路径、输出路径。扫描路径不作为第一版正式扫描前置条件。

[任务角色]

运维

#### TASK2：实现扫描阶段日志和退出码（归属模块：api-parser）

[任务详情]

按校验、编排、转换、上传、报告几个阶段打印日志，并返回 `0/1`。

[任务角色]

运维

### US2：执行机工具包和 Python 环境准备（归属模块：api-parser）

[需求背景]

用户执行机不应该在每次流水线里重新编译 `api_analysis`，也不应该手工拼装 Python 依赖。

[需求价值]

降低用户接入成本，让扫描脚本在 Ubuntu 22.04 执行机上可以开箱即用地完成 C/C++ 扫描。

[需求详情]

api-parser 仓库需要提供可直接使用的工具包和依赖声明。`api_analysis` 理论上由 openLibing 提前编译好，随 api-parser 开放仓目录发布，例如放在 `tools/api_analysis/linux-x86_64-ubuntu22-llvm15/` 下；APIInfoGenTool 的可调用入口也需要随工具包提供，扫描脚本运行时自动定位 APIInfoGenTool 和 `api_analysis`，并设置必要的运行库路径。`requirements.txt` 需要维护扫描脚本运行所需的 Python 依赖，脚本负责创建或复用 Python 环境并执行 `pip install -r requirements.txt`。

[验收标准和交付件]

api-parser 仓库包含 APIInfoGenTool 调用入口、`api_analysis` 预编译交付目录或等价下载定位规则；`requirements.txt` 覆盖扫描运行依赖；扫描脚本能打印依赖安装、工具定位和版本检查日志；缺少工具入口、二进制或依赖安装失败时返回明确错误码。

#### TASK1：交付预编译 `api_analysis` 二进制（归属模块：api-parser）

[任务详情]

基于目标执行机环境编译 `api_analysis`，第一版按 Ubuntu 22.04 / x86_64 / LLVM 15 作为主交付平台。将二进制和必要运行依赖放入 api-parser 公开仓库目录，例如 `tools/api_analysis/linux-x86_64-ubuntu22-llvm15/`，并提供版本说明、校验信息和脚本查找规则。如果仓库大小受限，再切换为 GitCode Release 或制品仓下载，但扫描脚本的使用方式保持不变。

[任务角色]

后端

#### TASK2：交付 APIInfoGenTool 调用入口（归属模块：api-parser）

[任务详情]

将 APIInfoGenTool 的最小可运行入口纳入 api-parser 工具包，或者在 api-parser 仓库中提供稳定的下载/定位规则。扫描脚本通过该入口调用 `api_analysis` 并生成 `func_export.json`、`data_export.json`、`func_call.json`，不要求用户单独安装 api-doc 仓库。

[任务角色]

后端

#### TASK3：适配 `requirements.txt` 和依赖安装逻辑（归属模块：api-parser）

[任务详情]

梳理 api-parser 运行时依赖和测试依赖，确保 `requirements.txt` 至少覆盖扫描脚本、CLI、JSON 转换和上报接口调用所需依赖。扫描脚本支持使用国内镜像源安装依赖，并在依赖安装失败时输出失败阶段、失败命令和建议处理方式。

[任务角色]

后端

#### TASK4：实现工具链自检（归属模块：api-parser）

[任务详情]

扫描脚本启动后检查 Python 版本、`requirements.txt` 安装结果、APIInfoGenTool、`api_analysis` 可执行权限、`compile_commands.json` 是否存在。所有检查通过后才进入扫描；检查失败直接返回给流水线，避免生成不可靠的扫描结果。

[任务角色]

后端

## FE2：C/C++ APIInfoGenTool 产物转换（归属模块：api-parser）

[特性背景]

APIInfoGenTool 会基于 `api_analysis` 产出 `func_export.json`、`data_export.json`、`func_call.json`。

[特性价值]

复用 api-doc 的 C/C++ 解析能力，同时输出 openLibing 已有系统可消费的 `result.json`。

[特性范围]

第一版核心转换 `func_export.json`；兼容读取 `data_export.json`、`func_call.json`，作为增强字段进入结果。

[特性验收标准和交付件]

扫描脚本能基于源码目录和 `compile_commands.json` 调用 APIInfoGenTool 生成产物；api-parser 能消费脚本内部生成的产物目录并转成 openLibing 格式 JSON；旧能力不被破坏。

### US1：函数级 API 转换（归属模块：api-parser）

[需求背景]

作为平台维护方，我需要把 `func_export.json` 转成 openLibing 的 `result.json`。

[需求价值]

这样可以复用原有接口增删改对比能力。

[需求详情]

映射函数名、参数、返回值、文件路径、可见性、是否定义，并生成 `signature_id`。

[验收标准和交付件]

`func_export.json` 能转换出函数/方法接口记录；参数和返回值正确；`signature_id` 稳定。

#### TASK1：实现 `func_export.json` 转换（归属模块：api-parser）

[任务详情]

在 C/C++ adapter 中读取 `func_export.json`，映射为 openLibing 接口字段。

[任务角色]

后端

#### TASK2：实现 APIInfoGenTool 产物目录的内部流转（归属模块：api-parser）

[任务详情]

扫描脚本根据源码目录和 `compile_commands.json` 创建临时产物目录，调用 APIInfoGenTool 全量生成 `func_export.json` 等文件，再把该目录交给 api-parser 转换。这个目录属于 openLibing 内部执行参数，不要求用户或流水线显式提供。

[任务角色]

后端

### US2：增强产物兼容读取（归属模块：api-parser / api-management）

[需求背景]

作为平台维护方，我希望保留结构体定义和调用关系数据。

[需求价值]

为后续结构体字段变化、类型依赖链和影响面分析做准备。

[需求详情]

`data_export.json` 转为数据定义记录；`func_call.json` 挂到函数记录的 `call_relations`，但第一版不参与门禁判断。

第一版需要明确边界：api-parser 可以在 `result.json` 中保留增强产物信息，但 api-management 当前主表模型主要承载函数级接口数据，`tbl_interfaces` / `tbl_pr_interfaces` 暂不具备完整保存 `data_export.json`、`func_call.json` 扩展信息的字段。因此第一版后端入库和门禁只消费函数/方法级 API 主数据，增强产物不参与增删改校验、不影响流水线通过与否。

[验收标准和交付件]

缺少 `data_export.json` 或 `func_call.json` 不阻断扫描；存在时 api-parser 能写入 `result.json`；api-management 第一版可以忽略这部分扩展数据，不作为审批和门禁依据。若要求后端留存增强产物，需要新增扫描快照表或扩展 JSON 字段作为单独交付。

#### TASK1：兼容 `data_export.json`（归属模块：api-parser）

[任务详情]

转换 struct、class、enum、typedef、macro 等数据定义。

[任务角色]

后端

#### TASK2：兼容 `func_call.json`（归属模块：api-parser）

[任务详情]

读取调用关系并写入函数记录扩展字段。

[任务角色]

后端

#### TASK3：标记 api-management 扩展数据承载边界（归属模块：api-management）

[任务详情]

梳理 api-management 当前 `tbl_interfaces`、`tbl_pr_interfaces` 的字段能力，明确第一版只入库函数级 API 主数据；`data_export.json`、`func_call.json` 作为增强产物暂不参与门禁。后续如需留存完整增强产物，新增 `raw_result_json` / `extension` JSON 字段，或新增扫描快照表保存 PR + commit + pipelineId 对应的原始扫描结果。

[任务角色]

后端

## FE3：PR 扫描结果入库与基线对比（归属模块：api-management）

[特性背景]

PR 扫描结果不能直接覆盖正式基线，需要先作为快照保存。

[特性价值]

支持 PR 级追溯、审批、合入后发布和接口历史管理。

[特性范围]

上传 `result.json`，保存 PR 快照，和 `master` 最新基线对比，生成接口变更记录。

[特性验收标准和交付件]

api-management 能保存 PR + commit + pipelineId 对应的扫描结果；能返回增删改摘要和详情链接。

### US1：保存 PR 扫描快照（归属模块：api-management）

[需求背景]

作为平台维护方，我需要保存每次 PR 扫描的完整结果。

[需求价值]

这样审批、问题追溯和合入发布都有依据。

[需求详情]

以 PR、commit、pipelineId 为维度保存本次扫描快照。扫描脚本优先通过接口直接上传 `result.json` 内容；如果后续接入对象存储，也可以额外保存结果文件地址，但文件地址不是第一版主路径。

[验收标准和交付件]

重复上传可幂等更新；快照可查询；不直接覆盖 `master` 基线。

#### TASK1：新增扫描结果上传接口（归属模块：api-management）

[任务详情]

接收项目、仓库、源分支、目标分支、PR、commit、pipelineId、parserVersion、扫描状态、错误信息和 `result.json` 内容。接口收到后由 api-management 保存快照并触发与 master 基线的对比。

[任务角色]

后端

#### TASK2：设计 PR 扫描快照存储（归属模块：api-management）

[任务详情]

保存扫描任务标识、运行元信息、扫描结果内容、状态和错误信息。扫描任务标识包括项目 ID、仓库地址、源分支、目标分支、PR 编号、commitId、pipelineId；运行元信息包括 parserVersion、扫描语言、扫描模式和触发时间，其中扫描模式第一版固定为 `full`。扫描结果内容优先保存本次上传的全量 `result.json` 原文或解析后的接口列表。结果文件地址仅作为可选字段，用于后续接入对象存储或流水线产物归档。参与门禁的扫描路径配置由 api-management 在对比阶段读取，并记录到接口变更记录或评审详情中。

[任务角色]

后端

### US2：与 master 基线对比（归属模块：api-management）

[需求背景]

作为开发者，我需要知道当前 PR 相比 master 改了哪些 API。

[需求价值]

这样可以在合入前发现接口风险。

[需求详情]

只有目标分支为 `master` 的 PR 执行对比；非 `master` PR 第一版跳过。

[验收标准和交付件]

返回新增、删除、修改、元数据变更、兼容性结论和详情链接。

#### TASK1：实现 PR 与 master 基线对比（归属模块：api-management）

[任务详情]

读取本次 PR 全量扫描快照中的函数/方法级 API 主数据，并查询同一项目 `master` 分支最新已发布全量基线。api-management 再读取项目启用的扫描路径配置，用同一组规则分别过滤 PR 全量快照和 master 全量基线，只对过滤后的接口集合参与对比。

对比规则如下：

1. 以 `file_path + name` 作为接口身份匹配键，用于判断同一个接口是否仍然存在。
2. 对于 PR 中存在、master 基线中不存在的接口，标记为“新增”。
3. 对于 master 基线中存在、PR 中不存在的接口，标记为“删除”。
4. 对于 `file_path + name` 相同但 `signature_id` 不同的接口，标记为“修改”。
5. 对于 `signature_id` 相同但描述、注释等非调用相关字段变化的接口，标记为“元数据变更”。
6. 第一版只把 `func_export.json` 转换出的函数/方法级 API 纳入门禁对比；`data_export.json`、`func_call.json` 只作为增强信息留存或忽略，不参与增删改判断。

扫描路径只作为接口对比前的过滤条件，用来决定哪些接口进入本次 PR 对比，不作为接口变更类型，也不限制 api-parser 实际扫描范围。配置格式统一推荐 `regex`，兼容 glob 写法；逗号分隔的多路径由后端拆分成多条规则，任意一条命中即视为进入对比范围。

对比完成后生成 PR 接口变更记录，记录变更类型、兼容性类型、审批状态、差异摘要和详情页关联信息。兼容性结论由变更类型和签名差异决定：删除接口、返回值类型变化、参数类型变化、参数删除等按非兼容处理；新增接口、仅参数名变化、描述变化等默认按兼容或元数据变更处理。

[任务角色]

后端

#### TASK2：实现非 master PR 跳过策略（归属模块：api-management）

[任务详情]

目标分支非 `master` 时不扫描或不生成接口变更记录。

[任务角色]

后端

### US3：master 基线初始化与 PR 合入后发布（归属模块：api-management）

[需求背景]

PR 扫描结果只是合入前快照，不能自动等同于正式基线。只有 master 分支的正式扫描结果，或者已经合入 master 的 PR 结果，才能更新接口基线。

[需求价值]

保证数据库里始终有一份可作为后续 PR 对比依据的 master 基线，同时保留接口历史，形成“扫描 -> 审批 -> 合入 -> 发布基线”的闭环。

[需求详情]

api-management 需要支持两类场景：

1. 初次接入或 master 首次扫描时，如果当前项目没有可用基线，则将本次 master 扫描得到的函数/方法级 API 全量写入正式基线。
2. PR 合入 master 后，根据 PR 扫描快照和审批结果，将本次 PR 的新增、修改、删除接口发布到正式基线，并记录接口历史。

如果 PR 未合入、审批驳回或目标分支不是 `master`，只保留 PR 扫描快照和审批记录，不更新正式基线。

[验收标准和交付件]

首次 master 扫描能生成项目基线；PR 合入 master 后能按变更类型更新正式接口列表；同一个 PR 合入事件重复推送时具备幂等能力；失败时保留错误信息且不破坏已有基线。

#### TASK1：实现 master 首次基线初始化（归属模块：api-management）

[任务详情]

当项目没有已发布 master 基线时，接收 master 扫描结果并将函数/方法级 API 全量写入 `tbl_interfaces`，状态置为 released 或等价基线状态，同时记录本次扫描快照和版本信息。增强产物不参与第一版基线判断。

[任务角色]

后端

#### TASK2：实现 PR 合入 master 后基线发布（归属模块：api-management）

[任务详情]

监听 PR 合入事件，校验目标分支为 `master`，读取该 PR 最新成功扫描快照和接口变更记录。对新增接口写入正式接口表，对修改接口更新正式接口表，对删除接口从正式基线移除或标记删除，并记录接口历史。审批驳回、未审批通过或无成功扫描快照时不发布基线。

[任务角色]

后端

#### TASK3：实现基线发布幂等和异常保护（归属模块：api-management）

[任务详情]

以项目、PR、commitId、pipelineId 或差异 hash 作为幂等依据，避免重复合入事件造成重复写入。发布过程中如果任一步失败，需要回滚本次基线更新或保持旧基线不变，并记录失败原因供详情页和流水线报告查看。

[任务角色]

后端

## FE4：门禁结论、审批与报告闭环（归属模块：api-management / api-parser）

[特性背景]

接口变更需要给流水线明确结论，并对非兼容变更发起审批。

[特性价值]

减少高风险接口变更直接合入 master 的风险。

[特性范围]

生成门禁状态、审批状态、变更详情链接；非兼容变更阻断，兼容性和元数据变更默认不阻断。

[特性验收标准和交付件]

流水线能根据后端结论成功或失败；非兼容变更未审批或审批驳回时返回失败并保留记录；审批通过后，后续重新触发或重跑扫描时可放行。

### US1：流水线获得门禁结果（归属模块：api-management / api-parser）

[需求背景]

作为开发者，我需要在流水线里看到 API 扫描是否通过。

[需求价值]

这样可以快速判断 PR 是否能继续合入。

[需求详情]

api-management 返回 `gateStatus`、`requiresApproval`、摘要和详情链接。

[验收标准和交付件]

无变更通过；兼容性变更通过但提示；非兼容变更未审批时返回失败并给出审批链接；审批通过后，重新触发或重跑扫描时返回通过。

#### TASK1：实现门禁结论返回（归属模块：api-management）

[任务详情]

返回扫描状态、变更摘要、风险等级、详情链接和退出建议。

[任务角色]

后端

#### TASK2：生成流水线报告（归属模块：api-parser）

[任务详情]

扫描脚本接收 api-management 返回的扫描状态、变更摘要、审批链接和退出建议，输出 `openlibing-scan-report.json` 和日志摘要，并将门禁结论映射为流水线退出码。无变更、兼容性变更或已审批通过时返回 `0`；扫描失败、非兼容变更未审批、审批驳回或后端处理失败时返回非 `0`。第一版不要求扫描脚本长时间阻塞等待人工审批，审批通过后通过重跑流水线或重新触发扫描完成放行。

[任务角色]

运维

### US2：非兼容变更审批（归属模块：api-management）

[需求背景]

作为接口负责人，我需要审批会破坏已有调用方的接口变更。

[需求价值]

这样可以避免高风险 API 变更未经确认进入 master。

[需求详情]

删除接口、修改参数类型、返回值变化等非兼容变更触发审批。

[验收标准和交付件]

审批通过后，后续重新触发或重跑扫描可通过；审批驳回后流水线失败；旧快照和审批记录保留。

#### TASK1：实现接口变更详情页（归属模块：api-management 前端）

[任务详情]

展示新增、删除、修改、元数据变化和审批状态。

[任务角色]

前端

#### TASK2：实现审批状态流转（归属模块：api-management）

[任务详情]

支持 pending、approved、rejected，并绑定 PR、commit、差异 hash。

[任务角色]

后端

## 3. 独立性和可落地性检查

### 3.1 US 独立性检查

| 检查项 | 结论 |
| --- | --- |
| 一个用户 | 每个 US 都面向单一角色：项目管理员、开发者、平台维护方、接口负责人 |
| 完整价值 | 每个 US 都能独立交付价值：接入扫描、转换结果、保存快照、对比基线、生成门禁、完成审批 |
| 不依赖 | US 之间按能力分层，可以独立排期，但最终串成完整闭环 |
| 避免重叠 | 扫描脚本和执行机工具包归 api-parser；结果接收、入库对比、审批门禁归 api-management |

### 3.2 TASK 可落地性检查

| 检查项 | 结论 |
| --- | --- |
| 模块明确 | 每个 TASK 标题已标注归属模块：api-parser、api-management 或 api-management 前端 |
| 实现动作明确 | 每个 TASK 都是具体实现动作：准备执行机工具包、转换 JSON、保存快照、生成对比、返回门禁 |
| 工作量可控 | 单个 TASK 预计不超过 3 天；若超过，需要继续拆成接口、页面、状态流转、测试等子任务 |
| 角色明确 | 每个 TASK 都标明前端、后端或运维 |

## 4. 第一版边界

第一版建议先做到：

```text
1. CodeArts 流水线可执行扫描脚本
2. api-parser 仓库交付 `requirements.txt`、扫描脚本、APIInfoGenTool 调用入口和预编译 `api_analysis` 工具包
3. C/C++ 项目能基于 compile_commands.json 运行 APIInfoGenTool
4. api-parser 至少基于 func_export.json 生成 result.json
5. result.json 内容能上传 api-management 并保存 PR 快照
6. PR 全量快照能按扫描路径配置过滤后和 master 全量基线对比
7. 非兼容变更能返回审批和门禁结论
8. PR 合入 master 后能更新正式基线和接口历史
```

第一版暂不承诺：

```text
1. PR 评论机器人
2. 结构体字段级递归类型依赖链
3. 基于 func_call.json 的完整影响面分析
4. elements.txt 作为正式入库格式
5. 官方 CodeArts 镜像
```

## 5. 一期闭环审查结论

整体闭环成立，前提是一期同时完成 api-parser 和 api-management 两侧改造。

| 流程环节 | 一期要求 | 归属模块 | 闭环状态 |
| --- | --- | --- | --- |
| 用户构建 | 用户流水线完成业务构建，并产出 `compile_commands.json` | 用户流水线 | 已明确 |
| 工具准备 | api-parser 提供扫描脚本、`requirements.txt`、APIInfoGenTool 调用入口和预编译 `api_analysis` | api-parser | 已明确 |
| C/C++ 扫描 | 扫描脚本校验环境，调用 APIInfoGenTool 生成 `func_export.json` 等产物 | api-parser | 已明确 |
| 格式转换 | api-parser 至少基于 `func_export.json` 生成 openLibing `result.json` | api-parser | 已明确 |
| 结果上报 | 扫描脚本将 `result.json` 内容和扫描任务标识上传给 api-management | api-parser / api-management | 已明确 |
| PR 快照 | api-management 以 PR、commitId、pipelineId 保存扫描快照 | api-management | 已明确 |
| 基线对比 | 目标分支为 `master` 的 PR 保存全量快照后，按扫描路径配置过滤 PR 快照和 master 最新基线，生成增删改记录 | api-management | 已明确 |
| 门禁报告 | api-management 返回门禁结论，api-parser 输出流水线报告并返回退出码 | api-management / api-parser | 已明确 |
| 审批处理 | 非兼容变更触发审批；未审批或驳回失败；审批通过后重跑可放行 | api-management / api-parser | 已明确 |
| 合入发布 | PR 合入 master 后发布到正式基线，并记录接口历史 | api-management | 已补齐 |

一期工程可以支撑完整流程：

```text
业务构建 -> compile_commands.json
-> openlibing_scan.sh
-> APIInfoGenTool + api_analysis
-> func_export.json
-> result.json
-> 上传 api-management
-> 保存 PR 快照
-> 按扫描路径配置过滤后对比 master 基线
-> 返回门禁结果和详情链接
-> 流水线 success / fail
-> 审批通过后重跑放行
-> PR 合入 master
-> 更新正式基线和接口历史
```

一期落地时需要重点看住三个工程风险：

1. `api_analysis` 预编译包必须匹配 Ubuntu 22.04 执行机，并带齐运行库或给出明确运行依赖。
2. APIInfoGenTool 调用入口必须随 api-parser 工具包交付，不能要求用户额外安装 api-doc 仓库。
3. api-management 需要新增或明确 PR 扫描快照存储能力，否则 `data_export.json`、`func_call.json` 等增强信息无法完整留存。

## 6. 一期交付顺序建议

一期建议按依赖关系分 6 个交付批次推进。前一批次产物稳定后，再进入后一批次，避免后端对比和门禁依赖一个还不稳定的 `result.json` 格式。

| 顺序 | 交付批次 | 主要内容 | 归属模块 | 验收方式 |
| --- | --- | --- | --- | --- |
| 1 | 工具链和执行机准备 | 交付 `requirements.txt`、`openlibing_scan.sh` 初版、APIInfoGenTool 调用入口、预编译 `api_analysis`，完成工具链自检 | api-parser | 在 Ubuntu 22.04 执行机上能完成依赖安装和工具自检 |
| 2 | C/C++ 本地扫描跑通 | 基于源码和 `compile_commands.json` 调用 APIInfoGenTool 全量产出 `func_export.json`，并转换为 openLibing `result.json` | api-parser | 拉公开 C/C++ 仓库本地验证，`result.json` 字段稳定且旧能力不破坏 |
| 3 | 扫描结果上报和快照 | 新增 api-management 扫描结果上传接口，接收 `result.json` 内容，保存 PR + commitId + pipelineId 快照 | api-management / api-parser | 扫描脚本能上传结果，api-management 能幂等保存并查询快照 |
| 4 | PR 与 master 基线对比 | 基于函数/方法级 API 主数据，按扫描路径配置过滤 PR 全量快照和 master 最新基线，生成新增、删除、修改、元数据变更记录 | api-management | 构造 PR 结果、master 基线和路径配置，能得到正确增删改摘要和详情 |
| 5 | 门禁报告和审批闭环 | api-management 返回门禁结论、审批链接和退出建议；api-parser 输出流水线报告并映射退出码；非兼容变更支持审批状态流转 | api-management / api-parser | 无变更/兼容变更通过；非兼容未审批失败；审批通过后重跑放行 |
| 6 | master 基线发布 | 支持 master 首次基线初始化；PR 合入 master 后按变更记录更新正式基线和接口历史，并保证幂等 | api-management | PR 合入事件能更新正式基线；重复事件不重复写入；失败不破坏旧基线 |

推荐里程碑：

```text
M1：api-parser 本地扫描闭环
    完成批次 1-2，证明 C/C++ 仓库能从 compile_commands.json 得到 result.json。

M2：api-management 接收和对比闭环
    完成批次 3-4，证明 result.json 能入库成 PR 快照，并与 master 基线得到增删改。

M3：流水线门禁和发布闭环
    完成批次 5-6，证明流水线能根据门禁成功/失败，PR 合入后能更新正式基线。
```

如果排期需要压缩，批次 1 和 2 可以并行推进，批次 3 的接口定义也可以提前评审；但批次 4 不建议早于 `result.json` 格式稳定，批次 5 不建议早于变更记录稳定，批次 6 不建议早于审批状态流转稳定。

## 7. 每日任务计划（2026-05-20 至 2026-05-27）

目标：2026-05-27 完成一期主流程联调，达到“本地/流水线可扫描 C/C++ 项目，结果可上报 api-management，能生成 PR 对比、门禁报告，并支持合入 master 后更新基线”的验收状态。

| 日期 | 当日目标 | 主要任务 | 归属模块 | 当日验收点 |
| --- | --- | --- | --- | --- |
| 2026-05-20 | 工具链方案定版，执行机能启动扫描前置流程 | 确认 `api_analysis` 预编译交付目录；确认 APIInfoGenTool 调用入口；梳理 `requirements.txt` 运行依赖；设计 `openlibing_scan.sh` 参数、日志和错误码 | api-parser | Ubuntu 22.04 上能完成 Python 依赖安装规划、工具路径规划和脚本参数设计评审 |
| 2026-05-21 | api-parser 本地扫描主链路跑通 | 实现或补齐扫描脚本初版；调用 APIInfoGenTool 生成 `func_export.json`；api-parser 消费产物目录并生成 `result.json`；补充工具链自检 | api-parser | 使用公开 C/C++ 仓库跑出稳定 `result.json`，缺少 `compile_commands.json` / 工具时能明确失败 |
| 2026-05-22 | 稳定 `result.json` 格式和上传协议 | 固化函数/方法级字段映射；确认增强产物第一版处理边界；定义 api-management 上传接口入参、返回值、错误码；扫描脚本准备 POST 上报逻辑 | api-parser / api-management | `result.json` 样例、上传接口契约、流水线报告格式三者评审通过 |
| 2026-05-23 | PR 快照存储落地 | 新增或调整 api-management 扫描结果上传接口；保存 PR、commitId、pipelineId、parserVersion、扫描状态和结果内容；实现幂等保存策略 | api-management | 重复上传同一 PR 扫描结果不会重复生成脏数据，能按 PR + commitId 查询快照 |
| 2026-05-24 | PR 与 master 基线对比落地 | 实现函数/方法级 API 主数据过滤；按 `file_path + name` 和 `signature_id` 生成新增、删除、修改、元数据变更；输出变更摘要和详情关联信息 | api-management | 构造 PR 快照和 master 基线样例，能得到正确增删改统计 |
| 2026-05-25 | 门禁、审批和流水线报告联调 | api-management 返回 `gateStatus`、`requiresApproval`、详情链接和退出建议；扫描脚本生成 `openlibing-scan-report.json` 并映射退出码；审批状态流转接口联调 | api-management / api-parser | 无变更/兼容变更返回成功；非兼容未审批返回失败和审批链接；审批通过后重跑可放行 |
| 2026-05-26 | master 基线发布和端到端联调 | 实现 master 首次基线初始化；实现 PR 合入 master 后发布基线；处理新增、修改、删除接口入正式表；补齐幂等和异常保护 | api-management | PR 合入 master 后能更新正式基线；重复合入事件不重复写入；失败不破坏旧基线 |
| 2026-05-27 | 一期验收和收口 | 端到端跑通完整流程；补齐测试用例和验收记录；整理已知风险、遗留事项和二期范围；更新文档和演示材料 | api-parser / api-management | 完成一条公开 C/C++ 仓库验证链路和一条模拟 PR 链路，输出验收报告 |

### 7.1 2026-05-20 完成记录

5/20 的目标是把执行机工具链方案先定住，并让扫描前置流程可以被流水线脚本启动。当天完成内容如下：

| 项目 | 完成结果 | 产物 |
| --- | --- | --- |
| 扫描脚本入口 | 新增 `scripts/openlibing_scan.sh`，作为 CodeArts / 本地执行机的统一入口。脚本负责参数校验、工具发现、Python 环境准备、APIInfoGenTool 调用、api-parser 调用、报告生成和可选上报。 | `scripts/openlibing_scan.sh` |
| `api_analysis` 预编译交付目录 | 约定第一版内置目录为 `tools/api_analysis/linux-x86_64-ubuntu22-llvm15/`。执行机优先从该目录查找 `api_analysis`，显式参数或 `PATH` 仅作为兜底。如果目录下存在 `lib/`，脚本会自动加入 `LD_LIBRARY_PATH`。 | `tools/api_analysis/linux-x86_64-ubuntu22-llvm15/README.md` |
| APIInfoGenTool 调用入口 | 第一版内置目录为 `tools/APIInfoGenTool/`，已集成 `ops_analyser.py`、`requirements.txt`、`app/analysis` 和 `app/config`，不要求用户执行机额外拉取 api-doc 仓库。 | `tools/APIInfoGenTool/README.md` |
| Python 依赖 | `requirements.txt` 增加 `requests>=2.31.0`，用于扫描脚本后续向 api-management 上报。脚本默认使用阿里云 PyPI 源安装 parser 依赖，并在 APIInfoGenTool 目录存在 `requirements.txt` 时同步安装。 | `requirements.txt` |
| 脚本参数 | 明确必填参数为 `--source`、`--compile-commands`、`--output`；常用参数包括 `--exclude`、`--languages`、`--api-management-url`、`--project-id`、`--repo-url`、`--source-branch`、`--target-branch`、`--pr-id`、`--commit-id`、`--pipeline-id`；工具参数包括 `--api-info-tool-home`、`--api-analysis-bin`、`--work-dir`、`--venv-dir`、`--pip-index-url`、`--dry-run`、`--skip-install`、`--verbose`。`--scan-paths` 保留为本地调试/兼容参数，但第一版正式集成不依赖该参数。 | `scripts/openlibing_scan.sh --help` |
| 日志和错误码 | 脚本按阶段打印 `Start`、`Check C/C++ toolchain`、`Prepare Python environment`、`Run APIInfoGenTool`、`Run api-parser`、`Upload result to api-management`。失败时输出错误码，并生成 `openlibing-scan-report.json`。 | `scripts/openlibing_scan.sh` |
| 扫描路径兼容参数 | 如果本地调试或旧流水线显式传入 `--scan-paths`，脚本会打印忽略提示，但不会校验路径、不会生成 `scan_file_list.txt`、不会限制 APIInfoGenTool 和 api-parser 的扫描范围。正式 PR 集成按全量扫描上报，扫描路径配置由 api-management 在对比阶段读取。 | `scripts/openlibing_scan.sh` |

脚本错误码第一版约定如下：

| 退出码 | 含义 |
| --- | --- |
| 0 | 执行成功 |
| 10 | 参数错误 |
| 11 | 源码目录不存在 |
| 12 | 输出路径不可用 |
| 13 | `compile_commands.json` 不存在 |
| 14 | Python 不存在 |
| 15 | Python 依赖安装失败 |
| 16 | APIInfoGenTool 不存在 |
| 17 | `api_analysis` 不存在或不可执行 |
| 18 | APIInfoGenTool 执行失败 |
| 19 | api-parser 执行失败 |
| 20 | 上传 api-management 失败 |
| 21 | 预留给历史扫描路径校验错误；第一版正式全量扫描链路不使用 |

5/20 已完成的本地验证：

```text
bash -n scripts/openlibing_scan.sh
结果：通过

wsl bash -n /mnt/c/Users/lizelin/Desktop/openLibing/openlibing-api-parser/scripts/openlibing_scan.sh
结果：通过

wsl bash scripts/openlibing_scan.sh --dry-run --skip-install
验证源码：.verify-api-parser/fmt-20260518195405/fmt
验证编译数据库：fmt/build/compile_commands.json
识别到 APIInfoGenTool：tools/APIInfoGenTool
识别到 api_analysis：tools/api_analysis/linux-x86_64-ubuntu22-llvm15/api_analysis
结果：dry-run passed

wsl bash scripts/openlibing_scan.sh --scan-paths include --dry-run --skip-install
验证内容：本地调试兼容参数校验
结果：打印 scan-paths 被忽略的提示，并 dry-run passed

wsl bash scripts/openlibing_scan.sh
验证内容：使用 api-parser 仓库内置 tools/APIInfoGenTool 和 tools/api_analysis 完整扫描 fmt 仓库
结果：成功产出 result.json，共 784 条接口记录
```

5/21 的输入已经具备：扫描脚本入口、工具查找约定、依赖安装策略和前置校验已经落地；下一步需要用公开 C/C++ 仓库做非 dry-run 的完整扫描，确认 APIInfoGenTool 产出 `func_export.json`，并由 api-parser 生成稳定的 `result.json`。

### 7.2 2026-05-21 完成记录

5/21 的目标是跑通 api-parser 本地扫描主链路，并验证“执行机全量扫描、扫描路径由 api-management 对比阶段消费”的最新口径。当天完成内容如下：

| 项目 | 完成结果 | 产物 |
| --- | --- | --- |
| 公开 C/C++ 仓库验证 | 拉取公开仓库 `fmtlib/fmt`，本地验证目录为 `.verify-api-parser/2026-05-21/fmt`，仓库提交为 `2f18a88`。 | `https://github.com/fmtlib/fmt.git` |
| 构建与编译数据库 | 使用 CMake 执行 `cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DFMT_DOC=OFF -DFMT_TEST=OFF`，并执行 `cmake --build build -j2`。构建通过，产出 `build/compile_commands.json`。 | `.verify-api-parser/2026-05-21/fmt/build/compile_commands.json` |
| APIInfoGenTool 产物 | 使用 `scripts/openlibing_scan.sh` 调用内置 APIInfoGenTool 和预编译 `api_analysis`，成功产出 `func_export.json`、`func_export_by_dir.json`、`func_call.json`、`elements.txt`。本次仓库未产出 `data_export.json`，不阻断函数级扫描。 | `.verify-api-parser/2026-05-21/.openlibing-scan/api-info-output/` |
| api-parser 转换 | api-parser 成功消费 APIInfoGenTool 产物目录，生成 openLibing 统一 `result.json`。 | `.verify-api-parser/2026-05-21/openlibing-result.json` |
| 全量扫描结果 | `result.json` 共 784 条接口记录，其中 C 30 条、C++ 754 条；`parser_engine` 全部为 `api_info_gen_tool`，`parser_source` 全部为 `func_export.json`。 | `openlibing-result.json` |
| 扫描路径兼容验证 | 传入不存在的 `--scan-paths does-not-exist` 后，脚本未失败、未按路径裁剪扫描，并再次产出 784 条接口记录。证明正式脚本已经按全量扫描口径执行。 | `openlibing-result-ignored-scan-path.json` |
| 依赖环境复用修复 | 修复 `--skip-install` 时未激活已有 venv 的问题。现在如果 `--skip-install` 且 `--venv-dir` 存在，脚本会复用虚拟环境，避免落到系统 Python 导致 `pydantic` 等依赖缺失。 | `scripts/openlibing_scan.sh` |

5/21 验证命令摘要：

```bash
git clone --depth 1 https://github.com/fmtlib/fmt.git .verify-api-parser/2026-05-21/fmt

cmake -S . -B build \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DFMT_DOC=OFF \
  -DFMT_TEST=OFF
cmake --build build -j2

bash scripts/openlibing_scan.sh \
  --source /mnt/c/Users/lizelin/Desktop/openLibing/.verify-api-parser/2026-05-21/fmt \
  --compile-commands /mnt/c/Users/lizelin/Desktop/openLibing/.verify-api-parser/2026-05-21/fmt/build/compile_commands.json \
  --output /mnt/c/Users/lizelin/Desktop/openLibing/.verify-api-parser/2026-05-21/openlibing-result.json \
  --work-dir /mnt/c/Users/lizelin/Desktop/openLibing/.verify-api-parser/2026-05-21/.openlibing-scan \
  --languages cpp \
  --parser-version api-parser-1.1.0-dev-20260521 \
  --verbose
```

5/21 结论：

```text
api-parser 本地 C/C++ 主链路已经跑通：
compile_commands.json
-> APIInfoGenTool + api_analysis
-> func_export.json / func_call.json / elements.txt
-> api-parser result.json

正式执行脚本已经按全量扫描逻辑执行；扫描路径参数只保留兼容提示，不再影响扫描范围。
```

每日推进建议：

```text
上午：确认前一天遗留问题和当天验收点
下午：完成编码/联调/验证
晚上前：沉淀当天结果、阻塞点和第二天输入
```

关键依赖关系：

1. 2026-05-22 前必须稳定 `result.json` 主字段，否则 2026-05-23 的快照存储和 2026-05-24 的对比逻辑会返工。
2. 2026-05-24 前必须明确 master 基线取数口径，否则门禁结论无法可信。
3. 2026-05-25 前必须确定审批状态对流水线退出码的影响，否则 2026-05-27 验收时很难闭环。

### 7.3 2026-05-22 完成记录

5/22 的目标是稳定 `result.json` 格式和上传协议，并在 api-management 主分支 `gamma-new-tag` 基础上拉出联调分支。当天完成内容如下：

| 项目 | 完成结果 | 产物 |
| --- | --- | --- |
| api-management 分支 | 从 `gamma-new-tag` 新建分支 `feature/api-parser-upload-contract-0522`，用于承接上传协议、快照和基线对比后续开发。 | `openlibing-design-api-management` |
| 上传接口契约 | 固化 `POST /interface/scan/result/upload`，请求体直接携带 `resultJson` 原文，不传执行机本地文件地址。 | `openspec/API扫描结果上传协议.md` |
| 请求上下文 | 明确上传字段包括 `openlibingProjectId`、`projectId`、`repoUrl` / `repositoryUrl`、源/目标分支、PR、commit、pipelineId、parserVersion、languages、scanMode、status、resultJson。 | 上传协议文档和样例 |
| 返回值契约 | 明确返回 `gateStatus`、`approvalStatus`、`requiresApproval`、`pipelineConclusion`、详情链接、审批链接和增删改摘要。 | `ScanResultUploadResponseBo` |
| 错误码 | 明确 `INVALID_REQUEST`、`INVALID_RESULT_JSON`、`BASELINE_NOT_READY`、`APPROVAL_REQUIRED`、`APPROVAL_REJECTED` 等后续联调错误码。 | 上传协议文档 |
| api-management 接口骨架 | 新增上传 Controller 和 BO，只做协议接收、基础校验和 accepted 响应；PR 快照、master 基线对比、审批创建留给 5/23 以后。 | `ScanResultUploadController` 等 |
| api-parser 上传字段 | 扫描脚本补充 `--openlibing-project-id` 参数，并同时上传 `openlibingProjectId`、`projectId`、`repoUrl`、`repositoryUrl`，兼容现有脚本参数和后端字段。 | `scripts/openlibing_scan.sh` |

5/22 验证结果：

```text
wsl bash -n scripts/openlibing_scan.sh
结果：通过

mvn -q -DskipTests compile
结果：api-management 编译通过
```

5/22 结论：

```text
第三天的契约已落地到文档和轻量接口骨架：
api-parser 仍然负责全量扫描、生成 result.json、上传结果；
api-management 接收 result.json 后，后续会按 PR + commit + pipelineId 保存快照，并与 master 基线对比。
```

### 7.4 2026-05-23 完成记录

5/23 的目标是让 api-management 能保存 PR 扫描快照，并具备幂等查询能力。当天完成内容如下：

| 项目 | 完成结果 | 产物 |
| --- | --- | --- |
| 快照表设计 | 新增 `tbl_scan_result_snapshots` 和 `tbl_scan_result_snapshot_items`，快照表保存项目、仓库、分支、PR、commit、pipelineId、parserVersion、languages、scanMode、status、错误信息、报告原文、结果 hash 和门禁摘要；明细表逐条保存 `resultJson` 接口记录。 | `db/changelog/db.changelog.xml` |
| 快照实体和仓库 | 新增 `ScanResultSnapshotDo`、`ScanResultSnapshotItemDo`、`ScanResultSnapshotRepository` 和 `ScanResultSnapshotItemRepository`，支持按幂等 hash、`snapshotId`、PR + commit + pipelineId 查询。 | api-management |
| 上传保存逻辑 | `POST /interface/scan/result/upload` 不再只返回 accepted，而是会保存本次上传的接口明细和流水线报告。 | `ScanResultSnapshotServiceImpl` |
| 幂等策略 | 幂等键为 `openlibingProjectId + repoUrl + prId + commitId + pipelineId`。重复上传相同内容返回原 `snapshotId`；同一幂等键但内容不同返回 409 业务错误。 | `idempotency_hash` 唯一约束 |
| 快照查询接口 | 新增 `POST /interface/scan/result/query-snapshots`，用于按项目、仓库、PR、commit、pipelineId 查询已上传快照。列表查询不返回完整 `resultJson`，避免响应过大。 | `ScanResultUploadController` |
| 契约文档 | 更新上传协议，补充快照保存字段、幂等冲突口径和查询接口。 | `openspec/API扫描结果上传协议.md` |

5/23 验证结果：

```text
mvn -q -DskipTests compile
结果：api-management 编译通过
```

5/23 结论：

```text
PR 扫描结果现在可以先以快照形式进入 api-management：
api-parser 上传 result.json
-> api-management 保存 PR 扫描快照和接口明细
-> 重复上传按幂等键复用原快照
-> 后续 5/24 可基于该快照和 master 基线做对比
```

### 7.5 2026-05-24 完成记录

5/24 的目标是让 api-management 基于 PR 快照和 master 基线生成增删改摘要、PR 接口变更记录和门禁结论。当天完成内容如下：

| 项目 | 完成结果 | 产物 |
| --- | --- | --- |
| master 目标分支判断 | 仅当 `targetBranch=master` 时进入接口对比；非 master 目标分支只保存快照，不生成 PR 接口变更记录。 | `ScanResultSnapshotServiceImpl` |
| 项目和基线读取 | 优先使用上传参数中的 `projectId`；未传时按 `openlibingProjectId + repoUrl + master` 查询项目，再读取已发布 master 基线。 | `ProjectRepository` / `InterfaceRepository` |
| 扫描路径过滤 | 保存全量快照后，读取启用的扫描路径配置，用同一组规则过滤 PR 快照接口和 master 基线接口；配置为空时不过滤。 | `ScanPathConfigRepository` / `PathPatternMatcher` |
| 函数/方法级对比 | 只对 `element_type=func` 或 `type=function/method` 的接口参与对比；按 `file_path + name` 识别同一接口，按 `signature_id` 判断签名变化。 | `ScanResultSnapshotServiceImpl` |
| 变更分类 | PR 有、master 无为“新增”；master 有、PR 无为“删除”；身份相同但 `signature_id` 不同为“修改”；签名未变但描述、返回说明、参数 JSON、行号变化为“元数据变更”。 | `tbl_pr_interfaces` |
| 门禁结论 | 删除和修改计为非兼容变更，返回 `approval_required`、`requiresApproval=true`、`pipelineConclusion=fail`；新增和元数据变更返回 `pass_with_warning`。 | `ScanResultUploadResponseBo` |
| PR 主记录同步 | 上传扫描结果时同步创建或更新 `tbl_prs` 主记录，`tbl_pr_interfaces.pr_id` 使用 `tbl_prs.id`，上传响应里的 `changeRecordId` 也返回该内部 ID。 | `PRRepository` / `tbl_prs` |
| PR 变更记录 | 对比结果写入 `tbl_pr_interfaces`，带 `scanType`、`compatibilityType`、`approvalStatus`、`diff` 和 `inScanPath`。`diff` 保持旧页面口径，使用类似 Git patch 的文本片段，不再写结构化 JSON。 | `PrInterfaceRepository` |
| PR 差异查询 | 主要复用旧接口 `POST /interface/merge/scan-list`，入参 `prId` 使用上传响应的 `changeRecordId`。同时保留轻量查询接口按 `prId` 直接读取 `tbl_pr_interfaces`，用于流水线报告或排查。 | `/interface/merge/scan-list` / `/interface/scan/result/query-pr-diffs` |
| 详情查询 | `query-snapshots` 支持按 `snapshotId` 查询，并补充 GET 形式，保证上传响应里的 `detailUrl` 可以作为详情入口。 | `ScanResultUploadController` |
| 契约同步 | 更新 api-management 上传协议，说明当前已支持 master 基线对比、快照明细表保存和详情链接查询。 | `openspec/API扫描结果上传协议.md` |

5/24 验证结果：

```text
mvn -q -Dtest=ScanResultSnapshotServiceImplTest test
结果：通过，覆盖 PR 快照与 master 基线的新增、删除、修改、元数据变更统计

mvn -q -DskipTests compile
结果：api-management 编译通过

接口联调：
基于项目 `192` 的 MindSpeed 已发布基线构造 PR 快照，得到新增 1、删除 1、修改 1、元数据变更 1；重复上传同一幂等键复用原快照。
```

5/24 结论：

```text
PR result.json -> 保存快照和接口明细
-> targetBranch=master 时读取扫描路径配置和 master 已发布基线
-> 过滤后按 file_path + name / signature_id 生成增删改和元数据变更
-> 写入 tbl_pr_interfaces
-> 返回门禁摘要、详情链接和审批状态
```
