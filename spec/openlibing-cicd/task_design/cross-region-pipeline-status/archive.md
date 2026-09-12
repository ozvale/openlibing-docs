# 【openlibing-cicd】黄蓝协同流水线状态查询接口 — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/52
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pull/556（源分支 cross_region）
- 目标分支: release_20260831_iter2

## 交付历程

| commit（完整 SHA）                         | 说明                                                           |
| ------------------------------------------ | -------------------------------------------------------------- |
| `d4090708bbccd6b98ffb145ec6a03d906a2fb994` | 新增获取黄蓝协同流水线状态信息接口（初版）                     |
| `6545d98ede2a788ecc561f5ccee981801c8a59f8` | 完善 YellowPipelineStatusVO 字段与 Service 耗时计算逻辑        |
| `f0cf69a636e0515ab427d8c8ebf649c176fbb80a` | 修订 DTO/VO 字段与枚举（新增 ALREADY_RUNNING 等）              |
| `ad5626b975a060a197a188f2b6de641d1c738542` | 修复 CrossRegionController/CrossRegionServiceImpl 代码格式问题 |

> 注：前三个 commit 的提交信息均为「新增获取黄蓝协同流水线状态信息接口」，表中「说明」按各 commit 实际变更内容归纳；短引用分别为
> d4090708b / 6545d98ed / f0cf69a63 / ad5626b97。

## 用户自测反馈

- 暂无线上用户自测记录。proposal 验收标准 9 项「通过」为归档时的代码静态核对结论（见下方设计偏差说明），非运行验证；线上功能验证待 release_20260831_iter2 发布后补充。

## 设计偏差与取舍

- **原计划 start.sh 新增 `-Dapollo.cache.file.enable=false` → 实际未落地**：分支合入 Apollo→Nacos 配置迁移（`6dc1f19a4a9ab4d4a55520ead8bba8d9cc922418`）后该参数已无意义，不随本功能交付
- 其余 spec 内容（接口、DTO/VO、Mapper SQL、枚举、@Deprecated）与最终实现一致；proposal 验收标准 9 项经代码逐项静态核对全部通过（归档时核对，未跑测试，与「最终验证」未执行项不冲突）

## 最终验证

- 编译: 通过（随 PR 556 合入 release_20260831_iter2，2026-09-01 merged，合入 CI 标签 ci-pipeline-passed）；归档时未在本地单独复跑构建
- 全量单元测试: 未执行（归档时未复跑，无运行记录；存量回归随 release 侧发布流程执行）
