# 跨社区工具使用审核标识 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为工具箱管理功能添加跨社区使用审核标识，支持"不需审核直接使用"的场景

**Architecture:** 在现有 tool_apply / tool_version 表扩展 `can_cross_project` 字段，ToolApplyServiceImpl 保存和审核时写入该字段，ToolProjectUseServiceImpl 使用工具时根据该字段判断是否跳过审核

**Tech Stack:** Java 17, Spring Boot, MyBatis, Liquibase, MySQL

---

### Task 1: DB changelog — tool_apply.xml 新增 can_cross_project 字段

**Files:**

- Modify: `src/main/resources/db/changelog/v1.0.1/tool/tool_apply.xml`

**Step 1: 在 tool_apply.xml 末尾新增 changeset**

在 `</databaseChangeLog>` 之前新增一个 changeset，使用 ALTER TABLE 添加 `can_cross_project` 列：

```xml
    <changeSet id="20260804_add_can_cross_project_tool_apply" author="zhuangzhiting">
        <preConditions onFail="MARK_RAN">
            <tableExists tableName="tool_apply"/>
            <not>
                <columnExists tableName="tool_apply" columnName="can_cross_project"/>
            </not>
        </preConditions>
        <sql>
            ALTER TABLE tool_apply
                ADD COLUMN can_cross_project VARCHAR(1) DEFAULT NULL COMMENT '跨项目使用，是否需审核 0-不需审核，可直接使用 1-需审核'
        </sql>
        <rollback>
            ALTER TABLE tool_apply
            DROP COLUMN can_cross_project
        </rollback>
    </changeSet>
```

**Step 2: 验证**

无需验证，Liquibase changeset 在应用时自动执行。

**Step 3: Commit**

---

### Task 2: DB changelog — tool_version.xml 新增 can_cross_project 字段

**Files:**

- Modify: `src/main/resources/db/changelog/v1.0.1/tool/tool_version.xml`

**Step 1: 在 tool_version.xml 末尾新增 changeset**

在 `</databaseChangeLog>` 之前新增一个 changeset：

```xml
    <changeSet id="20260804_add_can_cross_project_tool_version" author="zhuangzhiting">
        <preConditions onFail="MARK_RAN">
            <tableExists tableName="tool_version"/>
            <not>
                <columnExists tableName="tool_version" columnName="can_cross_project"/>
            </not>
        </preConditions>
        <sql>
            ALTER TABLE tool_version
                ADD COLUMN can_cross_project VARCHAR(1) DEFAULT NULL COMMENT '跨项目使用，是否需审核 0-不需审核，可直接使用 1-需审核'
        </sql>
        <rollback>
            ALTER TABLE tool_version
            DROP COLUMN can_cross_project
        </rollback>
    </changeSet>
```

**Step 2: Commit**

---

### Task 3: Entity 层 — ToolApplyEntity 和 ToolVersionEntity 新增字段

**Files:**

- Modify: `src/main/java/.../entity/tool/ToolApplyEntity.java`
- Modify: `src/main/java/.../entity/tool/ToolVersionEntity.java`

**Step 1: 修改 ToolApplyEntity.java**

在 `lastScanTime` 字段后添加：

```java
  /** 跨项目使用，是否需审核 0-不需审核，可直接使用 1-需审核 */
  private String canCrossProject;
```

**Step 2: 修改 ToolVersionEntity.java**

在 `hasUse` 字段前添加：

```java
  /** 跨项目使用，是否需审核 0-不需审核，可直接使用 1-需审核 */
  private String canCrossProject;
```

**Step 3: Commit**

---

### Task 4: DTO 层 — ToolApplyDTO 新增 canCrossProject 字段 + 校验

**Files:**

- Modify: `src/main/java/.../dto/tool/ToolApplyDTO.java`

**Step 1: 修改 ToolApplyDTO.java**

在 `lastScanTime` 字段后添加：

```java
  /** 跨项目使用，是否需审核 0-不需审核，可直接使用 1-需审核 */
  @NotBlank(message = "跨社区审核标识不能为空")
  @Pattern(regexp = "^(0|1)$", message = "跨社区审核标识不合法")
  private String canCrossProject;
```

**Step 2: 编译验证**

```bash
mvn compile -pl openlibing-framework-business -am
```

**Step 3: Commit**

---

### Task 5: ToolApplyServiceImpl — saveToolApply() 写入 canCrossProject

**Files:**

- Modify: `src/main/java/.../service/impl/ToolApplyServiceImpl.java`

**Step 1: 在 getToolApplyInfo() 中写入 canCrossProject**

在 `getToolApplyInfo()` 方法中，找到设置 `toolApplyEntity.setLastScanTime(...)` 的行，在其后添加：

```java
    toolApplyEntity.setCanCrossProject(toolApplyDTO.getCanCrossProject());
```

**Step 2: 编译验证**

```bash
mvn compile -pl openlibing-framework-business -am
```

**Step 3: Commit**

---

### Task 6: ToolApplyServiceImpl — reviewToolInfo() 写入版本 + 自动授权

**Files:**

- Modify: `src/main/java/.../service/impl/ToolApplyServiceImpl.java`

**Step 1: 注入 ToolUseConfigMapper**

在 `ToolApplyServiceImpl` 类中，`@Resource private ToolIconMapper toolIconMapper;` 后添加：

```java
  @Resource private ToolUseConfigMapper toolUseConfigMapper;
```

添加 import：

```java
import com.openlibing.framework.business.mapper.ToolUseConfigMapper;
import com.openlibing.framework.business.entity.tool.ToolUseConfigEntity;
```

**Step 2: 在 reviewToolInfo() 中写入 canCrossProject**

在 `reviewToolInfo()` 方法中，创建 `ToolVersionEntity` 后，在 `toolVersion.setOwnerProjectId(...)` 后添加：

```java
    toolVersion.setCanCrossProject(toolApplyInfo.getCanCrossProject());
```

**Step 3: 在 reviewToolInfo() 中调用 ToolUseConfigMapper.insert() 自动授权**

在 `toolVersionMapper.insert(toolVersion);` 后添加：

```java
    // 审核通过后，申请项目自动获得该工具版本使用权限
    ToolUseConfigEntity toolUseConfig = new ToolUseConfigEntity();
    toolUseConfig.setId(CommonUtil.getUuid());
    toolUseConfig.setToolId(toolId);
    toolUseConfig.setToolVersionId(toolVersion.getId());
    toolUseConfig.setProjectId(toolApplyInfo.getProjectId());
    toolUseConfig.setCreateBy(toolApplyInfo.getApplyBy());
    toolUseConfig.setCreateTime(DateUtilsExt.formatDateTime(new Date()));
    toolUseConfigMapper.insert(toolUseConfig);
```

**Step 4: 编译验证**

```bash
mvn compile -pl openlibing-framework-business -am
```

**Step 5: Commit**

---

### Task 7: ToolProjectUseServiceImpl — getToolUseApplyResultEntity() 增加 canCrossProject 判断

**Files:**

- Modify: `src/main/java/.../service/impl/ToolProjectUseServiceImpl.java`

**Step 1: 修改 getToolUseApplyResultEntity() 判断逻辑**

在 `ownerProjectId` 判断之后、`reviewBy` 为空判断之前，插入 `canCrossProject` 判断：

```java
    // 跨项目使用，不需审核，直接使用
    if (NumberConstant.STRING_ZERO.equals(toolVersionEntity.getCanCrossProject())) {
      toolUseApplyResultEntity.setId(CommonUtil.getUuid());
      toolUseApplyResultEntity.setResult(NumberConstant.STRING_ONE);
      toolUseApplyResultEntity.setRemark("跨项目使用，不需审核，直接可使用");
      return toolUseApplyResultEntity;
    }
```

**Step 2: 编译验证**

```bash
mvn compile -pl openlibing-framework-business -am
```

**Step 3: Commit**

---

### 验证清单

- [ ] `mvn compile` 编译通过
- [ ] 相关 UT 运行通过
- [ ] 代码符合生成前约束清单
