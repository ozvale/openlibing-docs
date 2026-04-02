| issueID | issue名称             | 责任人  | 评审结果 |
|---------|---------------------|------|------|
| #14     | [需求]: Nightly流水线测试用例指标建设 | caoxiaolin | 通过   |




`job_id` varchar(32) NULL COMMENT '任务ID',
`step_id` varchar(32) NULL COMMENT '步骤ID',
`step_name` varchar(512) NULL COMMENT '步骤名称',
`step_status` varchar(16) NULL COMMENT '步骤状态',
`step_start_time` datetime NULL COMMENT '步骤开始时间',
`step_end_time` datetime NULL COMMENT '步骤结束时间',
`step_build_job_id` varchar(32) NULL COMMENT '步骤输入参数',
`step_daily_build_number` varchar(16) NULL COMMENT '日构建编号',
`testcase_job_id` varchar(64) NULL COMMENT '用例id（输入的jobId+日构建编号）'


job_id,
step_id,
step_name,
step_status,
step_start_time,
step_end_time,
step_build_job_id,
step_daily_build_number,
testcase_job_id,