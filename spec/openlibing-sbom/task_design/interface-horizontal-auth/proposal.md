# Proposal：SBOM 接口横向鉴权整改

> 变更名：interface-horizontal-auth
> 目标仓：openlibing-sbom（分支 feat-interface-horizontal-auth，基线 prod/feat-sbom-excel-export）
> 日期：2026-10-29

## 需求背景

源自源仓安全 issue（6 个，PR 全关联）：

| Issue                    | 问题                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| #156【Argus L-0032】     | 资源型端点功能级授权缺失：packageId/productName 全链路无授权校验，可读取并全量导出任意产品/包 SBOM 数据 |
| #138【安全功能规范检查】 | 用户标识为空时横向鉴权默认放行                                                                          |
| #103【产品网络安全红线】 | 权限校验 userId 为空直接放行可绕过横向鉴权                                                              |
| #102【Argus H-0029】     | 唯一横向鉴权门双重缺陷：空白 userId 直接放行且客户端可自报身份                                          |
| #95【威胁建模报告】      | AuthServiceImpl 空 userId 直接放行绕过授权，与 framework fail-closed 语义不一致                         |
| #94【威胁建模报告】      | SBOM 发布/新增/刷新等写路径缺少产品级横向鉴权                                                           |

机机交互接口已在前序迭代迁移至 InternalController / ApigController / APIG 通道白名单（10 个机机接口不整改）。

## 整改范围

1. **需求 1**：移除 `AuthServiceImpl.checkPermissionByProductType` 中 userId 为空直接放行分支（已完成修改，随本分支交付）；
2. **需求 2**：SbomController 26 个入参含 productName/packageId 的人机接口补齐横向鉴权：
   - productName 类 20 个（反查 product.attribute.productType）
   - packageId 类 6 个（package → sbom → product 反查）
   - 前端在用 13 个 + 前端不用 13 个（决策 b1 全部补鉴权，废弃接口暂不下线）
3. **行为变化**：refreshDependencyType productName 必传化（空刷全量分支删除，批量走调用方循环）。

## 验收标准

- [x] userId 为空时不再放行，走远端鉴权并被拒绝（fail-closed）
- [x] 26 个接口无权限/反查失败时返回 403（固定文案，不泄露内部细节），warn 日志记录反查失败原因
- [x] 机机白名单接口不受影响（InternalController /internal-api 5 接口 + ApigController /apig-api 9 接口 + SbomController 机机通道 publishSbomFile / publishSbomFileWithCompress / sync，鉴权豁免由 APIG 通道凭证与网络隔离保障）
- [x] 除 refreshDependencyType 外前端零改造（gateway 注入 userId，可选 query 参数，缺省空；refreshDependencyType 前端无引用，行为变化不影响前端）
- [x] 反查失败默认拒绝（gamma 断链约 1.1% package 数据可接受被拒；2026-10-29 gamma PG 只读实测：约 1.89 万悬空 sbom_id + 5 个 product 缺失，断链排查/补数列为可选后续任务）
- [x] 单测覆盖：AuthServiceImpl 新方法各场景 + Controller 403 用例（代表性覆盖，26 接口参数化鉴权矩阵列为遗留增强项）
- [x] mvn 编译 + 相关单测全绿 + pre-commit 全部通过
- [x] PR 关联 6 个 issue（Fixes + 完整 URL）

交付结果（2026-10-30）：全部达成。业务 PR https://gitcode.com/openlibing/openlibing-sbom/merge_requests/169 已合入 release_20261029_iter2（AuthServiceImplTest 15/15、SbomControllerTest 44/44 全绿，pre-commit 全通过）。
