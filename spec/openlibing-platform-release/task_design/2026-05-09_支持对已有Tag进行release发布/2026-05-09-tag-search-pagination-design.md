# Tag搜索接口分页功能设计文档

## 1. 需求概述

### 1.1 需求背景

现有Tag搜索接口 `/tag/search` 只支持简单的数量限制（pageSize），不支持真正的分页功能。当Tag数量较多时，前端无法实现完整的分页展示，用户体验不佳。

### 1.2 需求目标

1. 添加分页参数（pageNum），支持真正的分页查询
2. 对搜索结果按ASCII码升序排序，保证结果有序性
3. 返回完整的分页信息（total、pageNum、pageSize、totalPages），方便前端展示
4. 保持向后兼容，不影响现有接口调用

### 1.3 用户角色

前端开发人员、社区开发者

---

## 2. 技术设计

### 2.1 接口参数变更

#### 2.1.1 新增参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| pageNum | Integer | 否 | 1 | 页码，从1开始 |
| pageSize | Integer | 否 | 20 | 每页大小，最大100 |

#### 2.1.2 完整参数列表

```java
@GetMapping("/search")
public DataResult<TagSearchResultVO> searchTags(
    @RequestParam(value = "userId") String userId,
    @RequestParam(value = "projectId") String projectId,
    @RequestParam(value = "repoUrl") String repoUrl,
    @RequestParam(value = "keyword", required = false) String keyword,
    @RequestParam(value = "pageNum", required = false, defaultValue = "1") Integer pageNum,
    @RequestParam(value = "pageSize", required = false, defaultValue = "20") Integer pageSize
)
```

#### 2.1.3 参数校验规则

- pageNum 必须 >= 1，如果传入0或负数，自动设置为1
- pageSize 必须 >= 1，如果传入0或负数，自动设置为20
- pageSize 最大值限制为100，防止一次请求过多数据
- pageNum 超出总页数时，自动调整为最后一页

### 2.2 返回数据结构变更

#### 2.2.1 TagSearchResultVO新增字段

```java
@Data
public class TagSearchResultVO implements Serializable {
    private static final long serialVersionUID = 1L;

    private List<TagInfoVO> tagList;  // Tag列表
    private Integer total;            // 总数量（过滤后）
    private Integer pageNum;          // 当前页码
    private Integer pageSize;         // 每页大小
    private Integer totalPages;       // 总页数
}
```

#### 2.2.2 成功响应示例

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

### 2.3 Service层实现逻辑

#### 2.3.1 方法签名变更

**变更前**：
```java
public List<TagInfoVO> searchTags(String projectId, String repoUrl, String keyword, Integer pageSize)
```

**变更后**：
```java
public TagSearchResultVO searchTags(String projectId, String repoUrl, String keyword, Integer pageNum, Integer pageSize)
```

#### 2.3.2 实现流程

```
1. 获取所有Tag列表（调用queryRepoTagList）
    ↓
2. 按关键字过滤（如果keyword不为空）
    ↓
3. 按ASCII码升序排序（使用String::compareTo）
    ↓
4. 计算分页信息（total、totalPages）
    ↓
5. 参数校验和调整（pageNum超出范围时调整）
    ↓
6. 分页截取（使用subList）
    ↓
7. 构建TagInfoVO列表（只对当前页的Tag获取commitId）
    ↓
8. 构建返回结果（TagSearchResultVO）
```

#### 2.3.3 核心代码实现

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

### 2.4 Controller层改造

#### 2.4.1 主要变更点

1. 新增 `pageNum` 参数接收
2. 添加参数校验逻辑
3. 直接返回Service层的 `TagSearchResultVO`
4. 移除手动构建返回结果的逻辑

#### 2.4.2 Controller实现

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

---

## 3. 改动清单

### 3.1 后端改动

| 序号 | 改动项 | 改动文件 | 说明 |
|------|--------|----------|------|
| 1 | VO类新增字段 | TagSearchResultVO.java | 新增pageNum、pageSize、totalPages字段 |
| 2 | Service方法改造 | ReleaseRepoTagHandleServiceImpl.java | searchTags方法添加排序和分页逻辑 |
| 3 | Controller方法改造 | ReleaseTagController.java | 新增pageNum参数，添加参数校验 |
| 4 | 设计文档更新 | 2026-05-09-tag-release-optimization-design.md | 更新API参数和响应结构说明 |
| 5 | 接口文档更新 | tag-release-api-document.md | 更新接口参数、返回结构和示例 |

### 3.2 前端改动

| 序号 | 改动项 | 说明 |
|------|--------|------|
| 1 | 分页组件集成 | 使用pageNum、pageSize、totalPages构建分页组件 |
| 2 | 页码跳转 | 支持页码输入和上一页/下一页功能 |
| 3 | 总页数展示 | 展示总页数和当前页码信息 |

---

## 4. 测试要点

### 4.1 功能测试

| 测试场景 | 测试步骤 | 预期结果 |
|----------|----------|----------|
| 基础分页 | pageNum=1, pageSize=10 | 返回第1页的10条数据，分页信息正确 |
| 跨页请求 | pageNum=2, pageSize=10 | 返回第2页的10条数据，pageNum=2 |
| 关键字过滤+分页 | keyword="v1.0", pageNum=1, pageSize=5 | 只返回包含"v1.0"的Tag，排序正确，分页正确 |
| 边界页码 | pageNum=100（超出总页数） | 自动调整为最后一页 |
| 无效页码 | pageNum=0或pageNum=-1 | 自动调整为pageNum=1 |
| 无效pageSize | pageSize=0或pageSize=-1 | 自动调整为pageSize=20 |
| 超大pageSize | pageSize=200 | 自动调整为pageSize=100 |
| 空Tag列表 | 仓库无Tag | 返回空列表，total=0, totalPages=0 |
| 关键字无匹配 | keyword="xyz"（无匹配） | 返回空列表，total=0, totalPages=0 |

### 4.2 排序测试

| 测试场景 | 测试数据 | 预期排序结果 |
|----------|----------|--------------|
| ASCII升序 | v1.0.0, v1.0.1, v1.1.0, v2.0.0 | v1.0.0 < v1.0.1 < v1.1.0 < v2.0.0 |
| 数字版本号 | v1, v10, v2, v20 | v1 < v10 < v2 < v20（ASCII排序） |
| 混合命名 | release-1, release-10, beta-1, beta-2 | beta-1 < beta-2 < release-1 < release-10 |

### 4.3 性能测试

| 测试场景 | 测试数据 | 性能指标 |
|----------|----------|----------|
| 少量Tag | 10个Tag | 响应时间 < 500ms |
| 中等Tag | 100个Tag | 响应时间 < 1s |
| 大量Tag | 500个Tag | 响应时间 < 2s |
| 关键字过滤 | 500个Tag，keyword匹配50个 | 响应时间 < 2s |

---

## 5. 风险评估

| 风险项 | 风险等级 | 应对措施 |
|--------|----------|----------|
| Tag数量过多（>1000） | 中 | 添加pageSize最大限制100，建议前端限制每页显示数量 |
| Git API获取commitId超时 | 中 | Service层已有异常处理，返回错误信息 |
| 排序性能问题 | 低 | Java内置排序性能足够，Tag数量可控 |
| 分页参数非法 | 低 | Controller层参数校验，自动调整为合法值 |
| 关键字过滤后无结果 | 低 | 返回空列表，前端友好提示 |

---

## 6. 兼容性考虑

### 6.1 向后兼容

- 新增参数都有默认值，旧接口调用不受影响
- 不改变现有参数的含义和用法
- 返回结构新增字段，不影响现有字段的使用

### 6.2 前端适配

- 前端需要更新分页组件，支持pageNum和pageSize参数
- 前端需要处理新增的分页信息字段（totalPages）
- 前端需要实现页码跳转和总页数展示功能

---

## 7. 附录

### 7.1 相关代码位置

- Tag搜索Controller: [ReleaseTagController.java](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/controller/ReleaseTagController.java)
- Tag搜索Service: [ReleaseRepoTagHandleServiceImpl.java:197](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java#L197)
- Tag搜索结果VO: [TagSearchResultVO.java](file:///d:/Code/openlibing-platform-release/src/main/java/com/openlibing/platformrelease/business/vo/base/TagSearchResultVO.java)
- 设计文档: [2026-05-09-tag-release-optimization-design.md](file:///d:/Code/openlibing-platform-release/docs/plans/2026-05-09-tag-release-optimization-design.md)
- 接口文档: [tag-release-api-document.md](file:///d:/Code/openlibing-platform-release/docs/api/tag-release-api-document.md)

### 7.2 实施计划

详见实施计划文档：`docs/plans/2026-05-09-tag-search-pagination-implementation.md`
