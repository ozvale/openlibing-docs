# 64-fix-redundant-interfaces — 需求背景与验收标准

## 背景

安全检查识别出 18 个疑似废弃接口（均未找到菜单配置），且普遍存在安全问题：多数无权限控制，可查询/操作任意项目或仓库数据（如 /releaseposion/posionChangeBoardData、/posion-pr/del/task 可删除任意扫描任务、/action-pr/scan 等），部分无审计日志记录（/shield/auditPassRevoke、/shield/problemAudit 等）。需确认废弃状态后删除冗余接口，或对仍在使用的接口整改安全问题。

关联业务 Issue：openlibing/openlibing-anti-poison#64

## 需求范围

- 逐个确认 18 个接口的废弃状态（菜单配置/调用方引用）
- 删除确认废弃的冗余接口（其中 4 个已在 remove-deprecated-apis（issue #71）工作中移除）
- 对仍在使用的接口补充权限控制与审计日志

## 验收标准

- [ ] 废弃接口全部移除，无悬挂引用残留（issue 仍 open，待验收）
- [ ] 保留接口具备权限控制与审计日志

## 风险

删除公开接口属破坏性变更，需确认无未知外部调用方。
