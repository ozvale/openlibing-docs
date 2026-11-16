# mongo-regex-injection-path-filename — scanIssue 查询 path/fileName 正则注入修复（#107）

## 需求背景

- Issue：[#107](https://gitcode.com/openlibing/openlibing-sca/issues/107)（closed）
- 漏洞编号 `argus-openlibingsca-20260828-001`，高危，CWE-943（NoSQL 注入 / ReDoS），
  来源 `reports/argus-openlibingsca-20260828-001.md`
- 报告定位：`src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java:1050`
  （`applyPathAndFileFilters`；当前实现 L1146-L1161）

事实与根因（issue 描述 + 当前代码核实）：

1. `applyPathAndFileFilters` 将 `ScanIssueQueryVO.path` / `fileName` 直接拼入 MongoDB
   `$regex`，修复前形态为：
   - `path` 非空：`"^" + path + (fileName 非空 ? ".*?" + fileName + ".*$" : ".*$")`
   - `path` 为空且 `fileName` 非空：`".*?" + fileName + ".*$"`
2. 用户可控值无长度限制、无字符白名单、无元字符转义，可注入 `(?i)`、`.*`、量词与嵌套量词
   （如 `(a+)+$`），造成前缀/子串过滤语义被篡改，或触发数据库正则灾难性回溯（ReDoS）。
3. 入口：`POST /open/scan/scanIssue/query`（`OpenScanController` L187-L197）→
   `OpenScanServiceImpl#getScanIssue`（L1307）→ L1324 调用 `applyPathAndFileFilters`。
   鉴权方面 `checkPermission`（L1045-L1055）在 `userId` 为空时仅拒绝非开源仓，
   开源仓 scanId 可免登录触发（issue 所述"无需鉴权"对应此场景）。
4. `getScanIssueAll`（L1363，对应 `/open/scan/scanIssue/queryAll`）复用同一 filter 方法（L1373），
   因此本修复同时覆盖机机接口。

本目录聚焦 `path` / `fileName` 在 `scanFile` 上的三个拼接点；`vendor` / `component` 见
`mongo-regex-injection-vendor-component`，两个接口的参数面视角见
`mongo-regex-injection-scanissue-query` 与 `mongo-regex-injection-scanissue-queryall`。

## 功能描述

**做什么**

1. 复用同提交新增的 `OpenScanServiceImpl#escapeRegex`（L1139-L1144），对 `path` 与 `fileName`
   在拼接前做元字符转义，三处拼接点全部覆盖：
   - L1152：`"^" + escapeRegex(path)`
   - L1154：`".*?" + escapeRegex(fileName) + ".*$"`（path 非空分支）
   - L1158：`".*?" + escapeRegex(fileName) + ".*$"`（仅 fileName 分支）
2. 保持服务端控制的 `^` 前缀与 `.*$` 后缀结构不变，用户值只做字面量匹配。
3. 单测：`getScanIssueAll_escapesRegexMetacharactersInUserFilters` 断言
   `path="src/(main)?"` → `src/\(main\)\?`、`fileName="a{2,}.java"` → `a\{2,\}\.java`；
   `getScanIssueAll_keepsLiteralSemanticsForNormalFilters` 断言 `src/main/java` / `App.java`
   仍按字面量匹配（点为 `\.`）。

**不做什么**

- 不修改 `vendor` / `component`（同提交已修，见兄弟目录）。
- 不把 `scanFile` 查询改为精确匹配、前缀索引或 text 查询，避免接口语义与排序（`scanFile` 升序）变化。
- 不新增 path / fileName 的长度上限、字符白名单或查询超时（本轮未覆盖）。
- 不修改 `/query` 的鉴权逻辑（开源仓免登录现状保持，属独立整改项）。
- 不调整 `file` 参数（`criteria.and("file").in(file)`，精确匹配，非正则）。

## 验收标准

- [x] `path` / `fileName` 的元字符在三个拼接点全部被转义（L1152、L1154、L1158）
- [x] 注入 `(a+)+$`、`src/(main)?` 等模式无法改变 `scanFile` 查询语义（单测断言转义文本）
- [x] 正常路径 / 文件名过滤语义不变（单测 `getScanIssueAll_keepsLiteralSemanticsForNormalFilters`）
- [x] path 为空、仅 fileName 的 else 分支同样覆盖，未留绕过路径
- [ ] 针对 `getScanIssue`（`/query`）的独立断言：本轮未新增，现有单测以共用 filter 的
      `getScanIssueAll` 为入口（覆盖等价，但 `getScanIssue` 路径未直接验证）
- [ ] 长度上限 / 字符白名单（issue 修复建议，本轮未覆盖）
- [ ] `mvn test` 全量回归与覆盖率达标（本轮未执行，结果未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `OpenScanServiceImpl` 与 `OpenScanServiceImplTest`。
- 接口：`POST /open/scan/scanIssue/query`（及共用 filter 的 `/queryAll`）参数不变；
  `path` / `fileName` 中的正则元字符由"语法"变为"字面量"。
- 配置 / 数据模型 / schema：无变化。
- 跨仓：无；文档归档 `openlibing-docs`。
