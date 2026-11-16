# mongo-regex-injection-scanissue-queryall — /open/scan/scanIssue/queryAll 正则注入修复（#114）

## 需求背景

- Issue：[#114](https://gitcode.com/openlibing/openlibing-sca/issues/114)（closed）
- 来源：master 分支 `8e8fc796` 外部参数校验排查（排查表 `外部参数校验排查.xlsx`），
  高危，CWE-943（NoSQL 注入 / ReDoS）
- 代码位置：`src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`
  - `getScanIssueAll`（issue 引用 L1269-L1291，当前 L1363-L1384）
  - 复用 `applyPathAndFileFilters`（当前 L1146-L1161）与 `applyVendorComponentFilters`
    （当前 L1163-L1176）

事实与根因（issue 描述 + 当前代码核实）：

1. `POST /open/scan/scanIssue/queryAll`（`OpenScanController` L205-L213）是机机接口，
   Controller 方法只接收 `@RequestBody ScanIssueQueryVO`，**无 userId 参数、无鉴权校验**，
   代码注释明确"机机接口，无需鉴权"。
2. `getScanIssueAll`（L1363）依次调用 `applyPathAndFileFilters`（L1373）与
   `applyVendorComponentFilters`（L1374），`path` / `fileName` / `vendor` / `component`
   直接拼入 Mongo `$regex`，与 `/scanIssue/query` 为同一代码缺陷。
3. 与 `/query` 的差异（本 issue 的放大因素）：
   - 无鉴权，任意可达 7979 端口的调用方即可触发；
   - 不分页：`mongoTemplate.find(query, ScanIssueVO.class)`（L1378）一次返回全量结果，
     正则回溯与结果集放大叠加，单请求资源消耗更高。
4. 风险：正则语法注入改变过滤语义、拉取非预期/全量数据；嵌套量词造成数据库侧灾难性回溯，
   单请求打满 CPU，影响同库其他业务。

本目录聚焦 `/queryAll` 接口视角；字段级修复细节见
`mongo-regex-injection-path-filename` 与 `mongo-regex-injection-vendor-component`，
`/query` 接口视角见 `mongo-regex-injection-scanissue-query`。

## 功能描述

**做什么**

1. 复用同一提交新增的 `OpenScanServiceImpl#escapeRegex`（L1139-L1144）：由于 `/queryAll`
   与 `/query` 共用两个 filter 方法，修改 filter 即同时覆盖本接口，无第二套实现。
2. 四个参数、5 处拼接点全部字面量化（L1152、L1154、L1158、L1166、L1170）。
3. 单测以 `getScanIssueAll` 为入口（与接口服务方法一一对应）：
   - `getScanIssueAll_escapesRegexMetacharactersInUserFilters`：捕获 `mongoTemplate.find` 的
     `Query`，断言四个字段的 `$regex` 文本已转义；
   - `getScanIssueAll_keepsLiteralSemanticsForNormalFilters`：正常输入语义不变。

**不做什么**

- 不增加 `/queryAll` 的调用方凭证、鉴权或限流（issue 修复建议 2），当前接口仍无鉴权。
- 不把全量返回改为分页或增加条数上限（属接口契约变化，未做）。
- 不新增长度上限 / 字符白名单 / 查询超时。
- 不改 `file`（`.in()` 精确匹配）等其他过滤条件。
- 不做压测与覆盖率复测。

## 验收标准

- [x] `/queryAll` 复用同一 filter，`path` / `fileName` / `vendor` / `component` 全部转义
      （L1373-L1374 调用同一实现）
- [x] 恶意回溯模式无法以正则语法进入 `$regex`（单测断言转义文本，原始注入串不存在）
- [x] 单测通过（提交内 2 个 `getScanIssueAll_*` 用例）；覆盖率达标未验证
- [ ] 机机接口鉴权 / 调用方凭证 / 限流（issue 修复建议 2）：**本轮未覆盖**。
      当前 `OpenScanController#getScanIssueQueryAll`（L205-L213）仍无 userId 参数，
      `getScanIssueAll`（L1363-L1384）未调用 `checkPermission`
- [ ] 全量返回放大风险（不分页）：本轮未处理，接口仍一次返回全部匹配结果
- [ ] 长度上限 / 字符白名单（本轮未覆盖）
- [ ] `mvn test` 全量回归（本轮未执行，结果未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `OpenScanServiceImpl` 与其单测。
- 接口：`POST /open/scan/scanIssue/queryAll` 参数与返回结构不变；四个过滤参数含元字符时
  按字面量匹配，不再被解释为正则语法。
- 鉴权 / 限流 / 分页：无变化（残余风险，见 design 风险表）。
- 配置 / 数据模型 / schema：无变化。
- 跨仓：无；文档归档 `openlibing-docs`。
