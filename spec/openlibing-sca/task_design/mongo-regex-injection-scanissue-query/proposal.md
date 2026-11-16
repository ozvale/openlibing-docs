# mongo-regex-injection-scanissue-query — /open/scan/scanIssue/query 外部参数正则注入修复（#113）

## 需求背景

- Issue：[#113](https://gitcode.com/openlibing/openlibing-sca/issues/113)（closed）
- 来源：master 分支 `8e8fc796` 外部参数校验排查（排查表 `外部参数校验排查.xlsx`），
  高危，CWE-943（NoSQL 注入 / ReDoS）
- 代码位置：`src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`
  - `applyPathAndFileFilters`（issue 引用 L1052-L1067，当前 L1146-L1161）
  - `applyVendorComponentFilters`（issue 引用 L1069-L1082，当前 L1163-L1176）

事实与根因（issue 描述 + 当前代码核实）：

1. `POST /open/scan/scanIssue/query`（`OpenScanController` L187-L197）的 `path`、`fileName`、
   `vendor`、`component` 四个查询参数来自 `@RequestBody ScanIssueQueryVO`，均为用户可控字符串
   （`ScanIssueQueryVO` L28-L33；四个过滤字段无 `@Size` / `@Pattern` 等校验注解，
   仅有 `scanId`、`pageNo`、`pageSize` 的 `@NotNull`）。
2. 调用链：`getScanIssue`（L1307）→ `applyPathAndFileFilters`（调用点 L1324）与
   `applyVendorComponentFilters`（调用点 L1325），四个值直接拼入 MongoDB `$regex`，
   共 5 处拼接点（path 分支 path + fileName、仅 fileName 分支、vendor、component）。
3. 影响：
   - 正则语法注入：`(?i)`、`.*`、量词等可改变前缀/子串过滤语义，拉取非预期数据；
   - ReDoS：嵌套量词（如 `(.+)+$`）可造成数据库侧灾难性回溯，单请求打满 CPU。
     issue 描述提到"Java `Pattern` 无执行超时"，实际拼接进 MongoDB `$regex` 由数据库侧执行，
     项目侧查询超时配置本轮未验证。
4. 鉴权现状：`getScanIssue` 调用 `checkPermission`（L1045-L1055），`userId` 为空时
   仅对非开源仓返回 4001，开源仓 scanId 可免登录访问。

本目录以 `/open/scan/scanIssue/query` 的**全参数外部输入视角**记录整改；字段级细节见
`mongo-regex-injection-path-filename`（path/fileName）与
`mongo-regex-injection-vendor-component`（vendor/component）；无鉴权机机接口
`/queryAll` 见 `mongo-regex-injection-scanissue-queryall`。

## 功能描述

**做什么**

1. 新增 `OpenScanServiceImpl#escapeRegex`（L1139-L1144），转义
   `\ [ ] { } ( ) * + ? . | ^ $`，null 返回空串。
2. 四个参数、5 处拼接点全部套用转义：
   - path（L1152）、fileName（L1154、L1158）
   - vendor（L1166）、component（L1170）
3. 保持原有查询结构与过滤语义：path 前缀 `^`、子串 `.*?...?` 匹配不变，仅用户值字面量化。
4. 单测 3 个：转义映射、注入被字面量化、正常输入语义不变（以共用 filter 的
   `getScanIssueAll` 为入口，通过 `ArgumentCaptor` 捕获 `$regex` 文本）。

**不做什么**

- 未按 issue 修复建议 1 复用/抽取 `LicenseServiceImpl#escapeRegex` 为公共工具（采用同实现副本，
  见 design D5），也未改用 `Pattern.quote()`。
- 未实现 issue 修复建议 2 的长度上限与字符白名单。
- 不改 `file` 参数（`.in(file)` 精确匹配）与 license/copyright 过滤（`is`/`ne`，非正则）。
- 不改接口契约、鉴权、分页与排序。
- 不做压测与覆盖率复测（本轮未覆盖）。

## 验收标准

- [x] 用户输入中的正则元字符被转义，无法改变查询语义：四个参数 5 处拼接点全部覆盖
      （L1152、L1154、L1158、L1166、L1170）
- [x] 恶意回溯模式（如 `(a+)+$`）以字面量文本进入 `$regex`，不再具有可执行量词结构
      （单测断言 `\(a\+\)\+\$`，并断言原始 `(a+)` 序列不存在）
- [x] 单测通过（提交内新增 3 个用例）；覆盖率达标情况未验证
- [ ] 长度上限与字符白名单校验（issue 修复建议 2，本轮未覆盖）
- [ ] 复用 `LicenseServiceImpl#escapeRegex` 或抽取公共工具类（本轮偏离，采用副本实现）
- [ ] 性能/CPU 压测：恶意模式不再进入正则引擎（实现层保证），但未做运行态压测，未验证
- [ ] `mvn test` 全量回归（本轮未执行，结果未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `OpenScanServiceImpl` 与其单测。
- 接口：`POST /open/scan/scanIssue/query` 参数不变；四个过滤参数含元字符时按字面量匹配。
- 配置 / 数据模型 / schema：无变化。
- 跨仓：无；文档归档 `openlibing-docs`。
