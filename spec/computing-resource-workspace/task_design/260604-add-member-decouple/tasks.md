# 添加成员接口解耦改造 - Tasks

## Task 1: FrameworkUserQueryService 改造为 Feign 调用

- [x] 1.1 新增 `FrameworkClient` (FeignClient) 接口，调用 framework 的 `/internal-server/get-user` 接口
- [x] 1.2 新增 `QueryUserInfoRequest` 和 `UserDetailInfo` DTO，镜像 framework 的请求/响应结构
- [x] 1.3 重构 `batchQueryByPlatformLogins` 方法：调用 FeignClient 替代 Mapper 查询，返回 `List<UserInfoResult>`
- [x] 1.4 重构 `queryByPlatformLogin` 方法：复用 `batchQueryByPlatformLogins`，取列表首项
- [x] 1.5 删除 `FrameworkThreePartyUserMapper` 依赖注入
- [x] 1.6 删除 `errorMsg` 字段的设置逻辑（改为调用方判断）
- [x] 1.7 补充 Feign 调用异常处理：接口不可用时返回空结果 + 日志告警
- [x] 1.8 启动类添加 `@EnableFeignClients` 注解

## Task 2: parseLogins 改造

- [x] 2.1 修改 `parseLogins` 方法：去掉 `distinct()`，保留原始顺序和重复项，返回 `rawLogins`
- [x] 2.2 新增工具方法：从 `rawLogins` 生成去重后的 `uniqueLogins`（LinkedHashSet 保持顺序）

## Task 3: 分批调用逻辑

- [x] 3.1 在 `FrameworkUserQueryService` 中新增分批调用逻辑：`uniqueLogins` 按 50 个一批拆分
- [x] 3.2 逐批调用 `FrameworkClient.getUserByPlatform`
- [x] 3.3 合并所有批次结果为 `userInfoMap: Map<accountLogin, UserInfoResult>`

## Task 4: processMemberAdditions 改造

- [x] 4.1 改为遍历 `rawLogins`（非 userInfoResults），通过 `userInfoMap.get(login)` 查找结果
- [x] 4.2 新增 `justAddedUserIds: Set<String>` 追踪本批次已成功添加的 userId
- [x] 4.3 实现判断逻辑（按优先级）：
  - login 在 userInfoMap 中不存在 → 失败
  - userId 为 null → 失败
  - userId 在 existingMembers 中且 status=1 → 失败
  - userId 在 justAddedUserIds 中 → 失败（同批次重复）
  - userId 在 existingMembers 中且 status=0 → 恢复成员 → 成功
  - 其他 → 新增成员 → 成功
- [x] 4.4 成功时将 userId 加入 `justAddedUserIds`

## Task 5: AddMembersResultVo 保持不变

- [x] 5.1 保持 `successCount` + `failedMembers` 格式，与接口文档一致
- [x] 5.2 `FailedMember` 包含 `accountLogin` + `reason` 字段
- ~~5.3 不改为逐条返回结构~~（保持原有格式，前端无需改动）

## Task 6: 清理废弃代码

- [x] 6.1 删除 `FrameworkThreePartyUserMapper.java`
- [x] 6.2 删除 `FrameworkThreePartyUserMapper.xml`
- [x] 6.3 清理 `FrameworkUserQueryService` 中所有 Mapper 相关 import

## Task 7: 测试

- [x] 7.1 更新 `FrameworkUserQueryServiceTest`：Mock FeignClient 调用替代 Mapper
- [x] 7.2 更新 `ProjectSpaceServiceImplTest`：覆盖以下场景
  - 单个用户添加成功
  - 用户不存在（userInfoMap 中无记录）
  - 用户未绑定（userId 为 null）
  - 重复 login 输入，第二次报"成员已存在"
  - 已存在成员（status=1）报"成员已存在"
  - 已删除成员（status=0）恢复
  - 接口调用失败时的降级处理
- [x] 7.3 运行全量测试确认无回归（579 tests passed）
