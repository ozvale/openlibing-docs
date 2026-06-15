# Design: fragment 代码片段加密存储及日志泄露防护

## 技术方案

### 加密方案

复用项目已有的 `SecurityHelper`（底层为 AES-GCM，三段式密钥管理），新增 `FragmentCryptoUtil` 工具类：

- **加密时机**：入库前，在 Operation 层的 insert 方法中调用
- **解密时机**：查询后，在 Operation 层的 find 方法返回结果前调用
- **加密粒度**：仅加密 `CodeCheckIssueFragment.lineContent` 字段（实际代码内容），`lineNum`/`startOffset`/`endOffset` 等元数据不加密
- **兼容性**：解密失败时保留原始值（兼容历史未加密数据），加密失败时抛异常中断入库

### 入库加密点

| 类 | 方法 | 集合 |
|---|---|---|
| FullDetailsOperation | saveInfo() | task_result_details |
| IncDetailsOperation | insertList() | task_inc_result_details |
| DatarecoveryOperation | insertList() | task_inc_result_details |

### 查询解密点

| 类 | 方法 |
|---|---|
| FullDetailsOperation | getFullMetricsDetail(), queryDetails(), getCmetricsDetail(), findDetailById(), queryDetailsUpload(), findNotSolutionDetails(), getDetailByPage() |
| IncDetailsOperation | getIncMetrics(), getIncResultDetail(), getInvalidIncDefect(), getAllPrDefectVos() |

### 日志泄露修复

| 文件 | 修改 |
|---|---|
| DatarecoveryDelegateImpl | `successDefects.toString()` → `successDefects.size()` |

### 防御性措施

| 类 | 字段 | 注解 |
|---|---|---|
| DefectVo | fragment | @ToString.Exclude |
| CodeCheckRuleVo | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleSheet | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleAccountVo | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleEntity | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleAccountEntity | rightExample, errorExample | @ToString.Exclude |

## 影响范围

- **数据模型**：无 schema 变更，MongoDB 动态集合
- **API 接口**：无接口变更，加解密对调用方透明
- **历史数据**：兼容，解密失败保留原值
- **性能**：加解密操作在 Operation 层，对查询性能有轻微影响（AES-GCM 加解密速度快）
