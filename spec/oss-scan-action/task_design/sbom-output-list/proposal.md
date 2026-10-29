# sbom-output-list — 开源软件清单输出

## 需求背景

OSS 扫描门禁插件（openlibing/trivy-action）当前只输出漏洞与 license 门禁结论，无法向客户展示"该项目使用了哪些开源组件、对应版本"。客户实际需要的是一份开源软件清单（OSL, Open Source List），而非完整 SBOM 文件。

已确认：trivy fs 的 JSON 结果（`Results[].Packages[]`）已包含组件全量信息（`Name`/`Version`/`Identifier.PURL`/`Relationship`），无需额外 SBOM 生成命令，直接解析现有结果即可。

关联业务 Issue：https://gitcode.com/openlibing/trivy-action/issues/2

## 功能描述

为 oss-pr-scan-action / oss-version-scan-action 新增开源软件清单输出能力：

1. 新增参数 `sbom-output`：
   - 默认 `null`（不开启）
   - 有效值 `list`：输出开源软件清单
   - 其余任意文本等同 `null`，不开启（为未来 SBOM 等模式预留）

2. 新增参数 `sbom-output-type`（仅 `sbom-output=list` 时生效）：
   - 默认 `table`：markdown 表格形式
   - `code`：代码块形式

3. 输出行为：
   - Step Summary 输出统计（组件总数 + direct/indirect）+ 清单
   - 清单行数 ≥500 时截断，顶部保留前 500 行并提示"完整清单见插件执行日志"
   - 插件日志用 `core.info` 输出全量清单（GitCode job 日志可回放）
   - 组件列格式 `group:artifact`（如 `ch.qos.logback:logback-classic`），按名称排序
   - 组件取值口径：trivy fs `Results[].Packages[]`（pom/lockfile 声明的全部组件，含直接与间接依赖）

## 不做的事

- 不输出完整 CycloneDX/SPDX SBOM（后续可能的 `sbom` 模式预留）
- 不改变现有漏洞门禁判定逻辑
- 不引入 rootfs/jar 内嵌扫描（保持 fs 扫源码定位）
- 不落盘清单文件（GitCode 用户无法查看落盘文件；清单长度可预知，输出到 Summary + 日志即可）

## 验收标准

- [ ] `sbom-output` 默认（null）不输出清单；设为 `list` 时输出
- [ ] `sbom-output-type` 默认 `table` 输出 markdown 表格；`code` 输出代码块
- [ ] 清单含组件总数 + direct/indirect 统计 + `group:artifact` + 版本列
- [ ] 清单行数 ≥500 时 Summary 截断并提示"完整清单见插件执行日志"；日志输出全量
- [ ] action.yml（PR/version）声明两参数；workflow 可传入（默认即可，无需强制传）
- [ ] 已有测试全绿，新增单测覆盖参数解析（null/list/非法值）与清单生成（table/code/截断）

## 影响范围

| 仓              | 文件                                                                 | 操作                             |
| --------------- | -------------------------------------------------------------------- | -------------------------------- |
| oss-scan-action | `shared/index.js`                                                    | 新增参数解析 + 清单生成/输出     |
| oss-scan-action | `oss-pr-scan-action/action.yml`                                      | 新增两输入声明                   |
| oss-scan-action | `oss-version-scan-action/action.yml`                                 | 新增两输入声明                   |
| oss-scan-action | `oss-pr-scan-action/test/*.test.js`                                  | 补单测                           |
| oss-scan-action | `oss-version-scan-action/test/*.test.js`                             | 补单测                           |
| oss-scan-action | `oss-pr-scan-action/README.md` / `oss-version-scan-action/README.md` | 文档说明                         |
| openlibing-docs | `spec/oss-scan-action/task_design/sbom-output-list/`                 | 本 spec（proposal/design/tasks） |
