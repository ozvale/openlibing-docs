# 【openlibing】【sbom】机机接口下线切换apig — 归档

## 需求信息

| 项                | 值                                                                |
| ----------------- | ----------------------------------------------------------------- |
| FE 需求名称       | 【openlibing】【sbom】机机接口下线切换apig                        |
| 业务仓            | openlibing/openlibing-sbom                                        |
| 业务 Issue        | https://gitcode.com/openlibing/openlibing-sbom/issues/61          |
| 业务 PR           | https://gitcode.com/openlibing/openlibing-sbom/merge_requests/123 |
| 业务 PR 目标分支  | release_20260813_iter1                                            |
| 业务 PR head 分支 | feat/apig-controller                                              |
| 流程模式          | Standard                                                          |

## 交付物

### 代码变更（业务仓 openlibing-sbom）

| 文件                                                                           | 操作 | 说明                                                                                       |
| ------------------------------------------------------------------------------ | ---- | ------------------------------------------------------------------------------------------ |
| `sbom-web/src/main/java/org/opensourceway/sbom/controller/ApigController.java` | 新增 | 复制 SbomController 中 8 个机机接口方法，路径前缀改为 `/apig-api`，注入 `SbomService` 依赖 |

### 文档变更（openlibing-docs 仓）

| 文件                                                                  | 操作 | 说明                |
| --------------------------------------------------------------------- | ---- | ------------------- |
| `spec/openlibing-sbom/task_design/apig-controller-switch/proposal.md` | 新增 | 需求背景 + 验收标准 |
| `spec/openlibing-sbom/task_design/apig-controller-switch/tasks.md`    | 新增 | 实现任务清单        |
| `spec/openlibing-sbom/task_design/apig-controller-switch/archive.md`  | 新增 | 本归档文件          |

### 业务仓 commit 列表

| commit     | 类型 | 说明                                           |
| ---------- | ---- | ---------------------------------------------- |
| `f30288aa` | feat | add ApigController for apig gateway migration  |
| `95243251` | fix  | fix CORS header and log typo（codecheck 修复） |

## 实现摘要

将 `SbomController` 中 8 个机机接口复制到新建的 `ApigController`（路径前缀 `/apig-api`），用于机机接口从 openlibing 切换至 apig（华为云 APIGW）网关的合规改造。原 `SbomController` 接口保留不变，新旧路径并存。

### 复制的 8 个接口

| #   | HTTP 方法 | 路径                                 | 说明                                    |
| --- | --------- | ------------------------------------ | --------------------------------------- |
| 1   | GET       | `/apig-api/querySbomPublishResult`   | 查询推送结果                            |
| 2   | POST      | `/apig-api/exportSbom`               | 导出 sbom                               |
| 3   | POST      | `/apig-api/querySbomPackageList`     | 查询 packages 列表                      |
| 4   | GET       | `/apig-api/querySbomPackages`        | 查询 package                            |
| 5   | GET       | `/apig-api/queryLicenseUniversalApi` | 查询 license                            |
| 6   | GET       | `/apig-api/queryProductStatistics`   | 查询单个产物总览数据                    |
| 7   | POST      | `/apig-api/addProduct`               | sbom 新增 product（已在 apig 平台配置） |
| 8   | POST      | `/apig-api/exportAllPackageSbom`     | 导出 sbom 的 package                    |

### 范围调整说明

- `publishSbomFile` 接口原计划复制，用户决策移除，不在本次 ApigController 复制范围
- 原 `SbomController` 中的 `publishSbomFile` 接口保留不变

### Codecheck 修复（commit 95243251）

1. **CORS 安全 bug 修复**：原 `SbomController` 代码校验 origin 在白名单内后，仍返回硬编码的 `http://localhost:8080`，导致白名单校验失效。ApigController 中改为返回经过校验的实际 `origin` 值
2. **日志拼写修正**：`query sbom publish resul` → `query sbom publish result`

## 验证结果

| 项                                      | 结果                                               |
| --------------------------------------- | -------------------------------------------------- |
| 编译验证 `mvn compile -pl sbom-web -am` | ✅ BUILD SUCCESS（11 模块全部通过）                |
| IDE 诊断                                | ✅ 0 错误 0 警告                                   |
| 原 SbomController 回归                  | ✅ 一行未改，无回归风险                            |
| 业务 PR Git Hooks                       | ✅ PASSED                                          |
| sbom-dev 分支同步                       | ✅ 已 merge 并 push 到 origin/sbom-dev（08e439c3） |

## 经验沉淀

### 可复用规则（建议沉淀到 ai_memory.md）

1. **ApigController 与 SbomController 并存模式**：机机接口从 openlibing 切换至 apig 网关时，采用新建 Controller（路径前缀 `/apig-api`）+ 原 Controller（`/sbom-api`）并存模式，原接口保留不变，新旧路径并存，后续下线时再删原接口
2. **CORS 响应头必须返回实际 origin**：校验 origin 在白名单内后，响应头 `Access-Control-Allow-Origin` 必须返回经过校验的实际 `origin` 值，不能返回硬编码值，否则白名单校验失效
3. **接口复制不复制范围决策**：`publishSbomFile` 类型的接口如果已经在 apig 平台单独配置，可以不复制到 ApigController，避免重复暴露

### 教训

1. **commit message 必须与实际内容一致**：本次开发中，用户在 commit 前通过 IDE 删除了 `publishSbomFile` 方法，但 AI 基于创建文件时的认知写了"9 个机机接口"的 commit message，导致 message 与实际内容（8 个接口）不一致。后续开发中，commit 前应重新核实文件实际内容，不要基于创建时的认知写 message
2. **gitcode CLI 参数与 AGENTS.md 描述可能不一致**：实际测试发现 `gitcode pr create` 支持 `--body-file` 参数（与 AGENTS.md 描述不一致），且不支持 `--label` 参数。后续遇到 CLI 参数问题时，应先 `gitcode pr create --help` 查询实际可用参数

## AI 参与说明

- 本需求由 AI 协助完成（Trae IDE / GLM-5.2 模型）
- 业务 PR 已添加 `ai-assisted` 标签
- docs PR 同样添加 `ai-assisted` 标签
