# static-alarm-snapshot-count 归档

## 交付信息

| 项          | 值                                                                        |
| ----------- | ------------------------------------------------------------------------- |
| FE 需求名称 | 静态告警入湖快照字段                                                      |
| 业务仓      | openlibing/openlibing-codecheck                                           |
| 业务分支    | add-count-yym（base: master 460b4025）                                    |
| 业务 PR     | openlibing/openlibing-codecheck#314（open，base: release_20260831_iter2） |
| 业务提交    | e5d58197 → 2eca002c → b1ff0c94                                            |
| 规模        | 4 文件，+215/-9                                                           |
| CI          | ci-pipeline-passed                                                        |

## 结果摘要

scanRun 实体以 7 个存量快照字段（状态维度 3 + 级别维度 4）+ snapshot_computed 标记替换原增量死字段；扫描结束（SUCCESS/PARTIAL_SUCCESS）通过覆盖索引聚合（$match+$project+$group）一次计算写入。聚合失败不阻塞入库（null + computed=false），成功路径 0 计数统一填 0，语义区分清晰。

## 遗留事项

- 业务 PR #314 未关联业务 Issue（部门要求 PR 合入必须关联 Issue，合入前需补建/关联）。
- 本 spec 与 openlibing-cicd apollo-to-nacos-migration spec 合并于同一 docs PR（用户明确选择，图方便，属「范围一致」规则的例外情形）。

## 经验沉淀

- MongoDB $group 不为 0 计数组合产出文档：未命中维度字段保持 null，聚合成功路径需显式统一填 0，避免与失败路径（null + computed=false）语义混淆。
- 聚合管道通过 $project 限定字段可命中覆盖索引（无 FETCH），$group 内存占用与集合总量无关，适合大表按维度计数场景。
