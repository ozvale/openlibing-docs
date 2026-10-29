# Tasks: 发布制品信息 Excel 模板导入与迭代缺陷修复

对应分支 `dsq_202610_iter2` → `release_20261029`，业务 PR [openlibing-platform-release#237](https://gitcode.com/openlibing/openlibing-platform-release/merge_requests/237)。

## 阶段 1：制品信息 Excel 模板能力

- [x] 新增发布制品信息 Excel 模板下载与上传解析接口（`6eae6522`）
- [x] 模板下载与解析接口增加项目成员校验（`b63d7629`）
- [x] 制品包模板表头批注错位修复（`a0144413`）
- [x] 制品模板下载与解析接口增加 reviewId 并校验评审单创建人（`7f98107a`）
- [x] 制品信息模板源码包页删除发布方式列（`df42b372`）
- [x] 制品信息 Excel 解析增加 tag 命名规范校验（`9b4fbe63`）
- [x] tag 名称增加 50 字符长度限制（`75b41e6e`）
- [x] 制品信息模板删除制品包路径列，改为前端勾选（`bc50107b`）
- [x] 删除制品包 tag 来源与分支列，统一改名源码仓来源（`905e907a`）
- [x] 清理 ReleaseArtifactExcelServiceImpl 冗余 DataFormatter（`180fab87`）

## 阶段 2：配套缺陷修复

- [x] 修复 pypi 仓库 ID 空串导致评审单详情查询崩溃（`5f9b38ad`）
- [x] 修正表格解析 pypi 仓库 ID 填充字段错位（`1cf002c9`）
- [x] PyPI 上传前过滤校验文件，避免 InvalidDistribution（`468f0ddd`）
- [x] 病毒扫描结果入库前过滤 ClamAV 告警行（`78d58942`）

## 阶段 3：验证与交付

- [x] 单元测试补充（ReleaseArtifactExcelServiceImplTest 等，+998 行测试代码）
- [x] 合入 master 同步（`4695e7fd`）
- [ ] CI 流水线通过（PR #237）
- [ ] 前端勾选交互联调（openlibing-web，关联 [#385](https://gitcode.com/openlibing/openlibing-web/issues/385)）
