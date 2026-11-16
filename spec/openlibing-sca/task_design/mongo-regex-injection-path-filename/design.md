# mongo-regex-injection-path-filename — 技术设计

## 方案概述

对 `scanFile` 字段的三处 `$regex` 拼接点逐字段转义用户输入（`path`、`fileName`），
保留服务端拼接的 `^` / `.*?` / `.*$` 边界与子串过滤语义。转义实现复用同提交在
`OpenScanServiceImpl` 内新增的 `escapeRegex`，与 `LicenseServiceImpl#escapeRegex` 行为一致。

## 数据流（修复后）

```
POST /open/scan/scanIssue/query（OpenScanController L187-L197）
  └─ getScanIssue (L1307)
        ├─ checkPermission(scanId, userId) (L1045：userId 为空时仅开源仓放行)
        └─ applyPathAndFileFilters (L1146-L1161, 调用点 L1324)
              ├─ path 非空：
              │     regex("^" + escapeRegex(path)
              │           + (fileName 非空 ? ".*?" + escapeRegex(fileName) + ".*$" : ".*$"))   (L1150-L1155)
              └─ path 为空、fileName 非空：
                    regex(".*?" + escapeRegex(fileName) + ".*$")                                (L1158)

POST /open/scan/scanIssue/queryAll（L205-L213）→ getScanIssueAll (L1363) → 同一 filter（L1373）
```

转义映射（`escapeRegex` L1139-L1144）：`\ [ ] { } ( ) * + ? . | ^ $` → 前置 `\`；
例：`src/(main)?` → `src/\(main\)\?`，`a{2,}.java` → `a\{2,\}\.java`。

## 架构决策

| 决策                                      | 理由                                                                                                                                           |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 逐字段转义而非整体正则字符串处理       | 只对用户输入部分转义，服务端边界 `^`、`.*?`、`.*$` 保持不变，避免误转义导致过滤语义丢失                                                        |
| D2 三个拼接点全部覆盖（含 path 为空分支） | 修复前 else 分支是独立注入路径；漏改会留下等价漏洞                                                                                             |
| D3 不使用 `Pattern.quote` 拼接            | 与仓库既有 `LicenseServiceImpl` 保持同一实现与输出形态，单测可直接断言；`Pattern.quote` 会引入 `\Q...\E`，与前后缀拼接组合的可读性和一致性较差 |
| D4 保持 `scanFile` 正则查询与排序不变     | 避免改动索引策略、查询计划与返回顺序（`Sort.asc("scanFile")`），把变更限制在输入处理层                                                         |
| D5 `file` 参数不纳入                      | `applyVendorComponentFilters` 中 `file` 使用 `.in(file)` 精确匹配，非正则                                                                      |
| D6 不新增长度/白名单校验                  | 属 issue 修复建议但非验收硬项，需产品确认上限，本轮未覆盖（列入残余风险）                                                                      |

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                                                                           |
| ------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`     | 修改 | 新增 `escapeRegex`；`applyPathAndFileFilters` 的 L1152、L1154、L1158 三处拼接套用转义          |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java` | 修改 | 注入类用例断言 `scanFile` 中 path / fileName 的转义文本；正常输入用例断言字面量语义与 `.` 转义 |

## 风险 & 缓解

| 风险                                                       | 缓解                                                                                |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 既有调用方依赖 path 中的正则语法（如 `.*` 通配）           | 过滤参数按字面量匹配是安全预期；行为变化需在接口文档/前端提示（本轮未覆盖文档同步） |
| 仅 `getScanIssueAll` 入口有单测，`getScanIssue` 未直接断言 | 两个方法调用同一 filter 实现（L1324、L1373），逻辑等价；后续可补入口级用例          |
| 无长度限制，超长输入仍可能拖慢查询                         | 本轮未覆盖；转义已消除回溯型攻击面                                                  |
| 转义后仍为无锚点正则（`.*?` 开头），无法利用索引           | 与修复前一致，未引入额外退化；未做执行计划验证                                      |
| 开源仓 `/query` 可免登录触发                               | 鉴权整改独立跟踪，本目录不改动                                                      |

## 跨仓影响

无。业务改动仅 `openlibing-sca`；spec 归档 `openlibing-docs`。
同一提交 `b018019d` 的其余视角见 `mongo-regex-injection-vendor-component`、
`mongo-regex-injection-scanissue-query`、`mongo-regex-injection-scanissue-queryall`。

## 明确不在范围

- `vendor` / `component` 拼接点（同提交已修）
- 入参长度上限、字符白名单、Mongo 查询超时
- `/query` 鉴权逻辑与 `queryAll` 分页策略
- `scanFile` 查询结构/索引优化
