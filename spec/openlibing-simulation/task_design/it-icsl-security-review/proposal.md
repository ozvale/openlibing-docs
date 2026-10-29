# IT-ICSL 安全送检专项排查（openlibing-simulation）

> 业务 Issue：https://gitcode.com/openlibing/openlibing-simulation/issues/48
> 迭代：2026.10（libing 9.2605.03-UR，10/20 ~ 10/29）
> 负责人：ligao963｜标签：`need_light`
> 性质：蓝区安全送检专项排查（需编码，免功能测试）

## 需求背景

为 11 月 IT-ICSL 安全认证送检做准备，对 `openlibing-simulation` 微服务做一轮完整的蓝区安全排查：
业务信息梳理 → 安全设计与威胁分析 → 两轮安全扫描 → 安全配置排查 → 安全专项排查，确保所有扫描
发现的问题修复并留证闭环。

代码侧整改已基本完成（分支 `fix-ip-or-hostname-validation`，master..HEAD 共 61 个提交，
102 个文件，+3606 / -5578），本 spec 用于把「Issue 要求」与「已交付代码 / 已有证据 / 未闭环项」
对齐，作为送检材料的版本化底稿。

## 功能描述

### 做什么

1. 按 Issue 的六大阶段整理交付物清单与证据台账；
2. 汇总代码侧已完成的安全整改项（CWE 类问题、输入校验、鉴权、日志、凭证、依赖、SSH）；
3. 明确第二轮扫描（截止 **10-30**）尚未闭环的项，并给出处理方式；
4. 把送检材料（威胁分析、架构说明书、通信矩阵、架构图等）纳入本文档目录统一管理。

### 不做什么

- 不做功能需求开发，不改变对外接口契约（除安全校验拒绝非法输入外）；
- 不覆盖 `openlibing-simulation` 之外的微服务；
- 不替代部门扫描工具本身，仅承接工具输出并做闭环管理。

## 验收标准

- [ ] 业务信息梳理：服务信息、API 清单、认证方式、数据流向四份材料齐备
- [ ] 安全设计及威胁分析：lowlevel 威胁分析、架构设计说明书、AI 威胁分析、通信矩阵、
      安全组网架构图、运维安全架构图 六份材料齐备
- [ ] 第一轮扫描：8 类工具（安全编译选项、SecBinaryCheck、nmap、墨菲/SC-SAST、SenInfo、
      C-Spider、SEC-SecEncryScan、开源合规）报告齐备
- [ ] 安全配置排查：注册中心、配置中心配置核查表齐备
- [ ] 安全专项排查：9 项 checklist 逐条有结论与证据
- [ ] 第二轮扫描：8 类工具全量重扫，第一轮问题全部闭环
- [ ] 所有扫描问题留存「问题 → 修复 commit → 复扫通过」证据链
- [ ] 代码侧最小验证通过（构建 + 相关单测；SpotBugs 0 issue）

## 影响范围

- 业务仓：`openlibing-simulation`（单仓，分支 `fix-ip-or-hostname-validation`）
- 文档仓：`openlibing-docs/spec/openlibing-simulation/`（本目录 + 既有 system_design / task_design）
- 运行环境：蓝区部署，无新增外部依赖；安全校验加严后，非法 IP / 非法路径 / 非法账号的请求
  会被 400 拒绝（属预期行为变化）
