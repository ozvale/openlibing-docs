# Design: 发布制品信息 Excel 模板导入与迭代缺陷修复

## 技术方案

### 1. 制品信息 Excel 模板下载与解析

新增组件（`openlibing-platform-release`）：

| 组件                                                              | 职责                                                                              |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `ReleaseBaseController`（扩展）                                   | 暴露模板下载与上传解析两个 REST 端点                                              |
| `ReleaseArtifactExcelService` / `ReleaseArtifactExcelServiceImpl` | 模板下载（生成 xlsx）与上传解析核心逻辑                                           |
| `ReleaseArtifactTemplateGenerator`                                | 模板生成器，产出 `release_artifact_info_template.xlsx` 结构（表头、批注、示例行） |
| `ReleaseArtifactParseResultVO` / `ReleaseArtifactRowErrorVO`      | 解析结果与逐行错误返回 VO                                                         |

数据流：

```text
前端 → ReleaseBaseController
        → 权限校验链（reviewId 存在性 → 评审单创建人 → 项目成员）
        → ReleaseArtifactExcelService
            下载: ReleaseArtifactTemplateGenerator 生成模板流
            解析: POI 读取行 → 逐行校验 → 组装 ParseResultVO（含 RowErrorVO 列表）
        → 回写评审单制品信息
```

### 2. 校验规则

- **reviewId 校验**：解析/下载接口必须携带有效 reviewId，评审单不存在时拒绝
- **创建人校验**：仅评审单创建人可下载模板与触发解析（`7f98107a`）
- **项目成员校验**：调用方必须为项目成员（`b63d7629`）
- **tag 命名规范**：解析时校验 tag 字符集与格式，非法即报行级错误（`9b4fbe63`）
- **tag 长度**：tag 名称最长 50 字符（`75b41e6e`）

### 3. 模板结构调整

- 删除"制品包路径"列，路径改为前端勾选（`bc50107b`）
- 删除"制品包 tag 来源与分支"列，统一改名"源码仓来源"（`905e907a`）
- 源码包页删除"发布方式"列（`df42b372`）
- 修复表头批注错位一列（`a0144413`）

### 4. 配套缺陷修复

| 问题                                                 | 修复                                                       |
| ---------------------------------------------------- | ---------------------------------------------------------- |
| ClamAV 告警行误入病毒扫描结果表                      | `SafeScanServiceImpl` 入库前按告警行特征过滤（`78d58942`） |
| PyPI 上传遇校验文件抛 InvalidDistribution            | 上传前过滤校验文件（`468f0ddd`）                           |
| 表格解析 pypi 仓库 ID 填充字段错位                   | 修正列映射（`1cf002c9`）                                   |
| pypi 仓库 ID 空串致评审单详情查询崩溃                | 空串防御（`5f9b38ad`）                                     |
| `ReleaseArtifactExcelServiceImpl` 冗余 DataFormatter | 清理死代码（`180fab87`）                                   |

## 影响范围

- **代码仓**：openlibing-platform-release（15 files，+1942/-9）
- **模块**：release 业务层（Controller/Service/VO）、SafeScan、测试
- **前端配合**：openlibing-web（制品包路径勾选交互，关联 #385）
- **无外部接口契约破坏**：新增端点，未变更既有端点行为（除模板列结构）

## 安全考量

- 上传解析入口实施三层权限校验（reviewId → 创建人 → 项目成员），防止越权读写他人评审单
- Excel 解析使用 POI 标准库，限制读取范围，避免恶意文件放大攻击面
- 无新增凭证/敏感信息落盘

## 测试策略

- 单元测试：`ReleaseArtifactExcelServiceImplTest`（783 行，覆盖模板生成/解析/逐行校验）、`SafeScanServiceImplTest`、`ReleaseBaseServiceImplTest`、`ReleaseDecisionServiceImplTest`
- 回归验证：模板下载、上传解析、病毒扫描入库、PyPI 上传全链路
