# mongo-regex-injection-scanissue-query — 技术设计

## 方案概述

`/open/scan/scanIssue/query` 的四个字符串过滤参数（`path`、`fileName`、`vendor`、`component`）
统一在拼入 Mongo `$regex` 前做正则元字符转义，覆盖 `applyPathAndFileFilters` 与
`applyVendorComponentFilters` 共 5 处拼接点。查询结构、前后缀与接口契约保持不变。

## 数据流（修复后）

```
POST /open/scan/scanIssue/query（OpenScanController L187-L197）
  └─ OpenScanServiceImpl#getScanIssue (L1307)
        ├─ checkPermission(scanId, userId) (L1045-L1055；userId 空时仅开源仓放行)
        ├─ applyPathAndFileFilters (L1146-L1161，调用点 L1324)
        │     ├─ path 非空：regex("^" + escapeRegex(path) + [".*?" + escapeRegex(fileName)] + ".*$")
        │     └─ 仅 fileName：regex(".*?" + escapeRegex(fileName) + ".*$")
        └─ applyVendorComponentFilters (L1163-L1176，调用点 L1325)
              ├─ vendor    → regex(".*?" + escapeRegex(vendor) + ".*$")
              ├─ component → regex(".*?" + escapeRegex(component) + ".*$")
              └─ file      → in(file)   // 精确匹配，无正则
```

转义：`escapeRegex`（L1139-L1144）对 `\ [ ] { } ( ) * + ? . | ^ $` 前置 `\`，null → `""`。

## 架构决策

| 决策                                                                            | 理由                                                                                               |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| D1 统一在字段拼接前转义，而非拦截/拒绝请求                                      | 不改变接口契约与合法输入行为，只把用户值字面量化；兼容现有调用方                                   |
| D2 5 处拼接点逐一覆盖                                                           | path 分支含 path + fileName 两个值，另有仅 fileName 分支，加 vendor/component，漏一处即留注入面    |
| D3 保留 `^`、`.*?`、`.*$` 边界                                                  | 维持既有"路径前缀 + 文件名子串"过滤语义，不引入索引/查询计划变化                                   |
| D4 `file`、license/copyright 等非正则条件不处理                                 | `file` 为 `.in()`，`licenseStatus`/`copyrightStatus` 为 `is`/`ne`，均无正则注入面（代码核实）      |
| D5 采用与 `LicenseServiceImpl#escapeRegex` 相同的实现副本，不改 `Pattern.quote` | 与仓库既有安全实践一致，便于比对与单测断言；公共化抽取涉及跨模块重构，本轮按最小改动处理（技术债） |
| D6 `escapeRegex` 包级 `static` 便于测试                                         | 单测可直接验证转义映射，不必构造完整请求上下文                                                     |

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                                                                         |
| ------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`     | 修改 | 新增 `escapeRegex`（L1139-L1144）；L1152、L1154、L1158、L1166、L1170 共 5 处转义             |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java` | 修改 | 新增 3 个用例：转义映射、注入字面量化（ArgumentCaptor 断言 `$regex` 文本）、正常输入语义不变 |

## 风险 & 缓解

| 风险                                   | 缓解                                                                   |
| -------------------------------------- | ---------------------------------------------------------------------- |
| 调用方依赖过滤参数中的正则语法         | 安全预期为字面量匹配；接口文档未同步（本轮未覆盖），需在发布说明中提示 |
| 两处 `escapeRegex` 副本长期漂移        | 当前实现一致；抽取 `RegexUtils` 列为后续技术债                         |
| 未增加长度上限，超长输入仍可造成慢查询 | 本轮未覆盖；回溯攻击面已消除                                           |
| 未做运行态压测，无法量化 CPU 改善      | 实现层已保证输入不含可执行量词；压测列为遗留项                         |
| 开源仓 `/query` 仍可免登录访问         | 鉴权整改独立跟踪，本目录不混入                                         |
| MongoDB 侧正则执行超时未配置（未验证） | 建议后续统一设置查询超时/慢查询监控，本轮未覆盖                        |

## 跨仓影响

无。业务改动仅 `openlibing-sca`；spec 归档 `openlibing-docs`。
同一提交 `b018019d` 的字段级与接口级视角见 `mongo-regex-injection-path-filename`、
`mongo-regex-injection-vendor-component`、`mongo-regex-injection-scanissue-queryall`。

## 明确不在范围

- 入参长度上限、字符白名单
- `escapeRegex` 公共工具化与 `LicenseServiceImpl` 改造
- `/query` 鉴权逻辑、分页与排序
- Mongo 查询超时与慢查询监控
