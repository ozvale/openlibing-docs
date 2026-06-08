# 添加成员接口解耦改造 - Proposal

## 一、需求背景

当前添加项目成员时，`FrameworkUserQueryService` 直接查询 framework 的数据库表（三方信息表 `user_info_*` + 用户主表 `user_basic_info`），违反了数据库解耦要求。需改为通过 OpenFeign 远程调用 framework 提供的批量查询接口，消除对 framework 数据库的直接依赖。

## 二、现状问题

1. 直接访问 framework 数据库表，违反解耦要求
2. `parseLogins` 做了 `distinct()` 去重，丢失了原始顺序和重复信息，无法支持表格导入场景
3. 无单次查询上限控制，大批量场景可能超载

## 三、改造范围

- `FrameworkUserQueryService`：从直接查数据库改为 OpenFeign 调用 framework 服务
- `FrameworkClient`（新增）：FeignClient 接口，通过 Eureka 服务发现调用 framework
- `QueryUserInfoRequest` / `UserDetailInfo`（新增）：Feign 请求/响应 DTO
- `ProjectSpaceServiceImpl`：parseLogins 保留原始顺序 + 重复数据处理 + 结果组装
- `AddMembersResultVo`：保持 `successCount` + `failedMembers` 格式不变
- `FrameworkThreePartyUserMapper` 及 XML：删除，不再需要

## 四、验收标准

### 功能验收

- [x] 添加成员不再直接访问 framework 的任何数据库表
- [x] 通过 OpenFeign (FrameworkClient) 远程调用 framework 的 `/internal-server/get-user` 接口
- [x] 通过 Eureka 注册中心自动解析 framework 服务地址，本地调试可通过 `framework.service.url` 配置直连
- [x] 支持批量添加，单次接口调用上限 50 个，超出自动分批
- [x] 重复 login 输入时，第二次报"成员已存在"
- [x] 单个用户添加：正常成功 / 用户不存在 / 未绑定 userId，行为与改造前一致
- [x] 已存在成员（status=1）添加：报"成员已存在"
- [x] 已删除成员（status=0）重新添加：恢复成员
- [x] 接口调用失败时，所有用户返回失败提示，不影响已有数据

### 非功能验收

- [x] 查 workspace_project_member 表仅 1 次（一次性加载）
- [x] 写 workspace_project_member 表仅限成功项
- [x] framework 接口调用次数 = ceil(uniqueLogins / 50)
- [x] 现有单元测试全部通过（579 tests），新增场景有对应测试覆盖

## 五、约束

- 不修改 `AddMemberRequest` 入参结构
- 不修改 `ProjectMember` 实体结构（不新增 accountLogin 字段）
- 不修改 `UserInfoSyncService` 逻辑
- 不修改 `AddMembersResultVo` 返回格式（保持 `successCount` + `failedMembers`）
- FeignClient 通过 Eureka 服务发现，不硬编码地址
