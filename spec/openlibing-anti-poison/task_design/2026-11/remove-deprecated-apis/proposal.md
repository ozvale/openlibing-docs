# remove-deprecated-apis — 需求背景与验收标准

## 背景

安全检查发现 4 个接口已废弃（无菜单配置引用），且无权限控制，可查询任意项目/仓库数据：

- `POST /posion-pr/query-pr-results`（查询任务列表）
- `POST /posion-pr/query-pr-results-detail`（查询扫描结果详情，代码中已标注 TODO 废弃接口）
- `GET /shield/getPoisoningSelect`（下拉列表）
- `GET /shield/get-pr-poisoning-select`（门禁扫描下拉列表）

关联业务 Issue：openlibing/openlibing-anti-poison#71

## 需求范围

- 删除上述 4 个接口的 controller 代码及对应单测用例、失效 import（Light 模式）
- service/operation 层方法本次保留（`queryResults`、`queryPRResultsDetail`、`getPoisoningSelect`、`getPRPoisoningSelect` 已成为无调用方代码，后续可再清理）
- 顺带修复 2 个分支遗留过期用例（测试 URL github.com 不在安全加固后的平台白名单内，改为 gitcode.com）

## 验收标准

- [x] 4 个接口从 controller 移除，编译通过（commit 3e76493）
- [x] 相关单测全部通过（PoisonPRControllerTest 4 + ProblemShieldControllerTest 35）
- [x] 其余接口（如 /query-pr-results-status）不受影响
- [x] 已随业务 PR openlibing/openlibing-anti-poison#139 合入 release_20261116_iter1

## 风险

破坏性变更：删除公开接口。已确认无菜单配置引用；若有未知外部调用方需同步通知。
