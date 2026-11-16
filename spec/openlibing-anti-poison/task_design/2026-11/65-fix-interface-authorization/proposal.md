# 65-fix-interface-authorization — 需求背景与验收标准

## 背景

antipoison 多个 web 接口资源权限控制不当，存在越权访问风险：/checkCenter/query/task 在 ExecutionStatus!=0 时直接用 branchid/repoid 查询数据、未校验关联性；/checkRule/add/rule/set 在规则集 id 存在时直接更新对应规则集、未校验其是否属于已鉴权的 projectid；/checkRule/query/rule/set/config 按规则集 id 查询自定义规则集、未校验 id 与 projectid 关系；/shield/getScanResult、/shield/get-scan-pr-result、/shield/get-scan-pr-result-group 直接根据前端参数查询、无权限控制。

关联业务 Issue：openlibing/openlibing-anti-poison#65

## 需求范围

- /checkCenter/query/task 补充 branchid/repoid 与操作用户的关联性校验
- 规则集新增/查询接口校验规则集 id 与 projectid 的归属关系
- /shield 三个结果查询接口补充权限控制

## 验收标准

- [x] 上述接口均完成越权校验，跨项目/仓库访问被拒绝（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

无。
