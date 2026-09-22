# License 文件兼容性分析继承逻辑 — 设计文档

## 1. 背景与目标

版本扫描的兼容性分析会对仓库中每个文件判定 License 兼容结论（Yes / No / Unrecognized）。
当同一文件（内容不变）在多次扫描、多个仓库、多个分支中反复出现时，运营人员不得不重复进行人工判定。

**继承逻辑**的目标：以文件内容 MD5 为唯一标识，将人工分析结论持久化到 MySQL，后续任何扫描只要遇到相同内容的文件即自动继承已有的人工结论，避免重复劳动。

## 2. 核心概念

| 概念 | 说明 |
|------|------|
| `fileHash` | 文件内容的 MD5 十六进制字符串（32 位小写），作为跨扫描、跨仓库的文件唯一标识 |
| 人工分析结论 | 运营人员对某文件做出的风险判定：`HAS_RISK(1)` / `NO_RISK(0)` + 文字说明 |
| 继承 | 新版本扫描处理文件时，若 `tbl_license_manual_analysis` 中已存在该 fileHash 的记录，则将人工结论写入新 LicenseIssue，并覆盖自动兼容性判定 |
| 优先级 | 人工结论 > 自动判定。继承逻辑在自动兼容性分析之后执行，可覆盖 `compatible` 字段 |

## 3. 数据模型

### 3.1 MySQL — `tbl_license_manual_analysis`

存储全局人工分析结论，以 `file_hash` 为检索键。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(64) | PK, NOT NULL | UUID 主键 |
| file_hash | VARCHAR(128) | NOT NULL, INDEX | 文件内容 MD5 |
| risk_level | VARCHAR(16) | NOT NULL | 风险等级编码：`0`=无风险, `1`=有风险 |
| description | VARCHAR(1024) | NULL | 分析说明 |
| analyzed_by | VARCHAR(64) | NULL | 分析人（userName） |
| scan_id | VARCHAR(64) | NULL | 首次分析时关联的扫描 ID |
| file_path | VARCHAR(512) | NULL | 首次分析时的文件路径 |
| created_at | DATETIME | NULL | 创建时间 |
| updated_at | DATETIME | NULL | 最后更新时间 |

索引：`idx_lma_file_hash (file_hash)`

Liquibase changelog：`src/main/resources/db/changelog/mysql/20260724/create-tbl-license-manual-analysis.xml`

### 3.2 MongoDB — `license_issue` 集合（新增字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| fileHash | String | 文件内容 MD5，扫描时写入 |
| manualRiskLevel | String | 继承或人工设置的风险等级编码 |
| manualDescription | String | 继承或人工设置的分析说明 |

### 3.3 枚举 — `ManualRiskLevel`

```java
public enum ManualRiskLevel {
  NO_RISK("0", "无风险"),
  HAS_RISK("1", "有风险");
}
```

路径：`com.openlibing.sca.common.enums.ManualRiskLevel`

## 4. 核心流程

### 4.1 版本扫描中的继承（读路径）

```
analysisVersion()
  └─ computeFileMd5Hashes(scanRequestVO)      // ① 预计算 workspace 所有文件 MD5
  └─ compatibleVersion(issue, scanRequestVO, fileHashes)
       └─ processFileLicenses(...)
            for each file:
              ├─ createLicenseIssue(...)       // ② 构建 LicenseIssue
              ├─ set fileHash                  // ③ 写入 MD5
              ├─ analyzeLicenseCompatibility() // ④ 自动兼容性判定
              └─ inheritManualAnalysis()       // ⑤ 继承人工结论（覆盖 compatible）
```

**关键实现**（`IntegrationApiServiceImpl`）：

1. **`computeFileMd5Hashes`**：在 workspace 被删除前，使用 `Files.walk` 遍历所有常规文件，逐个计算 MD5（8KB buffer + `MessageDigest`），返回 `Map<相对路径, md5hex>`。
2. **`processFileLicenses`**：遍历解析出的文件-License 映射，跳过无效文件后，为每个文件设置 fileHash、执行自动兼容性分析，最后调用继承。
3. **`inheritManualAnalysis`**：
   - 通过 `licenseManualAnalysisMapper.selectByFileHash(fileHash)` 查询 MySQL。
   - 若存在记录：设置 `manualRiskLevel`、`manualDescription`。
   - 同步覆盖 `compatible`：`HAS_RISK → "No"`，`NO_RISK → "Yes"`。
   - 异常仅 warn 日志，不中断扫描。

### 4.2 人工分析保存（写路径）

```
POST /license/manualAnalysis/batch?userName=xxx
  Body: List<LicenseAnalysisVO>
    └─ batchManualAnalysis(items, userName)
         for each item:
           └─ updateLicenseIssueManualAnalysis(item, userName)
                ├─ ① 更新 MongoDB（按 _id + fileHash 定位）
                │     set manualRiskLevel, manualDescription, compatible
                └─ ② upsertManualAnalysis(item, userName)
                      ├─ selectByFileHash → 存在则 update
                      └─ 不存在则 insert（UUID 主键）
```

**入参 `LicenseAnalysisVO`**：

| 字段 | 校验 | 说明 |
|------|------|------|
| objectId | @NotBlank | LicenseIssue 的 MongoDB _id |
| fileHash | @NotBlank | 文件 MD5 |
| file | — | 文件路径（冗余记录） |
| manualRiskLevel | — | 风险等级编码 |
| manualDescription | — | 分析说明 |

**兼容性联动**：保存人工分析时同步更新 `compatible` 字段（与继承逻辑一致）：
- `HAS_RISK(1)` → `compatible = "No"`
- `NO_RISK(0)` → `compatible = "Yes"`

### 4.3 查询展示

`getLicenseIssue` 查询文件详情时，将 `manualRiskLevel` 编码通过 `ManualRiskLevel.getDescriptionByCode()` 转为中文描述（"无风险"/"有风险"）后返回前端。

## 5. 涉及文件清单

| 文件 | 职责 |
|------|------|
| `IntegrationApiServiceImpl.java` | 扫描主流程：computeFileMd5Hashes / processFileLicenses / inheritManualAnalysis |
| `LicenseServiceImpl.java` | 人工分析保存：batchManualAnalysis / upsertManualAnalysis / 缓存刷新 |
| `LicenseController.java` | HTTP 接口：`POST /license/manualAnalysis/batch`、`POST /license/cache/refresh` |
| `LicenseIssue.java` | MongoDB 实体（新增 fileHash / manualRiskLevel / manualDescription） |
| `LicenseManualAnalysis.java` | MySQL 实体 + 手写 Builder（EI_EXPOSE_REP2 修复） |
| `LicenseManualAnalysisMapper.java` | MyBatis Mapper 接口 |
| `LicenseManualAnalysisMapper.xml` | SQL 映射（insert / update / selectByFileHash） |
| `LicenseAnalysisVO.java` | 批量人工分析入参 VO |
| `ManualRiskLevel.java` | 风险等级枚举 |
| `create-tbl-license-manual-analysis.xml` | Liquibase 建表 changelog |

## 6. 设计决策

| 决策 | 理由 |
|------|------|
| 以文件内容 MD5 而非文件路径作为继承键 | 同一文件可能出现在不同仓库/分支/路径下，内容相同即应继承 |
| 人工结论覆盖自动判定 | 人工分析成本更高、准确性更强，应作为最终结论 |
| 继承失败仅 warn 不中断 | 继承是增强功能，不应因 MySQL 查询异常导致整次扫描失败 |
| MySQL 存储人工结论（而非仅 MongoDB） | 需要跨 scanId 全局检索，MongoDB 按 scanId 分区不便于全局去重 |
| selectByFileHash 取 updated_at DESC LIMIT 1 | 同一 fileHash 理论上唯一，但允许历史脏数据时取最新 |
| 预计算 MD5（workspace 删除前） | workspace 在异步分析前会被清理，必须提前计算 |

## 7. 接口摘要

### 7.1 批量人工分析

```
POST /license/manualAnalysis/batch?userName={userName}
Content-Type: application/json

[
  {
    "objectId": "665f...",
    "fileHash": "d41d8cd98f00b204e9800998ecf8427e",
    "file": "src/main/java/Foo.java",
    "manualRiskLevel": "1",
    "manualDescription": "GPL 传染风险"
  }
]
```

响应：`200 "批量分析完成"` / `500 "批量分析失败"`

### 7.2 缓存刷新

```
POST /license/cache/refresh
```

异步清空并重建所有社区的 License 看板 Redis 缓存。

## 8. 风险与注意事项

- MD5 碰撞概率极低但非零；若需更高安全性可后续升级为 SHA-256。
- `tbl_license_manual_analysis` 当前无唯一约束（仅普通索引），并发写入同一 fileHash 可能产生重复行，查询取最新一条兜底。
- 继承逻辑在每个文件级别执行一次 MySQL 查询，大仓扫描（数万文件）可能有性能压力，后续可考虑批量预加载或 Redis 缓存。
