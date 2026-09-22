# 添加成员接口解耦改造设计

## 一、背景

当前添加项目成员时，`FrameworkUserQueryService` 直接查询 framework 的数据库表（三方信息表 + user_basic_info 表）。为满足数据库解耦要求，需改为通过 OpenFeign 远程调用 framework 提供的批量查询接口。

### 涉及表

| 表 | 当前方式 | 改造后 |
|---|---------|-------|
| user_info_gitcode 等（三方信息表） | 直接 SQL 查询 | 由 framework 接口聚合返回 |
| user_basic_info（用户主表） | 直接 SQL 查询 | 由 framework 接口聚合返回 |
| workspace_project_member（项目成员表） | 读写 | 不变 |

## 二、改造前流程

```
前端请求 (accountLogin: "a;b;c", accountPlatform: "gitcode")
    │
    ▼
parseLogins: 按 ";" 分割 → 去重 → List<String>
    │
    ▼
FrameworkUserQueryService.batchQueryByPlatformLogins
    ├─ 直接查三方信息表 (user_info_gitcode WHERE account_login IN (...))
    └─ 直接查用户主表 (user_basic_info WHERE user_id IN (...))
    │
    ▼
processMemberAdditions: 逐个判断 errorMsg / 成员是否存在 → 写入成员表
    │
    ▼
返回 AddMembersResultVo (successCount + failedMembers)
```

### 当前问题

1. 直接访问 framework 数据库表，违反解耦要求
2. `parseLogins` 做了 `distinct()` 去重，去重后的结果直接用于查询和返回，**丢失了原始顺序和重复信息**
3. 无单次查询上限控制
4. 先查三方表再查用户主表，未先过滤已存在的成员

## 三、改造后流程

```
前端请求 (accountLogin: "a;b;c;a", accountPlatform: "gitcode")
    │
    ▼
Step 1: 解析原始输入
    ├─ 按 ";" 分割，保留原始顺序和重复
    └─ rawLogins: ["a", "b", "c", "a"]
       uniqueLogins = rawLogins 去重: ["a", "b", "c"]
    │
    ▼
Step 2: 通过 Feign 调用 framework 接口查询
    ├─ uniqueLogins 按 50 个一批拆分
    ├─ 逐批调用 FrameworkClient.getUserByPlatform (POST /internal-server/get-user)
    └─ 合并所有批次结果，按 accountLogin 建索引：
       userInfoMap = {
         "zhangsan" → { userId: "001", userName: "张三", accountId: "xxx", accountName: "张三" },
         "lisi"     → { userId: null,   userName: null,   accountId: "yyy", accountName: "李四" },  // 未绑定
         // "wangwu" 不存在，userInfoMap 中没有这条记录
       }
    │
    ▼
Step 3: 一次性加载已有成员（1 次查询）
    ├─ 查 workspace_project_member（WHERE projectId = ?）
    └─ existingMembers: Map<userId, ProjectMember>
    │
    ▼
Step 4: 遍历 rawLogins 组装结果并写入
    ├─ 维护 justAddedUserIds: Set<String> 记录本批次已添加的 userId
    ├─ 遍历 rawLogins（保持原始顺序），通过 userInfoMap.get(login) 查找对应结果
    ├─ 对每个 login 判断：
    │   ├─ login 在 userInfoMap 中不存在 → 失败：用户未登录过平台，请确认账号是否正确
    │   ├─ userInfoMap 中该 login 的 userId 为 null → 失败：账号未关联平台用户ID，请确认
    │   ├─ userId 在 existingMembers 中且 status=1 → 失败：成员已存在
    │   ├─ userId 在 justAddedUserIds 中 → 失败：成员已存在（同批次重复）
    │   ├─ userId 在 existingMembers 中且 status=0 → 恢复成员 → 加入 justAddedUserIds → 成功
    │   └─ 其他 → 新增成员 → 加入 justAddedUserIds → 成功
    ├─ 写入 workspace_project_member 表
    └─ 失败项加入 failedMembers
    │
    ▼
返回 AddMembersResultVo (successCount + failedMembers)
```

### 重复数据处理示例

输入：`rawLogins = ["a", "b", "c", "a"]`

| 序号 | login | 查询结果 | 判断 | 最终状态 |
|------|-------|---------|------|---------|
| 1 | a | userId=001 | 新增 | ✅ 成功，001 加入 justAddedUserIds |
| 2 | b | userId=002 | 新增 | ✅ 成功，002 加入 justAddedUserIds |
| 3 | c | userId=null | 未绑定 | ❌ 账号未关联平台用户ID |
| 4 | a | userId=001 | 001 在 justAddedUserIds 中 | ❌ 成员已存在 |

### 数据库操作次数

| 操作 | 次数 | 说明 |
|------|------|------|
| 查 workspace_project_member | 1 次 | 一次性加载所有已有成员 |
| 写 workspace_project_member | ≤ rawLogins.size 次 | 仅成功的才写入 |
| Feign 调用 framework | ceil(uniqueLogins/50) 次 | 分批调用 |

## 四、详细改造点

### 4.1 FrameworkUserQueryService 改造

**删除**：直接查数据库的逻辑（Mapper 调用）

**新增**：通过 `FrameworkClient`（OpenFeign）远程调用 framework 服务

```
改造前：
  frameworkThreePartyUserMapper.queryByLogin(...)
  frameworkThreePartyUserMapper.queryByPlatformAndLogins(...)
  frameworkThreePartyUserMapper.queryUserBasicById(...)
  frameworkThreePartyUserMapper.queryUserBasicByIds(...)

改造后：
  FrameworkClient (FeignClient, name="openlibing-framework")
    └─ POST /internal-server/get-user
       请求：QueryUserInfoRequest { platform, accountLogins }
       响应：DataResult<List<UserDetailInfo>>
         └─ UserDetailInfo: { accountLogin, accountId, accountName, userId, userName }
```

**服务发现**：通过 Eureka 注册中心自动解析 `openlibing-framework` 服务地址。本地调试可通过 `framework.service.url` 配置直连（如 `kubectl port-forward`）。

**UserInfoResult 字段映射**：

| UserInfoResult 字段 | 接口返回字段 | 说明 |
|---------------------|-------------|------|
| userId | userId | 不变 |
| userName | userName | 不变 |
| accountId | accountId | 不变 |
| accountName | accountName | 不变 |
| accountPlatform | 请求参数 platform | 不变 |
| accountLogin | accountLogin | 不变 |
| errorMsg | — | 已删除，由调用方根据 userId 是否为 null 判断 |

**注意**：`errorMsg` 不再由接口返回，改为在 `ProjectSpaceServiceImpl` 中根据接口返回数据判断。

### 4.2 parseLogins 改造

```
改造前：
  按 ";" 分割 → trim → 过滤空串 → distinct() → 返回 List<String>
  问题：丢失了重复项和原始顺序

改造后：
  按 ";" 分割 → trim → 过滤空串 → 返回 List<String>（保留原始顺序和重复）
  rawLogins 用于最终结果组装
  uniqueLogins = rawLogins 去重后（LinkedHashSet），用于调用接口
```

### 4.3 新增：按批次调用 Feign 接口

分批逻辑在 `FrameworkUserQueryService.batchQueryByPlatformLogins` 中实现：

```java
private static final int BATCH_SIZE = 50;

List<UserInfoResult> allResults = new ArrayList<>();
for (int i = 0; i < uniqueLogins.size(); i += BATCH_SIZE) {
    int end = Math.min(i + BATCH_SIZE, uniqueLogins.size());
    List<String> batch = uniqueLogins.subList(i, end);
    List<UserInfoResult> batchResults = callBatchQueryApi(platform, batch);
    allResults.addAll(batchResults);
}
```

`callBatchQueryApi` 内部调用 `FrameworkClient.getUserByPlatform`，异常时返回空列表 + WARN 日志。

### 4.4 processMemberAdditions 改造

```
改造前：
  遍历 userInfoResults（已去重），直接按顺序处理
  errorMsg 由 FrameworkUserQueryService 设置

改造后：
  遍历 rawLogins（保留原始顺序和重复），通过 userInfoMap.get(login) 查找对应结果
  维护 justAddedUserIds: Set<String> 追踪本批次已成功添加的 userId

  判断逻辑（按优先级）：
    1. login 在 userInfoMap 中不存在 → 失败：用户未登录过平台，请确认账号是否正确
    2. userInfoMap 中该 login 的 userId 为 null → 失败：账号未关联平台用户ID，请确认
    3. userId 在 existingMembers 中且 status=1 → 失败：成员已存在
    4. userId 在 justAddedUserIds 中 → 失败：成员已存在（同批次重复）
    5. userId 在 existingMembers 中且 status=0 → 恢复成员 → justAddedUserIds.add(userId) → 成功
    6. 其他 → 新增成员 → justAddedUserIds.add(userId) → 成功
```

### 4.5 AddMembersResultVo 保持不变

保持原有 `successCount` + `failedMembers` 格式，与接口文档定义一致，前端无需改动。

```json
{
  "successCount": 2,
  "failedMembers": [
    { "accountLogin": "xxx", "reason": "成员已存在" }
  ]
}
```

### 4.6 FrameworkThreePartyUserMapper 清理

删除以下不再需要的 Mapper 方法和 XML SQL：

| 方法 | 说明 |
|------|------|
| `queryByLogin` | 单个查三方表 → 改用 Feign 接口 |
| `queryByPlatformAndLogins` | 批量查三方表 → 改用 Feign 接口 |
| `queryUserBasicById` | 单个查用户主表 → 由 Feign 接口聚合 |
| `queryUserBasicByIds` | 批量查用户主表 → 由 Feign 接口聚合 |

## 五、涉及文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| FrameworkClient.java | 新增 | FeignClient 接口，name="openlibing-framework" |
| QueryUserInfoRequest.java | 新增 | Feign 请求 DTO，镜像 framework 的 QueryUserInfoDTO |
| UserDetailInfo.java | 新增 | Feign 响应 DTO，镜像 framework 的 UserDetailInfoEntity |
| FrameworkUserQueryService.java | 重构 | 改为 Feign 调用，删除 Mapper 依赖，新增分批逻辑 |
| ProjectSpaceServiceImpl.java | 修改 | parseLogins 保留原始顺序 + justAddedUserIds + 结果组装 |
| AddMembersResultVo.java | 不变 | 保持 successCount + failedMembers 格式 |
| WorkspaceApplication.java | 修改 | 添加 @EnableFeignClients 注解 |
| FrameworkThreePartyUserMapper.java | 删除 | 不再需要 |
| FrameworkThreePartyUserMapper.xml | 删除 | 不再需要 |
| application-local.yaml | 修改 | 添加 framework.service.url 本地调试配置 |

## 六、验证方式

1. 单个用户添加：正常成功 / 用户不存在 / 未绑定 userId
2. 多个用户添加：部分成功部分失败
3. 重复用户添加：同一 login 出现多次，第二次报"成员已存在"
4. 批量超过 50 个：验证分批调用和结果合并
5. 已存在成员添加：报"成员已存在"
6. 已删除成员（status=0）重新添加：恢复成员
7. Feign 调用异常时：返回空结果 + 日志告警，不影响已有数据
