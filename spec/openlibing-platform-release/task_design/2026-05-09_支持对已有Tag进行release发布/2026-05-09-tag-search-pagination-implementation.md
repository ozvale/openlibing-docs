# Tag搜索接口分页功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为Tag搜索接口添加分页功能，支持pageNum参数，实现ASCII排序和完整分页信息返回

**Architecture:** 在现有Tag搜索接口基础上，添加分页参数，Service层实现过滤-排序-分页逻辑，Controller层添加参数校验，返回完整分页信息

**Tech Stack:** Java 21, Spring Boot 3.x, MyBatis, Lombok

---

## Task 1: 更新TagSearchResultVO类

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/vo/base/TagSearchResultVO.java`

**Step 1: 添加分页信息字段**

在TagSearchResultVO类中添加以下字段：

```java
/**
 * 当前页码
 */
private Integer pageNum;

/**
 * 每页大小
 */
private Integer pageSize;

/**
 * 总页数
 */
private Integer totalPages;
```

**Step 2: 验证字段添加正确**

检查文件内容，确保新增字段已正确添加到类中。

**Step 3: 提交VO类变更**

```bash
git add src/main/java/com/openlibing/platformrelease/business/vo/base/TagSearchResultVO.java
git commit -m "feat: add pagination fields to TagSearchResultVO

Add pageNum, pageSize, totalPages fields for pagination support

Co-authored-by: Trae AI <noreply@trae.ai>
Generated-by: glm-4-5"
```

---

## Task 2: 改造Service层searchTags方法

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java:197-218`

**Step 1: 修改方法签名**

将方法签名从：
```java
public List<TagInfoVO> searchTags(String projectId, String repoUrl, String keyword, Integer pageSize)
```

改为：
```java
public TagSearchResultVO searchTags(String projectId, String repoUrl, String keyword, Integer pageNum, Integer pageSize)
```

**Step 2: 实现过滤-排序-分页逻辑**

替换原有实现，添加完整的过滤、排序、分页逻辑：

```java
public TagSearchResultVO searchTags(String projectId, String repoUrl, String keyword, Integer pageNum, Integer pageSize)
    throws Exception {
    // 1. 获取所有Tag
    List<String> allTags = this.queryRepoTagList(projectId, repoUrl);

    // 2. 按关键字过滤
    List<String> filteredTags = allTags;
    if (StringUtils.isNotBlank(keyword)) {
        filteredTags = allTags.stream()
            .filter(tag -> tag.contains(keyword))
            .collect(Collectors.toList());
    }

    // 3. 按ASCII码升序排序
    filteredTags.sort(String::compareTo);

    // 4. 计算分页信息
    int total = filteredTags.size();
    int totalPages = (total + pageSize - 1) / pageSize;

    // 5. 参数校验
    if (pageNum < 1) {
        pageNum = 1;
    }
    if (pageNum > totalPages && totalPages > 0) {
        pageNum = totalPages;
    }

    // 6. 分页截取
    int startIndex = (pageNum - 1) * pageSize;
    int endIndex = Math.min(startIndex + pageSize, total);

    List<String> pageTags = filteredTags.subList(startIndex, endIndex);

    // 7. 构建TagInfoVO列表（获取commitId）
    List<TagInfoVO> tagList = new ArrayList<>();
    for (String tagName : pageTags) {
        TagInfoVO tagInfo = new TagInfoVO();
        tagInfo.setTagName(tagName);
        tagInfo.setCommitId(this.getTagCommitId(projectId, repoUrl, tagName));
        tagList.add(tagInfo);
    }

    // 8. 构建返回结果
    TagSearchResultVO result = new TagSearchResultVO();
    result.setTagList(tagList);
    result.setTotal(total);
    result.setPageNum(pageNum);
    result.setPageSize(pageSize);
    result.setTotalPages(totalPages);

    return result;
}
```

**Step 3: 添加必要的import**

确保文件顶部包含以下import：

```java
import java.util.stream.Collectors;
```

**Step 4: 验证代码编译**

运行Maven编译命令，确保代码无编译错误：

```bash
mvn clean compile
```

**Step 5: 提交Service层变更**

```bash
git add src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java
git commit -m "feat: implement pagination and sorting in searchTags method

- Add pageNum parameter for pagination support
- Implement keyword filtering before pagination
- Add ASCII ascending sort for tag results
- Return complete pagination info in TagSearchResultVO
- Optimize commitId fetching for current page only

Co-authored-by: Trae AI <noreply@trae.ai>
Generated-by: glm-4-5"
```

---

## Task 3: 改造Controller层searchTags方法

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/controller/ReleaseTagController.java:49-66`

**Step 1: 添加pageNum参数**

在Controller方法参数列表中添加pageNum参数：

```java
@RequestParam(value = "pageNum", required = false, defaultValue = "1") Integer pageNum
```

**Step 2: 添加参数校验逻辑**

在方法开始处添加参数校验：

```java
// 参数校验
if (pageNum == null || pageNum < 1) {
    pageNum = 1;
}
if (pageSize == null || pageSize < 1) {
    pageSize = 20;
}
if (pageSize > 100) {
    pageSize = 100;
}
```

**Step 3: 更新Service调用**

修改Service调用，传入pageNum参数：

```java
TagSearchResultVO result = releaseRepoTagHandleService.searchTags(projectId, repoUrl, keyword, pageNum, pageSize);
```

**Step 4: 简化返回逻辑**

直接返回Service层的结果，移除手动构建逻辑：

```java
return DataResult.successData(result);
```

**Step 5: 完整的Controller方法实现**

确保完整的方法实现如下：

```java
@GetMapping("/search")
public DataResult<TagSearchResultVO> searchTags(
        @RequestParam(value = "userId") String userId,
        @RequestParam(value = "projectId") String projectId,
        @RequestParam(value = "repoUrl") String repoUrl,
        @RequestParam(value = "keyword", required = false) String keyword,
        @RequestParam(value = "pageNum", required = false, defaultValue = "1") Integer pageNum,
        @RequestParam(value = "pageSize", required = false, defaultValue = "20") Integer pageSize) {
    try {
        // 参数校验
        if (pageNum == null || pageNum < 1) {
            pageNum = 1;
        }
        if (pageSize == null || pageSize < 1) {
            pageSize = 20;
        }
        if (pageSize > 100) {
            pageSize = 100;
        }

        // 调用Service层方法
        TagSearchResultVO result = releaseRepoTagHandleService.searchTags(projectId, repoUrl, keyword, pageNum, pageSize);

        return DataResult.successData(result);
    } catch (Exception e) {
        return DataResult.failureMessage("搜索Tag失败: " + e.getMessage());
    }
}
```

**Step 6: 验证代码编译**

运行Maven编译命令，确保代码无编译错误：

```bash
mvn clean compile
```

**Step 7: 提交Controller层变更**

```bash
git add src/main/java/com/openlibing/platformrelease/business/controller/ReleaseTagController.java
git commit -m "feat: add pagination support to tag search controller

- Add pageNum parameter with default value 1
- Add parameter validation for pageNum and pageSize
- Update service call to include pageNum
- Simplify return logic by using service result directly

Co-authored-by: Trae AI <noreply@trae.ai>
Generated-by: glm-4-5"
```

---

## Task 4: 更新设计文档

**Files:**
- Modify: `docs/plans/2026-05-09-tag-release-optimization-design.md:3.1.1`

**Step 1: 更新API参数表格**

在第3.1.1节的参数表格中添加pageNum参数：

```markdown
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| projectId | String | 是 | 项目ID |
| repoUrl | String | 是 | 仓库URL |
| keyword | String | 否 | 搜索关键字（模糊匹配） |
| pageNum | Integer | 否 | 页码，从1开始，默认1 |
| pageSize | Integer | 否 | 返回数量，默认20，最大100 |
```

**Step 2: 更新响应结构示例**

更新响应结构示例，添加分页字段：

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

**Step 3: 添加业务逻辑说明**

在API说明后添加业务逻辑说明：

```markdown
**业务逻辑**：
1. 获取所有Tag列表
2. 按关键字过滤（如果keyword不为空）
3. 按ASCII码升序排序
4. 计算分页信息（total、totalPages）
5. 参数校验和调整
6. 分页截取并返回结果
```

**Step 4: 提交设计文档更新**

```bash
git add docs/plans/2026-05-09-tag-release-optimization-design.md
git commit -m "docs: update tag search API with pagination parameters

- Add pageNum parameter to API specification
- Update response structure with pagination fields
- Add business logic description for sorting and pagination

Co-authored-by: Trae AI <noreply@trae.ai>
Generated-by: glm-4-5"
```

---

## Task 5: 更新接口文档

**Files:**
- Modify: `docs/api/tag-release-api-document.md`

**Step 1: 更新请求参数表格（第1.3节）**

在请求参数表格中添加pageNum参数：

```markdown
| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|--------|------|------|------|--------|
| userId | String | 是 | 用户ID | "user123" |
| projectId | String | 是 | 项目ID | "project456" |
| repoUrl | String | 是 | 仓库URL | "https://gitcode.com/openlibing/openlibing-platform-release.git" |
| keyword | String | 否 | 搜索关键字，用于过滤Tag名称 | "v1.0" |
| pageNum | Integer | 否 | 页码，从1开始，默认1 | 1 |
| pageSize | Integer | 否 | 返回数量，默认20，最大100 | 20 |
```

**Step 2: 更新成功响应示例（第1.4节）**

更新成功响应示例，添加分页字段：

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

**Step 3: 更新TagSearchResultVO对象说明**

在数据对象说明中添加分页字段：

```markdown
#### TagSearchResultVO - Tag搜索结果对象

| 字段名 | 类型 | 说明 |
|--------|------|------|
| tagList | List<TagInfoVO> | Tag列表 |
| total | Integer | 总数量（过滤后） |
| pageNum | Integer | 当前页码 |
| pageSize | Integer | 每页大小 |
| totalPages | Integer | 总页数 |
```

**Step 4: 更新请求示例（第1.6节）**

添加带分页参数的请求示例：

```markdown
#### 示例3：分页查询第2页

```http
GET /tag/search?userId=user123&projectId=project456&repoUrl=https://gitcode.com/openlibing/openlibing-platform-release.git&pageNum=2&pageSize=10
```

#### 示例4：关键字过滤+分页

```http
GET /tag/search?userId=user123&projectId=project456&repoUrl=https://gitcode.com/openlibing/openlibing-platform-release.git&keyword=v1.0&pageNum=1&pageSize=5
```
```

**Step 5: 更新业务逻辑说明（第1.7节）**

更新业务逻辑说明，添加排序和分页逻辑：

```markdown
### 1.7 业务逻辑说明

1. 根据仓库URL和项目ID获取仓库访问权限
2. 调用Git平台API（GitCode/AtomGit/Gitee）获取Tag列表
3. 如果提供了keyword，则过滤包含该关键字的Tag
4. **按ASCII码升序排序所有Tag**
5. 计算分页信息（total、totalPages）
6. 参数校验和调整（pageNum超出范围时调整）
7. 分页截取，只对当前页的Tag获取commitId信息
8. 返回Tag列表和完整分页信息
```

**Step 6: 更新前端集成建议（第1.8节）**

更新前端集成建议，添加分页组件说明：

```markdown
### 1.8 前端集成建议

1. **Tag选择器**: 使用此接口构建Tag下拉选择器，支持搜索和分页
2. **实时搜索**: 用户输入关键字时实时调用接口，展示匹配的Tag
3. **Tag信息展示**: 展示Tag名称、commitId和创建时间，帮助用户确认选择
4. **错误处理**: 处理接口失败情况，展示友好错误提示
5. **分页组件**: 使用pageNum、pageSize、totalPages构建分页组件
6. **页码跳转**: 支持页码输入和上一页/下一页功能
7. **总页数展示**: 展示总页数和当前页码信息，例如"第1页/共5页"
```

**Step 7: 提交接口文档更新**

```bash
git add docs/api/tag-release-api-document.md
git commit -m "docs: update tag search API documentation with pagination

- Add pageNum parameter to request parameters table
- Update response structure with pagination fields
- Add pagination request examples
- Update business logic description with sorting and pagination
- Enhance frontend integration suggestions with pagination component

Co-authored-by: Trae AI <noreply@trae.ai>
Generated-by: glm-4-5"
```

---

## Task 6: 验证和测试

**Files:**
- Test: Manual testing via API call

**Step 1: 启动应用**

启动Spring Boot应用，确保服务正常运行：

```bash
mvn spring-boot:run
```

**Step 2: 测试基础分页**

使用curl或Postman测试基础分页功能：

```bash
curl "http://localhost:8080/tag/search?userId=test&projectId=test&repoUrl=https://gitcode.com/openlibing/test.git&pageNum=1&pageSize=10"
```

预期结果：返回第1页的10条数据，包含total、pageNum、pageSize、totalPages字段

**Step 3: 测试关键字过滤+分页**

测试关键字过滤和分页结合：

```bash
curl "http://localhost:8080/tag/search?userId=test&projectId=test&repoUrl=https://gitcode.com/openlibing/test.git&keyword=v1.0&pageNum=1&pageSize=5"
```

预期结果：只返回包含"v1.0"的Tag，按ASCII排序，分页正确

**Step 4: 测试边界情况**

测试pageNum超出范围的情况：

```bash
curl "http://localhost:8080/tag/search?userId=test&projectId=test&repoUrl=https://gitcode.com/openlibing/test.git&pageNum=100&pageSize=10"
```

预期结果：自动调整为最后一页

**Step 5: 测试无效参数**

测试无效的pageNum和pageSize：

```bash
curl "http://localhost:8080/tag/search?userId=test&projectId=test&repoUrl=https://gitcode.com/openlibing/test.git&pageNum=0&pageSize=-1"
```

预期结果：pageNum自动调整为1，pageSize自动调整为20

**Step 6: 验证排序**

检查返回的Tag列表是否按ASCII升序排序

**Step 7: 提交测试验证**

记录测试结果，确认功能正常工作

---

## Task 7: 最终提交和推送

**Step 1: 检查所有变更**

查看所有未提交的变更：

```bash
git status
```

**Step 2: 查看提交历史**

查看最近的提交历史：

```bash
git log --oneline -10
```

**Step 3: 推送到远程分支**

推送所有提交到远程分支：

```bash
git push origin dev_wx_202603
```

---

## 实施完成检查清单

- [ ] TagSearchResultVO类已添加分页字段
- [ ] Service层searchTags方法已实现过滤-排序-分页逻辑
- [ ] Controller层已添加pageNum参数和参数校验
- [ ] 设计文档已更新API参数和响应结构
- [ ] 接口文档已更新所有相关章节
- [ ] 功能测试已验证分页、排序、参数校验正常
- [ ] 所有变更已提交到git
- [ ] 代码已推送到远程分支
