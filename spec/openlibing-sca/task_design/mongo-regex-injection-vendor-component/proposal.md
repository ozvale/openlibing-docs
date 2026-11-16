# mongo-regex-injection-vendor-component — scanIssue 查询 vendor/component 正则注入修复（#106）

## 需求背景

- Issue：[#106](https://gitcode.com/openlibing/openlibing-sca/issues/106)（closed）
- 漏洞编号 `argus-openlibingsca-20260828-002`，高危，CWE-943（NoSQL 注入 / ReDoS），
  来源 `reports/argus-openlibingsca-20260828-002.md`
- 报告定位：`src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java:1067`
  （`applyVendorComponentFilters`；当前实现 L1163-L1176）

事实与根因（issue 描述 + 当前代码核实）：

1. `applyVendorComponentFilters` 将 `ScanIssueQueryVO.vendor` / `component` 直接拼入
   MongoDB `$regex`：
   - L1166 `criteria.and("vendor").regex(".*?" + vendor + ".*$")`
   - L1170 `criteria.and("component").regex(".*?" + component + ".*$")`
2. 输入无验证、无元字符转义；攻击者可注入 `(?i)`、`.*`、量词及嵌套量词（如 `(a+)+$`），
   改变查询语义或触发数据库侧灾难性回溯（ReDoS），单请求即可占满 CPU。
3. 触发面：`ScanIssueQueryVO` 的 `vendor` / `component` 字段（`common/domain/ScanIssueQueryVO.java`
   L32-L33，无校验注解）。可达入口为：
   - `POST /open/scan/scanIssue/queryAll`（`OpenScanController` L205-L213，代码注释"机机接口，无需鉴权"）
   - `POST /open/scan/scanIssue/query`（`OpenScanController` L187-L197；`checkPermission` L1045-L1055
     在 `userId` 为空时仅对非开源仓拒绝，开源仓可免登录访问）
4. 项目内已有安全实践 `LicenseServiceImpl#escapeRegex`（L681-L686），但此前未在
   `OpenScanServiceImpl` 复用，属安全控制不一致。

本目录聚焦 `vendor` / `component` 两个字段；同批次的 `path` / `fileName` 与两个接口的完整整改视角
分别见兄弟目录 `mongo-regex-injection-path-filename`、`mongo-regex-injection-scanissue-query`、
`mongo-regex-injection-scanissue-queryall`。

## 功能描述

**做什么**

1. 新增 `OpenScanServiceImpl#escapeRegex`（L1139-L1144，包级 `static`），转义集合与
   `LicenseServiceImpl#escapeRegex` 相同：`\ [ ] { } ( ) * + ? . | ^ $`。
2. `applyVendorComponentFilters` 的两处拼接点套用转义：
   - L1166 `".*?" + escapeRegex(vendor) + ".*$"`
   - L1170 `".*?" + escapeRegex(component) + ".*$"`
     保留原有 `.*?<值>.*$` 子串匹配语义，仅把用户值字面量化。
3. 单测：`escapeRegex_escapesAllRegexMetacharacters` 断言转义映射；
   `getScanIssueAll_escapesRegexMetacharactersInUserFilters` 用 `ArgumentCaptor` 捕获查询文档，
   断言 vendor 为 `ven\.\*dor`、component 为 `\(a\+\)\+\$` 且不再出现原始注入串；
   `getScanIssueAll_keepsLiteralSemanticsForNormalFilters` 断言合法输入语义不变。

**不做什么**

- 不修改 `path` / `fileName` 拼接逻辑（由同一提交覆盖，文档见兄弟目录）。
- 不把 `escapeRegex` 提取为 `common.utils.RegexUtils`，也不改造 `LicenseServiceImpl` 既有实现
  （issue 修复建议 1 的"提取公共工具类"未执行，见 design D2）。
- 不新增入参长度上限、字符白名单或 MongoDB 查询超时（本轮未覆盖）。
- 不修改 `queryAll` 的鉴权与全量返回策略（独立整改项）；不调整接口契约。

## 验收标准

- [x] `vendor` / `component` 中的正则元字符被转义后再拼接（L1166、L1170）
- [x] 恶意嵌套量词输入（`(a+)+$`）不再以正则语法进入 `$regex`（单测断言转义后文本，且
      断言原始 `(a+)` 序列不存在）
- [x] 合法输入（`apache`、`commons-lang3`）仍按子串字面量匹配，未引入额外转义符
- [x] 空 / null 输入返回空串（单测 `escapeRegex(null)` 断言 `""`）
- [ ] 恶意回溯模式 CPU 压测（本轮未覆盖；转义后输入不含可执行量词，理论风险已消除）
- [ ] 按 issue 建议提取公共 `RegexUtils`（本轮未做，见 design D2）
- [ ] `mvn test` 全量回归与覆盖率达标（本轮未执行，结果未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `OpenScanServiceImpl` 与 `OpenScanServiceImplTest`。
- 接口：`POST /open/scan/scanIssue/query`、`POST /open/scan/scanIssue/queryAll` 参数不变；
  `vendor` / `component` 含正则元字符时由"按正则解释"变为"按字面量匹配"。
- 配置 / 数据模型 / schema：无变化。
- 跨仓：无；文档归档 `openlibing-docs`。
