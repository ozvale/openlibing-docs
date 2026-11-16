# mongo-regex-injection-vendor-component — 技术设计

## 方案概述

在字段值拼入 MongoDB `$regex` 之前做正则元字符转义（白名单式字面量化），不改查询结构、
不改接口契约。`escapeRegex` 与仓库内既有安全实践 `LicenseServiceImpl#escapeRegex` 同实现，
只转义用户输入部分，前后缀 `.*?` / `.*$` 仍由服务端控制。

## 数据流（修复后）

```
POST /open/scan/scanIssue/queryAll（OpenScanController L205-L213，无鉴权）
POST /open/scan/scanIssue/query   （OpenScanController L187-L197）
  └─ OpenScanServiceImpl#getScanIssueAll (L1363) / #getScanIssue (L1307)
        └─ applyVendorComponentFilters (L1163-L1176)
              ├─ vendor    → criteria.and("vendor").regex(".*?" + escapeRegex(vendor) + ".*$")       (L1166)
              ├─ component → criteria.and("component").regex(".*?" + escapeRegex(component) + ".*$") (L1170)
              └─ file      → criteria.and("file").in(file)   // 精确匹配，非 regex，不转义 (L1172-L1175)

escapeRegex (L1139-L1144)：
  null → ""；否则 input.replaceAll("([\\\\\\[\\]{}()*+?.|^$])", "\\\\$1")
```

## 架构决策

| 决策                                                           | 理由                                                                                                             |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| D1 字段级转义，保留 `$regex` 查询结构                          | 不改索引/查询语义与返回顺序，改动面最小；改用精确匹配或 text index 会改变既有过滤体验与数据模型                  |
| D2 在 `OpenScanServiceImpl` 内新增同实现副本，不抽取公共工具类 | 避免跨模块抽取与 `LicenseServiceImpl` 调用点迁移带来的额外回归面；issue 建议的公共化留作技术债（两处副本需同步） |
| D3 转义集合包含 `.`                                            | 组件名 / 供应商名中的点按字面量匹配，同时修正原实现"点匹配任意字符"的过宽语义                                    |
| D4 保留 `.*?` 前缀与 `.*$` 后缀                                | 维持原有"子串包含"过滤体验，只把用户值字面量化                                                                   |
| D5 `file` 字段不纳入                                           | 当前实现为 `criteria.and("file").in(file)`（精确匹配），不经过正则引擎，无注入面（代码核实结论）                 |
| D6 `escapeRegex` 声明为包级 `static`                           | 单测可直接断言转义映射，避免为测试扩大公开 API                                                                   |

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`     | 修改 | 新增 `escapeRegex`（L1130-L1144）；`applyVendorComponentFilters` 的 vendor（L1166）与 component（L1170）套用转义                                                                                                                                            |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java` | 修改 | 新增 `escapeRegex_escapesAllRegexMetacharacters`、`getScanIssueAll_escapesRegexMetacharactersInUserFilters`、`getScanIssueAll_keepsLiteralSemanticsForNormalFilters`；新增 `ArgumentCaptor` / `assertFalse` / `assertTrue` 导入与 `regexValueText` 辅助方法 |

## 风险 & 缓解

| 风险                                       | 缓解                                                             |
| ------------------------------------------ | ---------------------------------------------------------------- |
| 两处 `escapeRegex` 副本行为漂移            | 当前实现逐字符一致；后续可抽取公共工具（记为技术债）             |
| 用户依赖通配符过滤（如用 `*` 当通配）      | 过滤参数本应字面量匹配；单测覆盖正常输入语义不变，前端提示未覆盖 |
| 仅转义不限制长度，超长输入仍可能造成慢查询 | 本轮未覆盖，长度上限/白名单为遗留项（兄弟目录同样标注）          |
| `queryAll` 无鉴权，攻击面仍大于 `/query`   | 鉴权与限流属独立整改项，不在本 issue 范围；本目录不改动          |
| 转义后正则仍为无锚点匹配，可能走集合扫描   | 与修复前一致，未引入性能退化；未做执行计划验证                   |

## 跨仓影响

无。业务改动仅 `openlibing-sca`；spec 归档 `openlibing-docs`。
同一提交 `b018019d` 同时修复 `path` / `fileName`（见 `mongo-regex-injection-path-filename`）、
`/query` 全参数视角（`mongo-regex-injection-scanissue-query`）与 `/queryAll` 视角
（`mongo-regex-injection-scanissue-queryall`）。

## 明确不在范围

- `path` / `fileName` 拼接点（同提交已修，见兄弟目录）
- 入参长度上限、字符白名单、Mongo 查询超时
- `queryAll` 鉴权、限流与分页
- `LicenseServiceImpl#escapeRegex` 的公共化重构
