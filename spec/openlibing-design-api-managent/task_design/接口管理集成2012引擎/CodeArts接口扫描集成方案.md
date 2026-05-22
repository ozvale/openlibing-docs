# openLibing API 扫描流水线集成方案

## 1. 一句话说明

我们在用户现有的 CodeArts/CodeBuild 构建流水线后面增加一个 API 扫描步骤。

用户项目正常完成编译后，流水线执行 openLibing 提供的扫描脚本。脚本会调用 `api-parser` 分析 C/C++ 代码，生成 `result.json` 报告。

在本地验证阶段，`result.json` 可以先作为流水线产物归档；在 PR 门禁闭环阶段，扫描脚本必须把 `result.json` 上传到 `api-management`，否则后续的增删改对比、审批和基线发布无法完成。

第一版不做 PR 评论机器人，所有扫描结果都在流水线产物和平台报告里查看。

当前 api-parser 的集成基线分支是：

```text
feature-xym-improve
```

后续代码集成、验证和文档口径都以 `feature-xym-improve` 为准，不再以 `master` 作为 api-parser 的最新代码基线。

这里要把两个 `master` 概念分开：api-parser 自己的开发集成基线是 `feature-xym-improve`；用户业务仓的接口正式基线第一版统一按 `master` 维护。也就是说，业务 PR 只有目标分支是 `master` 时才进入接口扫描、基线对比、审批和合入发布闭环；目标分支不是 `master` 的 PR 第一版跳过接口检测，避免同一个业务仓维护多套接口基线。

需要特别说明的是，`feature-xym-improve` 已经有一套 C/C++ 解析增强能力，包括基于 `libclang` 的 `clang_parser.py` 和独立的 C/C++ 签名生成模块 `signature.py`。本次方案不是推翻这套能力，而是在它之上新增一条更精确的 C/C++ 解析适配路径：

```text
compile_commands.json + APIInfoGenTool + api_analysis
  -> func_export.json / data_export.json / func_call.json
  -> cpp_clang_adapter.py
  -> openLibing result.json
```

也就是说，第一版正式链路优先消费 APIInfoGenTool 编排后的产物。`func_export.json` 是对齐原有函数级 API 检测能力的核心输入；`data_export.json` 和 `func_call.json` 用于结构体/数据定义和调用关系增强。直接读取 `elements.txt` 的能力保留为本地调试或兜底能力；如果执行条件不满足，api-parser 仍然可以保留 `feature-xym-improve` 已有的解析链路作为本地调试或兜底能力。

## 2. 为什么要放在构建之后

C/C++ 项目和 Python/Java 不一样。很多接口是否能被准确识别，取决于项目真实编译时使用了哪些头文件、宏定义、include 路径和编译参数。

这些信息不能靠扫描工具凭空猜出来，必须来自用户项目自己的构建过程。

所以我们的集成原则是：

```text
用户负责真实构建，产出 compile_commands.json
openLibing 负责读取 compile_commands.json，完成 API 扫描
```

`compile_commands.json` 可以理解为 C/C++ 项目的“编译说明书”。有了它，`api-parser` 才知道每个源码文件应该按什么参数解析。

## 3. 整体流程

```text
1. 用户拉取业务代码
2. 用户执行原有构建
3. 构建阶段产出 compile_commands.json
4. 流水线执行 openLibing 扫描脚本
5. 扫描脚本准备 Python 环境
6. 扫描脚本下载或使用 api-parser
7. APIInfoGenTool 调用 api_analysis 全量分析 C/C++ 接口
8. APIInfoGenTool 产出核心产物 func_export.json，并尽量产出 data_export.json、func_call.json
9. api-parser 读取 APIInfoGenTool 产物并转换成全量 result.json
10. 扫描脚本上传 result.json 到 api-management
11. api-management 保存 PR 全量扫描快照
12. api-management 按扫描路径配置过滤 PR 快照和 master 基线，再做增删改对比
13. 流水线归档 result.json 和扫描报告
```

示意：

```text
业务仓库
  -> CodeBuild 构建
  -> compile_commands.json
  -> openlibing_scan.sh
  -> api-parser
  -> result.json
  -> api-management
  -> PR 扫描快照 / master 基线对比 / 接口评审 / 基线发布
```

## 4. 用户需要做什么

用户主要只需要在原有构建脚本里打开 CMake 的编译数据库开关。

如果用户项目是 CMake 项目，推荐写法是：

```bash
cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build -j"$(nproc)"
```

这样构建完成后会生成：

```text
build/compile_commands.json
```

然后在流水线里增加 openLibing 扫描步骤：

```bash
bash openlibing_scan.sh \
  --source "$PWD" \
  --compile-commands "$PWD/build/compile_commands.json" \
  --output "$PWD/openlibing-result.json" \
  --upload
```

第一版不建议由脚本根据扫描路径限制实际扫描范围。脚本和 api-parser 负责全量扫描当前 workspace，扫描路径配置由 `api-management` 在基线对比和门禁评审阶段使用。

`API_INFO_OUTPUT_DIR` 不由用户填写，它是扫描脚本内部创建的临时目录。脚本会先基于源码和 `compile_commands.json` 调用 APIInfoGenTool 全量生成产物，再把这个内部目录传给 api-parser 转换：

```bash
python "$API_INFO_GEN_TOOL_HOME/ops_analyser.py" \
  --target "$OPENLIBING_PROJECT_ID" \
  --out_dir "$API_INFO_OUTPUT_DIR" \
  --cc_dir "$COMPILE_COMMANDS_DIR" \
  --prefix "$SOURCE_DIR" \
  --mode full

python cli.py scan \
  --source "$SOURCE_DIR" \
  --output "$OUTPUT_JSON" \
  --languages cpp \
  --compile-commands "$COMPILE_COMMANDS" \
  --api-info-output "$API_INFO_OUTPUT_DIR" \
  --api-analysis "$API_ANALYSIS_BIN" \
  --parser-version "$PARSER_VERSION" \
  --verbose
```

如果用户项目不是 CMake，需要用户用自己的构建系统生成同等作用的 `compile_commands.json`。例如 Makefile 项目可以考虑 `bear`，但第一版我们先把 CMake 场景作为主路径。

## 5. openLibing 提供什么

我们提供三类东西：

1. **api-parser 代码仓**

   公开放到 GitCode，用户流水线可以直接拉取。

2. **openlibing_scan.sh 扫描脚本**

   这是需要交付给用户流水线使用的正式脚本。当前代码仓里已经提供 `scripts/openlibing_scan.sh` 初版，以及用于本地验证的 `scripts/verify_api_doc_integration_wsl.sh`；后续需要继续对齐 api-management 的真实上传接口和门禁响应协议。

   用户只需要在流水线里执行这个脚本。脚本负责：

   - 检查参数。
   - 检查 `compile_commands.json` 是否存在。
   - 创建 Python 虚拟环境。
   - 安装 parser 的 Python 依赖。
   - 调用 APIInfoGenTool + `api_analysis` 做 C/C++ 全量分析。
   - 调用 `api-parser` 转换成 `result.json`。
   - 生成 `result.json`。
   - 上传到 `api-management`。

3. **预编译 api_analysis**

   `api_analysis` 是底层 C/C++ 解析工具。我们建议提前编译好，随 `api-parser` 发布，或者放到 GitCode Release/制品仓里。

   这样用户执行机不需要每次编译 `api_analysis`，扫描脚本只需要准备 Python 环境，调用随仓库交付的 APIInfoGenTool / `api_analysis`，再运行 parser 做格式转换。

### 补充：APIInfoGenTool 的集成边界

api-doc 里的 APIInfoGenTool 是 `api_analysis` 的上层编排工具。它会调用 `api_analysis` 生成 `elements.txt`，再按自己的组件规则继续加工，导出 `func_export.json`、`data_export.json`、`func_call.json` 等文件，并服务于它自己的 API 兼容分析服务。

openLibing 这边会把 APIInfoGenTool 的**最小本地扫描运行集**集成到 api-parser 仓库中，但不集成 APIInfoGenTool 自己的上传包、服务端入库格式或兼容性分析结果。api-parser 最终仍然产出能交给 `api-management` 的统一 `result.json`。所以我们的集成边界是：

```text
集成 APIInfoGenTool 的本地扫描入口和编排逻辑
  -> 随 api-parser 携带 tools/APIInfoGenTool
  -> 随 api-parser 携带预编译 api_analysis
  -> 运行时产出 APIInfoGenTool 本地 JSON
  -> 第一版核心读取 func_export.json
  -> 同步兼容读取 data_export.json、func_call.json
  -> 在 api-parser 中适配成 openLibing 的 result.json
  -> 交给 api-management 入库、对比和审批
```

因此这件事更适合描述为 **APIInfoGenTool 最小运行集成 + 产物适配接入**，而不是“重写 APIInfoGenTool”或“集成 APIInfoGenTool 的整套平台能力”。直接读取 `elements.txt` 的能力可以保留为本地调试或兜底路径，但不作为第一版正式 PR 门禁主路径。

第一版能力边界可以这样理解：

| 输入产物 | 第一版定位 |
| --- | --- |
| `func_export.json` | 核心必需输入。对齐原有函数级 API 检测能力，生成函数/方法接口记录 |
| `data_export.json` | 增强输入。记录 struct、class、enum、typedef、macro 等数据定义；字段级差异和类型依赖链作为后续增强 |
| `func_call.json` | 增强输入。记录调用关系；影响面分析作为后续增强 |

也就是说，第一版不会降低原有能力：只靠 `func_export.json` 就能完成函数级 API 增删改对比；`data_export.json` 和 `func_call.json` 先进入统一结果模型，为后续“结构体字段变化影响哪些 API”预留数据基础。

## 6. api_analysis 是否可以提前编译好

可以。

但需要注意一点：`api_analysis` 不是完全独立的单文件程序，它依赖 LLVM/Clang 运行库。

我们本地验证的版本依赖 LLVM 15。常见依赖包括：

```text
libLLVM-15.so.1
libstdc++.so.6
libz.so.1
libtinfo.so.6
libxml2.so.2
```

所以推荐交付方式是：

```text
api_analysis 二进制 + 运行依赖库 + 启动脚本
```

目录可以设计成：

```text
tools/api_analysis/linux-x86_64-ubuntu22-llvm15/
  api_analysis
  lib/
  README.md
  SHA256SUMS
```

扫描脚本运行时设置：

```bash
export LD_LIBRARY_PATH="$API_ANALYSIS_HOME/lib:$LD_LIBRARY_PATH"
```

这样用户执行机不需要安装完整 LLVM 开发环境，也不需要编译 `api_analysis`。

如果后续我们做官方 CodeArts 镜像，可以直接把 Python、api-parser、api_analysis 和依赖库都放进镜像里，流水线执行速度会更快。

## 7. 扫描脚本做什么，不做什么

### 脚本会做

- 下载或定位 `api-parser`。
- 准备 Python 虚拟环境。
- 安装 Python 依赖。
- 定位预编译好的 `api_analysis`。
- 检查 `compile_commands.json`。
- 执行全量扫描并输出 `result.json`。
- PR 门禁模式上传扫描结果到 `api-management`。

### 脚本不做

- 不修改用户业务代码。
- 不替用户改构建脚本。
- 不猜测 C/C++ 编译参数。
- 不上传源码内容。
- 不在 PR 下评论。

这能保证集成方式比较轻量，也方便用户审计脚本做了什么。

## 8. 上传到 api-management

扫描完成后会得到一个标准 JSON 文件：

```text
openlibing-result.json
```

本地验证阶段，可以先把它作为流水线产物归档。

PR 门禁闭环阶段，脚本必须调用 `api-management` 上传扫描结果：

```bash
curl -X POST "$OPENLIBING_API_URL/api/scans" \
  -H "Authorization: Bearer $OPENLIBING_TOKEN" \
  -F "projectId=$OPENLIBING_PROJECT_ID" \
  -F "repoUrl=$OPENLIBING_REPO_URL" \
  -F "branch=$OPENLIBING_BRANCH" \
  -F "sourceBranch=$OPENLIBING_SOURCE_BRANCH" \
  -F "targetBranch=$OPENLIBING_TARGET_BRANCH" \
  -F "prId=$OPENLIBING_PR_ID" \
  -F "commit=$OPENLIBING_COMMIT" \
  -F "pipelineId=$OPENLIBING_PIPELINE_ID" \
  -F "result=@$OUTPUT_JSON"
```

建议上传接口做幂等处理。比如用下面的信息作为唯一键：

```text
项目 + 仓库 + PR + commit + pipelineId
```

同一轮流水线重复上传时，后端覆盖更新，不重复入库。

PR 场景里，`result.json` 不应该直接覆盖正式接口基线。合理处理方式是：

```text
1. api-management 先按 PR + commit + pipelineId 保存扫描快照
2. 确认 PR 目标分支是 master
3. 查询当前项目启用的扫描路径配置
4. 用扫描路径配置过滤 PR 快照和 master 最近一次结果
5. 只在过滤后的评审范围内生成新增、删除、修改类接口变更
6. 如有接口变更，发起审批并返回审批链接
7. PR 合入 master 后，用 PR 全量快照更新正式基线和接口历史
```

如果是初次扫描，没有历史基线，则把本次扫描结果视为全部新增；PR 合入 master 后，这份结果成为业务仓第一版正式接口基线。

### 8.1 扫描路径配置在第一版中的定位

第一版采用“全量扫描 + 按路径过滤对比”的策略：

```text
api-parser 全量扫描并上传 result.json
api-management 保存全量 PR 快照
api-management 读取 scan-path-config
api-management 用路径配置过滤 PR 快照和 master 基线
api-management 只对过滤后的接口做门禁评审
```

扫描路径配置不再控制“扫不扫”，而是控制“哪些接口进入基线对比和门禁评审”。这样可以避免路径扫描漏扫导致的误删，同时保留用户只关注指定目录/API 层的治理能力。

扫描路径配置统一按 `regex` 口径使用，兼容标准正则和 glob 风格：

| 写法 | 含义 |
| --- | --- |
| `src/.*\.cpp` | 标准正则，支持跨层级匹配 |
| `include/.*\.h` | 标准正则，匹配 include 下头文件 |
| `ci/*.py` | glob 风格，`*` 只匹配当前目录层级 |
| `src/api/.*\.py,src/service/.*\.py` | 保存时由后端按逗号拆成多条 regex 配置 |

后端匹配语义和现有 `PathPatternMatcher` 保持一致：多条配置是 OR 关系；regex 使用部分匹配；glob 风格的 `*`、`?` 会预处理成不跨目录的正则。`prefix`、`multi` 作为历史兼容类型保留，但新方案不再主推。

## 9. 最小执行环境

建议执行机环境：

```text
Ubuntu 22.04 x86_64
Python 3.10+
CMake
业务项目自己的 C/C++ 构建工具链
业务项目自己的依赖，例如 CANN/Ascend SDK
```

如果 `api_analysis` 由我们预编译并带齐运行库，则执行机不需要安装 LLVM 开发包。

用户真正必须保证的是：

```text
业务项目能成功构建，并且能产出 compile_commands.json
```

## 10. 已跑通案例

### 案例一：fmt 公开 C++ 仓库

仓库：

```text
https://gitee.com/mirrors/fmt.git
```

验证流程：

```bash
cmake -S fmt -B fmt/build \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DFMT_TEST=OFF \
  -DFMT_DOC=OFF \
  -DFMT_INSTALL=OFF \
  -DCMAKE_CXX_COMPILER=clang++-15

cmake --build fmt/build -j"$(nproc)"

python "$API_INFO_GEN_TOOL_HOME/ops_analyser.py" \
  --target fmt \
  --out_dir /tmp/openlibing-api-info-output \
  --cc_dir fmt/build \
  --prefix fmt \
  --mode full

python cli.py scan \
  --source fmt \
  --output fmt-openlibing-api.json \
  --languages cpp \
  --compile-commands fmt/build/compile_commands.json \
  --api-info-output /tmp/openlibing-api-info-output \
  --api-analysis /path/to/api_analysis
```

结果：

```text
api_analysis 可执行
fmt 构建成功
compile_commands.json 有效
APIInfoGenTool 可产出 func_export.json 和 func_call.json
data_export.json 在该验证项目中未生成，按空数据处理
api-parser 转换成功
输出 784 条 result.json 记录
记录 parser_engine=api_info_gen_tool
```

这说明对普通 CMake C/C++ 项目，`compile_commands.json + APIInfoGenTool + api-parser` 的主链路已经可以本地跑通。第一版至少依赖 `func_export.json` 完成函数级 API 检测；`data_export.json` 若项目或规则未产出，不阻断函数级扫描。

### 案例二：cann/ops-transformer

仓库：

```bash
git clone -b master https://gitcode.com/cann/ops-transformer.git
```

这里的 `master` 是 `ops-transformer` 业务仓验证时使用的分支，不是 api-parser 的开发基线分支。api-parser 本次集成仍然以 `feature-xym-improve` 为基线。

这个仓库是 CANN/Ascend 项目，对执行环境要求更高。

我们在普通 Ubuntu 22.04 验证机上尝试直接生成 `compile_commands.json`，失败原因是缺 CANN SDK：

```text
/usr/local/Ascend/latest/share/info/runtime/version.info does not exist
Check ops-transformer build dependencies failed
```

继续尝试关闭部分构建选项后，仍然缺 CANN 相关依赖：

```text
Could NOT find dlog
missing: dlog_TRANSFORMER_INCLUDE_DIR
```

我们又抽样测试了前 200 个非测试 C++ 文件：

```text
能被普通 Clang 直接解析：1 个
因为缺 CANN 头文件失败：199 个
```

典型缺失依赖：

```text
register/op_def_registry.h
register/op_impl_registry.h
kernel_operator.h
graph/utils/type_utils.h
```

这个结果说明：

```text
ops-transformer 这种项目必须在带 CANN/Ascend SDK 的真实构建环境里扫描。
普通 Ubuntu 环境不能替代真实构建环境。
```

我们对其中一个不依赖 CANN SDK 的可解析文件做了子集验证：

```text
文件：attention/flash_attn/op_host/fa_split_core_v2.cpp
输出：24 条结果
24 条全部来自 Clang 解析
```

这说明 parser 和 `api_analysis` 本身是可用的，完整扫描的前提是用户流水线环境必须能完成该项目的真实构建并产出 `compile_commands.json`。

## 11. 风险和边界

### 风险一：用户没有产出 compile_commands.json

没有这个文件，C/C++ 精准解析无法保证。

处理方式：

```text
脚本直接提示缺少 compile_commands.json
PR 门禁模式默认失败退出，返回明确错误原因
本地调试模式可以允许降级到 feature-xym-improve 已有解析链路
```

### 风险二：执行机缺业务依赖

比如 CANN 项目需要 CANN/Ascend SDK。没有这些依赖，即使有 parser，也无法完整解析业务代码。

处理方式：

```text
要求扫描步骤运行在用户真实构建环境之后
不要在脱离业务依赖的普通镜像里强行扫描
```

### 风险三：api_analysis 运行依赖

预编译二进制需要匹配运行库。

处理方式：

```text
发布 api_analysis 二进制包时带上运行依赖
或提供官方扫描镜像
```

### 风险四：扫描结果不等于最终业务接口

底层扫描会发现函数、类方法、构造函数等候选符号。哪些算“业务 API”，还需要一层规则过滤。

处理方式：

```text
第一版先产出完整候选结果
第二版增加接口过滤规则，例如只保留 op_api、公开头文件、导出符号等
```

## 12. 推荐落地节奏

### 第一期：先跑通流水线扫描

目标：

```text
用户构建后产出 compile_commands.json
openLibing 脚本生成 result.json
流水线归档 result.json
本地或流水线侧先验证扫描能力闭环
```

交付内容：

```text
基于 feature-xym-improve 的 api-parser 集成分支
api-parser cli.py scan 参数能力
openlibing_scan.sh 正式脚本
api_analysis 预编译包
接入说明文档
```

### 第二期：PR 结果入库和门禁闭环

目标：

```text
脚本上传 result.json
api-management 保存 PR 扫描快照
api-management 只处理目标分支为 master 的 PR
api-management 对比 master 基线
返回增删改摘要、审批链接和门禁结论
```

交付内容：

```text
扫描结果上传接口
PR 扫描快照表或对象存储
幂等上传逻辑
项目、仓库、PR、commit、pipelineId 维度查询
目标分支为 master 的 PR 才生成接口评审
审批发起和扫描报告返回
```

### 第三期：PR 合入发布和平台展示

目标：

```text
PR 合入后更新正式接口基线
更新接口历史
平台展示扫描报告、审批记录和接口变更历史
```

交付内容：

```text
PR merge 事件处理
PR 快照发布逻辑
接口历史更新逻辑
平台查询和展示接口
```

### 第四期：接口识别规则增强

目标：

```text
从“扫描到的函数/方法”中识别真正的业务接口
```

交付内容：

```text
路径规则
命名规则
导出符号规则
public API 过滤规则
项目自定义配置
```

## 13. 结论

这个集成方案是可行的，并且已经用公开 C++ 仓库跑通过。

最关键的设计点是：

```text
api-parser 集成基线是 feature-xym-improve
compile_commands.json 由用户真实构建产出
openLibing 扫描脚本只消费构建结果
api_analysis 预编译交付，用户侧不需要编译
result.json 作为流水线报告和后端入库依据
PR result.json 先保存为扫描快照，合入后再更新正式基线
扫描路径配置只用于 api-management 对比和门禁过滤，不限制 api-parser 全量扫描
```

对普通 CMake 项目，方案可以直接落地。  
对 CANN/Ascend 这类项目，需要在带完整 SDK 的真实构建环境中运行，不能脱离用户构建环境单独扫描。
