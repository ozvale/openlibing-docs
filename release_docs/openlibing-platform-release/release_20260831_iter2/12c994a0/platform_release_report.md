# openlibing-platform-release release_20260831_iter2 PR 报告

## PR 概览

| 项      | 值                                                                                        |
| ------- | ----------------------------------------------------------------------------------------- |
| PR      | [#202](https://gitcode.com/openlibing/openlibing-platform-release/merge_requests/202)     |
| 标题    | chore(release): 合入 dsq_202608_iter2 迭代变更至 release_20260831_iter2                   |
| 分支    | `dsq_202608_iter2` → `release_20260831_iter2`（fork: disiqi/openlibing-platform-release） |
| 作者    | disiqi                                                                                    |
| 状态    | merged                                                                                    |
| Commits | 29                                                                                        |
| 变更    | 23 files, +1135 / -92                                                                     |
| 标签    | ai-assisted, ci-pipeline-running                                                          |

## 关联 Issue 对照表

| issueID | issue名称                                                      | 责任人 | 评审结果 | 发布日期   |
| ------- | -------------------------------------------------------------- | ------ | -------- | ---------- |
| #67     | [缺陷]: 特性看板发布评审特性，发布评审平均完成时间指标数据异常 | disiqi | 通过     | 2026-08-31 |
| #66     | [缺陷]: 特性看板中发布评审特性数据采集时间和上报时间异常       | disiqi | 通过     | 2026-08-31 |

## 变更摘要

- fix: 修复定时任务看板数据上报与评审领域修改验证逻辑（关联 #66、#67）
- fix: 评审单操作日志区分保存/提交并新增字段可空变更集
- build: Apollo/Eureka 迁移 Nacos，升级 openlibing-common 至 1.0.20.1 / 20.5，补齐 prod 环境 nacos server-addr 端口号
- refactor: 移除 InternalAuthRequestInterceptor 内部鉴权拦截器
- ci: 接入 sca-pr-scan 与 malicious-code-pr-scan 流水线插件
- chore: pre-commit 以 gitleaks 替换 detect-secrets

## 测试计划

- [ ] 特性看板发布评审特性数据采集/上报时间正常，评审单个数类指标不再为 0（#66）
- [ ] 发布评审平均完成时间指标数据正常（#67）
- [ ] CI 流水线（sca-pr-scan / malicious-code-pr-scan）通过
