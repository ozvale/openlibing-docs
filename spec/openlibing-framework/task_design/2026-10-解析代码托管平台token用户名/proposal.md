# 解析代码托管平台 token 用户名

## 需求背景

前端/调用方在配置项目公共账号等场景时，需要校验用户填写的 gitee / gitcode / github token 是否有效，并获取该 token 对应的用户名（login），用于输入校验与回显。

当前 `ProjectServiceImpl` 在新增/修改项目公共账号时内部调用了三个平台工具类的 `getLoginByUserToken` 做解析，但没有对外暴露独立的校验入口，调用方无法单独校验 token。

关联业务 Issue：openlibing/openlibing-framework#115

## 功能描述

在 `openlibing-framework` 的 `ProjectController` 新增接口，接收平台类型（gitee / gitcode / github）与 token，复用 `Gitee` / `GitCode` / `GitHub` 工具类的 `getLoginByUserToken` 方法解析：

- token 有效：返回 token 对应的用户名
- token 无效或解析失败：返回明确的失败提示

**不做什么：**

- 不新增数据库表或字段
- 不修改现有 add-project / update-project 的 token 解析逻辑

## 验收标准

- [ ] 新增接口 `POST /project/parse-token-login`，JSON body 传 `platform` + `token`
- [ ] gitee / gitcode / github 三个平台的 token 均能正确解析并返回 login
- [ ] token、platform 为空或平台不支持时返回明确失败信息
- [ ] token 无效（解析返回空）时返回明确失败信息
- [ ] 补充单元测试，构建与相关测试通过

## 影响范围

- `openlibing-framework`
  - `business/controller/ProjectController.java`：新增接口
  - `business/service/ProjectService.java`：新增方法声明
  - `business/service/impl/ProjectServiceImpl.java`：新增方法实现
  - `business/dto/space/TokenParseDTO.java`：新增入参 DTO
  - `src/test/`：新增单元测试
