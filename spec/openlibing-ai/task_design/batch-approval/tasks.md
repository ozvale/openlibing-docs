# batch-approval — Implementation Plan

> **Goal:** 为 AiToolApplicationRecordService 新增批量审批功能，支持一次审批多条记录

> **Architecture:** 新增 BatchApprovalRequestDTO 承载批量请求参数，Service 层采用"预检查→批量更新"策略确
保事务性，App 层做薄委托透传

> **Tech Stack:** Java 21, Spring Boot, MyBatis-Plus, Lombok

---

## 进度: 3/3 complete

---

### Task 1: 创建 BatchApprovalRequestDTO

**Files:**
- Create: `src/main/java/com/openlibing/ai/api/dto/BatchApprovalRequestDTO.java`
- Reference: `src/main/java/com/openlibing/ai/api/dto/UpdateDistributionStatusDTO.java` (同类 DTO 模式)
- Reference: `src/main/java/com/openlibing/ai/api/dto/ApprovalRequestDTO.java` (单条审批 DTO)

**Step 1: 创建 DTO 类**

字段：`List<Long> ids` + `String action` + `String remarks`，参考 `UpdateDistributionStatusDTO` 的 `equals/hashCode` 防御性拷贝模式。

**Step 2: 验证编译**

```bash
mvn compile -f pom.xml -q
```

**Step 3: Commit**

```bash
git add src/main/java/com/openlibing/ai/api/dto/BatchApprovalRequestDTO.java
git commit -m "feat(aitool): add BatchApprovalRequestDTO for batch approval"
```

---

### Task 2: Service 层新增 batchApprove 方法

**Files:**
- Modify: `src/main/java/com/openlibing/ai/domain/aitool/service/AiToolApplicationRecordService.java`

**Step 1: 添加 import**

```java
import com.openlibing.ai.api.dto.BatchApprovalRequestDTO;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
```

**Step 2: 新增 batchApprove 方法** (~65 行，插入在 `approveApplication` 方法之后)

```java
public MultiResponse batchApprove(BatchApprovalRequestDTO request, String userId) {
    // 1. 参数校验
    if (request.getIds() == null || request.getIds().isEmpty()) {
        return new MultiResponse().code(400).message("failed").result("审批记录ID列表不能为空");
    }
    if (!"APPROVED".equals(request.getAction()) && !"REJECTED".equals(request.getAction())) {
        return new MultiResponse().code(400).message("failed").result("审批动作只能为 APPROVED 或 REJECTED");
    }

    // 2. 鉴权
    UserInfoUniportalEntity userInfo = getUserInfo(userId);

    // 3. 预检查循环
    List<Map<String, Object>> errors = new ArrayList<>();
    List<AiToolApplicationRecordDetailEntity> validRecords = new ArrayList<>();

    for (Long id : request.getIds()) {
        AiToolApplicationRecordDetailEntity record = aiToolApplicationRecordDetailMapper.selectById(id);
        if (record == null) { ... errors.add({"id":id, "reason":"申请记录不存在"}); continue; }
        if (!"PENDING".equals(record.getApplicationStatus())) { ... errors.add(...); continue; }
        if ("APPROVED".equals(request.getAction()) && !checkToolAvailability(...)) { ... errors.add(...); continue; }
        validRecords.add(record);
    }

    // 4. 预检查失败 → 返回错误明细
    if (!errors.isEmpty()) {
        return new MultiResponse().code(500).message("批量审批失败，部分记录预检查不通过").result(errors);
    }

    // 5. 批量更新
    for (AiToolApplicationRecordDetailEntity record : validRecords) {
        record.setApplicationStatus(request.getAction());
        record.setApproverEmployeeId(userInfo.getAccountLogin());
        record.setRemarks(request.getRemarks());
        if ("APPROVED".equals(request.getAction())) { record.setApprovalTime(LocalDateTime.now()); }
        else { record.setRejectionTime(LocalDateTime.now()); }
        aiToolApplicationRecordDetailMapper.updateById(record);
    }

    return new MultiResponse().code(200).message("批量审批成功").result(null);
}
```

**Step 3: 验证编译**

```bash
mvn compile -f pom.xml -q
```

**Step 4: Commit**

```bash
git add src/main/java/com/openlibing/ai/domain/aitool/service/AiToolApplicationRecordService.java
git commit -m "feat(aitool): add batchApprove method with pre-check and rollback on failure"
```

---

### Task 3: App 层新增委托方法

**Files:**
- Modify: `src/main/java/com/openlibing/ai/app/AiToolApplicationRecord.java`

**Step 1: 添加 import + 委托方法** (~12 行，插入在 `approveApplication` 之后)

```java
import com.openlibing.ai.api.dto.BatchApprovalRequestDTO;

public MultiResponse batchApprove(BatchApprovalRequestDTO request, String userId) {
    return aiToolApplicationRecordService.batchApprove(request, userId);
}
```

**Step 2: 验证编译**

```bash
mvn compile -f pom.xml -q
```

**Step 3: Commit**

```bash
git add src/main/java/com/openlibing/ai/app/AiToolApplicationRecord.java
git commit -m "feat(aitool): add batchApprove delegation in app layer"
```

---

## 测试场景清单

| # | 场景 | 输入 | 期望 |
|---|------|------|------|
| 1 | 全部通过 | 3 条 PENDING + 余量充足 + APPROVED | 200，全部更新为 APPROVED |
| 2 | 部分不存在 | 含不存在的 ID | 500，errors 含 "申请记录不存在" |
| 3 | 部分已审批 | 含已 APPROVED 的记录 | 500，errors 含 "已审批，不能重复操作" |
| 4 | 余量不足 | 含工具余量为 0 的记录 | 500，errors 含余量信息 |
| 5 | 参数为空 | ids=[] 或 action="" | 400 参数校验失败 |
| 6 | 全部驳回 | 3 条 PENDING + REJECTED | 200，全部更新为 REJECTED |
