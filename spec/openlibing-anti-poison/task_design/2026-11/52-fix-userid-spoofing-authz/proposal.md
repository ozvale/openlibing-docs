# 52-fix-userid-spoofing-authz — 需求背景与验收标准

## 背景

argus 漏洞挖掘确认（CWE-862，严重）：问题屏蔽申请（/shield/poisonApply）与审批（/shield/problemAudit）接口的 userId 取自 @RequestParam 可任意伪造；权限检查（versionDetailAuth、reviewerId 比对）依赖该自报 userId，攻击者可冒充审批者完成未授权审批或冒充他人提交屏蔽申请，破坏审计追溯。

关联业务 Issue：openlibing/openlibing-anti-poison#52

## 需求范围

- userId 改从服务端认证上下文（登录态/Token）解析，禁止信任客户端参数
- 审批人 reviewerId 不再取自客户端 paramModel.getUser()
- 屏蔽申请/审批链路操作者身份服务端化并落入审计记录

## 验收标准

- [x] 授权绕过已整改，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

身份来源变更涉及接口契约调整，需前端联动验证。
