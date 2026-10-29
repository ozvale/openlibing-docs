# review-mongo-compensation — 实现任务

## 进度: 0/8 complete

- [ ] Task 1: Liquibase 迁移 `create-tbl-review-mongo-compensation.xml` + include 进 db.changelog.xml
- [ ] Task 2: 补偿表实体 `TblReviewMongoCompensation` + Mapper 接口 + XML
- [ ] Task 3: `ReviewMongoCompensationService(+Impl)`：persistCompensations（载荷扩展 JSON 序列化）/ replayPendingBatch（stale guard + 退避）
- [ ] Task 4: `ConfirmReviewServceImpl.executeUpdate` 同步重试 + 失败落补偿（updateIssueData 去 bulkOperations 参数）
- [ ] Task 5: `ReviewMongoCompensationSchedule` 定时任务（cron 可配置 + 分布式锁薄壳）
- [ ] Task 6: 单测 `ConfirmReviewServceImplTest`：MongoFailureTriggersCompensation / MongoRetryThenSuccess / 分页边界补偿覆盖
- [ ] Task 7: 单测 `ReviewMongoCompensationServiceImplTest` + `ReviewMongoCompensationScheduleTest`：重放成功/退避/stale/幂等/round-trip
- [ ] Task 8: 验证（`python scripts/run-mvn.py clean test` + checkstyle/pmd/spotbugs）+ 交付 commit
