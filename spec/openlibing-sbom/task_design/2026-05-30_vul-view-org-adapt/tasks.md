# vul-view-org-adapt — 实现任务

## 进度: 12/12 complete

- [x] Task 1: `IssueDetail.java` 新增 `issueUrl` 字段及 getter/setter
- [x] Task 2: `VulnerabilityLifecycle.java` 新增 `productType`、`issueUrl` 字段及 getter/setter
- [x] Task 3: `VulnerabilityVo.java` 新增 `issueUrl`、`productType` 字段
- [x] Task 3b: 新增 `ShowVulnerabilityVo.java`，封装 `vulId` + `List<VulnerabilityVo> data`
- [x] Task 4: `VulnerabilityLifecycleRepository.java` 新增 `deleteByProductType`、`findByCveNumAndProductType` 方法
- [x] Task 5: `VulViewClient.java` 接口方法新增 `org` 参数
- [x] Task 6: `MajunVulServiceImpl.java` 改造为遍历 active 社区同步，映射 `productType` 和 `issueUrl`
- [x] Task 7: `SbomServiceImpl.java` 改造 `getVulnerabilityStatus` 返回 `ShowVulnerabilityVo`，按包所属社区过滤
- [x] Task 8: 更新测试适配新逻辑
- [x] Task 9: `productType` 提前解析优化，`getVulnerabilityStatus` 签名改为接收 `productType` 而非 `Package`
- [x] Task 10: 提取 `convertExternalToRequest`/`convertPackageToPkgInfo` 到 `PurlUtil`，新增 `parseBracketArray`；按包名+版本过滤漏洞，支持多 ExternalPurlRef 任一匹配
- [x] Task 11: `UvpServiceImpl` 委托 `PurlUtil` 公用方法，保持逻辑一致
