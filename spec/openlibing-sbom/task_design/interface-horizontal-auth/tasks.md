# Tasks：SBOM 接口横向鉴权整改

## 需求 1：移除空 userId 放行分支（已在工作区完成）

- [x] AuthServiceImpl 移除 blank userId 放行分支 + 清理 StringUtils import
- [x] AuthService 接口 Javadoc 更新（机机迁移说明）
- [x] AuthServiceImplTest 新增 blankUserId 拒绝用例（6/6 通过）

## 需求 2：25 接口补横向鉴权

- [ ] AuthService 接口 +checkPermissionByProductName / +checkPermissionByPackageId 声明
- [ ] PackageRepository +findProductTypeByPackageId（native 三表 JOIN 标量）
- [ ] AuthServiceImpl 构造注入两个 Repository，+2 公开方法 +2 私有 resolve
- [ ] SbomController productName 类 19 接口补 userId 入参 + 鉴权样板
- [ ] SbomController packageId 类 6 接口补 userId 入参 + 鉴权样板
- [ ] 文件流接口（exportSbomFile/exportSbom/exportPackageSbom/exportAllPackageSbom）403 直写 response
- [ ] body 入参接口（MultiFilter/VulCountSummary）productName blank 前置 400
- [ ] refreshDependencyType productName 必传化 + 删空刷全量分支

## 测试与验证

- [ ] AuthServiceImplTest：新方法成功/反查失败/blank/非法 UUID/远端拒绝用例
- [ ] SbomControllerTest：受影响既有用例补 mock；新增 403 用例
- [ ] mvn 编译 + AuthServiceImplTest/SbomControllerTest 全绿
- [ ] pre-commit 全部改动文件通过

## 交付（用户确认后）

- [ ] 报告分支/文件清单/验证结果，暂不 commit
- [ ] 用户自测确认后：commit → 合测试分支部署验证 → PR（关联 6 issue）→ spec 归档
