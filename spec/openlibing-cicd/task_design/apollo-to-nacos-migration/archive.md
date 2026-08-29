# apollo-to-nacos-migration — 归档

## 关联

- FE 需求名称：自建apollo、eureka服务替换为华为云CSE服务（nacos）
- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/217
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pull/542（head: `migrate-apollo-to-nacos` → base: `release_20260820`）
- docs Issue: https://gitcode.com/openlibing/openlibing-docs/issues/143
- docs PR: https://gitcode.com/openlibing/openlibing-docs/pull/863

## 交付历程

- commit `ac0b6bef`：迁移主体——common 1.0.19.5 → 1.0.20.0，启动类去 Apollo 化 + SnapShotSwitch，beta/gama 两环境 Nacos 化，guava/StringUtils 替换，jakarta.ws.rs-api 补偿声明，application.yaml secure，start.sh 清理，UT 切片适配
- commit `484c221f`：prod profile 迁移——独立 CSE 实例 + `openlibing-prod` namespace
- commit `c1ab588f`：common 升级 1.0.20.1（Refs #203）
- commit `f4f5b568`：common 升级 1.0.20.4（最终版本）

改动体量：12 文件，约 +80/-28 行。

## 用户自测反馈

- 用户对"改动量近 100 行是否合理"存疑 → 通过与 codecheck 迁移完成态逐项对齐核验：codecheck 的主体迁移（cf6c48bd，78 行）被直接 commit 进 release 分支未走 PR，其 PR 322 仅含收尾 20 余行；cicd 将"主体 + 收尾"一次做完，100 行即为完整迁移的正确体量，核验结论"改动合理、无缺漏、无多余"。
- 无返工轮次。

## 最终验证

- 编译/UT：通过（PR 542 对应分支）
- 静态核验（head 分支全量 grep）：`com.ctrip.framework.apollo` 代码级引用零残留（仅 1 处 javadoc 注释提及，无害）；原生 `com.google.common` 零残留；`ConfigContextInitializer` 零残留；死配置/死常量确认仓库中不存在
- 对照核验：与 openlibing-codecheck 完成态（cf6c48bd + PR 322）逐项对齐，skill 清单迁移项全部覆盖且更完整（import 清理比 codecheck 更干净）

## 设计偏差与取舍

- 原计划（Phase 1 spec 草稿）暂不处理 `application-prod.yaml`，实施中追加 prod 迁移（独立 commit `484c221f`，可独立回滚），spec 已同步更新
- 原计划 common 目标版本 1.0.19.8，实施中随平台统一升级最终定在 1.0.20.4
- `jakarta.ws.rs-api:3.1.0` 为 skill 清单外的必要补偿：6 个业务文件直接依赖该包，原由 Apollo 传递提供，移除 Apollo 后必须显式声明

## 可复用经验

- 已沉淀于 `apollo-eureka-to-cse-nacos-migration` skill，本仓无需重复沉淀 ai_memory。补充一条 skill 未覆盖的经验：**Apollo 移除后需排查 `jakarta.ws.rs.*` 等传递依赖断裂**（该包此前由 apollo-client 传递引入，业务代码直接 import 但无显式声明）。

## 归档日期

2026-08-29
