# Proposal: sbom-notice-export-api

## 需求背景

SBOM 页面（`/apps/sbomManage`）现有声明文档导出功能属于 openlibing-sca 服务，仅支持单制品导出。sca 侧计划新增"全量声明文档导出"能力：在 SBOM 页面按当前制品查询条件，导出全部制品的声明文档，并通过 **Feign 服务间调用**获取 openlibing-sbom 数据。

为此 openlibing-sbom 需提供后端支撑接口：

1. **制品名清单接口**：按 `queryProductListMultiFilter` 完全相同的筛选条件，返回当前条件下的全量制品名（不分页）；
2. **依赖类型批量接口**：按制品名批量返回该制品所有软件包的依赖类型数据，供 sca 在声明文档明细中补充"依赖类型"字段映射。

同时因 sca 走 Feign 机机调用，需新增 feign 专用 controller（参照 `ApigController` 先例），并将 `queryProductConfig` / `queryProduct` / `exportSbom` 三个既有接口并行迁移至该 controller（旧接口保持不变，并行一段时间）。

## 需求点

| #   | 需求                                         | 说明                                                                                                                                                          |
| --- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 新增 `InternalController`（`/internal-api`） | feign 机机接口专用，无横向鉴权、无 userId 入参                                                                                                                |
| 2   | 新增 `queryProductNamesByMultiFilter`        | filters 与页面查询同构，全量返回制品名                                                                                                                        |
| 3   | 新增 `queryPackageDependencyTypes`           | 返回 `(name, version, downloadLocation, purl, dependencyType)` 原始数据逐列透传：不去重、不做 NOASSERTION/NONE 回退与 0>2>1 优先级归并，取舍逻辑由 sca 侧处理 |
| 4   | 并行迁移 3 个接口副本                        | queryProductConfig / queryProduct / exportSbom，仅换前缀 + 去横向鉴权 + 去 userId，旧接口零改动                                                               |

## 验收标准

1. 接口 1（制品名清单）与页面 `queryProductListMultiFilter` 同条件查询结果完全一致（忽略排序/分页）；
2. 接口 2（依赖类型）为原始数据透传：返回 name / version / downloadLocation / purl / dependencyType 五字段与表列一一对应，downloadLocation 的 NOASSERTION/NONE 原样保留、未刷新的 dependencyType 为 null，同名同版本多行原样返回（不去重、不做优先级归并）；
3. 3 个迁移副本行为与原接口一致（响应结构、错误码、文件流格式），原接口无任何改动；
4. 新增 service 层单测覆盖：filters 透传、原始数据透传（含 null 与 NOASSERTION/NONE 原样）、不去重、空制品边界；
5. 本地编译 + 单测通过，改动文件 pre-commit 全部通过。

> 口径演进说明：接口 2 曾设计 downloadKey 计算（NOASSERTION/NONE 回退 purl）与 (name, version, downloadKey) 去重 + 0>2>1 优先级归并（v1/v2），评审后因 sca 有特殊处理逻辑，最终（v3）收敛为原始数据透传，上述回退/去重/归并逻辑全部移交 sca 侧。演进过程详见 design.md「核心实现决策」与 archive.md。

## 关联

- 跨仓影响：openlibing-sca（sca 团队负责 Feign client 与导出编排，不在本 spec 范围）
- 详细设计：同目录 [design.md](./design.md)（归档摘要 + 实现决策记录）
- 联调契约与验证用例：同目录 [api-contract.md](./api-contract.md)
