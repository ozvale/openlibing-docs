# mongo-regex-injection-scanissue-queryall — 技术设计

## 方案概述

`/open/scan/scanIssue/queryAll` 与 `/open/scan/scanIssue/query` 共用
`applyPathAndFileFilters` / `applyVendorComponentFilters`，因此正则转义修复只需落在
两个 filter 方法内即可同时覆盖两个接口。本目录确认 `/queryAll` 的调用链、
无鉴权与不分页特征，并核对单测确实从 `getScanIssueAll` 入口验证。

## 数据流（修复后）

```
POST /open/scan/scanIssue/queryAll（OpenScanController L205-L213，无 userId / 无鉴权）
  └─ OpenScanServiceImpl#getScanIssueAll (L1363-L1384)
        ├─ buildBaseCriteria / applyReviewFilters / applyTimeFilters / applyBasicFilters /
        │  applyLicenseCopyrightFilters
        ├─ applyPathAndFileFilters (L1146，调用点 L1373)
        │     ├─ path 非空：regex("^" + escapeRegex(path) [+ ".*?" + escapeRegex(fileName)] + ".*$")
        │     └─ 仅 fileName：regex(".*?" + escapeRegex(fileName) + ".*$")
        ├─ applyVendorComponentFilters (L1163，调用点 L1374)
        │     ├─ vendor    → regex(".*?" + escapeRegex(vendor) + ".*$")
        │     └─ component → regex(".*?" + escapeRegex(component) + ".*$")
        ├─ buildQuery + Sort.asc("scanFile")
        └─ mongoTemplate.find(query, ScanIssueVO.class)   // 不分页，返回全部匹配
```

## 架构决策

| 决策                                                    | 理由                                                                                     |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| D1 复用共享 filter，不复制一份 `/queryAll` 专用清洗逻辑 | 两接口共用实现，单点修复天然一致，避免双份转义逻辑漂移                                   |
| D2 单测选择 `getScanIssueAll` 作为入口                  | 该方法是 `/queryAll` 的唯一服务层入口，可同时验证两个接口共用的 filter 行为              |
| D3 不把鉴权/限流混入本次正则修复                        | 鉴权属接口安全策略变更，需调用方配合（机机接口凭证），与输入转义正交；本轮范围仅 CWE-943 |
| D4 不新增分页 / 条数上限                                | 会改变接口契约与调用方行为，需单独评审；本轮只标注残余风险                               |
| D5 保留 `Sort.asc("scanFile")` 与既有 enrich 流程       | 避免引入无关行为变化，变更仅限输入处理层                                                 |

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                                                                                                                    |
| ------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`     | 修改 | 新增 `escapeRegex`（L1139-L1144）；两个 filter 共 5 处拼接点套用转义（L1152、L1154、L1158、L1166、L1170）；`getScanIssueAll` 本身未改动 |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java` | 修改 | 新增 3 个用例，其中 2 个以 `getScanIssueAll` 为入口，直接覆盖 `/queryAll` 服务方法                                                      |

## 风险 & 缓解

| 风险                                                    | 缓解                                                                        |
| ------------------------------------------------------- | --------------------------------------------------------------------------- |
| `/queryAll` 仍无鉴权，任意网络可达方可持续调用          | 属于独立整改项（凭证/限流），本轮未覆盖；输入转义已消除正则注入与回溯攻击面 |
| 不分页全量返回，数据量与负载放大                        | 本轮未改；建议后续评估分页或条数上限（会变更契约）                          |
| 未加长度上限，超长过滤值仍可造成慢查询                  | 遗留项；转义已消除嵌套量词回溯                                              |
| 单测未覆盖 controller 层鉴权/参数绑定                   | controller 层无逻辑分支（仅委派），本轮未新增 web 层测试                    |
| 与 `/query` 共用 filter，若未来任一侧改造易出现行为分叉 | 两目录文档互引；建议后续把 filter 行为纳入参数化测试基类                    |

## 跨仓影响

无。业务改动仅 `openlibing-sca`；spec 归档 `openlibing-docs`。
同一提交 `b018019d` 的其他视角见 `mongo-regex-injection-vendor-component`、
`mongo-regex-injection-path-filename`、`mongo-regex-injection-scanissue-query`。

## 明确不在范围

- `/queryAll` 鉴权、调用方凭证、限流
- 分页 / 条数上限 / 响应体裁剪
- 入参长度与字符白名单
- Mongo 查询超时与慢查询监控
