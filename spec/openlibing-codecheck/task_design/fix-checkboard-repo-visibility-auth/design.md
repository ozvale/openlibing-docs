# fix-checkboard-repo-visibility-auth — 技术设计

## 1. 方案设计

在网关允许免登录的看板/导出 API 上，增加**业务层二级校验**：根据任务维度解析出 `RepoInfoEntity`，再按是否携带 `userId` 分支：

```
请求（userId 可选）
  → Controller / Delegate / ExcelReportImpl
    → CheckboardRepoAccessHelper（或 Service 门面）
        → userId 为空？
            是 → 仓 visibility 是否公开/开源？ 否 → 4001
            否 → framework Feign 仓读权限？ 否 → 403
        → 通过 → 继续原有查询/导出逻辑
```

全量检查与 MR 门禁使用**不同的 visibility 枚举值**：全量看 `public` 字符串；MR 看 `REPO_EXTERNAL` 常量。

## 2. 实现逻辑设计

### 2.1 入口与 Helper 方法映射

| 业务入口                            | Helper 方法                     | 定位键                       |
| ----------------------------------- | ------------------------------- | ---------------------------- |
| 全量任务详情 `getTaskResultDetails` | `assertFullSummaryAccess`       | summaryId                    |
| 全量趋势 `getFullTaskTrend`         | `assertFullTaskAccess`          | taskId → summary             |
| 详情数量 `getDetailNum`（全量）     | `assertFullSummaryAccess`       | summaryId                    |
| 详情数量 `getDetailNum`（MR）       | `assertIncAccess`               | uuid                         |
| Excel 提交任务                      | `assertExportAccess`            | summaryId + checkType + uuid |
| Excel 状态 / 按 recordKey 导出      | `assertExportAccessByRecordKey` | 先查 `ExportRecord` 再分流   |

### 2.2 响应约定

| 场景                       | code  | message                       |
| -------------------------- | ----- | ----------------------------- |
| summaryId/taskId/uuid 为空 | 50001 | `* must not empty`            |
| 免登录 + 非公开仓          | 4001  | `private repo, no permission` |
| 已登录 + 无仓读权限        | 403   | `no permission`               |
| 通过                       | —     | Helper 返回 `null`            |

文件导出拒绝时：`exportBoardByFile` 返回 `error.txt` 内容的 `FileResponse`。

## 3. 类设计

| 类                                           | 职责                                                |
| -------------------------------------------- | --------------------------------------------------- |
| `CheckboardRepoAccessHelper`                 | 仓解析、visibility 判断、Feign 读权限、assert* 系列 |
| `CheckboardRepoAccessService`                | 导出链路门面                                        |
| `CheckboardDelegateImpl`                     | 看板业务；关键读接口前调用 assert*                  |
| `ExcelReportImpl` / `FileDownLoadController` | 导出前校验                                          |

## 4. 数据模型设计

不涉及表结构变更。鉴权依赖 `RepoInfoEntity.visibility`、`ExportRecord.checkType/uuid`、任务与 repo 关联字段。

## 5. 性能设计

每次受保护请求增加少量 DB 查询 + 可选 1 次 Feign；免登录路径不调 Feign。

## 6. API 接口设计

| 方法     | 路径（ci-portal 前缀略）            | 变更                             |
| -------- | ----------------------------------- | -------------------------------- |
| GET      | `/codecheck/getDetailNum`           | 新增 optional `userId`           |
| GET      | `/codecheck/full/task/issues/trend` | 新增 optional `userId`           |
| GET/POST | Excel 导出相关                      | optional `userId` 或 Body.userId |

## 7. 安全设计

鉴权：继承原有鉴权逻辑

敏感信息：不打印日志，不明文存储数据库，不可下载

硬编码：appkey，token，cookie不写在代码中

审计日志：操作记录可追溯

---

## 跨仓影响

- 依赖 framework `checkRepoUserNamePermission`。
- 网关/前端登录态需透传 `userId`。
