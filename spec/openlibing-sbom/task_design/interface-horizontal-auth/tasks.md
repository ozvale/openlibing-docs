# Tasks：SBOM 接口横向鉴权整改

> 状态：已全部交付（业务 PR 已合入 release_20261029_iter2）

## 需求 1：移除空 userId 放行分支

- [x] AuthServiceImpl 移除 blank userId 放行分支 + 清理 StringUtils import
- [x] AuthService 接口 Javadoc 更新（机机迁移说明）
- [x] AuthServiceImplTest 新增 blankUserId 拒绝用例

## 需求 2：26 接口补横向鉴权

- [x] AuthService 接口 +checkPermissionByProductName / +checkPermissionByPackageId 声明
- [x] PackageRepository +findProductTypeByPackageId（native 三表 JOIN 标量）
- [x] AuthServiceImpl 字段注入（@Autowired）两个 Repository，+2 公开方法 +2 私有 resolve
- [x] SbomController productName 类 20 接口补 userId 入参 + 鉴权样板
- [x] SbomController packageId 类 6 接口补 userId 入参 + 鉴权样板
- [x] 文件流接口（exportSbomFile/exportSbom/exportPackageSbom/exportAllPackageSbom）403 直写 response
- [x] body 入参接口（MultiFilter/VulCountSummary）productName blank 前置 400
- [x] refreshDependencyType productName 必传化 + 删空刷全量分支

## 测试与验证

- [x] AuthServiceImplTest：新方法成功/反查失败/blank/非法 UUID/远端拒绝用例（15/15 通过）
- [x] SbomControllerTest：受影响既有用例补 mock + 新增代表性 403 用例（44/44 通过；26 接口参数化鉴权矩阵用例列为遗留增强项，见 design.md §7）
- [x] mvn 编译 + 单测全绿
- [x] pre-commit 全部改动文件通过

## 交付

- [x] 报告分支/文件清单/验证结果（用户审查通过）
- [x] commit → 合入 gamma 测试分支部署验证通过
- [x] 业务 PR 关联 6 个安全 issue：https://gitcode.com/openlibing/openlibing-sbom/merge_requests/169（base: release_20261029_iter2，已合入）
- [x] spec 归档 docs 仓 PR：https://gitcode.com/openlibing/openlibing-docs/merge_requests/1274
