# vul-view-org-adapt — 需求提案

## 背景

当前 openlibing-sbom 项目的漏洞视图数据同步仅适配 OpenEuler 社区。远程接口 `openlibing-vulnerability-view/admin/ci-portal/ci-admin/cve/details` 不传 `org` 参数时默认返回 openEuler 社区数据，导致其他社区（openGauss、MindSpore、OpenHarmony 等）的漏洞 Issue 信息无法入库和展示。

此外，一个 CVE 漏洞在不同社区可能各自关联了独立的 CVE-ISSUE，当前系统仅返回单条 Issue 记录，无法体现一对多关系，且返回结构中缺少 `issueUrl` 字段，前端无法直接跳转到 Issue 详情页。

## 需求目标

1. **多社区适配**：`cve/details` 接口新增 `org` 入参，支持按社区查询漏洞视图数据
2. **社区标识持久化**：数据库 `vulnerability_lifecycle` 表新增 `product_type` 字段，区分数据来源社区
3. **issueUrl 透传**：从 API 返回的 `issueUrl` 字段完整存储并返回给前端
4. **一对多返回**：一个 CVE 对应多个社区的 CVE-ISSUE 信息，以 `ShowVulnerabilityVo`（`vulId` + `List<VulnerabilityVo> data`）结构返回
5. **按包所属社区过滤**：查询漏洞时根据包所属的 Sbom → Product → productType 自动过滤，只返回该社区下的 Issue 信息
6. **productType 提前解析**：`productType` 在 `queryVulnerability` 中提前解析一次，避免遍历每条 Vulnerability 时重复计算
7. **按包名+版本过滤**：查询漏洞时根据包的 ExternalPurlRef 提取包名和版本号，过滤 `VulnerabilityLifecycle` 中 `affectedSoftware` 匹配包名且 `versions` 包含该版本的记录；支持多个 ExternalPurlRef，任一匹配即可

## 验收标准

| # | 验收条件 | 验证方式 |
|---|---------|---------|
| 1 | `VulViewClient.getMajunVulDetails(org)` 可按社区调用远程 API | 单元测试 + 日志确认不同 org 参数返回对应数据 |
| 2 | `syncMajunVulData` 遍历所有 active 社区逐个同步，每个社区数据独立刷新 | 手动触发同步任务，检查各社区数据入库 |
| 3 | `vulnerability_lifecycle` 表每条记录均有 `product_type` 值 | 数据库查询验证 |
| 4 | `vulnerability_lifecycle` 表每条记录均有 `issue_url` 值（API 返回时） | 数据库查询验证 |
| 5 | 查询漏洞返回 `ShowVulnerabilityVo` 结构，`data` 列表仅包含该包所属社区的 Issue 信息 | API 调用验证 |
| 6 | 单社区同步失败不影响其他社区 | 模拟某社区 API 异常，验证其他社区数据正常 |
| 7 | 存量数据（`product_type` 为 NULL）不影响系统运行 | 升级后首次同步前系统无报错 |
| 8 | 漏洞查询按包名+版本过滤，仅返回 `affectedSoftware` 匹配且 `versions` 包含该版本的记录 | API 调用验证，确认不同版本的包返回不同漏洞信息 |
| 9 | 多个 ExternalPurlRef 场景下，任一匹配即可返回对应漏洞信息 | 构造多 purl 的包，验证匹配结果 |
| 10 | 远程 API 返回 `result` 为 null 或空列表时，同步任务不报错，跳过该社区继续执行 | 模拟 API 返回 null，验证日志输出 skip 且其他社区正常同步 |

## 影响范围

- **模块**：漏洞同步（MajunVulService）、漏洞查询（SbomService）
- **数据库**：`vulnerability_lifecycle` 表新增 2 列
- **API 返回结构变更**：漏洞查询接口返回类型从 `VulnerabilityVo` 变为 `ShowVulnerabilityVo`
- **前端影响**：需适配新的 `ShowVulnerabilityVo` 返回结构

## 关联 Issue

openlibing-sbom#35
