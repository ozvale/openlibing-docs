# filter-meta 组合扫描合并 — 实现任务

- 业务 Issue：openlibing/openlibing-cicd#569（Refs 关联）
- 模式：Standard；两仓同构实现（cicd 先行，coderepo 镜像）

## openlibing-cicd

- [x] 1. `LogPipelineMapper.java` + `LogPipelineMapper.xml` 新增 `selectFilterMetaCombo`
- [x] 2. `LoggingServiceImpl`：combo filter 构建（白名单交集 + 时间区间，维度值列表置空）
- [x] 3. `LoggingServiceImpl`：应用侧维度拆分聚合（skip 自身、其他维度严格 IN 过滤、空值跳过、计数累加、Locale.ROOT 归一）
- [x] 4. `toFilterMetaItems` 重载：接受 counts + 三级排序 comparator（selected 优先 → count DESC → value 升序）
- [x] 5. 熔断回退：combo 行数 == 10000 走旧逐维度路径；combo 仅在值维度 ≥2 时启用，超限校验前移
- [x] 6. 单测：拆分正确性（多维交叉过滤）、skip 自身语义、空值语义、排序/截断、熔断回退、moduleId 不回归
- [x] 7. 构建验证 + 增量覆盖率 ≥ 80%（实测 98.00%）

## openlibing-coderepo（镜像 1-7）

- [x] 8. `OperationLogMapper.java` + `OperationLogMapper.xml` 新增 `selectFilterMetaCombo`
- [x] 9. `LoggingServiceImpl` 同构改动（combo filter / 拆分聚合 / 重载排序 / 熔断回退）
- [x] 10. 单测同构 + 构建验证 + 增量覆盖率 ≥ 80%（实测 97.12%）

## 交付

- [x] 11. 两仓各 3 轮 commit（初版 + 两轮检视修复）push
- [x] 12. 用户自测/反馈循环
- [x] 13. 业务 PR（关联 #569，Refs，ai-assisted 标签）：cicd !715 / coderepo !365，均已合入
- [x] 14. spec 归档（本目录随 docs PR 提交，含 archive.md）
