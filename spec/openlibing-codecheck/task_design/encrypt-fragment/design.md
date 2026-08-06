# Design: fragment 代码片段编码存储及日志泄露防护

## 技术方案

### 编码方案

使用 Base64 编码对 `CodeCheckIssueFragment.lineContent` 进行编码存储，通过 `FragmentCryptoUtil` 工具类统一处理：

> 说明：本方案仅做 Base64 编解码（非密码学加密），目的是避免明文密钥等内容在数据库中被直接审计/检索。工具类名 `FragmentCryptoUtil`、方法名 `encryptFragments`/`decryptFragments` 沿用历史命名，实际行为是 Base64 编码与解码。

- **编码时机**：入库前，在 Operation 层的 insert/save 方法中调用
- **解码时机**：查询后，在 Operation 层的 find/aggregate 方法返回结果前调用
- **编码粒度**：仅编码 `CodeCheckIssueFragment.lineContent` 字段（实际代码内容），`lineNum`/`startOffset`/`endOffset` 等元数据不编码
- **兼容性**：解码失败时保留原始值（兼容历史未编码数据），编码失败时使用占位提示词

### 解码安全机制（两阶段验证）

`Base64.isBase64()` 只检查字符是否属于 Base64 字母表（A-Z a-z 0-9 + / =），无法区分纯字母明文（如 "pass"、"return"、"test"）和真正的 Base64 编码数据。采用两阶段验证解决：

1. **isBase64 快速过滤**：含空格、特殊字符的源码（如 `"int x = 1;"`）在此被过滤，直接保留原值
2. **回检验证**：通过 isBase64 后，执行 decode → re-encode → 比对是否与原始值一致；不一致说明是碰巧由纯 Base64 字母表字符组成的明文，保留原值

回检原理：真正的 Base64 编码数据经过 decode → re-encode 后结果与原始值一致；而纯字母明文 decode 后产生乱码，re-encode 后结果与原始值不同。

### 入库编码点

| 类                     | 方法                      | 集合                                   |
| ---------------------- | ------------------------- | -------------------------------------- |
| FullDetailsOperation   | saveInfo()                | task_result_details                    |
| IncDetailsOperation    | insertList()              | task_inc_result_details                |
| DatarecoveryOperation  | insertList()              | task_inc_result_details                |
| ProblemShieldOperation | saveInfo()                | full_shield_detail / inc_shield_detail |
| ProblemShieldOperation | saveShieldDetail()        | full_shield_detail / inc_shield_detail |
| ProblemShieldOperation | getAddFullShieldDetails() | full_shield_detail / inc_shield_detail |

### 查询解码点

| 类                     | 方法                                                                                                                                             | 集合                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| FullDetailsOperation   | getFullMetricsDetail(), queryDetails(), getCmetricsDetail(), findDetailById(), queryDetailsUpload(), findNotSolutionDetails(), getDetailByPage() | task_result_details / full_shield_detail    |
| IncDetailsOperation    | getIncMetrics(), getIncResultDetail(), getInvalidIncDefect(), getAllPrDefectVos()                                                                | task_inc_result_details / inc_shield_detail |
| ProblemShieldOperation | getShieldDetailById(), getShieldDetailByUserId(), getInReviewAndUpdateStatu(), fullShieldDetail(), incShieldDetail()                             | full_shield_detail / inc_shield_detail      |
| ShieldDetailOperation  | shieldDetail()                                                                                                                                   | full_shield_detail / inc_shield_detail      |

### 日志泄露修复

| 文件                     | 修改                                                  |
| ------------------------ | ----------------------------------------------------- |
| DatarecoveryDelegateImpl | `successDefects.toString()` → `successDefects.size()` |
| CodeCheckIssueFragment   | lineContent 添加 `@ToString.Exclude`                  |

### 防御性措施

| 类                         | 字段                       | 注解              |
| -------------------------- | -------------------------- | ----------------- |
| DefectVo                   | fragment                   | @ToString.Exclude |
| CodeCheckIssueFragment     | lineContent                | @ToString.Exclude |
| CodeCheckRuleVo            | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleSheet         | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleAccountVo     | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleEntity        | rightExample, errorExample | @ToString.Exclude |
| CodeCheckRuleAccountEntity | rightExample, errorExample | @ToString.Exclude |

## 影响范围

- **数据模型**：无 schema 变更，MongoDB 动态集合
- **API 接口**：无接口变更，编解码对调用方透明
- **历史数据**：兼容，两阶段验证确保历史明文不被误解码
- **性能**：编解码操作在 Operation 层，回检验证增加一次 Base64 编解码，对查询性能影响极小
