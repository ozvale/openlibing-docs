# 发布流程优化接口文档 - Tag搜索与校验

## 文档信息

- **版本**: v1.0
- **创建日期**: 2026-05-09
- **作者**: lidebin
- **适用场景**: 支持已有Tag发布，增强发布流程的完整性校验

---

## 1. Tag搜索接口

### 1.1 接口说明

搜索仓库中的Tag列表，支持关键字过滤和分页控制。用于前端展示可选的Tag列表，帮助用户选择已有的Tag进行发布。

### 1.2 基本信息

- **接口地址**: `/tag/search`
- **请求方法**: `GET`
- **权限要求**: 需要登录认证（`@RequiresPermissions`）
- **接口标签**: 关键接口

### 1.3 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| userId | String | 是 | 用户ID | "user123" |
| projectId | String | 是 | 项目ID | "project456" |
| repoUrl | String | 是 | 仓库URL | "https://gitcode.com/openlibing/openlibing-platform-release.git" |
| keyword | String | 否 | 搜索关键字，用于过滤Tag名称 | "v1.0" |
| pageNum | Integer | 否 | 页码，从1开始，默认1 | 1 |
| pageSize | Integer | 否 | 返回数量，默认20，最大100 | 20 |

### 1.4 返回数据结构

#### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "tagList": [
      {
        "tagName": "v1.0.0",
        "commitId": "a1b2c3d4e5f6g7h8i9j0",
        "createTime": "2026-05-09 10:30:00"
      },
      {
        "tagName": "v1.0.1",
        "commitId": "b2c3d4e5f6g7h8i9j0k1",
        "createTime": "2026-05-09 11:45:00"
      }
    ],
    "total": 50,
    "pageNum": 1,
    "pageSize": 20,
    "totalPages": 3
  }
}
```

#### 失败响应

```json
{
  "code": 500,
  "message": "搜索Tag失败: 具体错误信息",
  "data": null
}
```

### 1.5 数据对象说明

#### TagInfoVO - Tag信息对象

| 字段名 | 类型 | 说明 |
|--------|------|------|
| tagName | String | Tag名称 |
| commitId | String | Tag对应的commitId |
| createTime | String | Tag创建时间 |

#### TagSearchResultVO - Tag搜索结果对象

| 字段名 | 类型 | 说明 |
|--------|------|------|
| tagList | List<TagInfoVO> | Tag列表 |
| total | Integer | 总数量（过滤后） |
| pageNum | Integer | 当前页码 |
| pageSize | Integer | 每页大小 |
| totalPages | Integer | 总页数 |

### 1.6 请求示例

#### 示例1：搜索所有Tag

```http
GET /tag/search?userId=user123&projectId=project456&repoUrl=https://gitcode.com/openlibing/openlibing-platform-release.git
```

#### 示例2：搜索包含关键字的Tag

```http
GET /tag/search?userId=user123&projectId=project456&repoUrl=https://gitcode.com/openlibing/openlibing-platform-release.git&keyword=v1.0&pageSize=10
```

#### 示例3：分页查询第2页

```http
GET /tag/search?userId=user123&projectId=project456&repoUrl=https://gitcode.com/openlibing/openlibing-platform-release.git&pageNum=2&pageSize=10
```

#### 示例4：关键字过滤+分页

```http
GET /tag/search?userId=user123&projectId=project456&repoUrl=https://gitcode.com/openlibing/openlibing-platform-release.git&keyword=v1.0&pageNum=1&pageSize=5
```

### 1.7 业务逻辑说明

1. 根据仓库URL和项目ID获取仓库访问权限
2. 调用Git平台API（GitCode/AtomGit/Gitee）获取Tag列表
3. 如果提供了keyword，则过滤包含该关键字的Tag
4. **按ASCII码升序排序所有Tag**
5. 计算分页信息（total、totalPages）
6. 参数校验和调整（pageNum超出范围时调整）
7. 分页截取，只对当前页的Tag获取commitId信息
8. 返回Tag列表和完整分页信息

### 1.8 前端集成建议

1. **Tag选择器**: 使用此接口构建Tag下拉选择器，支持搜索和分页
2. **实时搜索**: 用户输入关键字时实时调用接口，展示匹配的Tag
3. **Tag信息展示**: 展示Tag名称、commitId和创建时间，帮助用户确认选择
4. **错误处理**: 处理接口失败情况，展示友好错误提示
5. **分页组件**: 使用pageNum、pageSize、totalPages构建分页组件
6. **页码跳转**: 支持页码输入和上一页/下一页功能
7. **总页数展示**: 展示总页数和当前页码信息，例如"第1页/共5页"

---

## 2. Tag校验功能

### 2.1 功能说明

在发布流程的病毒扫描阶段，新增Tag commitId校验功能，确保用户选择的Tag与制品包的commitId匹配，增强发布流程的完整性校验。

### 2.2 校验流程

Tag校验集成在病毒扫描流程（`executeVirusScan`）中，校验逻辑如下：

1. 获取制品包的commitId（从构建数据中获取）
2. 检查用户选择的Tag是否存在于仓库中
3. 如果Tag不存在，返回"Tag不存在"状态（发布时会自动创建）
4. 如果Tag存在，获取Tag对应的commitId
5. 比较制品包commitId和Tag commitId是否匹配
6. 返回校验结果和详细信息

### 2.3 校验结果枚举

| 枚举值 | 代码 | 中文描述 | 英文描述 | 说明 |
|--------|------|----------|----------|------|
| MATCH_SUCCESS | 1 | 匹配成功 | match success | Tag commitId与制品包commitId完全匹配 |
| MISMATCH | 2 | 不匹配 | mismatch | Tag commitId与制品包commitId不匹配，发布会失败 |
| TAG_NOT_EXIST | 3 | Tag不存在 | tag not exist | 用户选择的Tag在仓库中不存在，发布时会自动创建 |
| VALIDATION_ERROR | 4 | 校验异常 | validation error | 校验过程出现异常（如获取commitId失败） |

### 2.4 校验详情数据结构

校验详情以JSON格式存储在`tagValidationDetail`字段中：

```json
{
  "tagName": "v1.0.0",
  "tagCommitId": "a1b2c3d4e5f6g7h8i9j0",
  "artifactCommitId": "a1b2c3d4e5f6g7h8i9j0",
  "repoUrl": "https://gitcode.com/openlibing/openlibing-platform-release.git",
  "message": "匹配成功"
}
```

#### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| tagName | String | 用户选择的Tag名称 |
| tagCommitId | String | Tag对应的commitId（Tag不存在时为空） |
| artifactCommitId | String | 制品包的commitId |
| repoUrl | String | 仓库URL |
| message | String | 校验结果描述信息 |

### 2.5 数据库字段变更

在`release_review_virus_scan`表中新增两个字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| tagValidationResult | Integer | Tag校验结果代码（1-4） |
| tagValidationDetail | String | Tag校验详情（JSON格式） |

### 2.6 前端展示建议

#### 2.6.1 校验结果展示

根据`tagValidationResult`值展示不同的状态：

- **1（匹配成功）**: 显示绿色图标，提示"Tag校验通过"
- **2（不匹配）**: 显示红色图标，提示"Tag与制品包不匹配，请重新选择Tag或制品包"
- **3（Tag不存在）**: 显示黄色图标，提示"Tag不存在，发布时将自动创建"
- **4（校验异常）**: 显示灰色图标，提示"校验异常，请检查仓库配置"

#### 2.6.2 详情展示

点击校验结果图标时，展示`tagValidationDetail`中的详细信息：

```
Tag名称: v1.0.0
Tag commitId: a1b2c3d4e5f6g7h8i9j0
制品包 commitId: a1b2c3d4e5f6g7h8i9j0
仓库URL: https://gitcode.com/openlibing/openlibing-platform-release.git
校验结果: 匹配成功
```

---

## 3. 完整业务流程

### 3.1 发布流程集成

#### 步骤1：用户选择Tag

前端调用`/tag/search`接口，展示可选的Tag列表，用户选择一个Tag。

#### 步骤2：提交发布申请

用户提交发布申请，包含选择的Tag名称和制品包信息。

#### 步骤3：病毒扫描与Tag校验

后端在执行病毒扫描时，自动进行Tag校验：
- 获取制品包的commitId
- 校验Tag commitId是否匹配
- 将校验结果保存到数据库

#### 步骤4：前端展示校验结果

前端查询病毒扫描结果时，获取`tagValidationResult`和`tagValidationDetail`，展示校验状态。

#### 步骤5：发布执行

根据校验结果决定发布策略：
- **匹配成功**: 直接使用已有Tag发布
- **Tag不存在**: 自动创建Tag后发布
- **不匹配**: 阻止发布，提示用户重新选择
- **校验异常**: 阻止发布，提示检查配置

### 3.2 前端交互流程图

```
用户输入Tag名称
    ↓
调用 /tag/search 接口
    ↓
展示Tag列表（包含commitId和创建时间）
    ↓
用户选择Tag
    ↓
提交发布申请
    ↓
后端执行病毒扫描 + Tag校验
    ↓
前端查询扫描结果
    ↓
展示Tag校验结果（匹配/不匹配/不存在/异常）
    ↓
根据结果决定是否继续发布
```

---

## 4. 错误处理

### 4.1 Tag搜索接口错误

| 错误场景 | 错误信息 | 处理建议 |
|----------|----------|----------|
| 仓库URL无效 | "搜索Tag失败: 仓库URL格式错误" | 检查仓库URL格式 |
| 权限不足 | "搜索Tag失败: 无权限访问仓库" | 检查项目配置的Git token |
| Git平台API异常 | "搜索Tag失败: API调用失败" | 检查Git平台服务状态 |
| 网络异常 | "搜索Tag失败: 网络连接失败" | 检查网络连接 |

### 4.2 Tag校验错误

| 错误场景 | 校验结果代码 | 错误信息 | 处理建议 |
|----------|--------------|----------|----------|
| 制品包无commitId | 4 | "制品包无commitId信息" | 检查制品包构建数据 |
| 获取Tag commitId失败 | 4 | "获取Tag commitId失败" | 检查Git平台API和权限 |
| Tag与制品包不匹配 | 2 | "Tag与制品包commitId不匹配" | 重新选择Tag或制品包 |
| 校验异常 | 4 | "校验异常: 具体错误信息" | 检查仓库配置和网络 |

---

## 5. 测试建议

### 5.1 Tag搜索接口测试

#### 测试场景1：正常搜索

```http
GET /tag/search?userId=testUser&projectId=testProject&repoUrl=https://gitcode.com/openlibing/test-repo.git
```

**预期结果**: 返回Tag列表，包含tagName、commitId、createTime

#### 测试场景2：关键字过滤

```http
GET /tag/search?userId=testUser&projectId=testProject&repoUrl=https://gitcode.com/openlibing/test-repo.git&keyword=v1.0
```

**预期结果**: 只返回包含"v1.0"的Tag

#### 测试场景3：分页控制

```http
GET /tag/search?userId=testUser&projectId=testProject&repoUrl=https://gitcode.com/openlibing/test-repo.git&pageSize=5
```

**预期结果**: 最多返回5个Tag

### 5.2 Tag校验功能测试

#### 测试场景1：Tag匹配成功

- 制品包commitId: `a1b2c3d4`
- Tag commitId: `a1b2c3d4`
- **预期结果**: tagValidationResult = 1，message = "匹配成功"

#### 测试场景2：Tag不匹配

- 制品包commitId: `a1b2c3d4`
- Tag commitId: `b2c3d4e5`
- **预期结果**: tagValidationResult = 2，message = "Tag与制品包commitId不匹配"

#### 测试场景3：Tag不存在

- 制品包commitId: `a1b2c3d4`
- Tag名称: `new-tag`（仓库中不存在）
- **预期结果**: tagValidationResult = 3，message = "Tag不存在，发布时自动创建"

---

## 6. 附录

### 6.1 相关实体类

#### ReleaseReviewVirusScanVo

```java
public class ReleaseReviewVirusScanVo {
    private Integer id;
    private String creatorId;
    private String creatorName;
    private String updaterId;
    private String updaterName;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private Integer reviewId;
    private Integer releaseArtifactInfoId;
    private String scanDetails;
    private String scanResult;
    private String obsBucketName;
    private String fileName;
    private String filePath;
    private String integrityCheck;
    private String sha256Sum;
    private Long contentLength;
    private String lastModified;

    // 新增字段
    private Integer tagValidationResult;  // Tag校验结果
    private String tagValidationDetail;   // Tag校验详情（JSON）
}
```

### 6.2 Git平台支持

当前支持以下Git平台的Tag搜索和校验：

- **GitCode**: https://gitcode.com
- **AtomGit**: https://atomgit.com
- **Gitee**: https://gitee.com

### 6.3 API版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-05-09 | 新增Tag搜索接口和Tag校验功能 |

---

## 7. 联系方式

如有接口使用问题，请联系：

- **接口开发者**: lidebin
- **文档维护**: AI Assistant (Trae AI)
- **Issue反馈**: https://gitcode.com/openlibing/openlibing-platform-release/issues

---

**文档生成时间**: 2026-05-09
**文档版本**: v1.0
**生成工具**: Trae AI
