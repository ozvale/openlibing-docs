# openlibing-platform-release PR #251 发布文档

## 基本信息

| 项目 | 内容 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PR | [#251 fix(cve): 回调解析兼容大写字段名CVE，修复收集cve回调保存失败](https://gitcode.com/openlibing/openlibing-platform-release/merge_requests/251) |
| 仓库 | openlibing/openlibing-platform-release |
| 分支方向 | fork `yichenz0927:check_safe_202611` → 主仓 `release_20261117` |
| 关联 Issue | [#125 收集CVE步骤回调保存失败](https://gitcode.com/openlibing/openlibing-platform-release/issues/125) |
| 作者 | yichenz0927 |
| 标签 | ai-assisted |
| 状态 | 待合并（CI 流水线运行中） |
| 变更规模 | 2 commits / 2 files / +4 行 |
| 涉及提交 | `50d4cec2`、`3115cf55` |
| 发布日期 | 2026-11-17 |

## 变更背景

安全改造（issue #124）将收集 CVE 回调解析从 fastjson2 切换为 Jackson 后，生产环境"收集CVE"步骤回调保存失败，步骤状态一直卡在"执行中"。

**根因**：cve-manager 回调报文使用大写字段名 `"CVE"`，与实体 `CveAndBugfixModel` 的 `@JsonProperty("cve")` 大小写不匹配。原生 `new ObjectMapper()` 默认开启 `FAIL_ON_UNKNOWN_PROPERTIES`，`convertValue` 解析时抛出 `IllegalArgumentException`，被 catch 后统一转为"cve回调数据格式非法"，导致回调整体保存失败。

## 修复方案

为 cve 字段追加 `@JsonAlias("CVE")` 别名，Jackson 反序列化同时接受 `cve` 与 `CVE` 两种命名：

| 实体 | 提交 | 覆盖链路 |
| ------------------------------ | ---------- | -------------------------------------------------------- |
| `CveAndBugfixModel.cve` | `50d4cec2` | `ExternalinterfaceDelegateImpl` 与 `ManyframeworkExternalinterfaceDelegateImpl` 两条回调解析链路（均以该实体为反序列化目标） |
| `ManyFrameworkCveAndBugfixModel.cve` | `3115cf55` | 多框架实体防御性对齐，兼容潜在大写 `CVE` 报文（当前入参为前端小写契约） |

主名 `cve` 不变，序列化输出与既有 fastjson `@JSONField` 别名行为均不受影响。

## 影响范围

- 模块：`openeuler/entity/model`，仅实体注解追加（2 文件 +4 行）
- 无接口契约变化、无数据库 schema 变化、无配置变化
- 受益方法：`saveCveAndBugfixList`（两个 Delegate 中逻辑相同，一处实体注解同时生效）

## 验证情况

- 独立 demo 三场景对照验证：
  1. 无别名：复现 `Unrecognized field "CVE"` 解析失败
  2. 加 `@JsonAlias("CVE")`：解析成功（含 `score` 整数到 String 的隐式转换）
  3. 仅关闭严格校验（`FAIL_ON_UNKNOWN_PROPERTIES=false`）：不抛异常但 `cve=null` 数据丢失，故排除该方案
- 使用生产实体类编译产物 + 真实回调样例验证解析通过（`getCve()` 正确返回 `CVE-2024-56705`）
- 生产部署后待验证：重新触发收集 CVE 步骤，确认回调保存成功、步骤状态置为"执行成功"

## 发布注意事项

1. 部署 `3115cf55` 或之后版本生效。
2. 部署后若"收集CVE"步骤仍处于"执行中"（此前失败留下的旧状态），需按运维手册修改 MongoDB `jenkins_job_exec_status`：`startModule` 置为 `can_execute`、当前步骤拨回 `"1"` 后重新触发。
3. 修正该集合时间字段时必须使用 `ISODate()` 写入（实体为 `java.util.Date`，字符串覆盖会破坏 Spring Data 映射）。

## 风险评估

低风险：纯注解别名追加，无行为破坏面。极端情况下报文同时含 `cve` 与 `CVE` 字段时以小写主名为准（`@JsonProperty` 优先），行为符合预期。
