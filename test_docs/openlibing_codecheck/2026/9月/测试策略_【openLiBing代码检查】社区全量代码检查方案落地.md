# 【openLiBing代码检查】社区全量代码检查方案落地 测试策略设计说明书

## 1. 基本信息

- **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2109899413
- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/190
- **需求名称**: 【openLiBing代码检查】社区全量代码检查方案落地
- **核心目标**:
  将社区全量代码检查所依赖的各款代码检查工具（gitleaks、eslint、clippy、spotbugs、gosec、bandit、clangtidy、codearts-check 等）工作流插件的检查报告，统一转换为 **SARIF 2.1.0** 格式；
  由通用上传插件 `openlibing-upload-sarif` 统一完成 OBS 上传（`{toolName}-results` 动态前缀）并经 APIG 回调 OpenLibing 接口 `/action-api/codescan/v1/result/receive`，触发后端报告解析入库，最终在代码检查页面统一展示各工具检查结果。
- **开发责任人**: taohuoquan
- **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

- [x] **功能自检测试**

> - **测试重点:** 各工具插件报告转 SARIF 的统一性（工具名 / 规则 / 级别 / 位置 / 代码片段）、上传插件 OBS 路径与动态前缀、`region.snippet` 自动补齐、APIG 回调 payload、codecheck 解析入库与页面展示、`build-result.json` 构建产物、多工具同仓共存、零告警空报告场景。
> - **目的:** 确保各工具检查报告格式统一、上传与回调链路完整、解析结果在页面正确呈现。
> - **触发条件:** 强制执行。

- [x] **体验测试**

> - **测试重点:** 代码检查页面多工具结果的可辨识性（工具 / 类别归属标识）、告警详情代码片段的可读性。
> - **目的:** 确保多工具结果汇入后用户仍可快速区分来源并定位问题。
> - **触发条件:** 强制执行。

- [x] **集成测试**

> - **测试重点:** 单工具端到端链路、8 款工具全量端到端链路、插件与 `openlibing-codecheck` 后端 SARIF 解析契约。
> - **目的:** 消除「扫描插件 → 上传插件 → APIG → OBS → codecheck 解析」多系统集成的级联风险。
> - **触发条件:** 强制执行。

- [x] **安全与隐私测试**

> - **测试重点:** OIDC 免密与零静态凭证、日志与输出脱敏、OBS 对象权限边界。
> - **目的:** 确保全链路无静态凭证依赖、不泄露敏感信息、上传对象不越界暴露源码。
> - **触发条件:** 强制执行（凭证与外部上传必选）。

- [x] **可靠性与韧性测试**

> - **测试重点:** OBS 上传与 APIG 回调的指数退避重试、回调失败降级、异常输入（路径缺失 / 无 SARIF / 空目录）处理。
> - **目的:** 确保网络抖动与异常输入下不丢数据、不误判成功 / 失败。
> - **触发条件:** 强制执行。

- [ ] **可服务性与可观测性测试**

- [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.各工具插件报告转 SARIF 格式统一性验证**:

- 前置条件: 各工具对应的工作流插件已发布，示例仓库已接入对应扫描插件
- 测试步骤:
  1. 依次触发 gitleaks、eslint、clippy、spotbugs、gosec、bandit、clangtidy、codearts-check 插件运行
  2. 收集各插件产出的 SARIF 文件，检查 `$schema` / `version`（2.1.0）
  3. 检查 `runs[0].tool.driver.name`、`results[].ruleId` / `level` / `message.text`
  4. 检查 `results[].locations[].physicalLocation.artifactLocation.uri` + `region.startLine`，以及 `region.snippet.text`
- 预期结果: 各工具报告均转换为合法 SARIF 2.1.0；工具名、规则 ID、级别、文件位置与代码片段字段完整且语义正确，后端无需按工具做差异化解析

**2.上传插件 OBS 路径与前缀验证**:

- 测试步骤:
  1. 运行 `openlibing-upload-sarif` 上传各工具 SARIF，检查对象路径
  2. 检查前缀是否按 `{toolName}-results` 动态拼装（工具名转小写、非法字符替换为 `-`）
  3. 构造工具名缺失的 SARIF，检查兜底前缀
- 预期结果: 路径为 `{前缀}/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/{文件名}`；前缀按工具名动态生成，缺失时兜底 `code-arts-check-results`；`runId` 缺失时用 `manual`

**3.region.snippet 自动补齐验证**:

- 测试步骤:
  1. 使用缺少 `region.snippet` 的 SARIF（如 SpotBugs 原生输出）触发上传
  2. 配置 `source_path`，检查是否按 `uri` + 行号读源码补齐并写回
  3. 使用已含 snippet 的 SARIF，检查是否跳过补齐
  4. 构造源码不可读场景（文件被删除 / 路径错误）
- 预期结果: 缺 snippet 的 result 被正确补齐（`startLine`~`endLine` 切分）；已有 snippet 跳过；源码不可读时静默跳过，不阻断上传

**4.APIG 回调 payload 验证**:

- 测试步骤:
  1. 触发上传插件，抓取回调请求
  2. 检查鉴权（V11-HMAC-SHA256 签名 + `X-Security-Token`）与回调地址（prod / beta `env_type`）
  3. 核对 payload 字段：repoUrl / pipelineId / pipelineName / pipelineRunId / branch / commitId / obsUrl（数组）/ category / source / sourceRunUrl
- 预期结果: 回调经签名鉴权成功；`obsUrl` 恒为数组；`source` 为 `GITCODE_ACTION`；HTTP 2xx 且 `code === 200 || code === 0` 判定为成功

**5.codecheck 解析入库与页面展示验证**:

- 前置条件: 各工具 SARIF 已上传并回调成功
- 测试步骤:
  1. 在代码检查页面按仓库查询最新检查结果
  2. 核对告警条目数、文件路径、行号、规则、严重级别、代码片段
  3. 检查各工具结果是否均能归属到对应检查类别
- 预期结果: 回调触发解析后数据入库，页面按工具 / 类别正确展示，告警字段与 SARIF 内容一致

**6.build-result.json 构建产物验证**:

- 测试步骤:
  1. 单文件上传，检查 `buildings` 形态与 `type`
  2. 多文件（目录 / 逗号多值）上传，检查 `buildings` 形态
  3. 检查构建产物所在 OBS 路径与 SARIF 是否一致
- 预期结果: 单文件 `buildings` 为对象、多文件为数组；`type` 为 `{toolName}代码检查结果（sarif）`；与 SARIF 同路径（首个工具目录前缀）

**7.多工具同一仓库共存验证**:

- 测试步骤: 在同一仓库同时接入多款工具插件并触发，检查 OBS 对象与页面展示
- 预期结果: 各工具 SARIF 分别落到各自 `{toolName}-results` 前缀，互不覆盖；页面可同时展示多个工具的检查结果

**8.零告警 / 空报告场景验证**:

- 测试步骤: 使用无任何告警的代码触发工具扫描，检查 SARIF 内容、上传与回调、页面展示
- 预期结果: 空 `results` 的 SARIF 正常上传并回调成功，解析后页面展示为无告警，不报错、不产生脏数据

### 3.2 体验测试专项

**1.页面多工具结果可辨识性验证**:

- 测试步骤: 在同一仓库下查看多工具扫描结果，检查来源 / 类别标识
- 预期结果: 各工具结果可明确区分（工具 / 类别标识清晰），不会混淆归属

**2.告警详情可读性验证**:

- 测试步骤: 打开若干告警详情，检查代码片段与位置信息展示
- 预期结果: 有 snippet 时展示对应源码片段，缺失时降级展示位置信息且不报错

### 3.3 集成测试专项

**1.单工具端到端链路验证**:

- 测试步骤: 触发某工具插件扫描 → 报告转 SARIF → 上传插件上传 OBS → APIG 回调 → codecheck 解析 → 页面展示
- 预期结果: 全链路打通，各环节数据一致，页面正确展示该工具检查结果

**2.8 款工具全量端到端验证**:

- 测试步骤: 依次对 gitleaks、eslint、clippy、spotbugs、gosec、bandit、clangtidy、codearts-check 执行单工具端到端链路
- 预期结果: 8 款工具均能端到端跑通并在代码检查页面统一展示，无工具被遗漏

**3.插件与 codecheck 后端契约验证**:

- 测试步骤: 对比各工具上传的 SARIF 版本与回调 payload 结构，检查后端是否按既有解析路由处理
- 预期结果: 统一为 SARIF 2.1.0 + `obsUrl` 数组 + 既有回调字段，`openlibing-codecheck` 解析路由无需按工具改造

### 3.4 安全与隐私测试专项

**1.OIDC 免密与零静态凭证验证**:

- 测试步骤:
  1. 检查各插件 workflow 仅声明 `permissions: id-token: write`，无 AK/SK 输入项
  2. 检查插件运行日志与产物，确认无静态凭证明文
- 预期结果: 全链路零静态凭证，OIDC 临时凭证仅存在于内存

**2.日志与输出脱敏验证**:

- 测试步骤: 检查插件日志中的 IP、凭证与回调响应输出
- 预期结果: IP 脱敏为 `[IP_ADDRESS]`；临时凭证不打印、不落盘、不进日志；失败日志不包含敏感参数

**3.上传对象权限边界验证**:

- 测试步骤: 检查 OBS 对象 ACL 与内容
- 预期结果: 对象为 `public-read` 仅暴露 SARIF 分析结果（非源码），由桶策略控制边界

### 3.5 可靠性与韧性测试专项

**1.OBS 上传与回调重试验证**:

- 测试步骤: 注入网络抖动 / 短暂失败，观察 OBS 上传与 APIG 回调的重试行为
- 预期结果: 上传（同步）与回调（异步）均按指数退避重试（默认 3 次，`2^(n-1)` 退避），抖动恢复后可成功

**2.回调失败降级验证**:

- 测试步骤: 使 APIG 回调持续失败，观察插件最终结果与日志
- 预期结果: 回调失败仅输出 WARN，SARIF 已上传成功时整体 `result=success`，不误判失败

**3.异常输入处理验证**:

- 测试步骤:
  1. `sarif_file` 指向不存在的路径
  2. 传入空目录（无 `.sarif` 文件）
  3. 最终未收集到任何 SARIF 文件
  4. 使 `build-result.json` 上传失败
- 预期结果: 路径不存在或最终无 SARIF 文件时 `result=failed` 退出；单个目录为空仅告警；构建产物上传失败仅 WARN 不阻断

---

## 4. 补充说明

1. 本测试策略对应 issue https://gitcode.com/openlibing/openlibing-codecheck/issues/190 ，涉及范围：通用上传插件 `openlibing-upload-sarif`（仓 `upload-sarif-action`）、gitleaks / eslint / clippy / spotbugs / gosec / bandit / clangtidy / codearts-check 各工作流插件、后端 `openlibing-codecheck`（SARIF 解析入库）；发布记录见 `release_20260923_iter2`（#190 评审结果：通过）。
