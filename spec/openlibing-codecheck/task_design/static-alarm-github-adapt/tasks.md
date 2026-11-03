# 代码检查页 Github 结果展示与处理适配 - 实现任务

## 代码改造

- [x] `StaticAlarmSourceEnum` 新增 `GITHUB_ACTION`、`GITEE_ACTION`，新增 `inferByRepoType(String repoType)`
- [x] `StaticAlarmReceiveDTO` 删除 `DEFAULT_SOURCE_CODE` 常量，更新 `source`、`repoType` 字段注释
- [x] 新增 `RepoHostKeywordSettings`（`codecheck.repo-host-keywords`，Map，默认空）
- [x] `RepoUrlParser` 新增 `parse(String url, Map<String,String> extraHostKeywords)` / `isSameRepo(String, String, Map<String,String>)` 重载，内置关键字抽为常量
- [x] `RepoInfoCoordinateResolverImpl` 坐标反查使用带额外关键字的重载
- [x] `StaticAlarmReceiveServiceImpl`：
  - [x] 注入域名关键字配置
  - [x] repoType 与解析结果一致性校验
  - [x] source 缺省按平台推断 + WARN 日志；无法推断时拒绝
  - [x] 显式 source 与可推断平台不一致时仅 WARN，不拒绝入库
- [x] `SarifParseServiceImpl` OBS 白名单默认值增加 `openlibing-github-action.obs.cn-southwest-2.myhuaweicloud.com`
- [x] 实体 / VO / DTO 注释同步：repoType 增加 github，source 增加 GITHUB_ACTION / GITEE_ACTION

## 测试

- [x] 单测：github 仓库 + 未传 source → `repoType=github`、`source=GITHUB_ACTION`
- [x] 单测：gitee 仓库 + 未传 source → `source=GITEE_ACTION`；gitcode 仓库 → `GITCODE_ACTION`
- [x] 单测：显式传合法 source 保持原值；非法 source 抛异常
- [x] 单测：显式 source 与 repoType 可推断平台不一致时仍入库，source 保持显式值
- [x] 单测：repoType 与 repoUrl 不一致抛异常；未传 source 且平台无法推断（codehub）时拒绝入库
- [x] 单测：`RepoUrlParser` 额外域名关键字可识别自定义域名，未配置时行为不变
- [x] 单测：OBS 白名单 github 桶与 gitcode 桶均可下载；白名单域名的后缀拼接仿冒域名仍被拒绝
- [x] 运行静态告警相关单测与构建

## 交付

- [x] 生成前端适配文档（来源枚举、平台枚举、展示建议）到 `openlibing/api-docs/openlibing-codecheck/`
- [x] 汇总 Nacos 配置项与代码兜底值
- [x] 确认 `codecheck.alarm.obs-host-whitelist`、`codecheck.repo-host-keywords` 在 Nacos 均未配置，全部走代码兜底值，本次无需变更配置
- [x] 本地改动不提交，等待用户自测后触发后续 PR / 归档流程
