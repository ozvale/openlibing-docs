# Proposal: 发布制品信息 Excel 模板导入与迭代缺陷修复（dsq_202610_iter2）

## 需求背景

发布评审流程中，制品信息此前依赖手工逐条录入，效率低且易出错。本迭代（分支 `dsq_202610_iter2`，合入 `release_20261029`）新增**发布制品信息 Excel 模板下载与上传解析**能力，并修复迭代期间发现的多项缺陷。

业务 Issue：

- [openlibing-platform-release#88](https://gitcode.com/openlibing/openlibing-platform-release/issues/88)
- [openlibing-web#385](https://gitcode.com/openlibing/openlibing-web/issues/385)

## 需求范围

### 1. 制品信息 Excel 模板下载与解析（核心特性）

- 新增制品信息 Excel 模板下载接口：模板含制品包信息表头，评审单创建人可按 reviewId 下载
- 新增上传解析接口：批量解析 Excel 行并回填到评审单
- 权限控制：接口增加 reviewId 校验、评审单创建人校验、项目成员校验

### 2. 制品模板校验规则

- tag 命名规范校验（非法字符/格式拒绝）
- tag 名称长度限制 50 字符
- 制品包路径列改为前端勾选（模板删除路径列）
- 模板删除制品包 tag 来源与分支列，统一改名"源码仓来源"
- 源码包页删除发布方式列

### 3. 配套缺陷修复

- 病毒扫描结果入库前过滤 ClamAV 告警行，避免误报入库
- PyPI 上传前过滤校验文件，避免 InvalidDistribution 异常
- 表格解析 pypi 仓库 ID 填充字段错位修正
- pypi 仓库 ID 空串导致评审单详情查询崩溃修复
- 制品包模板表头批注错位一列修复

## 验收标准

- [ ] 模板下载接口返回合法 xlsx，仅评审单创建人/项目成员可调用
- [ ] 上传解析对 tag 命名不规范、超 50 字符的行返回明确错误提示（ReleaseArtifactRowErrorVO）
- [ ] ClamAV 告警行不再写入病毒扫描结果表
- [ ] PyPI 上传含校验文件时不再抛 InvalidDistribution
- [ ] pypi 仓库 ID 为空串时评审单详情查询不崩溃
- [ ] 单元测试覆盖新增服务与校验逻辑（ReleaseArtifactExcelServiceImplTest 等）
