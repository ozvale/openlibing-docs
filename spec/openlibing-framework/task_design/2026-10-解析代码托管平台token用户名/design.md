# 解析代码托管平台 token 用户名 — 技术设计

## 方案概述

在 `ProjectController` 新增 `POST /project/parse-token-login` 接口，入参为 JSON body（`platform` + `token`）；`ProjectServiceImpl` 按平台路由到已注入的 `Gitee` / `GitCode` / `GitHub` 实例，调用其 `getLoginByUserToken` 方法解析用户名并返回。

## 架构决策

1. **复用现有工具类**：`getLoginByUserToken` 已封装各平台 API 调用与异常处理，直接复用，不新增 HTTP 调用逻辑。
2. **入参走 JSON body**：token 属敏感数据，避免出现在 URL/访问日志中。
3. **返回 `DataResult<String>`**：返回 token 对应的用户名；参数非法 / 平台不支持 / 解析失败时统一返回 `DataResult.failureMessage(...)`（与仓内多数 service 实现一致）。
4. **平台取值**：`gitee` / `gitcode` / `github`，入参用大小写不敏感正则 `(?i)^(gitee|gitcode|github)$` 校验，service 侧统一 `toLowerCase` 后路由。

## 接口定义

```
POST /project/parse-token-login
Content-Type: application/json

{
  "platform": "gitee",
  "token": "xxxxxxxx"
}
```

- 成功：`DataResult<String>`，`data` 为 token 对应用户名
- 失败：`DataResult` 返回失败码与提示（token/platform 为空、平台不支持、token 无效）

## 涉及文件

| 文件                                            | 操作 | 说明                                                           |
| ----------------------------------------------- | ---- | -------------------------------------------------------------- |
| `business/dto/space/ProjectTokenParseDTO.java`  | 新增 | 入参：platform（`@NotBlank`+`@Pattern`）、token（`@NotBlank`） |
| `business/controller/ProjectController.java`    | 修改 | 新增 `POST /project/parse-token-login`                         |
| `business/service/ProjectService.java`          | 修改 | 新增 `getLoginByToken(ProjectTokenParseDTO)` 声明              |
| `business/service/impl/ProjectServiceImpl.java` | 修改 | 实现平台路由与解析逻辑                                         |
| `src/test/.../ProjectServiceImplTest.java`      | 修改 | 补充各平台成功/失败用例                                        |

## 风险 & 缓解

- **敏感信息**：token 仅透传给平台 API，不落库、不打印日志；入参走 body 避免 URL 泄露。
- **外部接口依赖**：解析结果依赖平台可用性，工具类已对返回 null / 异常做兜底，接口统一返回"解析失败"。

## 跨仓影响

无。仅新增 `openlibing-framework` 对外接口，不改变现有契约。
