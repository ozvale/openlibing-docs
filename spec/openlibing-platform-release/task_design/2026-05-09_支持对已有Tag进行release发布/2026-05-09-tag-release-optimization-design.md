# 发布流程优化设计文档 - 支持已有Tag发布

## 1. 需求概述

### 1.1 需求背景

现有发布流程要求用户输入新的Tag名称，系统根据制品包构建的commitId自动创建Tag后进行发布。现需优化流程，支持用户选择已有Tag进行发布，同时增加commitId匹配校验。

### 1.2 需求目标

1. 用户可以搜索并选择已有Tag进行发布
2. 用户可以手动输入新Tag，发布时自动创建
3. 选择已有Tag时，校验Tag指向的commitId与制品包构建的commitId是否匹配
4. commitId不匹配时，返回详细对比信息

### 1.3 用户角色

社区开发者

---

## 2. 流程设计

### 2.1 整体流程

```
步骤1: 用户输入/搜索Tag
        │
        ├─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
   搜索选择已有Tag                          手动输入新Tag
   （新增搜索API）                           （前端tips提示：发布时自动创建）
        │                                         │
        ├─────────────────────────────────────────┤
        │                                         │
        ▼                                         ▼
步骤2: 用户选择制品包
        │
        ▼
步骤3: 异步完整性验证（病毒扫描 + Tag commitId校验 + SHA256校验）
        │
        ▼
步骤3.1: 病毒扫描（现有）
        │
        ▼
步骤3.2: Tag commitId校验（新增）
        │
        ├─────────────────────────────────────────┐
        │                                         │
        ▼                                         ▼
   Tag存在？                               Tag不存在
        │                                         │
        ▼                                         ▼
   校验Tag.commitId                         校验通过
   == 制品包.commitId                       （记录：Tag不存在）
        │                                         │
        ├─────────────┬─────────────┐             │
        │             │             │             │
        ▼             ▼             ▼             ▼
    匹配成功       匹配失败       校验异常      校验通过
        │             │             │             │
        ▼             ▼             ▼             ▼
    记录成功     记录失败详情    记录异常      记录通过
        │             │             │             │
        ▼             ▼             ▼             ▼
步骤3.3: SHA256完整性校验（现有）
        │
        ▼
步骤4: 评审过程（卡点）
        │
        ▼
步骤5: 发布前重新校验Tag ──▶ 不存在则自动创建（现有实现）
        │
        ▼
步骤6: 发布
```

### 2.2 与现有流程对比

| 环节 | 现有流程 | 优化后流程 |
|------|----------|------------|
| Tag输入 | 仅支持手动输入新Tag | 支持搜索已有Tag + 手动输入新Tag |
| Tag校验 | 已存在同名Tag则报错 | 已存在Tag时校验commitId匹配 |
| Tag创建 | 完整性验证阶段创建 | 发布前重新校验并创建 |
| 校验结果 | 简单错误提示 | 详细对比信息返回 |

---

## 3. 技术设计

### 3.1 新增API

#### 3.1.1 搜索已有Tag API

**接口路径**: `GET /api/release/tag/search`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| projectId | String | 是 | 项目ID |
| repoUrl | String | 是 | 仓库URL |
| keyword | String | 否 | 搜索关键字（模糊匹配） |
| pageNum | Integer | 否 | 页码，从1开始，默认1 |
| pageSize | Integer | 否 | 返回数量，默认20，最大100 |

**响应结构**:

```json
{
    "code": 200,
    "msg": "success",
    "data": {
        "tagList": [
            {
                "tagName": "v1.0.0",
                "commitId": "abc123...",
                "createTime": "2024-01-01 10:00:00"
            }
        ],
        "total": 100,
        "pageNum": 1,
        "pageSize": 20,
        "totalPages": 5
    }
}
```

**业务逻辑**：
1. 获取所有Tag列表
2. 按关键字过滤（如果keyword不为空）
3. 按ASCII码升序排序
4. 计算分页信息（total、totalPages）
5. 参数校验和调整
6. 分页截取并返回结果

### 3.2 异步完整性验证增强

#### 3.2.1 改动位置

完整性验证在 [SafeScanServiceImpl.java:230](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/SafeScanServiceImpl.java#L230) 的 `executeVirusScan` 方法中实现。

现有流程：
1. 防止路径穿越校验
2. 下载软件包
3. 获取软件包信息
4. 病毒扫描
5. SHA256完整性校验

**新增步骤**：在病毒扫描之后、SHA256完整性校验之前增加Tag commitId校验。

#### 3.2.2 校验逻辑

在 `executeVirusScan` 方法中增加Tag commitId校验逻辑：

```
executeVirusScan方法增强流程：
1. 防止路径穿越校验（现有）
2. 下载软件包（现有）
3. 获取软件包信息（现有）
4. 病毒扫描（现有）
5. 【新增】Tag commitId校验：
   a. 获取制品包构建的commitId（从ReleaseSoftwareBuildDataEntity）
   b. 查询Tag是否存在（调用queryRepoTagList）
   c. 如果Tag存在：
      - 获取Tag指向的commitId（调用Git API）
      - 比较Tag.commitId与制品包.commitId
      - 匹配成功：记录校验成功
      - 匹配失败：记录校验失败详情（Tag.commitId、制品包.commitId、repoUrl）
   d. 如果Tag不存在：记录校验通过（Tag不存在）
6. SHA256完整性校验（现有）
```

#### 3.2.3 数据结构变更

在 `ReleaseReviewVirusScanEntity` 表中新增Tag校验结果字段：

```java
/**
 * Tag校验结果（1-匹配成功，2-不匹配，3-Tag不存在，4-校验异常）
 */
private Integer tagValidationResult;

/**
 * Tag校验详情（JSON格式，包含tagName、tagCommitId、artifactCommitId、repoUrl、message）
 */
private String tagValidationDetail;
```

**匹配失败时的记录结构**:

```json
{
    "tagName": "v1.0.0",
    "tagCommitId": "abc123def456",
    "artifactCommitId": "xyz789uvw123",
    "repoUrl": "https://gitcode.com/xxx/xxx.git",
    "message": "Tag与制品包commitId不匹配"
}
```

### 3.3 发布前Tag创建（复用现有实现）

现有代码在发布前已有Tag校验和创建逻辑，无需修改：

- [ReleaseRepoTagHandleServiceImpl.java:119](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java#L119) - `createTags()` 方法

---

## 4. 改动清单

### 4.1 后端改动

| 序号 | 改动项 | 改动文件 | 说明 |
|------|--------|----------|------|
| 1 | 新增Tag搜索API | ReleaseTagController.java | 新增Controller和搜索方法 |
| 2 | Tag搜索Service | ReleaseRepoTagHandleServiceImpl.java | 新增搜索方法，支持模糊匹配 |
| 3 | 获取Tag详情方法 | ReleaseRepoTagHandleServiceImpl.java | 新增获取Tag commitId的方法 |
| 4 | 完整性验证增强 | SafeScanServiceImpl.java | 在executeVirusScan方法中，病毒扫描后、SHA256校验前增加Tag commitId校验 |
| 5 | 新增校验结果字段 | ReleaseReviewVirusScanEntity.java | 增加tagValidationResult、tagValidationDetail字段 |
| 6 | 数据库表变更 | release_review_virus_scan表 | 新增2个字段 |

### 4.2 前端改动

| 序号 | 改动项 | 说明 |
|------|--------|------|
| 1 | Tag输入组件 | 改为支持搜索选择的组合组件 |
| 2 | Tips提示 | 输入新Tag时显示"发布时自动创建"提示 |
| 3 | 校验结果展示 | 展示详细对比信息（Tag.commitId vs 制品包.commitId） |

---

## 5. 测试要点

### 5.1 功能测试

| 测试场景 | 预期结果 |
|----------|----------|
| 搜索已有Tag并选择 | 正确返回匹配的Tag列表 |
| 选择已有Tag，commitId匹配 | 病毒扫描后Tag校验成功，SHA256校验继续执行 |
| 选择已有Tag，commitId不匹配 | 病毒扫描后Tag校验失败，记录详细对比信息 |
| 输入新Tag | 病毒扫描后Tag校验通过（Tag不存在），SHA256校验继续执行 |
| 输入已存在的Tag名称 | 按已有Tag处理，进行commitId校验 |

### 5.2 边界测试

| 测试场景 | 预期结果 |
|----------|----------|
| Tag搜索关键字为空 | 返回全部Tag（限制数量） |
| Tag搜索无匹配结果 | 返回空列表 |
| 仓库无Tag | 搜索返回空列表 |
| 制品包无commitId信息 | 记录校验异常 |
| Git API获取Tag commitId失败 | 记录校验异常 |

---

## 6. 风险评估

| 风险项 | 风险等级 | 应对措施 |
|--------|----------|----------|
| Git API调用超时 | 中 | 增加超时配置，异步处理 |
| Tag数量过多导致搜索慢 | 低 | 限制返回数量，支持分页 |
| commitId获取失败 | 中 | 增加异常处理，记录校验异常 |
| 病毒扫描流程变长 | 低 | Tag校验放在病毒扫描后，不影响扫描结果 |

---

## 7. 附录

### 7.1 相关代码位置

- 完整性验证入口: [SafeScanServiceImpl.java:230](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/SafeScanServiceImpl.java#L230) - `executeVirusScan()` 方法
- Tag查询: [ReleaseRepoTagHandleServiceImpl.java:73](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java#L73) - `queryRepoTagList()` 方法
- Tag创建: [ReleaseRepoTagHandleServiceImpl.java:119](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java#L119) - `createTags()` 方法
- 发布入口: [ReleaseDecisionServiceImpl.java:199](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseDecisionServiceImpl.java#L199) - `runRelease()` 方法
- Tag存在校验: [ReleaseBaseServiceImpl.java:761-764](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseBaseServiceImpl.java#L761-L764)
- 病毒扫描实体: [ReleaseReviewVirusScanEntity.java](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/entity/base/ReleaseReviewVirusScanEntity.java) - 新增Tag校验结果字段
- 构建数据实体: [ReleaseSoftwareBuildDataEntity.java](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/entity/base/ReleaseSoftwareBuildDataEntity.java) - 包含commitId信息
