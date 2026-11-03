# 代码检查页 Github 结果展示与处理适配 - 需求提案

## 1. 需求背景

代码检查页的静态告警功能目前只适配了 Gitee 与 GitCode（含 atomgit.com 别名域名）。平台开始接入 GitHub，GitHub 仓库的静态扫描结果（SARIF）需要与 GitCode Action 一样上报到 codecheck，并在代码检查页正常展示与处理。

GitHub Action 侧上报链路与 GitCode Action 完全一致，唯一差异是代码托管平台由 gitcode 变为 github。

关联 Issue：https://gitcode.com/openlibing/openlibing-codecheck/issues/397

## 2. 需求范围

后端 openlibing-codecheck：

1. 静态告警数据来源枚举新增 `GITHUB_ACTION`、`GITEE_ACTION`。
2. 接收上报接口 source 缺省时，按仓库地址解析出的平台自动推断来源，并记录告警日志，便于发现漏传 source 的上报方。
3. 平台识别支持 GitHub 仓库地址；保留内置关键字识别，并提供配置项扩展自定义域名（兼容 GitHub Enterprise 自定义域名）。
4. SARIF 文件下载的 OBS 域名白名单默认值扩展 GitHub Action 桶。
5. 上报入参显式传入的 repoType 与仓库地址解析结果不一致时拒绝，避免绕过接口伪造平台。
6. 静态告警实体、VO、DTO 的平台与来源字段说明同步更新。
7. 不新增必填配置项：OBS 白名单与域名关键字均有代码兜底值，Nacos 无需变更（后续若显式配置 OBS 白名单，需同时保留 gitcode 与 github 两个桶）。

不在本次范围：

- 前端 openlibing-web 改造（由前端同事依据后端提供的适配文档完成）。
- GitHub 账号映射（`user_info_github` 在 codecheck 仓无 mapper）。
- 代码检查详情页、问题屏蔽页的 GitHub 用户主页链接。
- 代码检查执行链路的 GitHub PR 文件获取与参数解析（`GithubPlate.getRepoFileContents` / `getParamModel`）。

## 3. 验收标准

1. GitHub 仓库上报 SARIF 后，`static_alarm_scan_run.repoType` 为 `github`；未显式传 source 时自动推断为 `GITHUB_ACTION`，并产生可追溯的告警日志。
2. 静态告警列表、详情、数量统计、筛选项能正确展示 GitHub 仓库数据，平台筛选项包含 `github`。
3. 屏蔽、取消屏蔽、指定责任人、清理、导出对 GitHub 仓库数据均可用。
4. 消失问题自动流转（已解决）与分支告警数推送对 GitHub 仓库生效。
5. repoType 与 repoUrl 不一致、source 非法或无法推断时，上报被拒绝并返回可读错误。
6. SARIF 从 GitHub Action 的 OBS 桶可正常下载；白名单外域名仍被拒绝。
7. 存量 GitCode / Gitee 上报行为不变（source 显式传入时完全不受影响）。
