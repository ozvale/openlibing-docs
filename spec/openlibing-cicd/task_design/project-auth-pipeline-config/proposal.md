# project-auth-pipeline-config

## 需求背景

当前 `/updatePipelineConfig`、`/batchUpdatePipelineConfig`、`/cancelPipelineQueue`、`/getPipelineJobTypes` 几个接口虽然在 gateway 已配置了项目管理员权限，但缺少项目级别的横向鉴权。现有的 `@CheckPermission` 注解在仓库为公开仓时会跳过 `hasPermission` 校验，导致其他项目的项目管理员可能跨项目触发本项目的接口。

## 功能描述

1. 新增 `@ProjectAuth` 注解，实现项目级别横向鉴权，与现有 `@CheckPermission` 注解解耦
2. 为上述 4 个接口添加 `@ProjectAuth` 注解，确保只有本项目的项目管理员才能触发本项目相关接口
3. 将 `/updateDetailInfo` 接口和实现方法标注为 `@Deprecated`

## 不做什么

- 不修改现有 `@CheckPermission` 的逻辑，保持向后兼容
- 不修改其他接口的鉴权方式

## 验收标准

- [ ] 4 个接口添加 `@ProjectAuth` 注解后，非本项目用户无法触发
- [ ] `/getPipelineJobTypes` 接口新增 `projectId` 和 `userId` 参数
- [ ] `/cancelPipelineQueue` 接口新增 `userId` 参数
- [ ] `/updatePipelineConfig` 和 `/batchUpdatePipelineConfig` 接口新增 `userId` 参数
- [ ] `/updateDetailInfo` 接口和方法标注 `@Deprecated`
- [ ] 现有 `@CheckPermission` 鉴权逻辑不受影响
- [ ] 相关测试通过

## 影响范围

- `openlibing-cicd` 仓：鉴权模块、流水线控制器、流水线服务
- 前端调用方需适配新增的 `userId`/`projectId` 参数
