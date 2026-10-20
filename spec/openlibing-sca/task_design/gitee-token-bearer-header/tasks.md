# Gitee Token Bearer 化 — 实现任务

## 进度: 6/7 complete

- [x] 下载链路（DownLoadFilesUtils）：HttpGet / HttpURLConnection 统一 Bearer 头，buildScanossUrl / buildDownloadUrl 去掉 token 拼接（SEC-2 / SEC-1）
- [x] API 调用链路（ScanCommonServiceImpl）：getFromPlatformApi 收敛双参 get，contents / compare / commits / files URL builder 去掉 gitee token 拼接
- [x] 扫描与仓库链路（OpenScanServiceImpl、IntegrationApiServiceImpl）：fetchFileContent、urlAdd、generatePrUrl、分支列表、仓库信息、buildRepoSizeCheckUrl（4 参 → 3 参）、sendToMqBasedOnRepoSize 改造
- [x] 清理遗留物：删除 PrCommonName.TOKEN / ACCESS_TOKEN / SCA_GITEE_RECURSIVE 常量、ApiUrlDto.urlToken 字段
- [x] 更新单测：DownLoadFilesUtilsTest、PrCommonNameTest、IntegrationApiServiceImplTest、ScanCommonServiceImplTest；新增本地 HttpServer 实收 Bearer 头测试 2 个
- [x] 创建 PR #330（`ms_gitee_token` → `release_20261019_iter1`），CI 流水线通过（`ci-pipeline-passed`），已打 `ai-assisted` 标签
- [ ] 手动验证真实 gitee 环境下载与扫描结果一致（PR 测试计划勾选项）

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/330
- 分支: `ms_gitee_token` → `release_20261019_iter1`
- 关联 Issue: openlibing/openlibing-sca#85、openlibing/openlibing-sca#104
