# 流水线任务明细增加机器/资源池 — 实现任务

## 进度: 8/8 complete

- [x] 确认任务明细主表/接口与资源申请表口径：`dwi_rd_efc_resource_apply_info` + `npu_num > 0`；确认 codearts 申请 job_id 与统一 job_id 不一致
- [x] 确定数据获取方式：分页主查询后按当页 jobIds 批量查询（固定 3 次 SQL，避免 1:N JOIN 放大行数）
- [x] 实现 `queryJobMachines`：申请表过滤 `npu_num > 0`、codearts job_id 映射、机器维表取资源池、空 IP 过滤、按 IP 去重
- [x] 响应对象新增 `machines: [{serverIp, resourcePoolName}]`；空数组/null 池口径统一
- [x] Service 批量填充：按 `(pipeline_run_id, job_id)` 分组、同 IP 去重、IPv4 四段数值序排序
- [x] 补充单元测试：多机跨池配对、同 IP 去重、空白 IP、空池、非 IPv4 排序、null 结果、页内批量作用域、XML 结构与解耦断言
- [x] 质量门禁：定向单测 19/19、spotless、checkstyle（0 违规）、pmd、spotbugs 全部通过
- [x] 真实数据验证：codearts / gitcode 各一个 run，分页/total 不变、机器配对与数仓 SQL 一致；本地 8098 重启后验证通过

## 后续（不在本次范围）

- [ ] `openlibing-ops-web` 任务明细表格新增「机器/资源池」列（需前端仓包含 #294 的 `pr-pipeline-job-detail.vue`）
- [ ] 需求单交付属性/系统用户/前置条件等字段补齐；页面标注数据截止时间口径
