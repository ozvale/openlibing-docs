# Tag Release Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support searching existing tags for release and add commitId matching validation.

**Architecture:** Add tag search API for frontend, enhance SafeScanServiceImpl.executeVirusScan() to validate tag commitId after virus scan and before SHA256 validation, store validation result in ReleaseReviewVirusScanEntity.

**Tech Stack:** Java 21, Spring Boot 3.x, MyBatis, MySQL, Git API (Gitcode/Gitee)

---

## Task 1: Add Tag Validation Fields to ReleaseReviewVirusScanEntity

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/entity/base/ReleaseReviewVirusScanEntity.java`
- Create: `src/main/resources/db/changelog/2026-05-09-add-tag-validation-fields.yaml`

**Step 1: Add fields to Entity**

```java
/**
 * Tag校验结果（1-匹配成功，2-不匹配，3-Tag不存在，4-校验异常）
 */
private Integer tagValidationResult;

/**
 * Tag校验详情（JSON格式）
 */
private String tagValidationDetail;
```

**Step 2: Create Liquibase change**

```yaml
databaseChangeLog:
  - changeSet:
      id: add-tag-validation-fields
      author: developer
      changes:
        - addColumn:
            tableName: release_review_virus_scan
            columns:
              - column:
                  name: tag_validation_result
                  type: int
                  remarks: Tag校验结果
              - column:
                  name: tag_validation_detail
                  type: varchar(500)
                  remarks: Tag校验详情
```

**Step 3: Run application to apply database changes**

Run: `mvn spring-boot:run`
Expected: Application starts successfully

**Step 4: Commit**

```bash
git add src/main/java/com/openlibing/platformrelease/business/entity/base/ReleaseReviewVirusScanEntity.java src/main/resources/db/changelog/2026-05-09-add-tag-validation-fields.yaml
git commit -m "feat: add tag validation fields to ReleaseReviewVirusScanEntity"
```

---

## Task 2: Add Get Tag CommitId Method

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java`

**Step 1: Add method to Service**

```java
/**
 * 获取Tag指向的commitId
 *
 * @param projectId 项目ID
 * @param repoUrl 仓库URL
 * @param tagName Tag名称
 * @return commitId，如果Tag不存在返回null
 * @throws Exception 获取失败时抛出异常
 */
public String getTagCommitId(String projectId, String repoUrl, String tagName) throws Exception {
    ProjectCommonAccountInfoEntity accountInfo = releaseReviewDao.queryProjectCommonAccountInfoEntity(projectId);
    String accessToken;

    if (repoUrl.contains("gitcode") || repoUrl.contains("atomgit")) {
        accessToken = SecurityManagerUtil.decrypt(accountInfo.getGitcodeToken());
        String owner = repoUrl.split("/")[3];
        String repo = repoUrl.split("/")[4].replace(".git", "");
        String url = GITCODE_URL_PREFIX + "repos/" + owner + "/" + repo + "/tags/" + tagName + "?access_token=" + accessToken;

        String response = HttpUtil.get(url);
        JSONObject json = JSON.parseObject(response);
        if (json.containsKey("commit")) {
            return json.getJSONObject("commit").getString("sha");
        }
    } else if (repoUrl.contains("gitee")) {
        accessToken = SecurityManagerUtil.decrypt(accountInfo.getGiteeToken());
        String owner = repoUrl.split("/")[3];
        String repo = repoUrl.split("/")[4].replace(".git", "");
        String url = GITEE_URL_PREFIX + "repos/" + owner + "/" + repo + "/tags/" + tagName + "?access_token=" + accessToken;

        String response = HttpUtil.get(url);
        JSONObject json = JSON.parseObject(response);
        if (json.containsKey("commit")) {
            return json.getJSONObject("commit").getString("sha");
        }
    }

    return null;
}
```

**Step 2: Run compile to verify**

Run: `mvn compile`
Expected: BUILD SUCCESS

**Step 3: Commit**

```bash
git add src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java
git commit -m "feat: add getTagCommitId method"
```

---

## Task 3: Add Tag Search API

**Files:**
- Create: `src/main/java/com/openlibing/platformrelease/business/controller/ReleaseTagController.java`
- Create: `src/main/java/com/openlibing/platformrelease/business/vo/base/TagSearchResultVO.java`
- Modify: `src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java`

**Step 1: Create VO classes**

```java
@Data
public class TagSearchResultVO {
    private List<TagInfoVO> tagList;
    private Integer total;
}

@Data
public class TagInfoVO {
    private String tagName;
    private String commitId;
    private String createTime;
}
```

**Step 2: Add search method to Service**

```java
/**
 * 搜索仓库Tag列表
 *
 * @param projectId 项目ID
 * @param repoUrl 仓库URL
 * @param keyword 搜索关键字
 * @param pageSize 返回数量
 * @return Tag列表
 * @throws Exception 搜索失败时抛出异常
 */
public List<TagInfoVO> searchTags(String projectId, String repoUrl, String keyword, Integer pageSize) throws Exception {
    List<String> allTags = this.queryRepoTagList(projectId, repoUrl);

    List<TagInfoVO> result = new ArrayList<>();
    for (String tagName : allTags) {
        if (StringUtils.isNotBlank(keyword) && !tagName.contains(keyword)) {
            continue;
        }

        TagInfoVO tagInfo = new TagInfoVO();
        tagInfo.setTagName(tagName);
        tagInfo.setCommitId(this.getTagCommitId(projectId, repoUrl, tagName));
        result.add(tagInfo);

        if (result.size() >= pageSize) {
            break;
        }
    }

    return result;
}
```

**Step 3: Create Controller**

```java
@RestController
@RequestMapping("/api/release/tag")
public class ReleaseTagController {

    @Autowired
    private ReleaseRepoTagHandleServiceImpl releaseRepoTagHandleService;

    @GetMapping("/search")
    public DataResult<TagSearchResultVO> searchTags(
            @RequestParam String projectId,
            @RequestParam String repoUrl,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false, defaultValue = "20") Integer pageSize) {
        try {
            List<TagInfoVO> tagList = releaseRepoTagHandleService.searchTags(projectId, repoUrl, keyword, pageSize);

            TagSearchResultVO result = new TagSearchResultVO();
            result.setTagList(tagList);
            result.setTotal(tagList.size());

            return DataResult.successData(result);
        } catch (Exception e) {
            return DataResult.failureMessage("搜索Tag失败: " + e.getMessage());
        }
    }
}
```

**Step 4: Run compile to verify**

Run: `mvn compile`
Expected: BUILD SUCCESS

**Step 5: Commit**

```bash
git add src/main/java/com/openlibing/platformrelease/business/controller/ReleaseTagController.java src/main/java/com/openlibing/platformrelease/business/vo/base/TagSearchResultVO.java src/main/java/com/openlibing/platformrelease/business/service/impl/ReleaseRepoTagHandleServiceImpl.java
git commit -m "feat: add tag search API"
```

---

## Task 4: Add Tag CommitId Validation Method

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/service/impl/SafeScanServiceImpl.java`

**Step 1: Add validation method**

```java
/**
 * 校验Tag commitId与制品包commitId是否匹配
 *
 * @param artifactInfo 制品信息
 * @param artifactCommitId 制品包构建的commitId
 * @param tagCommitId Tag指向的commitId
 * @return 校验结果（1-匹配成功，2-不匹配）
 */
private Integer validateTagCommitId(ReleaseArtifactInfoEntity artifactInfo, String artifactCommitId, String tagCommitId) {
    if (StringUtils.equals(artifactCommitId, tagCommitId)) {
        return 1;
    }
    return 2;
}

/**
 * 构建Tag校验详情JSON
 *
 * @param tagName Tag名称
 * @param tagCommitId Tag指向的commitId
 * @param artifactCommitId 制品包构建的commitId
 * @param repoUrl 仓库URL
 * @param message 消息
 * @return JSON字符串
 */
private String buildTagValidationDetail(String tagName, String tagCommitId, String artifactCommitId, String repoUrl, String message) {
    JSONObject json = new JSONObject();
    json.put("tagName", tagName);
    json.put("tagCommitId", tagCommitId);
    json.put("artifactCommitId", artifactCommitId);
    json.put("repoUrl", repoUrl);
    json.put("message", message);
    return json.toJSONString();
}
```

**Step 2: Run compile to verify**

Run: `mvn compile`
Expected: BUILD SUCCESS

**Step 3: Commit**

```bash
git add src/main/java/com/openlibing/platformrelease/business/service/impl/SafeScanServiceImpl.java
git commit -m "feat: add validateTagCommitId method"
```

---

## Task 5: Integrate Tag Validation into executeVirusScan

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/service/impl/SafeScanServiceImpl.java`

**Step 1: Add service injection**

```java
@Autowired
private ReleaseRepoTagHandleService releaseRepoTagHandleService;
```

**Step 2: Add tag validation logic after virus scan**

在病毒扫描循环结束后、SHA256校验之前添加：

```java
// 5. Tag commitId校验（新增）
Integer tagValidationResult = 3;
String tagValidationDetail = "";
try {
    String tagName = releaseArtifactInfoEntity.getTagName();
    String repoUrl = releaseArtifactInfoEntity.getRepoUrl();

    if (StringUtils.isNotBlank(tagName) && StringUtils.isNotBlank(repoUrl)) {
        List<ReleaseSoftwareBuildDataEntity> buildDataEntities = releaseSoftwareBuildDataDao.queryByReleaseArtifactInfoId(releaseArtifactInfoEntity.getId());
        String artifactCommitId = null;
        if (!CollectionUtils.isEmpty(buildDataEntities)) {
            artifactCommitId = buildDataEntities.get(0).getCommitId();
        }

        if (StringUtils.isNotBlank(artifactCommitId)) {
            List<String> existingTags = releaseRepoTagHandleService.queryRepoTagList(projectId, repoUrl);

            if (existingTags.contains(tagName)) {
                String tagCommitId = releaseRepoTagHandleService.getTagCommitId(projectId, repoUrl, tagName);

                if (StringUtils.isNotBlank(tagCommitId)) {
                    tagValidationResult = validateTagCommitId(releaseArtifactInfoEntity, artifactCommitId, tagCommitId);

                    if (tagValidationResult == 2) {
                        tagValidationDetail = buildTagValidationDetail(tagName, tagCommitId, artifactCommitId, repoUrl, "Tag与制品包commitId不匹配");
                        log.warn("Tag commitId mismatch: tagName={}, tagCommitId={}, artifactCommitId={}", tagName, tagCommitId, artifactCommitId);
                    }
                } else {
                    tagValidationResult = 4;
                    tagValidationDetail = buildTagValidationDetail(tagName, "", artifactCommitId, repoUrl, "获取Tag commitId失败");
                }
            } else {
                tagValidationResult = 3;
                tagValidationDetail = buildTagValidationDetail(tagName, "", artifactCommitId, repoUrl, "Tag不存在，发布时自动创建");
            }
        } else {
            tagValidationResult = 4;
            tagValidationDetail = buildTagValidationDetail(tagName, "", "", repoUrl, "制品包无commitId信息");
        }
    }
} catch (Exception e) {
    log.error("Tag validation failed: {}", e.getMessage());
    tagValidationResult = 4;
    tagValidationDetail = buildTagValidationDetail(releaseArtifactInfoEntity.getTagName(), "", "", releaseArtifactInfoEntity.getRepoUrl(), "校验异常: " + e.getMessage());
}

releaseReviewVirusScanDao.update(
    new LambdaUpdateWrapper<ReleaseReviewVirusScanEntity>()
        .eq(ReleaseReviewVirusScanEntity::getReleaseArtifactInfoId, releaseArtifactInfoEntity.getId())
        .set(ReleaseReviewVirusScanEntity::getTagValidationResult, tagValidationResult)
        .set(ReleaseReviewVirusScanEntity::getTagValidationDetail, tagValidationDetail)
);
```

**Step 3: Run compile to verify**

Run: `mvn compile`
Expected: BUILD SUCCESS

**Step 4: Commit**

```bash
git add src/main/java/com/openlibing/platformrelease/business/service/impl/SafeScanServiceImpl.java
git commit -m "feat: integrate tag commitId validation into executeVirusScan"
```

---

## Task 6: Update VO for Frontend Display

**Files:**
- Modify: `src/main/java/com/openlibing/platformrelease/business/vo/base/ReleaseReviewVirusScanVo.java`

**Step 1: Add fields to VO**

```java
/**
 * Tag校验结果（1-匹配成功，2-不匹配，3-Tag不存在，4-校验异常）
 */
private Integer tagValidationResult;

/**
 * Tag校验详情（JSON格式）
 */
private String tagValidationDetail;
```

**Step 2: Run compile to verify**

Run: `mvn compile`
Expected: BUILD SUCCESS

**Step 3: Commit**

```bash
git add src/main/java/com/openlibing/platformrelease/business/vo/base/ReleaseReviewVirusScanVo.java
git commit -m "feat: add tag validation fields to ReleaseReviewVirusScanVo"
```

---

## Task 7: Run All Tests and Final Verification

**Step 1: Run all tests**

Run: `mvn test`
Expected: All tests pass

**Step 2: Run compile**

Run: `mvn compile`
Expected: BUILD SUCCESS

**Step 3: Final commit**

```bash
git status
git add -A
git commit -m "feat: complete tag release optimization implementation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add database fields | Entity + Liquibase |
| 2 | Add getTagCommitId method | Service |
| 3 | Add tag search API | Controller + Service + VO |
| 4 | Add validation method | SafeScanServiceImpl |
| 5 | Integrate validation | SafeScanServiceImpl.executeVirusScan |
| 6 | Update VO | ReleaseReviewVirusScanVo |
| 7 | Final verification | All tests |
